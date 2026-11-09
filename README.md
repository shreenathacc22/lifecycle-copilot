# Lifecycle Copilot

Takes this period's CMDB export and last period's TLM sheet for one tower, and writes the lifecycle workbook: every row kept, matched to last period by exact rules, blank dates filled from an approved policy table, and a reason next to every value it filled.

Synthetic data only. Real exports never go in this folder.

## Setup

```bash
cd DAY1/TLM-Project/Lifecycle_copilot
~/.local/bin/uv venv --python 3.12 .venv        # skip if .venv already exists
~/.local/bin/uv pip install --python .venv/bin/python -e '.[dev]'
```

## Run

```bash
.venv/bin/lifecycle-copilot sample                       # writes data/sample/current.xlsx and prior.xlsx
.venv/bin/lifecycle-copilot run --current data/sample/current.xlsx --prior data/sample/prior.xlsx --out output/
.venv/bin/python -m pytest -q
```

Expected output of `run` on the sample:

```
current rows 11: serial 3, hostname 2, new 4, needs review 2
prior rows   10: matched 5, dropped 4, needs review 1
OS EOS: 1 from source, 6 from policy, 3 carried, 0 from peers, 1 still blank
```

The Report sheet has a Status column (Matched, New, Needs review). Needs review rows are shaded and got no peer values.

Asset EOL/EOS are not filled from same-model peers unless you pass `--peer-asset-dates`. It's off until the ITAM team confirms how Asset EOS is based.

The workbook lands in `output/lifecycle-copilot-report.xlsx` with six sheets: Report, Summary, Matching Logic, Match Detail, Dropped, Data Quality.

Other commands: `ingest` (read and check only), `match` (read, check and match). If a column looks pasted by row position from the prior file, the run stops; `--ack-provenance` continues and keeps the warning on the Data Quality sheet.

## Built so far

| Milestone | Status |
|---|---|
| M0 synthetic sample | done |
| M1 ingest and checks | done |
| M2 deterministic matching | done |
| M4 carry forward and Windows OS policy | done |
| M6 six-sheet export | done |
| M3 SQLite run log | not started |
| M5 decision rules, M7 review, M8 AI research, M9 UI | on hold until the ITAM team session |

Spec: `docs/05-product-spec.md`. Plan: `docs/07-build-plan.md`. Sample contract: `tests/sample_manifest.md`.
