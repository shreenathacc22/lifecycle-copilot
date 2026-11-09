# 05. Product spec: Lifecycle Copilot v1

Status: **draft, not validated.** Nothing in here has been shown to the operator yet. See `06-validation.md`.
Drafted 24-Oct-2026 from docs 01 to 04, `product.md` and the build spec (`tlm_ai_product_build_spec-1024.md`).

Interview evidence: none yet. Anything that depends on how the ITAM team actually works is marked **[unvalidated]**.

---

## 0. Contradictions, unsupported claims and questions

Sort these out before the spec is accepted.

### Contradictions

| # | Where | Conflict | Proposed resolution |
|---|---|---|---|
| C1 | Forge draft / `03` vs build spec / guide | Target is 1 h in one place and 45 min in the other | **Resolved 24-Oct: 1 h hands-on** (product owner). |
| C2 | Build spec §5 Decide vs guide rule | Build spec falls through to `ELSE → Manage`. The guide says missing evidence means Unknown / Needs review, not Manage. | Guide wins. A row with no OS EOS and no asset EOS gets **Needs review**, not Manage. See §8. |
| C3 | Build spec §8.1 vs I1 | Build spec lists "entity normalisation" using embeddings to tie model names together. That's fuzzy matching by another name. | Out of v1. If it ever comes in, it may only normalise **model names for policy lookup**, never asset identity, and it always goes to review. |
| C4 | Build spec §9 vs guide prompt | Build spec puts override UI and audit log in v1.1. The guide says citations, review and audit history are in v1. | In v1, but thin: a review queue, sticky overrides and a run log. No polished UI. |
| C5 | Build spec §3.3 vs `product.md` I1 | Build spec allows hostname fallback when "prior row has no serial OR the same serial". If the serial were the same, the serial step would already have matched. | Hostname fallback only when **at least one side has a blank serial**, and the name is unique in both files. If both serials are present and different, it's replaced hardware: no match. |
| C6 | Build spec §8.3 / §11 | "Byte-compare the export against the known-good workbook". Two openpyxl saves won't be byte-identical (timestamps, metadata). | Compare cell values, headers and date types instead of bytes. |
| C7 | `01` vs build spec §11 | "3 of 9 towers never done" vs "4 / 9 towers with coverage". That leaves 2 towers unaccounted for. | Check the real tower list. Partial coverage probably explains it. |
| C8 | Guide §4 vs `01` | Guide names the sponsor by name. `01` says "Infrastructure leadership". | Keep the role in shared docs. Confirm the name privately. |

### Unsupported claims (true maybe, but not measured)

- About 16 h per tower. Estimate only. Needs one timed run (`03` measurements log).
- About 39% of assets have a defensible dated EOL/EOS (build spec). Source not stated in the shareable doc.
- "The Sep-2026 refresh is the known-good answer." The build spec also says a real run understated risk and needed a correction pass. Is the frozen set the corrected version?
- That the tool removes dependence on me. Only true once someone else runs it (the ITAM team, timed).
- That no existing tool does this. `04` found none doing period-over-period reconciliation, but we haven't checked what ServiceNow licenses we hold.

### Open questions

1. Which version of the Sep-2026 workbook is the frozen test set, and who signs it off?
2. Do we already license SAM Pro / HAM Pro lifecycle content? If yes, OS and model dates should come from there first. (`04`)
3. Where does asset EOL come from with no ship date in the CMDB? v1 answer: carry forward, policy table, peers, otherwise blank plus reason.
4. Who owns the org map (Tribe, Line, Team, DG)? v1 answer: carry forward only, never invented.
5. When OS EOS has passed, is the call Retire or Renew? The build spec says "(policy)". Need the actual rule.
6. ~~Is the ITAM team willing to test, and when?~~ Yes, Sun 25-Oct 10:10 AM PT.

---

## 1. User and job

| | |
|---|---|
| Primary operator | ITAM analyst who refreshes the tower extracts (ITAM team, confirmed for Sun 25-Oct) |
| Backup operator | CMDB extract owner |
| Report consumer | Infrastructure leadership |
| Not the operator | Me. If only I can run it, the problem isn't fixed. |

**Job:** Given a raw CMDB export and last period's TLM sheet for one tower, produce the finished lifecycle workbook. Every row gets EOL/EOS dates (or an honest blank), a Manage / Renew / Retire / Needs review call, and the reason for every value the tool filled in.

## 2. Problem

One tower takes about two days by hand: match the export to last period's sheet, look up vendor dates one at a time, decide each row, and write it up. Duplicate serials and reused hostnames need extra checks. Three of nine towers have never been done. Only one person can run it. (`01`)

## 3. First-release scope

**In**
- One tower: EUC Windows
- Upload the current CMDB export and the prior TLM sheet (`.xlsx`)
- Keep every source row (I4)
- Deterministic matching, tested (I1)
- Carry forward on match, recompute OS dates when the OS changed
- Fill blanks from: approved policy table, then peers, then vendor rules, then cited LLM proposal (I2, I3)
- Decision with rationale
- Review queue for exceptions and AI proposals, with sticky human overrides
- Six-sheet export: Report, Summary, Matching Logic, Match Detail, Dropped, Data Quality
- Run log / audit history in local SQLite

**Out (non-goals)** in §13.

## 4. User stories

| # | As the operator I want to... | So that... |
|---|---|---|
| U1 | upload this period's export and last period's sheet | I don't have to copy columns by hand |
| U2 | see the upload rejected if a column is a positional copy of last period's file | a bad extract doesn't silently corrupt the report (I6) |
| U3 | have rows matched by serial, then by a safe hostname rule | I stop doing the matching by hand |
| U4 | see every match, non-match and dropped row with its reason | I can check the matching without redoing it |
| U5 | have blank dates filled with a stated basis | I stop looking up vendor pages one at a time |
| U6 | review only the rows that need me (conflicts, AI proposals, no evidence) | my time goes on the hard cases |
| U7 | override any value and have it stick next period | my judgment isn't recomputed away |
| U8 | download a workbook that looks like the one leadership already reads | nobody has to learn a new format |
| U9 | see the run's counts in a Summary tab | I can sanity-check before sending |

As the report consumer:

| # | I want to... | So that... |
|---|---|---|
| R1 | see which assets are past or near vendor support, with a recommendation | I can prioritise upgrades |
| R2 | see what the report couldn't determine | I know where the gaps are |

## 5. Inputs and outputs

### Inputs

| Input | Format | Notes |
|---|---|---|
| Current CMDB export | `.xlsx`, one tower | Columns per build spec §4.2 / §5. Headers normalised on ingest (double spaces, typos, `Unnamed:` columns dropped). |
| Prior TLM sheet | `.xlsx`, same tower | Canonical 21 core columns plus delivered extensions (Disposition Strategy, Disposition Date, Remarks, Ship Date). |
| Lifecycle policy table | SQLite, loaded from the EOL-EOS reference sheet | Keyed on vendor + product + version + **edition**. Approved facts only. |
| Org map | Carried forward from the prior sheet | No separate source in v1. |

Only synthetic or approved de-identified files in `data/sample/`.

### Outputs

One `.xlsx` with six sheets:

| Sheet | Content |
|---|---|
| Report | Every current row, canonical schema, legacy headers, real Excel dates |
| Summary | Totals: rows in, matched by serial, matched by hostname, new, dropped, blanks remaining, duplicates, needs review |
| Matching Logic | The rules applied this run, plus caveats |
| Match Detail | Per row: method, prior keys, what changed (OS, edition, hostname) |
| Dropped | Prior rows with no current match, with reason |
| Data Quality | Every duplicate, conflict, reused hostname, provenance warning |

## 6. Deterministic matching rules

1. **Normalise** serial and hostname: trim, upper-case, strip zero-width characters. Blank or placeholder serials (for example `N/A`, `0`, `To be filled by O.E.M.`) count as blank. *(placeholder list to confirm with operator)*
2. **Serial match**: exact match on normalised serial → `method = serial`.
   - If a serial appears more than once in either file, those rows **do not auto-match**. They go to review with a DQ entry. All rows are kept.
3. **Hostname fallback**, only if all of these hold:
   - the row didn't match by serial
   - the hostname is unique in the current file **and** in the prior file
   - at least one side has a blank serial
   → `method = hostname`
4. Same hostname, both serials present and different → **no match**. Treat as replaced hardware. Log in Data Quality as hostname reuse.
5. Anything else → `method = none` (new asset).
6. Prior rows with no match → Dropped, with reason.

Never fuzzy, Levenshtein, similarity score or "closest match". AI never matches assets.

## 7. Lifecycle-policy evidence

### Carry forward (on match)

Inherit: Asset EOL/EOS, OS EOL/EOS, Disposition Strategy and Date, Remarks, org fields, Ship Date.
Conditional: FQDN only if the hostname didn't change.
**Not** inherited when OS name, version **or edition** changed: OS EOL/EOS are cleared and recomputed. Remarks say so.
Never inherit anything the CMDB supplies this period.

### Fill blanks (I2: blanks only, never overwrite)

| Order | Source | `basis` value | Goes to review? |
|---|---|---|---|
| 1 | Approved policy row on vendor + product + version + edition | `policy` | No |
| 2 | Peers: same model, one consistent value across them | `peer` | No, but listed in DQ if peers disagree |
| 3 | Vendor rule (for example Microsoft 24 / 36 month by edition) | `vendor_rule` | No, if the rule is in the approved table |

**Proposed change (qa, 24-Oct; PM provisional yes, product owner sign-off pending):** for OS fields the order is policy, then vendor rule, then peers, because OS dates depend on OS version and edition, not the hardware model. The order above stays for hardware/asset fields.
| 4 | LLM proposal with a citation URL | `llm_proposed` | **Yes, always** |
| 5 | Nothing found | blank + reason | Yes |

Rules:
- AI proposals are stored apart from approved policy. They only become policy when the operator approves them.
- No vendor date without a citation. No citation → blank.
- Every filled value writes its basis to Remarks (I3), for example `OS EOS from policy: Windows 11 Enterprise 24H2, learn.microsoft.com/... (approved 2026-10-24)`.
- For EUC Windows, rows 1 and 3 should cover nearly all OS dates (Microsoft publishes them by version and edition, see `04`). The LLM step is for leftovers. **[hypothesis]**

## 8. Decision rules

Evaluated top to bottom. First match wins. Human override always wins and is never recomputed.

| # | Condition | Call |
|---|---|---|
| D0 | Human override exists | keep it |
| D1 | Same-model peers already carry one consistent disposition | reuse it |
| D2 | OS EOS < today | Renew or Retire **(rule to confirm, open question 5)** |
| D3 | Vendor marks the model obsolete | Retire (recommendation only) |
| D4 | Vendor marks the model vintage and EOS < today + 12 months | Renew |
| D5 | Asset EOS < today | Renew |
| D6 | OS EOS and asset EOS both known and in the future | Manage |
| D7 | Not enough evidence | **Needs review** |

Retire is always a recommendation. Every call writes a one-line rationale.

## 9. Review workflow

1. The run finishes and lists the review queue: duplicate serials, LLM proposals, Needs review rows, peer conflicts, provenance warnings.
2. For each item the operator can **accept**, **edit** or **reject**. Each action is logged with who, when, old value and new value.
3. Accepted LLM dates can be promoted to the policy table (with source URL and date).
4. Overrides are stored and applied first on the next run (D0).
5. Export is allowed with open review items, but the Summary shows how many are open.

Thin UI or CLI for v1. **[unvalidated: does the operator want to review in the app, or in the exported Excel?]**

## 10. Data model (SQLite for v1)

Per build spec §6, with these changes:

```
run(run_id, tower, period, current_file_hash, prior_file_hash,
    policy_snapshot_id, model_id, started_at, finished_at, operator)

asset_row(run_id, row_no, source ENUM('current','prior'),
          serial_norm, hostname_norm, raw_payload JSON)        -- every row kept (I4)

match_edge(run_id, current_row_no, prior_row_no,
           method ENUM('serial','hostname','none'), reason)

lifecycle_value(run_id, row_no, field, value,
                basis ENUM('source','carried','policy','peer','vendor_rule','llm_proposed','human'),
                citation_url, note)

lifecycle_policy(id, vendor, product, version, edition, model_id,
                 eol_date, eos_date, basis, source_url, asserted_at,
                 status ENUM('approved','proposed'))

disposition(run_id, row_no, call ENUM('Manage','Renew','Retire','Needs review'),
            rule_id, rationale)

override(asset_key, field, value, by, at, reason)             -- sticky across runs

dq_issue(run_id, severity, category, row_no, detail)

review_log(run_id, item_ref, action ENUM('accept','edit','reject'),
           old_value, new_value, by, at)
```

Same inputs plus the same policy snapshot plus the same pinned model give the same output.

## 11. Acceptance criteria

Each one becomes a test. Synthetic data unless the frozen set is approved.

| # | Given | Then |
|---|---|---|
| A1 | Current and prior rows share a hostname but have different, non-blank serials | No match. Current row is new, prior row is Dropped, DQ logs hostname reuse. |
| A2 | Matched row whose OS edition changed from Pro to Enterprise | OS EOL/EOS are not carried. They're recomputed from the Enterprise policy row. Remarks say why. |
| A3 | A serial appears twice in the current file | Neither row auto-matches. Both are in Report. Both are in the review queue. DQ has an entry. |
| A4 | Current file has N rows | Report has exactly N rows. Summary in-count = N. |
| A5 | A date filled by the LLM step | Has a citation URL, basis `llm_proposed`, and is in the review queue. With no citation, the field is blank. |
| A6 | A field already has a value in the source or from a human | It isn't changed by any fill step. |
| A7 | A column in the current export matches the prior file by row position, but not when rows are paired by serial (a positional copy). Unchanged columns such as Manufacturer must not trigger it. | Ingest raises a provenance error and the run stops until the operator acknowledges it. |
| A8 | A row with no OS EOS and no asset EOS | Call is Needs review, not Manage. |
| A9 | A human override from the previous run | Applied this run. Not recomputed. |
| A10 | Hostname matches, one side has a blank serial, name unique in both files | Matches with `method = hostname`. |
| A11 | Hostname matches, one side blank serial, but the hostname appears twice in the prior file | No match. DQ entry. |
| A12 | Frozen Sep-2026 test set | Match counts (serial, hostname, new, dropped) equal the known-good counts exactly. |
| A13 | Every date column in Report | Is an Excel date, not text. |
| A14 | Timed run by the operator (not me) | Hands-on time recorded in `03`. Target 1 h. |

## 12. Risks

| Risk | Mitigation |
|---|---|
| Wrong match corrupts history without anyone noticing | Deterministic rules, A1 to A3, A10 to A12 as tests, frozen set check |
| LLM invents a vendor date | Cite or abstain, always reviewed, never promoted without approval |
| Operator doesn't trust the output | Reasons on every value, Match Detail tab, run in parallel with the manual refresh first |
| Export looks different from the current sheet | Legacy headers and column order kept, cell-level compare against known-good |
| ServiceNow already does the date part | Check licenses first (`04`). If so, import from there and drop the LLM step. |
| Real data ends up in the project folder | Only synthetic or approved de-identified data in `data/sample/`; `.gitignore` covers `data/*` and `output/` |
| No operator available to test | Backup operator named. Without a test, the metric can't be claimed. |
| Scope creeps to more towers | v1 is one tower. Tower config can wait. |

## 13. Non-goals (v1)

- Live ServiceNow API access
- Write-back to the CMDB
- More than one tower
- SSO or multi-user
- Dashboards or trend views
- Ticketing
- Autonomous remediation. Retire is a recommendation only.
- Fuzzy or AI identity matching
- Warranty API integration
- Natural-language query

## 14. Assumptions

- The EUC Windows export has serial, hostname, OS name, OS version and edition as separate columns, or edition can be parsed from the OS name exactly. **[check on sample]**
- The prior sheet follows the canonical template closely enough to map headers by rule.
- The EOL-EOS reference sheet can be loaded as approved policy for Windows.
- The operator can get a de-identified or synthetic sample approved for testing.
- Python 3.12, FastAPI, SQLite, openpyxl, pydantic, Claude API and pytest, per `product.md`. Nothing is installed until the build plan is accepted.
