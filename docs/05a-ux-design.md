# 05a. UX design: Lifecycle Copilot v1

Status: **draft, not validated.** Built from `05-product-spec.md`. No operator has seen it yet.
Drafted 24-Oct-2026. Validation session with the ITAM operator: Sun 25-Oct-2026, 10:10 AM PT (covers 05, 05a and 06).

Prototype: `prototype/review-flow.html` (clickable, synthetic data only). It's for the validation session only. The demo build is CLI only, and nothing from the prototype goes into `src/`.

---

## 1. Who is at the screen

| | |
|---|---|
| Operator | ITAM analyst doing one tower refresh per period **[unvalidated]** |
| Setting | Laptop. Excel with last period's sheet is probably open next to the app. |
| Frequency | One refresh per tower per period. Nobody gets fast through practice. Every screen has to make sense the first time, or after a month away. |
| Time budget | 1 h hands-on for the whole refresh (C1 closed 24-Oct-2026 by the product owner). The UI's job is to spend that hour on the hard rows only. |
| What they already trust | The six-sheet workbook. The app produces that workbook. It doesn't replace it. |

## 2. UX rules

Each rule comes from an invariant or acceptance criterion in `05`. If a screen breaks one of these, it's a bug.

| # | Rule | Comes from |
|---|---|---|
| X1 | **Rows in = rows out is always on screen.** Every step shows the current row count and where every row went. A count that doesn't add up turns red. | I4, A4 |
| X2 | **Every filled value shows where it came from.** A small chip next to the value, same words as Remarks. | I3 |
| X3 | **AI proposals look different and are never pre-accepted.** Dashed outline, "AI proposed" label, citation link next to the value. No citation means no value is shown. | A5, §7 |
| X4 | **Unknown stays visible.** "Needs review" is its own state with its own colour. It never falls back to Manage. | C2, A8 |
| X5 | **Review only what needs a person, and group identical decisions.** Thirty laptops of the same model with the same missing date are one decision, not thirty. This is where most of the hour gets saved. | U6 |
| X6 | **A blocking problem stops the run in plain words.** Name the column, say what's wrong, say what to do. | A7, U2 |
| X7 | **Use the sheet's own words.** Disposition, Remarks, Asset EOS, OS EOS, Dropped. Don't use internal terms like "match edge", "basis enum" or "lifecycle_value". | U8 |
| X8 | **Keyboard first in the review queue.** J/K to move, A accept, E edit, R reject. Mouse works too. | 1 h target |
| X9 | **Overrides say they'll stick.** Any edit shows "applies next period too", so nobody is surprised next month. | U7, A9 |

### Where-it-came-from chips (X2)

| Chip | Meaning | Look |
|---|---|---|
| From CMDB | Supplied by this period's export | plain, no fill |
| Carried | Inherited from last period's sheet | grey |
| Policy | Approved policy table | solid accent |
| Peer | Same model, consistent value | outline accent |
| Vendor rule | Approved vendor rule (e.g. Microsoft 24/36 months by edition) | outline accent |
| AI proposed | LLM proposal with citation, waiting for review | dashed amber |
| You | Human override | dark solid |

## 3. Flow

Four steps, always in this order. The step bar at the top shows where you are, and you can go back to any finished step.

```
1 Upload  ──>  2 Check  ──>  3 Review  ──>  4 Export
two files      blocking       only rows that   preflight list,
               problems,      need a person    download workbook
               row counts
```

Run history sits outside the flow (one link in the header).

## 4. Screens

### 4.1 Upload (U1, U2)

- Tower is fixed to **EUC Windows** in v1 and shown as a label, not a dropdown. One less decision to make.
- Two drop zones side by side: **This period's CMDB export** and **Last period's TLM sheet**. Each shows the file name, row count, sheet name and a short file fingerprint once it's loaded.
- Period is read from the file name if it can be, and can be edited.
- Header check runs as soon as a file lands. It lists the required columns (Serial, Hostname, OS name, OS version, edition) with a tick or a cross.
- Errors, in plain words:
  - Wrong file type: "This is a .csv. Upload the .xlsx export from ServiceNow."
  - Missing column: "No Serial Number column found. Expected a header like 'Serial Number'. Found: Serial No., Asset Tag…" plus the list of headers it saw.
  - Same file twice: "Both files are identical. The prior sheet should be last period's finished report."
- **Run matching** stays disabled until both files pass.

### 4.2 Check (U2, U4, U9, A7)

The first thing on screen is the provenance result, because it can stop everything.

- **Blocking: positional copy (A7).** "Column 'Assigned To' is identical, row for row, to last period's file (1,198 of 1,198 rows). This usually means the export was built by pasting the old sheet." Two choices: **Stop and re-export** (default) or **I've checked, continue**. The second needs a one-line reason and is written to the run log.
- **Reconciliation equation (X1).** Shown as two sums, not a pie chart:
  - This period: matched by serial + matched by hostname + new = rows in
  - Last period: matched by serial + matched by hostname + dropped = prior rows
  Each number links to the rows behind it.
- **What changed** (info only): OS edition changed (dates recomputed), hostname changed on same serial, carried forward rows.
- **Review queue size**, split by type, with a rough time estimate. Next button: **Start review (n items)**.

### 4.3 Review (U5, U6, U7, A3, A5, A8, A9)

Layout: queue on the left, the selected item on the right. On a narrow screen the queue goes above the item.

| Queue group | What the operator does | Grouping | Default |
|---|---|---|---|
| Duplicate serial (A3) | Pick which prior row each current row continues, or "neither". | One item per serial | Nothing chosen. All rows stay in Report either way. |
| AI-proposed dates (A5) | Check the cited page. Accept, edit the date, or reject (leaves it blank). Optional: add to policy table. | By product + version + edition | Not accepted |
| Needs review (A8) | Choose Manage / Renew / Retire, or leave it as Needs review. Short reason required for anything other than leaving it. | By model | Leave as Needs review |
| Peer conflict | Pick which peer value is right, or none. | By model | None |
| Listed only (no action) | Hostname reuse (treated as replaced hardware), OS recomputes. Read-only, collapsed by default. | By type | n/a |

The item panel always shows:
- **This period vs last period** side by side, changed fields highlighted.
- **Why it's here**: the rule that fired, in one sentence ("Serial 5CG2141KQ7 appears twice in this period's export").
- **Rows affected** with a count and a list you can expand.
- For AI proposals: the proposed value, the citation as a link, and the quoted line from the page it relied on.
- After an action: "Accepted for 27 rows. Applies next period too. Undo."

Every action writes who, when, old value, new value to the review log (§9 of `05`).

Leaving with open items is allowed. The header shows "4 open", and the export says so too.

### 4.4 Export (U8, U9, A4, A13)

A preflight list, then one button.

- ✓ Rows in = rows in Report (1,240 = 1,240)
- ✓ Provenance warning acknowledged (by whom, reason)
- ! 4 review items open. They'll show as Needs review in Report and be counted in Summary.
- ✓ No vendor date without a citation
- The six sheets with their row counts: Report, Summary, Matching Logic, Match Detail, Dropped, Data Quality.
- **Download workbook**. The file name follows the current convention, e.g. `EUC-Windows_TLM_2026-10.xlsx` *(convention to confirm)*.

### 4.5 Run history

A plain table: date, period, operator, file fingerprints, rows in, open items at export, hands-on time. It answers "what did we send last month and from which files".

## 5. Hands-on timer (idea, needs operator OK)

`03-success-metric.md` needs measured hands-on time. The app could time it: it runs while the app is in front and the operator is active, pauses after 2 minutes idle, and shows in the header. It gets saved with the run. This is only switched on with the operator's agreement, and the number is shown to them, not hidden. Otherwise we time it with a stopwatch.

## 6. States every screen needs

| State | Treatment |
|---|---|
| Empty | Says what goes here and what to do first |
| Working | Shows which stage is running (reading, matching, filling dates). No bare spinner. |
| Error | What went wrong, which file or column, how to fix it |
| Partial | Run finished with open review items. Allowed, always counted. |
| Done | Workbook downloaded, run saved to history |

## 7. UX questions for the validation session (merge into `06`)

For the ITAM operator, Sun 25-Oct 10:10 AM PT. Ask while the prototype is on screen, one step at a time. Write down their words in `06`, not a summary. UX1 and UX2 matter most because they change what gets built.

| # | Show in prototype | Question | Why it matters | Decision it feeds in `06` |
|---|---|---|---|---|
| UX1 | Step 3, any item | "Would you rather make these calls here, or in the exported Excel with a filter on a Review column?" | If Excel, v1 needs no review screen. The CLI writes a review column and reads decisions back. Changes the build plan. | Review in app vs in Excel (`05` §9) |
| UX2 | Step 2 "What changed" and step 3 "Listed only" | "Which of these do you need to look at yourself, and which can just be listed in the Data Quality tab?" Go through: duplicate serial, hostname reuse, OS edition changed, AI-proposed date, no citation, no evidence (Needs review), peers disagree, provenance warning. | Sets what goes in the review queue and what's listed only. | Which exceptions need a human (`06` operator Q2) |
| UX3 | Step 3, "Windows 11 Enterprise 23H2" | "Is one decision for all 27 rows OK, or do you need to see each row?" | Grouping is the main time saver toward the 1 h target. | Grouping rule |
| UX4 | Step 3, "Win10 Ent Eval" | "When there's no source, is leaving it blank and marking Needs review right?" | Checks C2 / A8 with the person who uses the report. | C2 |
| UX5 | Step 3, AI item checkbox | "Should you be the one adding dates to the policy table, or should someone else approve that?" | Who owns approved policy facts. | Policy approval owner |
| UX6 | Step 2, provenance warning | "Have you seen a column copied from last period's file? Would you stop the run, or check and carry on?" | Whether the blocking step fits real practice. | A7 handling |
| UX7 | Step 3, Needs review options | "Retire (recommended)" or just "Retire"? And when OS support has ended, is it Renew or Retire? | Wording, and feeds the D2 rule. | D2 rule |
| UX8 | Header timer | "Is it OK if the tool times your hands-on minutes, or would you rather we use a stopwatch?" | Measured baseline for `03`. | Timing method |

If time runs short, ask UX1 and UX2 only.

## 8. What the prototype is and isn't

- It **is** a clickable walk through the four steps with one synthetic EUC Windows run, so the operator can react to layout and wording.
- It **isn't** connected to anything. No files are read, no workbook is produced, nothing is saved.
- All hostnames, serials and counts are made up. No real export data.

## 9. Traceability

| Story / criterion | Screen |
|---|---|
| U1 upload | 4.1 |
| U2 / A7 positional copy | 4.1 header check, 4.2 blocking |
| U3 / U4 matching visible | 4.2 equation, 4.3 duplicate serial |
| U5 / A5 fill with basis | 4.3 AI proposals, chips everywhere |
| U6 review only what needs me | 4.3 grouping |
| U7 / A9 sticky override | 4.3 "applies next period" |
| U8 / A13 familiar workbook | 4.4 |
| U9 / A4 counts | header count, 4.2, 4.4 |
| A8 no evidence → Needs review | 4.3 Needs review group |
| R1 / R2 consumer | Out of the app. Served by the workbook's Report and Data Quality tabs. |
