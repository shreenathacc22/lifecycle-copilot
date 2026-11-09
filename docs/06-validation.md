# 06. Validation

Feedback on `05-product-spec.md` from real people only. A spec isn't validated just because an assistant wrote it.

## Session 1

- Date:
- Who (operator / sponsor):
- What they looked at:

### Questions to ask

Operator:
1. Does this workflow fix the part that actually takes the time?
2. Which exceptions do you need to review yourself, and which can just be listed?
3. Would you review in the app or in the exported Excel?
4. When OS support has ended, is the call Renew or Retire? What decides it?
5. What would stop you using this for the next refresh?

UX questions, from `05a` §7. Show each one in the prototype (https://claude.ai/artifact/K2us8MtdrW4Z3nUCCfo6Ai) while asking. If time is short, ask UX1 and UX2 only.

| # | Show in prototype | Question | Feeds decision |
|---|---|---|---|
| UX1 | Step 3, any item | Would you rather make these calls here, or in the exported Excel with a filter on a Review column? | Review in app vs in Excel |
| UX2 | Step 2 "What changed", step 3 "Listed only" | Which of these do you need to look at yourself, and which can just be listed in Data Quality? (duplicate serial, hostname reuse, OS edition changed, AI date, no citation, no evidence, peers disagree, provenance warning) | Which exceptions need a human |
| UX3 | Step 3, "Windows 11 Enterprise 23H2" | Is one decision for all 27 rows OK, or do you need to see each row? | Grouping rule |
| UX4 | Step 3, "Win10 Ent Eval" | When there's no source, is blank plus Needs review right? | C2 |
| UX5 | Step 3, AI item checkbox | Should you add dates to the policy table, or should someone else approve that? | Policy approval owner |
| UX6 | Step 2, provenance warning | Have you seen a column copied from last period's file? Stop the run, or check and carry on? | A7 handling |
| UX7 | Step 3, Needs review options | "Retire (recommended)" or just "Retire"? When OS support has ended, Renew or Retire? | D2 rule |
| UX8 | Header timer | OK for the tool to time your hands-on minutes, or use a stopwatch? | Timing method |

Also ask: does OS EOL differ from OS EOS for Windows in the TLM sheet?

Sponsor:
1. Does the report help you decide what to upgrade first?
2. Is "Needs review" acceptable in the report you receive?

### What they said (their words)

-

## Decisions

Mark each one accepted, changed or unresolved. Leave it blank until someone has actually decided.

| Item | Status | Decided by | Note |
|---|---|---|---|
| C1 target: 1 h or 45 min | Accepted: 1 h | Product owner, 24-Oct | |
| C2 no evidence → Needs review, not Manage | | | |
| C3 no embedding / AI normalisation in v1 | | | |
| C4 thin review queue and audit log in v1 | | | |
| C5 hostname fallback only when one serial is blank | | | |
| C6 cell-level compare, not byte compare | | | |
| C7 tower coverage count | | | |
| Frozen test set version (open question 1) | | | |
| ServiceNow SAM/HAM license check (open question 2) | | | |
| D2 rule: OS EOS passed → Renew or Retire | | | |
| Placeholder serial list (spec §6 step 1) | | | |
| Review in app vs in Excel (spec §9) | | | |
| Acceptance criteria A1 to A14 | | | |
| Non-goals list (§13) | | | |
| OS fill order: policy, vendor rule, then peers (§7 proposed change) | PM provisional yes | | Needs product owner OK |
| A7 positional-copy definition (paired by serial) | Accepted for build | PM, 24-Oct | Matches the spec's intent; wording fixed |
| Grouping rule (UX3) | | | |
| Policy approval owner (UX5) | | | |
| Timing method (UX8) | | | |
| Windows OS EOL vs OS EOS | | | |
