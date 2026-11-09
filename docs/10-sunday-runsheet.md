# 10. Sunday run sheet (25 Oct)

Owner: PM. Times are Pacific.

## Before 10:10 (owner, 10 minutes)

- Open a terminal in `Lifecycle_copilot` and run `.venv/bin/python -m pytest -q`. Expect 157 passed, 4 skipped.
- Run the demo once so the file is fresh:
  `.venv/bin/lifecycle-copilot run --current data/sample/current.xlsx --prior data/sample/prior.xlsx --out output/`
  It prints the warnings and writes `output/lifecycle-copilot-report.xlsx` in well under a second.
- Open the prototype link from `06` in a browser tab. Decide whether you share it or drive it on screen.
- Have a stopwatch ready (UX8, unless the operator OKs the built-in timer).
- Sample data only. No real CMDB export on screen or on this machine.

## 10:10 to 12:30: session with the ITAM operator (M5)

| Time | What | Output |
|---|---|---|
| 10:10 | Show the problem in one minute: the two input files, then the six-sheet workbook | |
| 10:15 | The operator works the sample report as they would a real refresh. Time hands-on minutes only. | Measured minutes against the 1 h target |
| 10:45 | Operator questions 1 to 5 from `06` | Their words, in `06` "What they said" |
| 11:05 | UX1 and UX2 first, then UX3 to UX8 if time allows. Ask OS EOL vs EOS. | Answers in `06` |
| 11:30 | Ask for the three decisions we need: what "Asset EOS" means, the disposition rule when OS support has ended (D2, U6), and sign-off on the OS fill order (policy, then vendor rule, then peers) | Rows in `06` Decisions |
| 11:45 | Sponsor questions, if the sponsor joins | |
| 12:00 | PM writes up `02`, `06`, `03`; dev lists any change it implies | Notes done by 12:30 |

Rule for the session: write down what they say, not what we hoped. No new build during the session. Changes wait until after Demo Day unless they are a one-line fix.

## 1:15: Defend

Two audiences, two minutes each.
- **The ITAM operator's manager:** the hands-on time measured this morning, against about 2 days by hand. Nothing is overwritten, every filled value says where it came from, and Retire is only ever a recommendation.
- **Technical reviewer:** deterministic matching (serial, then unique hostname, never fuzzy), every row kept, exceptions as their own tabs, 157 tests, Windows dates sourced from Microsoft.
- Known limits, said out loud: one tower (Windows end-user devices), CLI only, sample data only, dates outside the policy table are left blank and flagged.

## 2:00 to 3:30: Demo Day

1. One sentence: what it does and for whom.
2. Run the demo command live (under a second). Read two of the warnings: replaced hardware, and the source date that differs from Microsoft's.
3. Open the workbook: Report, then Matching Logic, then Data Quality.
4. Show the measured time from this morning.
5. Show the site, memorymanager.stream, and the waitlist form (live since 8:41 AM). Don't submit a real address on screen.

Fallback if the laptop fails: the board and the site still work from a phone. Keep a copy of `output/lifecycle-copilot-report.xlsx` somewhere you can open without the terminal.

## After 3:30

- The VM stays on (owner, 25-Oct). The site and waitlist stay live.
- PM updates the board and `00` with the session results.
