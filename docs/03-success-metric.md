# 03. Success metric

## Pilot metric

Analyst hands-on time to produce and approve one EUC Windows tower refresh. The clock starts when the export is in hand and stops when the finished workbook is sent. It includes exception review and corrections. Waiting for the extract email doesn't count.

Total elapsed time gets recorded separately.

| | |
|---|---|
| Baseline | about 16 h (two working days). An estimate. Needs a measured run. |
| Target | 1 h hands-on. Decided 24-Oct by the product owner. |
| Test set | Sep-2026 EUC Windows refresh, where the correct answer is already known |

## Quality conditions

A fast run doesn't count unless all of these hold:

- Every current input row shows up in the export.
- No wrong automatic identity links on the test set.
- Every derived date has evidence behind it.
- Unknown values stay visible as Unknown / Needs review.

## Longer-term measure

Analysts other than me keep running refreshes and accepting the output, with less hands-on effort each time.

Time spent in the app is not a success measure. The point is to spend less time.

## Measurements log

| Date | Who | Tower | Hands-on time | Elapsed time | Notes |
|---|---|---|---|---|---|
| 24-Oct | QA (automated) | EUC Windows, synthetic sample (11 current, 10 prior rows) | not measured | 0.06 to 0.08 s per full run, CLI start to workbook written (3 runs). The tool reports 0.01 s for the work itself. | Machine time only, on made-up data. Not the pilot metric. |

### Forge "Measured" evidence, 24-Oct

What's measured so far is the software, not the person.

- Tests: 45 passed, 0 failed, 4 skipped (`pytest`, 0.34 s).
- Earlier run, 42 passed, 1 failed. A column copied by row position from last period's file wasn't caught when it had only a few distinct values, like OS edition. Dev fixed the check. QA also fixed its own test, whose sample data didn't really copy anything.
- Skipped: A12 (the frozen Sep-2026 set, no real data on this machine), A5 (LLM step), A8 (decision rules) and A9 (overrides). The last three are deferred until after the user session.
- Matching on the synthetic sample gives exactly the planted counts in `tests/sample_manifest.md`.
- A full run takes under 0.1 s on 21 rows. That says the code is fast. It doesn't say anything about the 16 h → 1 h claim.

The hands-on number comes from the ITAM team's timed run on Sunday 25-Oct. Until then, the pilot metric has no measured value.
