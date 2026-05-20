# Dashboard usage guide

The EOL Intelligence Dashboard is a self-contained HTML file that visualises
the `eol_report.json` produced by the Python script.  No server, no build
step — just a browser.

---

## Opening the dashboard

### Option A — directly in a browser

1. Generate the report:
   ```bash
   python src/akips_eol_checker.py --demo
   ```
2. Open `dashboard/index.html` in Chrome, Firefox, Edge, or Safari
3. Click **Load report** and select `eol_report.json`

### Option B — local web server (avoids file:// restrictions)

```bash
python -m http.server 8080
# open http://localhost:8080/dashboard/
```

### Option C — GitHub Pages / internal web server

Copy `dashboard/index.html` and `eol_report.json` to any web server.  The
dashboard will auto-load `eol_report.json` from the same directory if found.

---

## Views

### Table view

Displays every device as a sortable, filterable row.

**Columns**

| Column | Notes |
|---|---|
| Hostname | From AKIPS `sysName` |
| IP | Management IP address |
| Vendor | Auto-detected — Cisco, Juniper, Fortinet, etc. |
| Model | Hardware model |
| Version | OS / firmware version |
| EOS date | End-of-sale date (`null` if not in endoflife.date) |
| EOL date | End-of-life date (`null` if not in endoflife.date) |
| Days to EOL | Positive = future, zero or negative = already past |
| Status | Colour-coded badge — see below |

**Sorting** — click any column header.  Click again to reverse.

### Timeline view

A Gantt-style chart.  Each device is one horizontal bar starting at today and
ending at its EOL date.  Bars are colour-coded by status.  Hover a bar to see
hostname, model, and exact dates.

---

## Status colours

| Status | Colour | Meaning |
|---|---|---|
| `EOL` | Red | Already past end-of-life — no security patches |
| `Critical` | Amber | < 180 days to EOL — replace now |
| `Warning` | Yellow | < 365 days to EOL — start procurement |
| `OK` | Green | Supported and not near EOL |
| `Unknown` | Grey | Not found in endoflife.date — check product slug map |

---

## Filters

### Vendor selector

Dropdown that limits the view to one vendor.  Defaults to "All vendors".

### Status chips

Toggle buttons for each status (`EOL`, `Critical`, `Warning`, `OK`,
`Unknown`).  Multiple statuses can be active simultaneously.  Click to
toggle on or off.

### EOL proximity slider

**"Show devices expiring within N days"**

| Slider position | Effect |
|---|---|
| Far left (0) | Show only devices already past EOL |
| Middle | Show devices expiring within that many days |
| Far right (max) | Show all devices |

The slider label updates in real time to show the current threshold in days.

---

## Loading data

Click **Load report** to open a file picker and select any
`eol_report.json` file produced by the Python script.  The dashboard updates
immediately.

The demo data built into the dashboard (15 sample devices) is always
available when no file has been loaded.

---

## Exporting from the dashboard

- Use the **Download CSV** button (if present) to export the current filtered
  view as a CSV
- The underlying JSON is `eol_report.json` — open it in any editor or import
  it into Excel, Splunk, Grafana, etc.
