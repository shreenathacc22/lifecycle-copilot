# Simulated operator acceptance test, 24-Oct

**This is QA role-playing the ITAM team. It is not interview evidence.** Nothing here goes into `02` or `06`. Use it to prepare for Sunday's real session, and check every point with the ITAM team there.

Run: `lifecycle-copilot run` on the synthetic sample (11 current, 10 prior rows). It took 0.01 s and wrote all 6 sheets. All 45 automated tests pass.

## Would I send this workbook to leadership?

Not yet. The matching is right and I can follow every decision on Match Detail. But the Report sheet, the one leadership reads, hides things I'd have to fix by hand before sending.

## Blocking (I'd have to fix it by hand every refresh)

| # | What I saw | Why it matters to me | Ask |
|---|---|---|---|
| U1 | New and replaced devices get Asset EOL/EOS copied from older devices of the same model. WKS-0003 is brand-new hardware that replaced an old box, and it got the old box's peers' date (31-Jan-2027). WKS-0008 is the same. | If asset EOS is based on purchase or ship date, a laptop bought this year would show as needing replacement next January. That's wrong, and it's exactly the row leadership would ask about. | Confirm with the ITAM team what Asset EOS means: the model's vendor end of support, or a refresh date from the ship date. If it's ship date, turn off peer fill for asset dates and leave them blank with a reason. (`product.md` open question 3.) |
| U2 | The Report sheet has no review flag. WKS-0004A and WKS-0004B (duplicate serial) look like normal rows with full dates. Only Match Detail says "review". | I work in Report, and leadership only sees Report. Unresolved rows would go out looking finished. | Add a status column to Report (matched / new / needs review) or highlight the review rows. Also skip peer-filling dates on rows whose identity isn't resolved yet. |
| U3 | A source OS EOS of 01-Jan-2030 against Microsoft's 12-Oct-2027 (WKS-0010) is logged as **info** only. | A date 2 years off from Microsoft is either a typo or a bad extract. I need to see it, not find it in a list of info lines. | Make `policy_mismatch` a warning, and put it in the console output. Keep the source value (rule I2). |

## Should fix before the real trial

| # | What I saw | Ask |
|---|---|---|
| U4 | Summary's OS EOS lines (6 policy + 3 carried + 0 peers + 1 blank) add up to 10, not 11. The 11th row's date came from the source file, and there's no line for it. | Add "OS EOS from source" so the counts add up. I check that before sending. |
| U5 | Every row's Remarks repeat the full Microsoft URL and "OS EOL left blank: ... confirm with the ITAM team". On a few thousand rows that's mostly noise. | Put the source URL once on Matching Logic, or on a Sources sheet, and use a short tag per row. Keep the global OS EOL note on Matching Logic only. |
| U6 | Disposition is carried forward even when the OS changed. WKS-0007 kept "Manage" from when it was on Pro. | Same root cause as QA finding 1 in spec review. When the OS changed, don't carry the disposition, or flag it for review. |
| U7 | Policy table has only Windows 10 22H2. No Windows 10 21H2 and no LTSC versions (Windows 10 LTSC 2019/2021, Windows 11 LTSC 2024), which EUC fleets often still have for kiosks and shop-floor PCs. | Every such device comes out blank. Add those rows from Microsoft's lifecycle pages before Sunday, or expect a lot of blanks on real data. |
| U8 | The OS Edition column in Report is blank on every row. The edition is only inside the Operating System name. | Either fill OS Edition from the parsed name (it's a derived value, so give its basis) or drop the column. A blank column next to an edition change looks like missing data. |
| U9 | Dropped includes the duplicate-serial prior row with status "needs review". | Fine with the Status column, but name the sheet "Dropped and unresolved" or move review rows to their own sheet. |

## Worked well

- Match Detail reasons are clear: "hostname WKS-0003 reused, serial changed from SN-OLD-003" is exactly what I'd write by hand.
- The Summary check rows ("... = current rows: OK") are the first thing I'd look at.
- Placeholder serials (`To be filled by O.E.M.`, `N/A`) were handled without me doing anything.
- Build numbers like `10.0.22631.4317` map to 23H2, so the lookup should cope with real exports.
- Dates are real Excel dates (`dd-mmm-yyyy`), the header row is frozen, and the existing column layout is kept.
- Leaving OS EOL blank with a stated reason is better than guessing.

## Questions to take to the real session

1. What does Asset EOS mean in our sheet: model support end or refresh date? (U1)
2. Do you work in Report or Match Detail? Where do you want review rows? (U2)
3. Is a source date that disagrees with Microsoft a typo, or sometimes deliberate (extended support, ESU)? (U3)
4. Which Windows 10 and LTSC versions are still in the fleet? (U7)
5. When the OS changes, does the old disposition still stand? (U6)

Not verified by QA: the 26H1 dates in `data/policy/windows_os.csv`.

---

## Re-test after dev's fixes, 24-Oct evening

Still a simulation by QA, not interview evidence. Suite: 67 passed, 0 failed, 4 skipped. A full CLI run takes 0.09 s.

| # | Result | What I checked |
|---|---|---|
| U1 | **Closed** (pending meaning question) | Copying asset dates from same-model peers is off by default. New and replaced devices are blank, and Remarks say peer fill for asset dates is off. `--peer-asset-dates` turns it back on. |
| U2 | **Closed** | Report has Status and Match Method columns. WKS-0004A and WKS-0004B say Needs review, are shaded, and got no peer values. |
| U3 | **Closed** | A warning in the console and on DQ. The Report Remarks for WKS-0010 now say "Source OS EOS differs from Microsoft 12-Oct-2027; kept". |
| U4 | **Closed** | OS EOS lines: 1 source + 6 policy + 3 carried + 0 peers + 1 blank = 11. |
| U5 | **Closed** | No URLs or OS EOL notes in Remarks. The sources are listed once on Matching Logic. |
| U6 | **Closed as a flag** | DQ warning `disposition_carried_os_change` on WKS-0007. The rule itself waits for Sunday. |
| U7 | **Closed** | Windows 10 and LTSC rows are loaded. Builds 19044 and 26100 resolve differently for LTSC, and LTSC never borrows the general-channel date (tests). QA checked LTSC 2019, IoT LTSC 2024 and Win10 21H2 Enterprise against Microsoft's lifecycle pages: all match. |
| U8 | **Closed** | OS Edition is filled from the OS name on every row. |
| U9 | **Open** | Not in this round. Dropped still includes the review row. Minor. |

New from the re-test:

- **N1. Closed.** The Matching Logic "Fill blanks" text now depends on the switch: "Asset EOL/EOS: carried forward only. Peer fill is off for this run."
- **N2. Most asset dates are now blank.** Summary shows Asset EOS still blank on 7 of 11 rows. That's the honest result with peer fill off, but on real data most new devices will be blank. Taking it to Sunday as part of the U1 question.
