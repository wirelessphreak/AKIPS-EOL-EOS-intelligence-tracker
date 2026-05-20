# Changelog

All notable changes to this project are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning follows [Semantic Versioning](https://semver.org/).

---

## [1.0.0] — 2025-05-20

### Added
- `AKIPSClient` — REST API client supporting HTTP Basic and Bearer token auth
- `EOLClient` — client for the public `endoflife.date` API with local caching
- `PRODUCT_SLUG_MAP` — vendor/model → EOL slug mappings for Cisco, Juniper,
  Fortinet, Palo Alto, F5, Aruba, and common Linux distros
- `enrich()` — cross-references AKIPS device list with lifecycle dates
- Status classification: `eol`, `critical` (< 180 d), `warning` (< 365 d),
  `ok`, `unknown`
- JSON and CSV export
- CLI with `--demo`, `--no-ssl-verify`, `--output-json`, `--output-csv`,
  `--eol-warn-days` flags
- Interactive dashboard (table view + Gantt timeline view)
- Dashboard filters: vendor selector, status chips, EOL proximity slider
- GitHub Actions CI workflow
- Issue templates (bug report, feature request)
- Unit tests for device info parsing and slug resolution
