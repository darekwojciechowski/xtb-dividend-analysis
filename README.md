# XTB dividend analysis

> A production-grade Python pipeline, engineered as a **senior-level testing showcase** —
> 530+ tests across 8 independent tiers: unit, integration, property-based, fuzz,
> metamorphic, contract, security, and mutation.

![CI/CD](https://img.shields.io/github/actions/workflow/status/darekwojciechowski/xtb-dividend-analysis/ci.yml?branch=main&style=flat-square&logo=github-actions&logoColor=white&label=CI/CD)
![Coverage](https://img.shields.io/badge/dynamic/json?url=https://raw.githubusercontent.com/darekwojciechowski/xtb-dividend-analysis/main/coverage.json&query=$.totals.percent_covered_display&label=Coverage&suffix=%25&style=flat-square&color=success)
![Python Version](https://img.shields.io/python/required-version-toml?tomlFilePath=https%3A%2F%2Fraw.githubusercontent.com%2Fdarekwojciechowski%2Fxtb-dividend-analysis%2Fmain%2Fpyproject.toml&style=flat-square&logo=python&logoColor=white&label=Python)
![Pytest](https://img.shields.io/pypi/v/pytest?label=Pytest&style=flat-square&logo=pytest&logoColor=white&color=0A9EDC)
![Hypothesis](https://img.shields.io/pypi/v/hypothesis?label=Hypothesis&style=flat-square&logo=python&logoColor=white&color=A020F0)
![Pandera](https://img.shields.io/pypi/v/pandera?label=Pandera&style=flat-square&logo=python&logoColor=white&color=FF6F61)
![Mutmut](https://img.shields.io/pypi/v/mutmut?label=Mutmut&style=flat-square&logo=python&logoColor=white&color=DC143C)
![Bandit](https://img.shields.io/badge/Bandit-SARIF-FFD43B?style=flat-square&logo=python&logoColor=white)
![Playwright](https://img.shields.io/pypi/v/playwright?label=Playwright&style=flat-square&logo=playwright&logoColor=white&color=2EAD33)
![Poetry](https://img.shields.io/pypi/v/poetry?label=Poetry&style=flat-square&logo=poetry&logoColor=white&color=60A5FA)
![License](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)

A Python data pipeline that parses XTB broker statements (`.xlsx`), converts
foreign dividends to PLN using NBP D-1 exchange rates, calculates Polish Belka
tax (19%) with WHT deduction, and exports a tab-separated CSV ready for Google
Sheets. The pipeline is a real-world problem; the **repository is a showcase
of risk-based, multi-layer test engineering**.

![Terminal](assets/xtb-dividend-analysis-terminal.gif)

---

## Testing strategy

Each tier was chosen deliberately — it catches a class of defect the others
cannot. This is **defense-in-depth applied to test design**: example-based
tests pin the happy path, property-based tests generalise it, metamorphic
tests replace the missing oracle, fuzz tests probe hostile input, contract
tests guard the data boundary, and mutation tests verify the tests
themselves are actually asserting something.

| Tier            | Files | Framework                        | What it catches that nothing else does                                                                                         |
|-----------------|-------|----------------------------------|--------------------------------------------------------------------------------------------------------------------------------|
| Unit            | 17    | `pytest` + `unittest.mock`       | Logic defects in every specialist class in isolation; all I/O mocked                                                           |
| Integration     | 6     | `pytest` + real DataFrames       | Wiring defects — end-to-end pipeline against real XLSX fixtures and NBP CSV files                                              |
| Property-based  | 2     | `hypothesis` (100 examples/run)  | Violated mathematical invariants in tax, FX, and date logic that hand-picked cases miss                                        |
| Metamorphic     | 3     | `hypothesis` + relation asserts  | Incorrect behaviour when there is no ground-truth oracle — permutation, duplication, additivity, linear scaling relations      |
| Fuzz            | 2     | `hypothesis` (binary + text)     | Crashes, hangs, and silent corruption on hostile XLSX bytes and malformed strings; whitelisted exceptions only                 |
| Contract        | 2     | `pandera`                        | Silent broker format drift — schema tripwires on raw XTB XLSX and the exported Google-Sheets CSV                               |
| Security        | 2     | `bandit` + SARIF parser          | Insecure code patterns; SARIF output structure + severity mapping for GitHub Security tab integration                          |
| Mutation        | —     | `mutmut`                         | **Test-suite weakness** — whether the assertions would actually fail if the production code were broken                        |

All tests follow the **AAA pattern** (Arrange / Act / Assert, blank line between
sections) and are named `test_<unit>_<scenario>_<expected_outcome>`. Run the
full suite or a single tier:

```bash
poetry run pytest                        # full suite
poetry run pytest -m property_based      # one tier at a time
poetry run pytest -m metamorphic
poetry run pytest -m fuzz
poetry run pytest -m contract
poetry run tox                           # Python 3.9–3.13 locally
```

---

## Quality engineering toolkit

Skills and practices applied throughout — each one is visible in the repo,
not just listed.

- **Risk-based test design** — 8 tiers, each targeting a distinct failure mode,
  not overlapping coverage
- **Property-based testing** — generative invariants over tax, FX, and date
  logic with `hypothesis`; shrinks to minimal counter-examples automatically
- **Metamorphic testing** — tolerates the absence of an oracle by asserting
  *relations* between runs (permutation, duplication, additivity, scaling)
- **Fuzz testing** — hostile binary and text input strategies; whitelisted
  exception set prevents silent regressions
- **Schema contracts** — `pandera` tripwires on both input and output data,
  failing loudly on upstream format drift
- **Mutation testing** — `mutmut` validates that the suite *actually* catches
  broken code; skip-rules pragma-marked inline for auditability
- **Static analysis stack** — `mypy` strict mode, `ruff`, `bandit` with SARIF
  upload to GitHub Security, `safety` dependency CVE scanning
- **Deterministic CI** — dependency cache keyed on lockfile hash;
  `dorny/paths-filter` skips test job when no Python changed; JUnit XML +
  Codecov artifacts
- **Test hygiene** — AAA pattern enforced; `pytest-randomly` catches
  order-dependent tests; strict markers; deprecation warnings escalated to
  errors for first-party modules only
- **Structured logging** — `loguru` throughout; zero `print()` calls in source
- **Type-safe configuration** — `pydantic-settings`; no hardcoded paths,
  rates, or URLs in source

---

## CI/CD pipeline

### `ci.yml` — quality gates
Runs on `ubuntu-latest` with Python 3.13. Twelve jobs gated by a fail-fast
quality stage: lint → type-check → unit → integration → property-based →
metamorphic → fuzz → contract → security → coverage → mutation-smoke.
Artifacts: JUnit XML (`dorny/test-reporter`), Codecov upload with PR comment,
Bandit SARIF report to the GitHub Security tab. Lint and security jobs use
`continue-on-error: true` so a style warning never blocks a merge; functional
test jobs are strict.

### `fast-tests.yml` — smoke feedback loop
Ubuntu + Python 3.12, sub-60-second feedback before the full pipeline
completes. Used as a pre-push sanity check.

### Local parity
`poetry run tox` runs the suite against Python 3.9–3.13 locally so drift
between developer machine and CI is caught pre-commit.

---

<details>
<summary><strong>Architecture</strong> — facade orchestrator + delegate-then-assign specialists</summary>

<br />

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://mermaid.ink/svg/JSV7aW5pdDogeyd0aGVtZSc6ICdkYXJrJywgJ3RoZW1lVmFyaWFibGVzJzogeyAncHJpbWFyeUNvbG9yJzogJyMxZjI5MzcnLCAnbWFpbkJrZyc6ICcjMWYyOTM3JywgJ2NsdXN0ZXJCa2cnOiAnIzExMTgyNycsICdjbHVzdGVyQm9yZGVyJzogJyMzNzQxNTEnLCAnbGluZUNvbG9yJzogJyM5Y2EzYWYnLCAnZm9udEZhbWlseSc6ICdTZWdvZSBVSSwgc2Fucy1zZXJpZicsICdlZGdlTGFiZWxCYWNrZ3JvdW5kJzogJyMxMTE4MjcnIH19fSUlCmdyYXBoIExSCiAgICBzdWJncmFwaCBEYXRhIFsiJm5ic3A7Jm5ic3A7Jm5ic3A7Jm5ic3A7Jm5ic3A7Jm5ic3A7Jm5ic3A7Jm5ic3A7RGF0YSBTY3VyY2VzJm5ic3A7Jm5ic3A7Jm5ic3A7Jm5ic3A7Jm5ic3A7Jm5ic3A7Jm5ic3A7Jm5ic3A7Il0KICAgICAgICBkaXJlY3Rpb24gVEIKICAgICAgICBBW1hUQiBTdGF0ZW1lbnRzXTo6OmRhdGEKICAgICAgICBCW05CUCBBcmNoaXZlXTo6OmRhdGEKICAgIGVuZAoKICAgIHN1YmdyYXBoIExvZ2ljIFsiJm5ic3A7Jm5ic3A7Jm5ic3A7Jm5ic3A7Jm5ic3A7Jm5ic3A7Jm5ic3A7Jm5ic3A7UHJvY2Vzc2luZyBQaXBlbGluZSZuYnNwOyZuYnNwOyZuYnNwOyZuYnNwOyZuYnNwOyZuYnNwOyZuYnNwOyZuYnNwOyJdCiAgICAgICAgZGlyZWN0aW9uIFRCCiAgICAgICAgQyhQbGF5d3JpZ2h0IERMKTo6OnByb2MKICAgICAgICBEe0RhdGEgRXh0cmFjdG9yfTo6OnByb2MKICAgICAgICBFW0RhdGVDb252ZXJ0ZXJdOjo6cHJvYwogICAgICAgIEZbREYgUHJvY2Vzc29yXTo6OnByb2MKICAgIGVuZAoKICAgIHN1YmdyYXBoIFVJIFsiJm5ic3A7Jm5ic3A7Jm5ic3A7Jm5ic3A7T3V0cHV0ICYgVmlzdWFsaXphdGlvbiZuYnNwOyZuYnNwOyZuYnNwOyZuYnNwOyJdCiAgICAgICAgZGlyZWN0aW9uIFRCCiAgICAgICAgR1tHb29nbGUgU2hlZXRzXTo6OnVpCiAgICAgICAgSFtWaXN1YWxpemF0aW9uc106Ojp1aQogICAgICAgIElbU3RyZWFtbGl0IERhc2hib2FyZF06Ojp1aQogICAgZW5kCgogICAgQiAtLT58RG93bmxvYWR8IEMKICAgIEMgLS0-fENTVnwgRAogICAgQSAtLT58UGFyc2V8IEQKICAgIEQgLS0-fE5vcm1hbGl6ZXwgRQogICAgRSAtLT58VHJhbnNmb3JtfCBGCiAgICBGIC0tPnxFeHBvcnR8IEcKICAgIEYgLS0-fFBsb3R8IEgKICAgIEcgLS0-fFN0cmVhbXwgSQogICAgSCAtLT58RW5oYW5jZXwgSQoKICAgIGNsYXNzRGVmIGRhdGEgZmlsbDojMTcyNTU0LHN0cm9rZTojNjBhNWZhLHN0cm9rZS13aWR0aDoycHgsY29sb3I6I2RiZWFmZSxyeDo4LHJ5Ojg7CiAgICBjbGFzc0RlZiBwcm9jIGZpbGw6IzJlMTA2NSxzdHJva2U6I2E3OGJmYSxzdHJva2Utd2lkdGg6MnB4LGNvbG9yOiNmM2U4ZmYscng6OCxyeTo4OwogICAgY2xhc3NEZWYgdWkgZmlsbDojMDY0ZTNiLHN0cm9rZTojMzRkMzk5LHN0cm9rZS13aWR0aDoycHgsY29sb3I6I2QxZmFlNSxyeDo4LHJ5Ojg7CiAgICBzdHlsZSBEYXRhIGZpbGw6IzExMTgyNyxzdHJva2U6IzM3NDE1MSxzdHJva2Utd2lkdGg6MXB4LHJ4OjEwLHJ5OjEwCiAgICBzdHlsZSBMb2dpYyBmaWxsOiMxMTE4Mjcsc3Ryb2tlOiMzNzQxNTEsc3Ryb2tlLXdpZHRoOjFweCxyeDoxMCxyeToxMAogICAgc3R5bGUgVUkgZmlsbDojMTExODI3LHN0cm9rZTojMzc0MTUxLHN0cm9rZS13aWR0aDoxcHgscng6MTAscnk6MTAK">
  <img alt="System architecture diagram" src="https://mermaid.ink/svg/JSV7aW5pdDogeyd0aGVtZSc6ICdiYXNlJywgJ3RoZW1lVmFyaWFibGVzJzogeyAncHJpbWFyeUNvbG9yJzogJyNmZmYnLCAnbWFpbkJrZyc6ICcjZmZmJywgJ2NsdXN0ZXJCa2cnOiAnI2Y5ZmFmYicsICdjbHVzdGVyQm9yZGVyJzogJyNlNWU3ZWInLCAnbGluZUNvbG9yJzogJyM2YjcyODAnLCAnZm9udEZhbWlseSc6ICdTZWdvZSBVSSwgc2Fucy1zZXJpZicsICdlZGdlTGFiZWxCYWNrZ3JvdW5kJzogJyNmOWZhZmInIH19fSUlCmdyYXBoIExSCiAgICBzdWJncmFwaCBEYXRhIFsiJm5ic3A7Jm5ic3A7Jm5ic3A7Jm5ic3A7Jm5ic3A7Jm5ic3A7Jm5ic3A7Jm5ic3A7RGF0YSBTY3VyY2VzJm5ic3A7Jm5ic3A7Jm5ic3A7Jm5ic3A7Jm5ic3A7Jm5ic3A7Jm5ic3A7Jm5ic3A7Il0KICAgICAgICBkaXJlY3Rpb24gVEIKICAgICAgICBBW1hUQiBTdGF0ZW1lbnRzXTo6OmRhdGEKICAgICAgICBCW05CUCBBcmNoaXZlXTo6OmRhdGEKICAgIGVuZAoKICAgIHN1YmdyYXBoIExvZ2ljIFsiJm5ic3A7Jm5ic3A7Jm5ic3A7Jm5ic3A7Jm5ic3A7Jm5ic3A7Jm5ic3A7Jm5ic3A7UHJvY2Vzc2luZyBQaXBlbGluZSZuYnNwOyZuYnNwOyZuYnNwOyZuYnNwOyZuYnNwOyZuYnNwOyZuYnNwOyZuYnNwOyJdCiAgICAgICAgZGlyZWN0aW9uIFRCCiAgICAgICAgQyhQbGF5d3JpZ2h0IERMKTo6OnByb2MKICAgICAgICBEe0RhdGEgRXh0cmFjdG9yfTo6OnByb2MKICAgICAgICBFW0RhdGVDb252ZXJ0ZXJdOjo6cHJvYwogICAgICAgIEZbREYgUHJvY2Vzc29yXTo6OnByb2MKICAgIGVuZAoKICAgIHN1YmdyYXBoIFVJIFsiJm5ic3A7Jm5ic3A7Jm5ic3A7Jm5ic3A7T3V0cHV0ICYgVmlzdWFsaXphdGlvbiZuYnNwOyZuYnNwOyZuYnNwOyZuYnNwOyJdCiAgICAgICAgZGlyZWN0aW9uIFRCCiAgICAgICAgR1tHb29nbGUgU2hlZXRzXTo6OnVpCiAgICAgICAgSFtWaXN1YWxpemF0aW9uc106Ojp1aQogICAgICAgIElbU3RyZWFtbGl0IERhc2hib2FyZF06Ojp1aQogICAgZW5kCgogICAgQiAtLT58RG93bmxvYWR8IEMKICAgIEMgLS0-fENTVnwgRAogICAgQSAtLT58UGFyc2V8IEQKICAgIEQgLS0-fE5vcm1hbGl6ZXwgRQogICAgRSAtLT58VHJhbnNmb3JtfCBGCiAgICBGIC0tPnxFeHBvcnR8IEcKICAgIEYgLS0-fFBsb3R8IEgKICAgIEcgLS0-fFN0cmVhbXwgSQogICAgSCAtLT58RW5oYW5jZXwgSQoKICAgIGNsYXNzRGVmIGRhdGEgZmlsbDojZWZmNmZmLHN0cm9rZTojM2I4MmY2LHN0cm9rZS13aWR0aDoycHgsY29sb3I6IzFlM2E4YSxyeDo4LHJ5Ojg7CiAgICBjbGFzc0RlZiBwcm9jIGZpbGw6I2Y1ZjNmZixzdHJva2U6IzhiNWNmNixzdHJva2Utd2lkdGg6MnB4LGNvbG9yOiM0YzFkOTUscng6OCxyeTo4OwogICAgY2xhc3NEZWYgdWkgZmlsbDojZWNmZGY1LHN0cm9rZTojMTBiOTgxLHN0cm9rZS13aWR0aDoycHgsY29sb3I6IzA2NGUzYixyeDo4LHJ5Ojg7CiAgICBzdHlsZSBEYXRhIGZpbGw6I2Y5ZmFmYixzdHJva2U6I2U1ZTdlYixzdHJva2Utd2lkdGg6MXB4LHJ4OjEwLHJ5OjEwCiAgICBzdHlsZSBMb2dpYyBmaWxsOiNmOWZhZmIsc3Ryb2tlOiNlNWU3ZWIsc3Ryb2tlLXdpZHRoOjFweCxyeDoxMCxyeToxMAogICAgc3R5bGUgVUkgZmlsbDojZjlmYWZiLHN0cm9rZTojZTVlN2ViLHN0cm9rZS13aWR0aDoxcHgscng6MTAscnk6MTAK">
</picture>

`DataFrameProcessor` is a facade that owns `self.df` and delegates every
transformation to a stateless specialist class. Each step follows
**delegate-then-assign**:

```python
specialist = SpecialistClass(self.df)
self.df = specialist.method()
```

| Step | Specialist class     | Responsibility                                                                               |
|------|----------------------|----------------------------------------------------------------------------------------------|
| 1    | `ColumnNormalizer`   | Maps bilingual (PL/EN) column names to canonical English names via `ColumnName` enum         |
| 2    | `DividendFilter`     | Filters dividend and WHT rows; groups by ticker, date, and comment                           |
| 3    | `DataAggregator`     | Merges split rows, moves negative WHT values to a dedicated column, reorders columns         |
| 4    | `CurrencyConverter`  | Detects account currency from XLSX cell F6; looks up NBP D-1 mid-rate for each payment date  |
| 5    | `TaxExtractor`       | Parses WHT percentage from free-text comment strings using `MultiConditionExtractor`         |
| 6    | `TaxCalculator`      | Computes Belka tax: `gross × 0.19 − WHT_paid` in PLN; handles both USD and PLN accounts      |
| 7    | `ColumnFormatter`    | Applies ANSI ticker colorization, formats display columns, appends currency labels           |

All domain constants (`ColumnName`, `Currency`, `TickerSuffix`) are enums in
`data_processing/constants.py`. No raw string literals for column names or
currency codes appear anywhere in source.

</details>

<details>
<summary><strong>Getting started</strong> — install, run, export to Google Sheets</summary>

<br />

### Prerequisites
- Python 3.13 or later
- [Poetry](https://python-poetry.org/) for dependency management
- Chromium (installed automatically by Playwright during setup)

### Installation

```bash
git clone https://github.com/darekwojciechowski/xtb-dividend-analysis.git
cd xtb-dividend-analysis
poetry install
poetry run playwright install chromium
```

### Usage

**Step 1 — Download NBP exchange rate archives.** The files are saved to
`data/` as `archiwum_tab_a_<YYYY>.csv`.

```bash
poetry run python data_acquisition/playwright_download_currency_archive.py
```

**Step 2 — Process the broker statement.** Place your XTB `.xlsx` in `data/`,
then run:

```bash
poetry run python main.py
```

Output is written to `output/for_google_spreadsheet.csv`.

**Step 3 — Import to Google Sheets.** Paste the contents of
`output/for_google_spreadsheet.csv` directly into a sheet. Tab separators are
recognized automatically.

**Step 4 — Visualize (optional).** Feed the exported CSV into the
[Streamlit Dividend Dashboard](https://github.com/darekwojciechowski/Streamlit-Dividend-Dashboard).

![Dashboard Demo](assets/streamlit-dashboard-demo.gif)

</details>

---

## Stack

**Core:** Python 3.13, pandas, numpy, openpyxl, pydantic-settings, loguru, playwright

**Testing:** pytest, hypothesis, pandera, mutmut, bandit, safety, tox, pytest-randomly

**Tooling:** Poetry, ruff, mypy (strict), pre-commit, Codecov, GitHub Actions

## License
MIT
