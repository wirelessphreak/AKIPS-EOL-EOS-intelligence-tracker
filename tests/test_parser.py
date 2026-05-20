"""
Unit tests for parse_device_info(), resolve_slug(), and _parse_date().

Run with:  python -m pytest tests/ -v
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from datetime import date
from akips_eol_checker import parse_device_info, resolve_slug, _parse_date


# ─── parse_device_info ────────────────────────────────────────────────────────

class TestParseDeviceInfo:
    def test_cisco_ios_xe(self):
        descr = "Cisco IOS XE Software, Version 17.9.4a, RELEASE SOFTWARE"
        vendor, model, version = parse_device_info(descr, "Catalyst 9300-48P", "")
        assert vendor == "cisco"
        assert "9300" in model
        assert "17.9.4a" in version

    def test_cisco_ios_legacy(self):
        descr = "Cisco IOS Software, Version 12.2(55)SE12, RELEASE SOFTWARE"
        vendor, model, version = parse_device_info(descr, "Catalyst 3750-48PS", "")
        assert vendor == "cisco"
        assert "12.2(55)SE12" in version

    def test_junos_version(self):
        descr = "Juniper Networks EX4300 Junos 21.4R3"
        vendor, model, version = parse_device_info(descr, "EX4300-48T", "21.4R3")
        assert vendor == "juniper"
        assert version == "21.4R3"

    def test_fortios_version(self):
        descr = "Fortinet FortiGate 60F FortiOS v7.0.12"
        vendor, model, version = parse_device_info(descr, "FortiGate 60F", "")
        assert vendor == "fortinet"
        assert "7.0.12" in version

    def test_panos_version(self):
        descr = "Palo Alto Networks PAN-OS 10.1.6"
        vendor, model, version = parse_device_info(descr, "PA-220", "")
        assert vendor == "palo alto"
        assert "10.1.6" in version

    def test_f5_vendor(self):
        descr = "F5 Networks BIG-IP Version 15.1.5"
        vendor, model, version = parse_device_info(descr, "BIG-IP 2200s", "")
        assert vendor == "f5"

    def test_unknown_vendor(self):
        descr = "Some Unknown Device v1.2.3"
        vendor, _, _ = parse_device_info(descr, "", "")
        assert vendor == "unknown"

    def test_sw_rev_takes_priority(self):
        descr = "Cisco IOS XE Software, Version 17.6.4"
        vendor, model, version = parse_device_info(descr, "ISR 4331", "17.9.4a")
        # sw_rev should win over sysDescr parsing
        assert version == "17.9.4a"


# ─── resolve_slug ─────────────────────────────────────────────────────────────

class TestResolveSlug:
    def test_catalyst_9300(self):
        slug = resolve_slug("cisco", "Catalyst 9300-48P", "17.9.4a")
        assert slug == "cisco-catalyst-9300"

    def test_catalyst_3750(self):
        slug = resolve_slug("cisco", "Catalyst 3750-48PS", "12.2(55)SE12")
        assert slug == "cisco-catalyst-3750"

    def test_ios_xe_fallback(self):
        slug = resolve_slug("cisco", "Unknown Cisco Device", "ios xe 17.3")
        assert slug == "cisco-ios-xe"

    def test_junos(self):
        slug = resolve_slug("juniper", "EX4300-48T", "junos 21.4R3")
        assert slug == "juniper-ex4300"

    def test_fortios(self):
        slug = resolve_slug("fortinet", "FortiGate 60F", "fortios 7.0.12")
        assert slug == "fortios"

    def test_unknown_vendor_returns_none(self):
        slug = resolve_slug("unknown", "SomeDevice", "v1.0")
        assert slug is None

    def test_unrecognised_model_returns_none(self):
        slug = resolve_slug("cisco", "Completely Unknown Model XYZ", "99.0")
        assert slug is None


# ─── _parse_date ─────────────────────────────────────────────────────────────

class TestParseDate:
    def test_iso_date(self):
        result = _parse_date("2026-09-30")
        assert result == date(2026, 9, 30)

    def test_year_month(self):
        result = _parse_date("2024-06")
        assert result == date(2024, 6, 1)

    def test_year_only(self):
        result = _parse_date("2025")
        assert result == date(2025, 1, 1)

    def test_true_means_today(self):
        result = _parse_date(True)
        assert result == date.today()

    def test_false_means_none(self):
        assert _parse_date(False) is None

    def test_none_means_none(self):
        assert _parse_date(None) is None

    def test_invalid_string(self):
        assert _parse_date("not-a-date") is None
