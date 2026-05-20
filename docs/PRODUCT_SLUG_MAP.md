# Product slug map reference

`PRODUCT_SLUG_MAP` is the dictionary in `src/akips_eol_checker.py` that maps
vendor/model/version substrings to [endoflife.date](https://endoflife.date)
product slugs.  This is the most important thing to customise for your
environment.

---

## How matching works

For each device the script builds a search string:

```
search = f"{model} {version}".lower()
```

It then iterates over the entries under the detected vendor key.  The first
entry whose keyword is a **substring** of `search` wins.

Example:

```python
vendor = "cisco"
search = "catalyst 9300-48p 17.9.4a"

# Checked in order:
"catalyst 9300" in search  →  True  →  slug = "cisco-catalyst-9300"  ✓
```

Keywords are checked in **insertion order**, so put more specific keywords
before less specific ones:

```python
"cisco": {
    "catalyst 9300-48uxm": "cisco-catalyst-9300",  # more specific first
    "catalyst 9300":       "cisco-catalyst-9300",  # fallback
    ...
}
```

---

## Finding a slug

1. Browse [endoflife.date](https://endoflife.date)
2. Search or scroll to your product
3. Copy the last path segment of the URL

Examples:

| Product page URL | Slug |
|---|---|
| `https://endoflife.date/cisco-catalyst-9300` | `cisco-catalyst-9300` |
| `https://endoflife.date/fortios` | `fortios` |
| `https://endoflife.date/junos` | `junos` |
| `https://endoflife.date/f5-big-ip` | `f5-big-ip` |

---

## Current mappings

### Cisco

| Keyword | Slug |
|---|---|
| `catalyst 9300` | `cisco-catalyst-9300` |
| `catalyst 9200` | `cisco-catalyst-9200` |
| `catalyst 3850` | `cisco-catalyst-3850` |
| `catalyst 3750` | `cisco-catalyst-3750` |
| `catalyst 2960` | `cisco-catalyst-2960` |
| `asr 1001` / `asr 1002` / `asr 1006` | `cisco-asr-1001` |
| `isr 4321` / `isr 4331` / `isr 4351` / `isr 4431` | `cisco-isr-43xx` |
| `nexus 9300` / `nexus 9500` | `cisco-nexus-9000` |
| `nexus 5000` | `cisco-nexus-5000` |
| `nexus 7000` | `cisco-nexus-7000` |
| `asa 5506` / `asa 5508` / `asa 5516` | `cisco-asa-5500` |
| `ios xe` / `ios-xe` | `cisco-ios-xe` |
| `ios` | `cisco-ios` |
| `nx-os` | `cisco-nx-os` |

### Juniper

| Keyword | Slug |
|---|---|
| `ex2300` | `juniper-ex2300` |
| `ex3300` | `juniper-ex3300` |
| `ex4300` | `juniper-ex4300` |
| `ex4600` | `juniper-ex4600` |
| `srx300` | `juniper-srx300` |
| `srx1500` | `juniper-srx1500` |
| `mx480` / `mx960` | `juniper-mx` |
| `junos` | `junos` |

### Fortinet

| Keyword | Slug |
|---|---|
| `fortigate` / `fortios` | `fortios` |

### Palo Alto

| Keyword | Slug |
|---|---|
| `pa-220` / `pa-460` / `pa-850` / `pa-3220` | `panos` |
| `pan-os` | `panos` |

### F5

| Keyword | Slug |
|---|---|
| `big-ip` / `tmos` | `f5-big-ip` |

### Aruba / HPE

| Keyword | Slug |
|---|---|
| `2930` | `aruba-2930` |
| `3810` | `aruba-3810` |
| `6300` | `aruba-cx-6300` |

### Linux

| Keyword | Slug |
|---|---|
| `ubuntu` | `ubuntu` |
| `debian` | `debian` |
| `centos` | `centos` |
| `rhel` / `red hat` | `rhel` |

---

## Adding a new mapping

### In the script

Open `src/akips_eol_checker.py` and find `PRODUCT_SLUG_MAP`:

```python
PRODUCT_SLUG_MAP: dict[str, dict[str, str]] = {
    "cisco": {
        ...
        "catalyst 1000": "cisco-catalyst-1000",   # ← add here
    },
    # Add an entirely new vendor:
    "arista": {
        "eos": "arista-eos",
    },
}
```

### Adding a new vendor

Vendor detection happens in `parse_device_info()` using `sysDescr` / `model`
substring matching.  Add your vendor to that function too:

```python
elif "arista" in combined:
    vendor = "arista"
```

---

## Debugging slug resolution

Add a temporary print to `enrich()` to trace what is being matched:

```python
print(f"DEBUG  {hostname}  vendor={vendor}  model={model_name}  "
      f"version={sw_version}  slug={slug}")
```

Or run with a single known device in demo mode:

```bash
python src/akips_eol_checker.py --demo 2>&1 | grep DEBUG
```
