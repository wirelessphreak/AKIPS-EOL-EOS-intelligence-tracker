# AKIPS EOL / EOS Intelligence Tracker

> Automatically cross-reference your AKIPS network device inventory against
> public end-of-life and end-of-sale data — then visualise the results in a
> rich interactive dashboard.

---

## Table of contents

- [Overview](#overview)
- [Features](#features)
- [Screenshots](#screenshots)
- [Architecture](#architecture)
- [Quick start](#quick-start)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Dashboard](#dashboard)
- [Extending the product map](#extending-the-product-map)
- [API reference](#api-reference)
- [Contributing](#contributing)
- [License](#license)

---

## Overview

Network devices that have reached **end-of-life (EOL)** no longer receive
security patches.  Devices approaching **end-of-sale (EOS)** need to be in
the procurement pipeline now.  Keeping track of this across hundreds of
devices is tedious — this project automates it.

```
AKIPS REST API  ──►  akips_eol_checker.py  ──►  eol_report.json
                              │
                              ▼
                    endoflife.date  API
                              │
                              ▼
              EOL Intelligence Dashboard  (HTML)
```

The Python script pulls every device, model, and software version from AKIPS,
enriches each record with lifecycle dates from the public
[endoflife.date](https://endoflife.date) API, and writes a structured
`eol_report.json`.  The companion HTML dashboard lets you explore the data
with table and Gantt-timeline views, vendor filters, status badges, and an
EOL-proximity slider.

---

## Features

| Category | Details |
|---|---|
| **Data collection** | Queries AKIPS via REST API — `sysDescr`, `sysName`, `entPhysicalModelName`, `entPhysicalSoftwareRev` |
| **EOL enrichment** | Calls `endoflife.date` for every recognised device/OS/version |
| **Status classification** | `eol` · `critical` (< 180 d) · `warning` (< 365 d) · `ok` · `unknown` |
| **Exports** | JSON + CSV reports for downstream tooling |
| **Dashboard — table view** | Sortable columns, vendor filter, status chip filters |
| **Dashboard — timeline view** | Gantt-style chart with colour-coded EOL windows |
| **Proximity slider** | Instantly filter devices by how many days remain until EOL |
| **Demo mode** | Built-in sample data — no AKIPS credentials required |
| **Extensible** | Add any vendor/model → slug mapping in < 1 minute |

---

## Screenshots

### Table view
![Table view showing devices sorted by days-to-EOL with status badges](docs/images/screenshot-table.png)

### Timeline (Gantt) view
![Gantt chart showing EOL windows for all devices](docs/images/screenshot-timeline.png)

> Screenshots are illustrative.  Run with `--demo` to see the live dashboard.

---

## Architecture

```
akips-eol-tracker/
├── src/
│   └── akips_eol_checker.py   # Core script — AKIPS client, EOL enrichment, CLI
├── docs/
│   ├── CONFIGURATION.md       # Full config reference
│   ├── AKIPS_API.md           # AKIPS REST API notes
│   ├── ENDOFLIFE_API.md       # endoflife.date API notes
│   ├── PRODUCT_SLUG_MAP.md    # How to extend vendor/model mappings
│   └── DASHBOARD.md           # Dashboard usage guide
├── tests/
│   └── test_parser.py         # Unit tests for parse helpers
├── examples/
│   └── eol_report.sample.json # Sample output for dashboard testing
├── .github/
│   ├── ISSUE_TEMPLATE/
│   │   ├── bug_report.md
│   │   └── feature_request.md
│   └── workflows/
│       └── ci.yml             # GitHub Actions — lint + test
├── requirements.txt
├── .env.example
├── .gitignore
├── CONTRIBUTING.md
├── CHANGELOG.md
└── LICENSE
```

---

## Quick start

```bash
# 1 — Clone
git clone https://github.com/YOUR_ORG/akips-eol-tracker.git
cd akips-eol-tracker

# 2 — Install dependencies
pip install -r requirements.txt

# 3 — Try with demo data (no AKIPS credentials needed)
python src/akips_eol_checker.py --demo

# 4 — Open eol_report.json in the dashboard
#     Paste the contents of dashboard/index.html into a browser,
#     or serve it:  python -m http.server 8080  then open localhost:8080
```

---

## Installation

### Requirements

| Requirement | Version |
|---|---|
| Python | 3.9 + |
| `requests` | 2.28 + |
| `tabulate` | 0.9 + (optional — pretty-prints the CLI summary) |

### Install

```bash
# From PyPI dependencies only (recommended)
pip install -r requirements.txt

# Or manually
pip install requests tabulate
```

### Virtual environment (recommended)

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

---

## Configuration

### Environment variables

The script reads the following environment variables so you never need to
put credentials on the command line:

| Variable | Description | Default |
|---|---|---|
| `AKIPS_HOST` | Full URL of your AKIPS server | `https://your-akips-server` |
| `AKIPS_USERNAME` | AKIPS login username | `admin` |
| `AKIPS_PASSWORD` | AKIPS login password | *(empty)* |
| `AKIPS_API_KEY` | API key (alternative to username/password) | *(empty)* |

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

Then load it before running:

```bash
# bash / zsh
export $(grep -v '^#' .env | xargs)
python src/akips_eol_checker.py
```

Or use a tool like [python-dotenv](https://pypi.org/project/python-dotenv/)
if you prefer automatic loading.

### Command-line flags

All environment variables can be overridden via CLI flags:

```
usage: akips_eol_checker.py [-h] [--host HOST] [--username USERNAME]
                             [--password PASSWORD] [--api-key API_KEY]
                             [--demo] [--no-ssl-verify]
                             [--output-json PATH] [--output-csv PATH]
                             [--eol-warn-days N]

optional arguments:
  -h, --help            show this help message and exit
  --host HOST           AKIPS server URL  (or set AKIPS_HOST)
  --username USERNAME   AKIPS username   (or set AKIPS_USERNAME)
  --password PASSWORD   AKIPS password   (or set AKIPS_PASSWORD)
  --api-key API_KEY     AKIPS API key    (or set AKIPS_API_KEY)
  --demo                Use built-in demo data (no AKIPS needed)
  --no-ssl-verify       Disable SSL certificate verification
  --output-json PATH    JSON output path  (default: eol_report.json)
  --output-csv  PATH    CSV  output path  (default: eol_report.csv)
  --eol-warn-days N     Days threshold for "warning" status  (default: 365)
```

---

## Usage

### Basic — demo mode

```bash
python src/akips_eol_checker.py --demo
```

Outputs a summary table to stdout and writes:
- `eol_report.json` — structured device data for the dashboard
- `eol_report.csv`  — flat CSV for Excel / Splunk / etc.

### Live AKIPS — username / password

```bash
python src/akips_eol_checker.py \
  --host https://akips.corp.example.com \
  --username netops \
  --password 'S3cret!'
```

### Live AKIPS — API key

```bash
python src/akips_eol_checker.py \
  --host https://akips.corp.example.com \
  --api-key eyJhbGciOiJIUzI1NiIs...
```

### Self-signed certificate (common on internal servers)

```bash
python src/akips_eol_checker.py --no-ssl-verify
```

### Custom output paths

```bash
python src/akips_eol_checker.py --demo \
  --output-json /var/reports/network-eol.json \
  --output-csv  /var/reports/network-eol.csv
```

### Automate with cron (daily refresh)

```cron
# Run at 06:00 every day, append log
0 6 * * * cd /opt/akips-eol-tracker && \
  /opt/akips-eol-tracker/.venv/bin/python src/akips_eol_checker.py \
  >> /var/log/akips-eol.log 2>&1
```

---

## Dashboard

The dashboard is a self-contained HTML file — no server required.

### How to open it

1. Run the Python script to generate `eol_report.json`
2. Open `dashboard/index.html` in any modern browser
3. Click **Load report** and select `eol_report.json`

Or serve it locally:

```bash
python -m http.server 8080
# then open http://localhost:8080/dashboard/
```

### Views

#### Table view

Every device appears as a row.  Click any column header to sort.

| Column | Description |
|---|---|
| Hostname | Device name from AKIPS `sysName` |
| IP | Management IP |
| Vendor | Detected vendor (Cisco, Juniper, Fortinet, …) |
| Model | Hardware model |
| Version | Software / OS version |
| EOS date | End-of-sale date |
| EOL date | End-of-life date |
| Days to EOL | Positive = future, negative = already past |
| Status | Colour-coded badge |

#### Timeline view

A Gantt-style chart with one bar per device.  Bar colour matches EOL status.
Hover a bar to see the full device details.

### Filters

| Control | How it works |
|---|---|
| **Vendor selector** | Shows only devices from the chosen vendor |
| **Status chips** | Toggle `EOL` / `Critical` / `Warning` / `OK` / `Unknown` on/off |
| **EOL proximity slider** | Drag left to show only devices expiring very soon; drag right to show all |

---

## Extending the product map

The script matches devices to `endoflife.date` slugs using
`PRODUCT_SLUG_MAP` near the top of `src/akips_eol_checker.py`.

### How it works

```python
PRODUCT_SLUG_MAP = {
    "cisco": {
        "catalyst 9300": "cisco-catalyst-9300",  # keyword → EOL slug
        "ios xe":        "cisco-ios-xe",
        ...
    },
    "juniper": { ... },
}
```

The script converts the device's model + version string to lowercase, then
checks each keyword for a substring match.  The first match wins.

### Adding a new device

1. Find the product on [endoflife.date](https://endoflife.date) and copy
   its slug from the URL (e.g. `https://endoflife.date/fortigate` → slug is
   `fortigate`).

2. Add an entry under the correct vendor key:

   ```python
   "fortinet": {
       "fortigate 40f": "fortigate",   # ← new line
       "fortigate 60f": "fortigate",
       ...
   },
   ```

3. Re-run the script.  The device will now show lifecycle dates.

See [docs/PRODUCT_SLUG_MAP.md](docs/PRODUCT_SLUG_MAP.md) for a complete
reference and common mappings.

---

## API reference

See [docs/AKIPS_API.md](docs/AKIPS_API.md) for AKIPS REST API endpoint
details and [docs/ENDOFLIFE_API.md](docs/ENDOFLIFE_API.md) for
`endoflife.date` API notes.

### Key classes

```python
from src.akips_eol_checker import AKIPSClient, EOLClient, enrich

client = AKIPSClient(host="https://akips.corp.com", username="admin", password="...")
devices = client.get_devices()           # list[dict]

eol = EOLClient()
enriched = enrich(devices, eol)          # list[dict] with eolDate, eosDate, status, …
```

### Output schema

Each device in the JSON output has the following fields:

```jsonc
{
  "hostname":    "core-sw-01.nyc",
  "ip":          "10.1.0.1",
  "location":    "",
  "vendor":      "Cisco",
  "model":       "Catalyst 3750-48PS",
  "version":     "12.2(55)SE12",
  "productSlug": "cisco-catalyst-3750",
  "eolCycle":    "12.2SE",
  "eosDate":     "2016-10-30",     // null if unknown
  "eolDate":     "2018-10-30",     // null if unknown
  "daysToEos":   -2394,            // negative = already past
  "daysToEol":   -2394,
  "status":      "eol"             // eol | critical | warning | ok | unknown
}
```

---

## Contributing

Contributions are welcome!  Please read [CONTRIBUTING.md](CONTRIBUTING.md)
before opening a pull request.

### Development setup

```bash
git clone https://github.com/YOUR_ORG/akips-eol-tracker.git
cd akips-eol-tracker
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m pytest tests/
```

### Reporting issues

Use the GitHub issue templates:
- **Bug report** — unexpected output, crashes, wrong EOL dates
- **Feature request** — new vendors, dashboard features, export formats

---

## Changelog

See [CHANGELOG.md](CHANGELOG.md).

---

## License

MIT — see [LICENSE](LICENSE).

---

*Built with [endoflife.date](https://endoflife.date) and
[AKIPS](https://www.akips.com/) APIs.*
