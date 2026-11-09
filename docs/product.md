# Lifecycle Copilot: product file

Owner: Product owner
Last updated: 24-Oct-2026
Course: AI Founder L5 (Modern AI Pro), the Forge

This is the single file I keep up to date as the product changes. The longer docs next to it hold the detail:

- `forge_step1_draft.md` holds my Forge Step 1 answers (idea, user, number, shape).

---

## 1. What it is

Lifecycle Copilot takes a raw CMDB export and the previous period's TLM sheet and gives back a finished lifecycle workbook. The workbook has EOL/EOS dates, a Manage/Renew/Retire call on each row, and the reason behind every value it filled in.

Today one tower takes me about two days by hand. Three of our nine towers have never been done. Only I can run it.

## 2. User and number

| | |
|---|---|
| Primary user | ITAM analyst who refreshes the tower extracts (ITAM team, confirmed for Sun 25-Oct 10:10 AM PT) |
| Backup user | CMDB extract owner (sends the CMDB extracts) |
| Report consumer | Infrastructure leadership |
| Shape | Internal tool a team adopted |
| Metric | Hours to refresh one tower, from export in hand to finished workbook sent |
| Today | about 16 h (an estimate, still needs a measured baseline) |
| Target | 1 h |
| Test set | Sep-2026 EUC Windows refresh, where the correct answer is already known |

## 3. Directory structure

### What exists today

```
L5_training/
├── .env                          secrets, never commit or share
├── requriement                   course welcome email (schedule and links)
├── DAY0/
│   └── recording/                session 1 recording, runbook and SOP (pdf/pptx)
└── DAY1/
    ├── PROTOCOL.md               blackboard protocol for peer agents
    ├── lifecycle-copilot-vscode-guide.md   setup and spec-first workflow guide
    └── TLM-Project/
        ├── product.md            this file
        ├── forge_step1_draft.md
        ├── ChatGPT Image Oct 24, 2026, 01_57_*.png   Forge screenshots (3)
        └── Lifecycle_copilot/    the app, empty for now
```

### Planned layout for `Lifecycle_copilot/`

The VS Code guide puts the project at `~/Documents/ai-projects/lifecycle-copilot`. I'm keeping it here in `DAY1/TLM-Project/Lifecycle_copilot/` instead, so every path in the guide's prompts should be read relative to this folder.

```
Lifecycle_copilot/
├── docs/
│   ├── 01-problem-and-user.md
│   ├── 02-interview-notes.md     real interview only, no AI rehearsal
│   ├── 03-success-metric.md
│   ├── 04-market-scan.md
│   ├── 05-product-spec.md
│   ├── 06-validation.md
│   └── 07-build-plan.md
├── prompts/                      reusable copies of the Claude Code prompts
├── data/
│   └── sample/                   synthetic or approved de-identified workbooks only
├── output/                       generated workbooks, not committed
├── src/lifecycle_copilot/        created only once the build plan is accepted
│   ├── ingest/                   parse, validate, provenance checks
│   ├── match/                    serial then hostname, no fuzzy matching
│   ├── lifecycle/                policy lookup, peer inference, vendor rules, LLM researcher
│   ├── decide/                   Manage/Renew/Retire plus rationale
│   ├── dq/                       data quality register
│   └── export/                   6-sheet Excel writer
├── tests/                        one test per invariant (I1 to I6) plus frozen test set checks
└── .gitignore                    .env, output/, data/ except sample/
```

To create the docs skeleton:

```bash
cd <PROJECT_ROOT>/DAY1/TLM-Project/Lifecycle_copilot
mkdir -p docs prompts data/sample output
touch docs/01-problem-and-user.md docs/02-interview-notes.md docs/03-success-metric.md \
      docs/04-market-scan.md docs/05-product-spec.md docs/06-validation.md docs/07-build-plan.md
```

`src/` and `tests/` wait until `05-product-spec.md` and `07-build-plan.md` are reviewed. The guide's rule is spec first, then one milestone at a time.

## 4. How it works

```
CMDB export ──┐
              ├─> match (serial, then hostname, no fuzzy)
prior sheet ──┘        │
                       v
           carry forward lifecycle and disposition
                       v
           fill blanks from policy, peers, vendor rules, then LLM (cited)
                       v
           decide Manage / Renew / Retire, with the reason
                       v
           export: Report, Summary, Matching Logic, Match Detail,
                   Dropped, Data Quality
```

## 5. Rules that don't change

| # | Rule |
|---|---|
| I1 | No fuzzy matching. Serial first. Hostname only if it's unique in both files and the serials don't conflict. |
| I2 | Only fill blanks. Never overwrite a source or human value. |
| I3 | Every derived value says where it came from in Remarks. |
| I4 | Keep every source row, duplicates included. |
| I5 | Ship the exceptions as their own tabs (Dropped, Data Quality). |
| I6 | Don't trust inbound columns. Check for positional copies of last period's file. |

Extra rules from the guide:

- If the OS, version or edition changed, recompute the OS dates. Don't carry the old ones forward.
- Missing evidence means Unknown / Needs review, not Manage.
- Keep AI-proposed values separate from approved policy facts.
- Retire is a recommendation only.

## 6. v1 scope

In:
- One tower (EUC Windows)
- Upload the current and prior `.xlsx` files
- Deterministic matching with tests
- Policy lookup, then peer inference, then vendor rules
- Cited LLM research for versions that are still unresolved
- Decision with rationale
- Six-sheet export
- Data quality register
- Local SQLite with snapshot history

Out:
- Live ServiceNow API
- Write-back to the CMDB
- More than one tower
- SSO
- Dashboards
- Ticketing
- Autonomous remediation

Stack: Python 3.12, FastAPI, SQLite (later Postgres), openpyxl, pydantic, Claude API, pytest.

## 7. Build order

1. Input schema and synthetic sample in `data/sample/`
2. Ingest and validation
3. Match engine and tests. It has to reproduce the known-good counts before anything else goes ahead.
4. Carry-forward and policy application
5. Review and disposition
6. Six-sheet export
7. Thin UI
8. Timed run with the user, then record the before and after

## 8. Acceptance checks

- Same hostname but a different serial does not match.
- A changed OS edition does not inherit a stale EOS.
- Ambiguous duplicate serials go to review.
- Every current input row shows up in the export.
- No vendor date goes out without a citation.

## 9. Housekeeping

- `.env` sits at the `L5_training` root. Keep it out of any repo, and never paste it into chat or the Forge.
- Real exports stay off this machine's project folder. Only synthetic or approved de-identified data goes in `data/sample/`.
- Don't copy the Forge text boxes from this file. Retype them in my own words, per `forge_step1_draft.md`.

## 10. Open questions

1. ~~Is the ITAM team confirmed for 30 minutes on Sunday?~~ Yes.
2. Measured baseline: how many hours does one tower actually take?
3. Where does asset EOL/EOS come from when the CMDB has no ship date?
4. Who owns the org map (Tribe, Line, Team, DG)?
5. ~~Is the target 1 h or 45 min?~~ 1 h, decided 24-Oct.
