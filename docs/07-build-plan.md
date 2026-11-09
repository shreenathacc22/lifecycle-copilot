# 07. Build plan: Lifecycle Copilot v1

Status: **draft.** Based on `05-product-spec.md`, which is itself not validated yet. `06-validation.md` has no feedback recorded, so nothing below counts as approved.
Drafted 24-Oct-2026.

Rule for every milestone: build it on synthetic data in `data/sample/`, get the checks green, show the output, and wait for a go before starting the next one.

---

## Unresolved decisions

These come from `06`. None of them has been decided yet. The milestone that needs each one is listed, so work can start before all of them are closed.

| Item | Needed by | What I'll do until it's decided |
|---|---|---|
| Placeholder serial list (spec §6 step 1) | M2 | Use `N/A`, `NA`, `0`, `NONE`, `TO BE FILLED BY O.E.M.`, `DEFAULT STRING`, blank. Keep it in one config list. |
| C5 hostname fallback only when one serial is blank | M2 | Build it the way the spec says. It's a one-line change if the decision goes the other way. |
| Frozen test set version and sign-off | M2 (A12) | Synthetic data only. A12 stays skipped. |
| C6 cell-level compare, not byte compare | M6 | Cell-level compare. |
| ServiceNow SAM/HAM license check | M4 | Policy table loaded from the EOL-EOS reference sheet. |
| D2: OS EOS passed → Renew or Retire | M5 | Output `Needs review` for D2 rows, with the rationale "rule D2 not decided". |
| C2 no evidence → Needs review | M5 | Needs review, as the spec says. |
| C4 thin review queue and audit log in v1 | M7 | CLI review only. |
| Review in the app or in Excel | M7 | CLI first. Excel round-trip only if the operator asks. |
| C1 target 1 h or 45 min | M8 | Record the real time. The target doesn't change the build. |
| Acceptance criteria A1 to A14 | all | Build the tests as written. Change them if feedback changes them. |
| Non-goals list | all | Don't build anything on it. |

---

## Milestones

### M0. Project skeleton and synthetic sample

Make the folder runnable, and create the fake data every later test uses.

Output:
- `pyproject.toml` (Python 3.12, openpyxl, pydantic, pytest; nothing else yet)
- `src/lifecycle_copilot/` package with an empty `__init__.py`
- `tests/`
- `scripts/make_sample.py`, which writes `data/sample/current.xlsx` and `data/sample/prior.xlsx`
- The sample covers each matching case on purpose: clean serial match, hostname-only match, hostname reuse with different serials, duplicate serial, placeholder serial, OS edition change, new asset, dropped asset

Checks:
- `pip install -e .` and `pytest` run clean (zero tests is fine)
- `python scripts/make_sample.py` is deterministic: two runs give the same cell values
- No real hostnames, serials or names in the sample

### M1. Ingest and validation

Read the two workbooks into rows, without losing or changing anything.

Output:
- `ingest/` reads `.xlsx` and normalises headers (double spaces, known typos, drops `Unnamed:` columns), then maps them to canonical field names
- Keeps the raw row and its row number next to the normalised fields
- Checks run before anything else: required columns present, row count, null rate per column, duplicate serials listed, positional copy check (I6)
- CLI: `lifecycle-copilot ingest --current ... --prior ...` prints row counts and any warnings

Checks:
- A4 (part): N rows in → N rows held, duplicates included
- A7: a column copied row for row from the prior file stops the run with a clear message
- A missing required column gives an error that names the column
- An empty file, a wrong file type and a password-protected file each fail cleanly, with no stack trace

### M2. Deterministic matching

Port the rules in spec §6 exactly. This is the core of the product, and nothing after it starts until it's green.

Output:
- `match/` with normalise → serial match → hostname fallback → none → dropped
- Each pair gets a `method` and a `reason`
- DQ entries for duplicate serials, hostname reuse and placeholder serials
- CLI: `lifecycle-copilot match ...` prints counts for serial, hostname, new, dropped and needs review

Checks:
- A1 same hostname, different serials → no match, DQ hostname reuse
- A3 duplicate serial → neither row auto-matches, both are kept, DQ entry
- A10 one blank serial, unique hostname → `method = hostname`
- A11 one blank serial, hostname appears twice → no match, DQ entry
- Placeholder serials are treated as blank
- No library or code path does similarity scoring (a test greps the package for `difflib`, `fuzz`, `levenshtein`)
- Matching the same inputs twice gives identical results
- A12 frozen test set: written but skipped until the set is signed off

### M3. SQLite store and run log

Save each run so results can be checked and overrides can stick later.

Output:
- `store/` with the spec §10 tables (`run`, `asset_row`, `match_edge`, `dq_issue` first; the rest are added by the milestones that need them)
- Each run records the file hashes, start and end time, and the operator
- `data/lifecycle.db` is local and in `.gitignore`

Checks:
- Running twice on the same files gives two runs with identical match edges
- Every current and prior row is in `asset_row` (I4)

### M4. Carry forward and policy fill

Fill the blanks, in the order the spec gives, and never overwrite anything.

Output:
- `lifecycle/carry.py`: inherit on match; clear and recompute OS dates when the OS name, version or edition changed; FQDN only if the hostname didn't change
- `lifecycle/policy.py`: load the policy table (synthetic Windows rows to start), look up on vendor + product + version + edition
- `lifecycle/peers.py`: same-model peers with one consistent value
- Every filled value writes a `basis` and a Remarks line

Checks:
- A2 Pro → Enterprise edition change gets the Enterprise date, and Remarks says why
- A6 a value from the source or a human is never changed
- A row with no evidence stays blank and gets a reason
- Same version under two editions gives two different dates

No LLM in this milestone.

### M5. Decision rules

Output:
- `decide/` runs D0 to D7 from spec §8, top to bottom, first match wins
- Each call stores its `rule_id` and a one-line rationale

Checks:
- A8 no OS EOS and no asset EOS → Needs review
- A9 an override from the last run is applied and not recomputed
- D2 gives Needs review until the rule is decided
- A table test that covers each rule D0 to D7 at least once

### M6. Six-sheet export

Output:
- `export/` writes Report, Summary, Matching Logic, Match Detail, Dropped and Data Quality
- Legacy headers and column order on Report
- Real Excel dates
- CLI: `lifecycle-copilot run --current ... --prior ... --out output/`

Checks:
- A4 Report has exactly N rows and Summary in-count = N
- A13 every date column is an Excel date
- Summary totals add up: serial + hostname + new + review = current rows; matched + dropped + prior review = prior rows (corrected by QA: duplicate-serial rows are neither matched nor new)
- Cell-level compare against a hand-checked expected workbook for the synthetic sample

This is the first point where a full run is useful end to end. Show it to the operator here if possible, even before M7.

### M7. Review queue and overrides (CLI)

Output:
- `lifecycle-copilot review` lists open items: duplicate serials, Needs review rows, peer conflicts, provenance warnings
- Accept, edit or reject each one; every action goes to `review_log` with who, when, old and new value
- Edits become sticky overrides (`override` table)
- Summary shows the count of open review items

Checks:
- An override made in run 1 is applied in run 2 (A9, end to end)
- Exporting with open items works, and the open count is right

### M8. LLM proposals (last, and behind review)

Only for blanks left after M4. Only after M0 to M7 are green.

Output:
- `lifecycle/research.py` asks the Claude API for a date with a citation URL, for one product + version + edition at a time
- Model version is pinned per run and recorded in `run`
- Results are stored as `status = proposed` and always go to the review queue
- Accepting one can promote it to the policy table, with the URL and date

Checks:
- A5 an LLM date has a citation, `basis = llm_proposed`, and is in review; no citation means blank
- With the API turned off, the run still finishes and leaves those fields blank
- Tests use a recorded fake response, not the live API
- The API key comes from `.env` and is never logged

### M9. Thin UI and timed trial

Output:
- A minimal local page: upload two files, run, see the review queue, download the workbook
- Only if the operator wants it. The CLI may be enough.

Checks:
- A14 the operator (not me) does one timed refresh. Record hands-on minutes in `03`.
- A12 runs against the frozen test set, if it has been signed off by then

---

## Order and dependencies

```
M0 → M1 → M2 → M3 → M4 → M5 → M6 → M7 → M8 → M9
                ▲                     ▲
       nothing past here        first full run to show
       until M2 is green        the operator
```

Data quality checks (M1, M2) come before any AI (M8), as the guide says.

## Not in this plan

Everything in spec §13: ServiceNow API, write-back, more towers, SSO, dashboards, ticketing, fuzzy matching, warranty APIs, natural-language query.
