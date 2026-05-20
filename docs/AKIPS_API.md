# AKIPS REST API notes

This document summarises the AKIPS API endpoints the script uses and how to
verify connectivity.

---

## Authentication

AKIPS supports two authentication methods:

### HTTP Basic (username / password)

```
GET /api/query?...
Authorization: Basic <base64(username:password)>
```

### Bearer token (API key)

```
GET /api/query?...
Authorization: Bearer <api_key>
```

The script selects Bearer when `AKIPS_API_KEY` is set, otherwise falls back
to Basic.

---

## Endpoint used

```
GET /api/query
```

### Parameters

| Parameter | Description | Example |
|---|---|---|
| `function` | Query function type | `mib` |
| `mib` | MIB to query | `ALL`, `ENTITY-MIB` |
| `device` | Device filter — `*` for all | `*` or `core-sw-01` |
| `attribute` | Comma-separated attribute list | `sysDescr,sysName` |

### Example request

```
GET https://akips.corp.example.com/api/query
    ?function=mib
    &mib=ALL
    &device=*
    &attribute=sysDescr,sysName
```

---

## Response format

AKIPS can return either plain text or JSON depending on version.

### Text format (older AKIPS versions)

```
core-sw-01   10.1.0.1   sysDescr   Cisco IOS Software Version 12.2(55)SE12
core-sw-01   10.1.0.1   sysName    core-sw-01
```

Fields are whitespace-separated.  Values may contain spaces — the parser
splits on the first three whitespace boundaries only.

### JSON format (newer AKIPS versions)

```json
[
  {
    "device": "core-sw-01",
    "ip": "10.1.0.1",
    "attribute": "sysDescr",
    "value": "Cisco IOS Software Version 12.2(55)SE12"
  }
]
```

The script detects format automatically — it attempts JSON parsing first, then
falls back to text parsing.

---

## MIB attributes collected

| MIB | Attribute | Purpose |
|---|---|---|
| SNMPv2-MIB | `sysDescr` | OS/version string — primary source for version detection |
| SNMPv2-MIB | `sysName` | Device hostname |
| ENTITY-MIB | `entPhysicalModelName` | Hardware model string |
| ENTITY-MIB | `entPhysicalSoftwareRev` | Software revision (more reliable than sysDescr parsing) |

---

## Verifying AKIPS connectivity

```bash
# Check reachability (replace with your AKIPS URL)
curl -u admin:password \
  "https://akips.corp.example.com/api/query?function=mib&mib=ALL&device=*&attribute=sysName" \
  -k -s | head -20
```

A valid response lists hostnames, one per line.  If you see an HTML login
page, your credentials are wrong.  If you get a connection error, check
`AKIPS_HOST` and firewall rules (TCP 443 from the machine running the script).

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `Cannot connect to AKIPS` | Wrong host URL or firewall | Check `AKIPS_HOST` and network path |
| `401 Unauthorized` | Wrong credentials | Verify username/password or API key in AKIPS admin |
| `No devices returned` | API returns empty body | Try the `curl` test above; check AKIPS user permissions |
| Devices returned but no model/version | ENTITY-MIB not polled | In AKIPS, ensure ENTITY-MIB polling is enabled for those devices |
| Devices show `unknown` status | Model not in `PRODUCT_SLUG_MAP` | See [PRODUCT_SLUG_MAP.md](PRODUCT_SLUG_MAP.md) to add mappings |
