# Contributing to akips-eol-tracker

Thank you for taking the time to contribute!  This document explains how to
get set up, what kinds of contributions are most useful, and how the review
process works.

---

## Types of contributions

| Type | Where to start |
|---|---|
| Bug report | [Open a bug report issue](../../issues/new?template=bug_report.md) |
| Feature request | [Open a feature request issue](../../issues/new?template=feature_request.md) |
| New vendor / product mappings | Edit `PRODUCT_SLUG_MAP` in `src/akips_eol_checker.py` |
| Dashboard improvements | Edit `dashboard/index.html` |
| Documentation | Edit files in `docs/` or `README.md` |
| Tests | Add to `tests/` |

---

## Development setup

```bash
# 1 — Fork the repo on GitHub, then clone your fork
git clone https://github.com/YOUR_USERNAME/akips-eol-tracker.git
cd akips-eol-tracker

# 2 — Create a virtual environment
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 3 — Install dependencies
pip install -r requirements.txt

# 4 — Run the tests to confirm everything works
python -m pytest tests/ -v
```

---

## Workflow

1. **Create a branch** off `main` with a descriptive name:

   ```bash
   git checkout -b feat/add-arista-mappings
   git checkout -b fix/version-parsing-junos
   git checkout -b docs/improve-slug-guide
   ```

2. **Make your changes** and commit with a clear message:

   ```
   feat: add Arista EOS product slug mappings
   fix: handle Junos version strings with -SX suffix
   docs: add EOS date field explanation to output schema
   ```

3. **Run tests** before pushing:

   ```bash
   python -m pytest tests/ -v
   ```

4. **Open a pull request** against `main`.  Fill in the PR template:
   - What does this change?
   - How was it tested?
   - Any breaking changes?

---

## Adding vendor / product mappings

This is the most common and valuable contribution.  Here's how:

1. Find the product slug on [endoflife.date](https://endoflife.date) —
   it's the last segment of the URL, e.g.
   `https://endoflife.date/cisco-catalyst-9300` → slug = `cisco-catalyst-9300`

2. Open `src/akips_eol_checker.py` and find `PRODUCT_SLUG_MAP`

3. Add an entry under the correct vendor key.  The key is a **lowercase
   substring** that will be matched against the device's model + version
   string:

   ```python
   "arista": {
       "eos": "arista-eos",
   },
   ```

4. Add a test in `tests/test_parser.py` that confirms the new mapping resolves

5. Update `docs/PRODUCT_SLUG_MAP.md` with the new entries

---

## Code style

- Follow [PEP 8](https://pep8.org/)
- Use type hints on all function signatures
- Keep line length ≤ 100 characters
- No external formatters are enforced, but `ruff` is recommended:
  `pip install ruff && ruff check src/`

---

## Questions

Open a [Discussion](../../discussions) if you are unsure where to start or
want to validate an idea before building it.
