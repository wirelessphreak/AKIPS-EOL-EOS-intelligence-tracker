#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════╗
║           AKIPS EOL / EOS Intelligence Checker               ║
║  Collects device inventory from AKIPS, cross-references with ║
║  endoflife.date API, and exports a structured report.        ║
╚══════════════════════════════════════════════════════════════╝

Usage:
    # Live AKIPS connection
    python akips_eol_checker.py --host https://akips.corp.local \
        --username admin --password secret

    # Environment variable auth
    export AKIPS_HOST=https://akips.corp.local
    export AKIPS_USERNAME=admin
    export AKIPS_PASSWORD=secret
    python akips_eol_checker.py

    # Demo mode (no AKIPS needed)
    python akips_eol_checker.py --demo

    # Custom output paths
    python akips_eol_checker.py --demo --output-json report.json --output-csv report.csv

Dependencies:
    pip install requests tabulate
"""

import os
import re
import sys
import json
import csv
import argparse
from datetime import date, datetime
from typing import Optional
import urllib3

try:
    import requests
except ImportError:
    print("[ERROR] Missing dependency: pip install requests")
    sys.exit(1)

# Suppress SSL warnings (common in internal networks with self-signed certs)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# ─── CONFIGURATION ────────────────────────────────────────────────────────────

AKIPS_HOST     = os.getenv("AKIPS_HOST",     "https://your-akips-server")
AKIPS_USERNAME = os.getenv("AKIPS_USERNAME", "admin")
AKIPS_PASSWORD = os.getenv("AKIPS_PASSWORD", "")
AKIPS_API_KEY  = os.getenv("AKIPS_API_KEY",  "")   # If using API-key auth

EOL_API_BASE   = "https://endoflife.date/api"

# ── Map vendor/model keywords → endoflife.date product slugs ─────────────────
# Extend this dict to cover devices in your environment.
# Keys are lowercase substrings that may appear in the model/sysDescr fields.
# Values are the slug used at https://endoflife.date/api/{slug}.json
PRODUCT_SLUG_MAP: dict[str, dict[str, str]] = {
    "cisco": {
        "catalyst 9300": "cisco-catalyst-9300",
        "catalyst 9200": "cisco-catalyst-9200",
        "catalyst 9100": "cisco-catalyst-9100",
        "catalyst 3850": "cisco-catalyst-3850",
        "catalyst 3750": "cisco-catalyst-3750",
        "catalyst 2960": "cisco-catalyst-2960",
        "catalyst 2960x": "cisco-catalyst-2960x",
        "asr 1001": "cisco-asr-1001",
        "asr 1002": "cisco-asr-1002",
        "asr 1006": "cisco-asr-1001",
        "isr 4321": "cisco-isr-4321",
        "isr 4331": "cisco-isr-4331",
        "isr 4351": "cisco-isr-4351",
        "isr 4431": "cisco-isr-4431",
        "nexus 9300": "cisco-nexus-9000",
        "nexus 9500": "cisco-nexus-9000",
        "nexus 5000": "cisco-nexus-5000",
        "nexus 7000": "cisco-nexus-7000",
        "asa 5506": "cisco-asa-5500",
        "asa 5508": "cisco-asa-5500",
        "asa 5516": "cisco-asa-5500",
        "wlc 3504": "cisco-wlc-3504",
        "ios xe": "cisco-ios-xe",
        "ios-xe": "cisco-ios-xe",
        "ios": "cisco-ios",
        "nx-os": "cisco-nx-os",
    },
    "juniper": {
        "ex2300": "juniper-ex2300",
        "ex3300": "juniper-ex3300",
        "ex4300": "juniper-ex4300",
        "ex4600": "juniper-ex4600",
        "srx300": "juniper-srx300",
        "srx1500": "juniper-srx1500",
        "mx480": "juniper-mx",
        "mx960": "juniper-mx",
        "junos": "junos",
    },
    "aruba": {
        "2930": "aruba-2930",
        "3810": "aruba-3810",
        "6300": "aruba-cx-6300",
    },
    "fortinet": {
        "fortigate": "fortios",
        "fortios": "fortios",
    },
    "palo alto": {
        "pa-220": "panos",
        "pa-460": "panos",
        "pa-850": "panos",
        "pa-3220": "panos",
        "pan-os": "panos",
    },
    "f5": {
        "big-ip": "f5-big-ip",
        "tmos": "f5-big-ip",
    },
    "linux": {
        "ubuntu": "ubuntu",
        "debian": "debian",
        "centos": "centos",
        "rhel": "rhel",
        "red hat": "rhel",
    },
}


# ─── AKIPS CLIENT ─────────────────────────────────────────────────────────────

class AKIPSClient:
    """
    REST API client for AKIPS Network Management.

    AKIPS returns MIB data in newline-separated text format:
        device_name  ip_address  mib_object  value
    or in some versions as JSON.

    Authentication: HTTP Basic (username/password) or Bearer token (api_key).
    """

    def __init__(
        self,
        host: str,
        username: str = "",
        password: str = "",
        api_key: str = "",
        verify_ssl: bool = False,
    ):
        self.host = host.rstrip("/")
        self.session = requests.Session()
        self.session.verify = verify_ssl

        if api_key:
            self.session.headers["Authorization"] = f"Bearer {api_key}"
        elif username and password:
            self.session.auth = (username, password)

    # ── Public methods ────────────────────────────────────────────────────────

    def get_devices(self) -> list[dict]:
        """
        Fetch all IP devices from AKIPS with their sysDescr (OS/version string)
        and sysName (hostname).
        """
        print("[AKIPS] Fetching device list …")
        devices: list[dict] = []

        # Fetch sysDescr and sysName in one call
        raw = self._query(
            mib="ALL",
            device="*",
            attribute="sysDescr,sysName",
        )
        if raw is None:
            return []

        interim = self._parse_mib_response(raw)

        # Fetch hardware model strings from ENTITY-MIB (best effort)
        raw_model = self._query(
            mib="ENTITY-MIB",
            device="*",
            attribute="entPhysicalModelName,entPhysicalSoftwareRev",
        )
        model_data: dict[str, dict] = {}
        if raw_model:
            for entry in self._parse_mib_response(raw_model):
                host = entry["hostname"]
                if host not in model_data:
                    model_data[host] = {}
                model_data[host].update(entry)

        # Merge
        for dev in interim:
            host = dev["hostname"]
            dev["model"]    = model_data.get(host, {}).get("entphysicalmodelname", "")
            dev["sw_rev"]   = model_data.get(host, {}).get("entphysicalsoftwarerev", "")
            devices.append(dev)

        print(f"[AKIPS] Found {len(devices)} devices")
        return devices

    # ── Private helpers ───────────────────────────────────────────────────────

    def _query(self, mib: str, device: str, attribute: str) -> Optional[str]:
        """Execute a MIB query against the AKIPS API."""
        url = f"{self.host}/api/query"
        params = {
            "function":  "mib",
            "mib":       mib,
            "device":    device,
            "attribute": attribute,
        }
        try:
            resp = self.session.get(url, params=params, timeout=45)
            resp.raise_for_status()
            return resp.text
        except requests.exceptions.ConnectionError:
            print(f"[ERROR] Cannot connect to AKIPS at {self.host}. "
                  "Check AKIPS_HOST and network connectivity.")
        except requests.exceptions.HTTPError as e:
            print(f"[ERROR] AKIPS API returned {e.response.status_code}: {e}")
        except requests.RequestException as e:
            print(f"[ERROR] AKIPS request failed: {e}")
        return None

    def _parse_mib_response(self, raw: str) -> list[dict]:
        """
        Parse AKIPS MIB query output into a list of device dicts.

        AKIPS text format (whitespace-separated):
            device_name  ip_address  mib_attribute  value

        JSON format (some versions): list of {device, ip, attribute, value}
        """
        devices: dict[str, dict] = {}

        # Try JSON first
        try:
            data = json.loads(raw)
            if isinstance(data, list):
                for item in data:
                    hostname = item.get("device") or item.get("name") or "unknown"
                    if hostname not in devices:
                        devices[hostname] = {"hostname": hostname, "ip": item.get("ip", "")}
                    attr = item.get("attribute", "").lower().replace("-", "").replace(".", "")
                    devices[hostname][attr] = item.get("value", "")
            return list(devices.values())
        except (json.JSONDecodeError, KeyError):
            pass

        # Parse text/CSV format
        for line in raw.strip().splitlines():
            # Skip comment / blank lines
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            # Split on whitespace (AKIPS separates fields with spaces/tabs)
            parts = line.split(None, 3)
            if len(parts) < 4:
                continue

            hostname, ip, attribute, value = parts[0], parts[1], parts[2], parts[3]
            if hostname not in devices:
                devices[hostname] = {"hostname": hostname, "ip": ip}
            attr_key = attribute.lower().replace("-", "").replace(".", "")
            devices[hostname][attr_key] = value.strip()

        return list(devices.values())


# ─── ENDOFLIFE.DATE CLIENT ────────────────────────────────────────────────────

class EOLClient:
    """
    Client for the public endoflife.date REST API.
    See: https://endoflife.date/docs/api/
    """

    def __init__(self):
        self.session = requests.Session()
        self.session.headers["Accept"] = "application/json"
        self._cache: dict[str, list] = {}

    def get_all_products(self) -> list[str]:
        """Return the full list of product slugs tracked by endoflife.date."""
        try:
            r = self.session.get(f"{EOL_API_BASE}/all.json", timeout=15)
            r.raise_for_status()
            return r.json()
        except requests.RequestException as e:
            print(f"[EOL] Could not fetch product index: {e}")
            return []

    def get_cycles(self, slug: str) -> list[dict]:
        """Return all release cycles for a product slug (cached)."""
        if slug in self._cache:
            return self._cache[slug]

        try:
            r = self.session.get(f"{EOL_API_BASE}/{slug}.json", timeout=15)
            if r.status_code == 404:
                self._cache[slug] = []
                return []
            r.raise_for_status()
            data = r.json()
            self._cache[slug] = data
            return data
        except requests.RequestException as e:
            print(f"[EOL] Failed to fetch '{slug}': {e}")
            self._cache[slug] = []
            return []

    def best_cycle(self, slug: str, version: str) -> Optional[dict]:
        """Find the release cycle that best matches a version string."""
        cycles = self.get_cycles(slug)
        if not cycles:
            return None

        version_lower = version.lower()

        # 1. Exact match on cycle field
        for c in cycles:
            if str(c.get("cycle", "")).lower() == version_lower:
                return c

        # 2. Version starts with cycle (e.g. "17.3.5" matches cycle "17.3")
        for c in cycles:
            cycle_str = str(c.get("cycle", "")).lower()
            if cycle_str and version_lower.startswith(cycle_str):
                return c

        # 3. Partial match (cycle is a substring of version)
        for c in cycles:
            cycle_str = str(c.get("cycle", "")).lower()
            if cycle_str and cycle_str in version_lower:
                return c

        # 4. Fallback: return the first (latest) cycle
        return cycles[0] if cycles else None


# ─── DEVICE ENRICHMENT ────────────────────────────────────────────────────────

def parse_device_info(sys_descr: str, model: str = "", sw_rev: str = "") -> tuple[str, str, str]:
    """
    Extract (vendor, model_name, software_version) from raw MIB strings.
    Returns lowercase vendor for slug-map lookups.
    """
    combined = f"{sys_descr} {model} {sw_rev}".lower()

    # ── Vendor detection ──────────────────────────────────────────────────────
    vendor = "unknown"
    if "cisco" in combined:
        vendor = "cisco"
    elif "juniper" in combined or "junos" in combined:
        vendor = "juniper"
    elif "aruba" in combined or "hpe" in combined or "hp procurve" in combined:
        vendor = "aruba"
    elif "fortinet" in combined or "fortigate" in combined:
        vendor = "fortinet"
    elif "palo alto" in combined or "pan-os" in combined:
        vendor = "palo alto"
    elif "f5" in combined or "big-ip" in combined or "tmos" in combined:
        vendor = "f5"
    elif "ubuntu" in combined:
        vendor = "linux"
    elif "debian" in combined:
        vendor = "linux"
    elif "centos" in combined:
        vendor = "linux"
    elif "red hat" in combined or "rhel" in combined:
        vendor = "linux"

    # ── Model name ────────────────────────────────────────────────────────────
    model_name = model.strip() if model.strip() else "unknown"

    # Attempt to extract from sysDescr if not provided
    if model_name == "unknown" and vendor == "cisco":
        m = re.search(r"cisco\s+([\w\-]+(?:\s+[\w\-]+)?)", sys_descr, re.IGNORECASE)
        if m:
            model_name = m.group(1)

    # ── Software version ──────────────────────────────────────────────────────
    sw_version = "unknown"

    # Use entPhysicalSoftwareRev if available
    if sw_rev.strip() and sw_rev.strip().lower() not in ("", "unknown"):
        sw_version = sw_rev.strip()
    else:
        # Cisco IOS/IOS-XE: "Version 17.6.4"
        m = re.search(r"\bversion\s+([\d.a-z()]+)", sys_descr, re.IGNORECASE)
        if m:
            sw_version = m.group(1)

        # Junos: "Junos 21.4R3"
        m2 = re.search(r"\bjunos:?\s+([\d.A-Z\-]+)", sys_descr, re.IGNORECASE)
        if m2:
            sw_version = m2.group(1)

        # FortiOS: "FortiOS v7.0.12"
        m3 = re.search(r"fortios\s+v?([\d.]+)", sys_descr, re.IGNORECASE)
        if m3:
            sw_version = m3.group(1)

        # PAN-OS: "pan-os 10.1.6"
        m4 = re.search(r"pan-os\s+([\d.]+)", sys_descr, re.IGNORECASE)
        if m4:
            sw_version = m4.group(1)

    return vendor, model_name, sw_version


def resolve_slug(vendor: str, model: str, version: str) -> Optional[str]:
    """Map a vendor/model/version to an endoflife.date product slug."""
    vendor_map = PRODUCT_SLUG_MAP.get(vendor.lower(), {})
    if not vendor_map:
        return None

    search_text = f"{model} {version}".lower()

    for keyword, slug in vendor_map.items():
        if keyword in search_text:
            return slug

    return None


def _parse_date(raw) -> Optional[date]:
    """Convert various EOL date formats to a date object."""
    if raw is True:
        return date.today()      # API signals "already EOL" with boolean true
    if raw is False or raw is None:
        return None
    if isinstance(raw, str):
        for fmt in ("%Y-%m-%d", "%Y-%m", "%Y"):
            try:
                return datetime.strptime(raw, fmt).date()
            except ValueError:
                continue
    return None


def enrich(raw_devices: list[dict], eol_client: EOLClient) -> list[dict]:
    """
    Cross-reference raw AKIPS devices with endoflife.date data.
    Returns enriched device list with status, eolDate, eosDate, daysToEol, etc.
    """
    today = date.today()
    results: list[dict] = []

    total = len(raw_devices)
    for idx, dev in enumerate(raw_devices, 1):
        hostname = dev.get("hostname") or dev.get("sysname") or "unknown"
        if idx % 25 == 0 or idx == total:
            print(f"[EOL]  Enriching device {idx}/{total}: {hostname}")

        sys_descr = dev.get("sysdescr") or dev.get("sys_descr") or ""
        model     = dev.get("model")    or dev.get("entphysicalmodelname") or ""
        sw_rev    = dev.get("sw_rev")   or dev.get("entphysicalsoftwarerev") or ""

        vendor, model_name, sw_version = parse_device_info(sys_descr, model, sw_rev)
        slug = resolve_slug(vendor, model_name, sw_version)

        eol_date = eos_date = None
        days_to_eol = days_to_eos = None
        cycle_label = None

        if slug:
            cycle = eol_client.best_cycle(slug, sw_version)
            if cycle:
                cycle_label = cycle.get("cycle")
                eol_date    = _parse_date(cycle.get("eol"))
                # EOS can come from different fields depending on product
                eos_date = (
                    _parse_date(cycle.get("eoas"))      # end of active support
                    or _parse_date(cycle.get("eos"))    # end of security
                    or _parse_date(cycle.get("eoes"))   # end of extended support
                )
                if eol_date:
                    days_to_eol = (eol_date - today).days
                if eos_date:
                    days_to_eos = (eos_date - today).days

        # Determine status
        if days_to_eol is None:
            status = "unknown"
        elif days_to_eol <= 0:
            status = "eol"
        elif days_to_eol <= 180:
            status = "critical"
        elif days_to_eol <= 365:
            status = "warning"
        else:
            status = "ok"

        results.append({
            "hostname":       hostname,
            "ip":             dev.get("ip", ""),
            "location":       dev.get("location", ""),
            "vendor":         vendor.title(),
            "model":          model_name,
            "version":        sw_version,
            "productSlug":    slug,
            "eolCycle":       cycle_label,
            "eosDate":        eos_date.isoformat()  if eos_date  else None,
            "eolDate":        eol_date.isoformat()  if eol_date  else None,
            "daysToEos":      days_to_eos,
            "daysToEol":      days_to_eol,
            "status":         status,
        })

    return results


# ─── OUTPUT HELPERS ───────────────────────────────────────────────────────────

def print_summary(devices: list[dict]) -> None:
    """Print a formatted summary table to stdout."""
    try:
        from tabulate import tabulate
        _tabulate = tabulate
    except ImportError:
        # Minimal fallback renderer
        def _tabulate(rows, headers, tablefmt=None):
            widths = [max(len(str(h)), max((len(str(r[i])) for r in rows), default=0))
                      for i, h in enumerate(headers)]
            sep  = "+" + "+".join("-" * (w + 2) for w in widths) + "+"
            hdr  = "|" + "|".join(f" {str(h).ljust(w)} " for h, w in zip(headers, widths)) + "|"
            lines = [sep, hdr, sep]
            for row in rows:
                lines.append("|" + "|".join(f" {str(v).ljust(w)} " for v, w in zip(row, widths)) + "|")
            lines.append(sep)
            return "\n".join(lines)

    headers = ["HOSTNAME", "IP", "VENDOR", "MODEL", "VERSION", "EOS DATE", "EOL DATE", "DAYS TO EOL", "STATUS"]
    rows = []

    for d in sorted(devices, key=lambda x: (x["status"] in ("unknown",), x.get("daysToEol") or 9999)):
        rows.append([
            d["hostname"],
            d["ip"]       or "—",
            d["vendor"],
            d["model"],
            d["version"],
            d["eosDate"]  or "N/A",
            d["eolDate"]  or "N/A",
            d["daysToEol"] if d["daysToEol"] is not None else "N/A",
            d["status"].upper(),
        ])

    print("\n" + _tabulate(rows, headers=headers, tablefmt="grid"))


def export_json(devices: list[dict], path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(devices, f, indent=2, default=str)
    print(f"[OK] JSON report → {path}  ({len(devices)} devices)")


def export_csv(devices: list[dict], path: str) -> None:
    if not devices:
        return
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(devices[0].keys()))
        writer.writeheader()
        writer.writerows(devices)
    print(f"[OK] CSV  report → {path}  ({len(devices)} devices)")


# ─── DEMO DATA ────────────────────────────────────────────────────────────────

DEMO_DEVICES: list[dict] = [
    {"hostname": "core-sw-01.nyc",  "ip": "10.1.0.1",  "sys_descr": "Cisco IOS Software, Version 12.2(55)SE12",       "model": "Catalyst 3750-48PS",   "sw_rev": ""},
    {"hostname": "core-sw-02.nyc",  "ip": "10.1.0.2",  "sys_descr": "Cisco IOS XE Software, Version 17.9.4a",         "model": "Catalyst 9300-48P",    "sw_rev": "17.9.4a"},
    {"hostname": "dist-fw-01.nyc",  "ip": "10.2.0.1",  "sys_descr": "Cisco Adaptive Security Appliance Version 9.12.4","model": "ASA 5506-X",           "sw_rev": ""},
    {"hostname": "edge-rtr-01.nyc", "ip": "10.3.0.1",  "sys_descr": "Cisco IOS XE Software, Version 17.6.4",          "model": "ISR 4331",             "sw_rev": ""},
    {"hostname": "edge-rtr-02.lax", "ip": "10.3.0.2",  "sys_descr": "Cisco IOS XE Software, Version 16.9.8",          "model": "ISR 4321",             "sw_rev": ""},
    {"hostname": "vpn-gw-01.lax",   "ip": "10.4.0.1",  "sys_descr": "Palo Alto Networks PAN-OS 10.1.6",               "model": "PA-220",               "sw_rev": ""},
    {"hostname": "vpn-gw-02.lax",   "ip": "10.4.0.2",  "sys_descr": "Palo Alto Networks PAN-OS 11.0.2",               "model": "PA-460",               "sw_rev": ""},
    {"hostname": "fw-01.chi",       "ip": "10.5.0.1",  "sys_descr": "Fortinet FortiGate 60F FortiOS v7.0.12",         "model": "FortiGate 60F",        "sw_rev": ""},
    {"hostname": "fw-02.chi",       "ip": "10.5.0.2",  "sys_descr": "Fortinet FortiGate 100D FortiOS v6.0.14",        "model": "FortiGate 100D",       "sw_rev": ""},
    {"hostname": "core-sw-03.chi",  "ip": "10.6.0.1",  "sys_descr": "Juniper Networks EX3300 Junos 18.4R3-S9",        "model": "EX3300-48T",           "sw_rev": "18.4R3-S9"},
    {"hostname": "dist-sw-02.chi",  "ip": "10.6.0.2",  "sys_descr": "Juniper Networks EX4300 Junos 21.4R3",           "model": "EX4300-48T",           "sw_rev": "21.4R3"},
    {"hostname": "lb-01.nyc",       "ip": "10.7.0.1",  "sys_descr": "F5 Networks BIG-IP Version 15.1.5",              "model": "BIG-IP 2200s",         "sw_rev": ""},
    {"hostname": "lb-02.nyc",       "ip": "10.7.0.2",  "sys_descr": "F5 Networks BIG-IP Version 17.1.0",              "model": "BIG-IP 4000s",         "sw_rev": ""},
    {"hostname": "wlc-01.nyc",      "ip": "10.8.0.1",  "sys_descr": "Cisco WLC 3504 Version 8.10.150.0",              "model": "WLC 3504",             "sw_rev": ""},
    {"hostname": "mgmt-sw-01.nyc",  "ip": "10.9.0.1",  "sys_descr": "HP ProCurve Switch 2910al-48G W.15.18",          "model": "ProCurve 2910al",      "sw_rev": ""},
]


# ─── CLI ENTRY POINT ──────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="AKIPS EOL/EOS Checker — cross-reference your network inventory with endoflife.date",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--host",        default=AKIPS_HOST,     help="AKIPS server URL  (or set AKIPS_HOST)")
    parser.add_argument("--username",    default=AKIPS_USERNAME,  help="AKIPS username   (or set AKIPS_USERNAME)")
    parser.add_argument("--password",    default=AKIPS_PASSWORD,  help="AKIPS password   (or set AKIPS_PASSWORD)")
    parser.add_argument("--api-key",     default=AKIPS_API_KEY,   help="AKIPS API key    (or set AKIPS_API_KEY)")
    parser.add_argument("--demo",        action="store_true",     help="Use built-in demo data (no AKIPS needed)")
    parser.add_argument("--no-ssl-verify", action="store_true",   help="Disable SSL verification (default: off)")
    parser.add_argument("--output-json", default="eol_report.json", help="JSON output path (default: eol_report.json)")
    parser.add_argument("--output-csv",  default="eol_report.csv",  help="CSV  output path (default: eol_report.csv)")
    parser.add_argument("--eol-warn-days", type=int, default=365,   help="Days threshold for warnings (default: 365)")
    args = parser.parse_args()

    banner = """
╔══════════════════════════════════════════════════════════════╗
║           AKIPS EOL / EOS Intelligence Checker               ║
╚══════════════════════════════════════════════════════════════╝"""
    print(banner)

    # ── Step 1: Collect devices ───────────────────────────────────────────────
    if args.demo:
        print("\n[INFO] Demo mode — using built-in sample devices")
        raw_devices = DEMO_DEVICES
    else:
        print(f"\n[INFO] Connecting to AKIPS → {args.host}")
        client = AKIPSClient(
            host=args.host,
            username=args.username,
            password=args.password,
            api_key=args.api_key,
            verify_ssl=not args.no_ssl_verify,
        )
        raw_devices = client.get_devices()
        if not raw_devices:
            print("[WARN] No devices returned from AKIPS. Try --demo to test the pipeline.")
            sys.exit(0)

    # ── Step 2: Enrich with EOL data ──────────────────────────────────────────
    print(f"\n[INFO] Fetching EOL data from {EOL_API_BASE} for {len(raw_devices)} devices …")
    eol_client = EOLClient()
    devices = enrich(raw_devices, eol_client)

    # ── Step 3: Summary ───────────────────────────────────────────────────────
    counts = {s: sum(1 for d in devices if d["status"] == s)
              for s in ("eol", "critical", "warning", "ok", "unknown")}

    print(f"""
┌─────────────────────────────────────┐
│           SUMMARY                   │
├─────────────────────────────────────┤
│  Total devices   : {len(devices):>5}              │
│  End of Life     : {counts['eol']:>5}  ← immediate risk  │
│  Critical (<180d): {counts['critical']:>5}              │
│  Warning  (<365d): {counts['warning']:>5}              │
│  Supported       : {counts['ok']:>5}              │
│  No EOL data     : {counts['unknown']:>5}              │
└─────────────────────────────────────┘""")

    # ── Step 4: Print table ───────────────────────────────────────────────────
    print_summary(devices)

    # ── Step 5: Export ────────────────────────────────────────────────────────
    print()
    export_json(devices, args.output_json)
    export_csv(devices,  args.output_csv)

    print(f"""
[NEXT STEPS]
  1. Open the dashboard:  Load {args.output_json} into the EOL Intelligence Dashboard
  2. Filter by status:    Use the status toggles and EOL slider
  3. View the timeline:   Switch to Timeline view for a Gantt-style overview
  4. Update slug map:     Edit PRODUCT_SLUG_MAP in this script to cover your devices
""")


if __name__ == "__main__":
    main()
