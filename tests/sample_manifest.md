# Synthetic sample: planted cases and expected counts

Owner: QA. Agreed with dev before `scripts/make_sample.py` is final. If the sample changes, change this file in the same edit, and the tests will follow it.

All values are made up. Serials start `SN-`, hostnames start `WKS-`. No real assets.

## Fields used

serial, hostname, os_name, os_version, os_edition, model, os_eos. Header names in the xlsx are whatever dev's canonical mapping uses. The tests only use the canonical names.

## Rows

C = `data/sample/current.xlsx`, P = `data/sample/prior.xlsx`.

| Case | Current | Prior | Expected | Spec |
|---|---|---|---|---|
| CLEAN | C1 SN-CLEAN-001, ` wks-0001 ` (lower case, spaces) | P1 SN-CLEAN-001, WKS-0001 | serial match | §6 step 1, 2 |
| HOST_ONLY | C2 serial blank, WKS-0002 | P2 SN-HOST-002, WKS-0002 | hostname match | A10 |
| HOST_REUSE | C3 SN-NEW-003, WKS-0003 | P3 SN-OLD-003, WKS-0003 | no match. C3 new, P3 dropped, DQ hostname_reuse | A1 |
| DUP_SERIAL | C4a SN-DUP-004, WKS-0004A and C4b SN-DUP-004, WKS-0004B | P4 SN-DUP-004, WKS-0004A | no auto-match. C4a, C4b and P4 go to review, DQ duplicate_serial | A3 |
| PLACEHOLDER | C5 `To be filled by O.E.M.`, WKS-0005 | P5 `N/A`, WKS-0005 | both serials count as blank, hostname match, DQ placeholder_serial | §6 step 1 |
| HOST_DUP_PRIOR | C6 serial blank, WKS-0006 | P6a SN-H6A-006, WKS-0006 and P6b SN-H6B-006, WKS-0006 | no match. C6 new, P6a and P6b dropped, DQ entry | A11 |
| EDITION_CHANGE | C7 SN-ED-007, Windows 11 23H2 **Enterprise**, os_eos blank | P7 SN-ED-007, Windows 11 23H2 **Pro**, os_eos 2025-11-11 | serial match. os_eos becomes 2026-11-10 (basis policy), Remarks say edition changed | A2 |
| NEW | C8 SN-NEW-008, WKS-0008 | none | new | §6 step 5 |
| DROPPED | none | P9 SN-GONE-009, WKS-0009 | dropped, with reason | §6 step 6 |
| SOURCE_VALUE | C10 SN-SRC-010, Windows 11 24H2 Enterprise, os_eos **2030-01-01** (source value, wrong on purpose) | P10 SN-SRC-010 | serial match. os_eos stays 2030-01-01 | A6 |
| NO_EVIDENCE | C11 SN-NOEV-011, Windows 11 Enterprise **28H2** (doesn't exist yet, so it can never be in the policy table) | none | new. os_eos blank with a reason | M4, A8 later |

C11 used to be Windows 10 21H2. That stopped testing "no evidence" once real Windows 10 rows were added to the policy table (U7). Use a version that can't exist yet.

## Expected counts

Current file: **11 rows**.

| method | count | rows |
|---|---|---|
| serial | 3 | C1, C7, C10 |
| hostname | 2 | C2, C5 |
| new | 4 | C3, C6, C8, C11 |
| needs review | 2 | C4a, C4b |
| **total** | **11** | |

Prior file: **10 rows**.

| outcome | count | rows |
|---|---|---|
| matched | 5 | P1, P2, P5, P7, P10 |
| dropped | 4 | P3, P6a, P6b, P9 |
| needs review | 1 | P4 |
| **total** | **10** | |

Summary check, corrected from build plan M6: serial + hostname + new + needs review = current rows, and matched + dropped + prior needs review = prior rows. The M6 version (serial + hostname + new = current) leaves out duplicate serials and won't add up.

## Policy table (synthetic copy of public Microsoft dates)

| product | version | edition | os_eos |
|---|---|---|---|
| Windows 11 | 23H2 | Pro | 2025-11-11 |
| Windows 11 | 23H2 | Enterprise | 2026-11-10 |
| Windows 11 | 24H2 | Pro | 2026-10-13 |
| Windows 11 | 24H2 | Enterprise | 2027-10-12 |

Source: learn.microsoft.com/en-us/windows/release-health/windows11-release-information, checked 24-Oct-2026. The same version with two editions gives two dates, which covers the M4 check.

## Not in the main sample

- **A7 positional copy.** The test builds its own pair in a temp folder. Rows are reordered so serials don't line up, and one column is copied by row position from the prior file. A second pair, where Manufacturer is simply unchanged, must **not** trip the check.
- **Bad files.** Empty xlsx, a `.csv` renamed to `.xlsx`, and a missing required column. All are built in a temp folder by the test.
