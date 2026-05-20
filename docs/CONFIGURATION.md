# Configuration reference

This document covers every configuration option available in
`akips_eol_checker.py`.

---

## Environment variables

Set these in your shell, in a `.env` file, or in your CI/CD secrets.

| Variable | Required | Description | Example |
|---|---|---|---|
| `AKIPS_HOST` | Yes (unless `--demo`) | Full URL of your AKIPS server including scheme | `https://akips.corp.example.com` |
| `AKIPS_USERNAME` | One of these two | AKIPS login username | `netops` |
| `AKIPS_PASSWORD` | One of these two | AKIPS login password | `S3cret!` |
| `AKIPS_API_KEY` | (alternative) | API key — takes precedence over username/password | `eyJhbGci…` |

### Loading a `.env` file

```bash
# Option A — export each variable manually
export AKIPS_HOST=https://akips.corp.example.com
export AKIPS_USERNAME=netops
export AKIPS_PASSWORD=S3cret!

# Option B — export all from .env file (bash/zsh)
export $(grep -v '^#' .env | xargs)

# Option C — use python-dotenv
pip install python-dotenv
# Then prepend to your script or use the CLI wrapper below
```

---

## Command-line flags

Flags override environment variables.

| Flag | Default | Description |
|---|---|---|
| `--host` | `$AKIPS_HOST` | AKIPS server URL |
| `--username` | `$AKIPS_USERNAME` | AKIPS username |
| `--password` | `$AKIPS_PASSWORD` | AKIPS password |
| `--api-key` | `$AKIPS_API_KEY` | AKIPS API key |
| `--demo` | off | Use built-in demo devices instead of querying AKIPS |
| `--no-ssl-verify` | off | Disable TLS certificate validation (self-signed certs) |
| `--output-json` | `eol_report.json` | Path for JSON output file |
| `--output-csv` | `eol_report.csv` | Path for CSV output file |
| `--eol-warn-days` | `365` | Devices with fewer than this many days to EOL get `warning` status |

---

## Status thresholds

Status is assigned by `daysToEol`:

| Status | Condition |
|---|---|
| `eol` | `daysToEol <= 0` — device is already past end-of-life |
| `critical` | `0 < daysToEol <= 180` — less than 6 months remaining |
| `warning` | `180 < daysToEol <= eol_warn_days` — within warning window |
| `ok` | `daysToEol > eol_warn_days` — supported and not near EOL |
| `unknown` | EOL date could not be determined |

Change the warning window with `--eol-warn-days`:

```bash
# Warn me about anything expiring within 2 years
python src/akips_eol_checker.py --eol-warn-days 730
```

---

## SSL / TLS

AKIPS installations commonly use self-signed certificates.  SSL warnings are
suppressed by default (via `urllib3.disable_warnings`).  Certificate
verification is **off** by default when connecting to AKIPS — to enable it
remove the `verify_ssl=False` default from `AKIPSClient.__init__` or pass
`verify='/path/to/ca-bundle.crt'` in code.

For the `endoflife.date` API (public internet), the system trust store is
used and verification is always on.

---

## Proxy

If your environment requires a proxy to reach `endoflife.date`, set standard
environment variables before running:

```bash
export HTTPS_PROXY=http://proxy.corp.example.com:3128
export NO_PROXY=akips.corp.example.com
python src/akips_eol_checker.py
```

`requests` respects these automatically.
