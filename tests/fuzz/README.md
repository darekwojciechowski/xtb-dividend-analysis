# Fuzz tests

Hypothesis-driven fuzzing of the XLSX loader and string parsers in
`data_processing/`. The goal is not to find logic bugs — property-based and
metamorphic suites cover that — but to prove the parsers are **crash-resistant
boundaries**: they either return a well-typed value or raise a whitelisted
domain exception.

## Run

```bash
pytest -m fuzz                        # local, 200 examples per test
HYPOTHESIS_PROFILE=fuzz-ci pytest -m fuzz   # CI, 500 examples per test
```

## Exception whitelist

| Parser                              | Allowed exceptions         |
| ----------------------------------- | -------------------------- |
| `import_and_process_data`           | *none* (returns `(None, None)` on failure) |
| `convert_date`                      | `ValueError`, `TypeError`  |
| `TaxCalculator._parse_*`            | `ValueError`, `TypeError`  |
| `CurrencyConverter.extract_dividend_from_comment` | *none* (returns `(None, None)` on failure) |

Anything outside this list — `KeyError`, `IndexError`, `AttributeError`,
`UnicodeError` — is a real bug and must be fixed at the parser boundary, not
by widening the whitelist.

## Reproducing a failure

Hypothesis prints a `@reproduce_failure` decorator on failure. Paste it above
the failing test and rerun. Minimal examples are cached in
`.hypothesis/examples/`, which is committed to the repo so CI replays known
regressions before exploring new space.
