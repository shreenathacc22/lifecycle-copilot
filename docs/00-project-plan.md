# 00. Project plan and status

PM: Claude (this session). Owner: product owner.
Last updated: Sat 24-Oct-2026, 3:02 PM PT.

Live status board (Claude Desktop / claude.ai): https://claude.ai/artifact/MLewDKX4q6pFPPj4cHYJrJ . PM updates it from team reports.

## Team

| Session | Role | Owns |
|---|---|---|
| PM | Project manager | This plan, the status board, decisions, cross-team sync |
| dev | Build | `07-build-plan.md`, `src/`, sample data |
| qa | Tests and evidence | `tests/`, A1 to A13, Forge Measured |
| ux | Design | `05a-ux-design.md`, prototype, operator questions |
| devops | Infra | `DAY1/INFRA.md`, AWS VM, memorymanager.stream, Forge Secured |

Every session reports to PM by message when something finishes or blocks. Roles only in docs, no personal names.

## Status: AMBER on schedule

Team synced. Landing page live. Tests written. Code started (M0). Built and Measured land tonight. Two items wait on the product owner (git, origin cert / IAM).

| Area | Status | Note |
|---|---|---|
| Problem and user (01) | Green | Written |
| Interview (02) | Amber | The ITAM team confirmed for Sun 10:10 AM. Notes empty until then. |
| Metric (03) | Amber | Target set: 1 h. Baseline is still an estimate. |
| Market scan (04) | Green | Done. One big open item: what ServiceNow licenses we have. |
| Spec (05) | Amber | Drafted, not validated. 8 contradictions listed. |
| Validation (06) | Amber | Questions ready, UX1 to UX8 merged. Needs the operator session. |
| Build plan (07) | Green | Written by dev. Go given on M0, M1, M2, M4, M6. |
| Code | Green | M0, M1, M2, M4, M6 done plus review fixes. 69 passed, 4 skipped (PM and qa re-ran). Backup on the VM, Mac is source of truth. |
| Forge steps 5 to 7 (Built, Secured, Measured) | Amber | Secured in place (devops). Built and Measured tonight. |

## Course deadlines

| When (PT) | What | Forge step |
|---|---|---|
| Sat, now to 3:30 PM | Lab 2: Measure | 7 Measured |
| Sat evening | Catch up on Built and Secured | 5, 6 |
| Sun 10:10 AM to 12:30 PM | Iterate with a real user | 2 Interview (late), validation |
| Sun 1:15 PM | Defend it to two audiences | 9 Defend |
| Sun 2:00 to 3:30 PM | Demo Day | 8 Shipped |

## The schedule problem, and my call

The VS Code guide says: spec, then validate with the user, then the build plan, then code. The course says: build today, user on Sunday morning, demo Sunday afternoon. We can't do both in order.

**Recommendation:** build tonight on synthetic data only, and keep the scope to the part that doesn't depend on user answers. Matching and ingest follow fixed rules (I1 to I6) that won't change whatever the ITAM team says. Decision rules and review UI do depend on the ITAM team, so they wait until Sunday's session.

That keeps the guide's spirit (nothing user-dependent is built before validation) and still gives something real to demo.

## Proposed build plan (compressed for the weekend)

Feeds `07-build-plan.md` once accepted.

| # | Milestone | When | Output | Done when |
|---|---|---|---|---|
| M0 | Synthetic sample | Sat eve, 1 h | `data/sample/current.xlsx`, `prior.xlsx` with the hard cases planted: duplicate serial, hostname reuse, blank serial, OS edition change, positional-copy column | Files open in Excel. No real data. |
| M1 | Ingest and validation | Sat eve, 1.5 h | Reads both files, normalises headers, keeps every row, positional-copy check | A4, A7 pass |
| M2 | Match engine | Sat eve, 2 h | Serial, then safe hostname, then none. Dropped list. | A1, A3, A10, A11 pass |
| M3 | Export (Report, Summary, Match Detail, Dropped, Data Quality) | Sat late, 1.5 h | 5 of 6 sheets, real Excel dates | A4, A13 pass. Opens cleanly. |
| M4 | Carry-forward and Windows OS policy lookup | Sun early, 1.5 h | Fill blanks from a small approved Windows table (Microsoft 24 / 36 month rule) | A2, A5, A6 pass |
| M5 | User session with the ITAM team | Sun 10:10 to 12:30 | The ITAM team runs it on the sample, timed. Fill 02, 06, 03. | Real quotes and a measured time recorded |
| M6 | Decide and fix | Sun 12:30 to 1:15 | Apply what the ITAM team said. Decision rules if agreed (D-rules). | 06 has decisions marked |
| M7 | Demo | Sun 2:00 | Live run: upload, match, export, show Data Quality tab | Forge 8 and 9 receipts |

Cut for the weekend (still in v1 spec, just not by Sunday): LLM researcher, review queue UI, sticky overrides, FastAPI. A CLI is enough for the demo.

**Secured (Forge step 6):** for this project, that means no real data in the repo, `.env` never read by the app unless needed, no secrets in code, `.gitignore` checked. Cheap to show.

**Measured (Forge step 7):** run time on the synthetic set plus the A1 to A13 test results. The real hands-on number comes from the ITAM team on Sunday (M5).

## Decisions needed from the product owner now

| # | Decision | My recommendation |
|---|---|---|
| P1 | Accept building tonight before validation, scoped to M0 to M4? | Yes |
| P2 | Target: 1 h or 45 min? | 1 h. It's in the Forge already and it's yours. |
| P3 | CLI only for the demo, no web UI? | Yes |
| P4 | Is the ITAM team confirmed for Sunday 10:10? If not, message the CMDB extract owner tonight. | Send T-01 now if not confirmed |

## Risks

| Risk | Likelihood | Impact | Action | Owner |
|---|---|---|---|---|
| No real user on Sunday | Medium | High: no interview, no measured number, weak defend | Confirm the ITAM team tonight, the CMDB extract owner as backup | Product owner |
| Build overruns tonight | High | Medium | Strict order M0 to M3. M4 only if time. | PM |
| Test set can't come onto this machine | High | Medium | Synthetic only this weekend. Frozen set check (A12) moves to after the course. | PM |
| Demo shows AI that isn't there | Low | High | Say plainly: matching is deterministic by design, AI comes later and only for cited dates | Product owner |
| ServiceNow already does the date part | Unknown | Medium for the defend | Check licenses Monday. Say so honestly if asked. | Product owner |

## Action log

| Date | Action | Who | Status |
|---|---|---|---|
| 24-Oct | Docs 01, 03 written | Product owner | Done |
| 24-Oct | Market scan (04), spec draft (05), validation template (06) | Claude | Done |
| 24-Oct | Project plan (this file) | Claude (PM) | Done |
| 24-Oct | Confirm the ITAM team for Sunday | Product owner | Done |
| 24-Oct | Decided P1 (scoped build: yes), P2 (1 h), P4 (the ITAM team confirmed). P3 CLI only taken as default. | Product owner | Done |
| 24-Oct | Build plan 07 written | dev | Done |
| 24-Oct | PM stopped coding; handed pyproject/.venv to dev | PM | Done |
| 24-Oct | Team synced, status board published | PM | Done |
| 24-Oct | Spec A7 reworded (paired by serial); OS fill order proposed | PM, qa | Done, fill order waits on owner |
| 24-Oct | UX questions merged into 06 | PM, ux | Done |
| 24-Oct | Landing page live at memorymanager.stream | devops | Done |
| 24-Oct | Acceptance suite written | qa | Done |
| 24-Oct | M0, M1, M2, M4, M6 | dev | Done; A7 gap found by qa, fixed |
| 24-Oct | qa simulated operator review; dev fixed 8 of 9 findings; PM sourced 7 Windows 10/LTSC dates, qa checked them | dev, qa, PM | Done |
| 24-Oct | No GitHub for now; code backed up on the VM | Product owner | Decided |
| 24-Oct | Accept Xcode license (local git, optional now) | Product owner | Superseded, now required (see below) |
| 24-Oct | Keep or delete the empty private GitHub repo | Product owner | Open |
| 24-Oct | Origin cert, root/IAM decision | Product owner | Open |
| 24-Oct 7:53 PM | Owner-approved exception to git-flow, one time only: devops synced the latest code to the VM's private backup copy straight from the Mac (git still blocked). VM 157 passed / 4 skipped, same as Mac. Nothing public changed: no waitlist service, no nginx change, live site unchanged. The next deploy goes through main. | Product owner, devops | Done |
| 24-Oct 8:39 PM | Owner said "complete all remaining actions on priority". Taken as yes to the recommended defaults: the one-time push that creates main, G2 (site/ in the repo) and G1 (push guard hook). Destructive or paid items still wait for an explicit yes. | Product owner | Decided |
| 24-Oct 8:39 PM | PR3 privacy and llms.txt text staged in docs/release/pr3-site/ for devops to commit with the form | PM | Done |
| 24-Oct 8:39 PM | Sunday run sheet written (10); demo run checked from scratch | PM | Done |
| 24-Oct 8:39 PM | Accept the Xcode license (sudo, owner only). Blocks all three PRs. | Product owner | Open |
| 24-Oct 8:56 PM | Second owner-approved exception to git-flow: owner chose "waitlist go-live, all together" as a direct deploy while git is blocked. Devops installs the service and nginx and publishes the form, privacy.html (dated today) and llms.txt in one step. Freeze on landing/, waitlist/, docs/release/pr3-site/ for about 20 min. PR3 will record exactly what's live. | Product owner, devops | Done 25-Oct 8:41 AM |
| 25-Oct 8:44 AM | Waitlist live. Devops checks all pass (W-A7, W-A9 with real-IP proof, 429 pages, headers, no logs, backup, W-A10, test row deleted, 0 rows). PM checked the live hashes against docs/release/pr3-site: they match (Cloudflare only strips the email_off comments). Freeze lifted. | devops, PM | Done |
| 25-Oct 8:44 AM | Policy accuracy: the nginx page-view log records X-Forwarded-For (the real visitor IP), but the policy says "usually a Cloudflare address". Owner decided 9:05 AM: drop it from the log format (devops). | Product owner | Decided
| 25-Oct 8:44 AM | VM stop at 3:30 PM: owner decided to keep the VM running | Product owner | Decided
| 25-Oct 8:44 AM | Live sha256 for PR3 to match: index.html (wrapped) 184093ce546c1c642cf5aa4d0d19f94b7afe351f28bc8c0cbbda1c3fdadf8799; privacy.html 62687a8b1318d04f0ef762af1c73f70ac708ba9bd061c8f25238aa51959d458c; llms.txt 3d1d1b06724dadc7b213cc23f01d5406cf950e332b88b3962e3273ef07c7b9d9. Rollback copies in ~/site-backup-pre-waitlist on the VM. | devops | Recorded |
| 25-Oct 9:07 AM | ux live check: consent line, in-place messages, 429 page all pass (headless Chrome, 1280 and 390 px). qa live check 15/0. | ux, qa | Done |
| 25-Oct 9:07 AM | Cloudflare injects its Web Analytics beacon into every page, but the policy says "No analytics". devops to turn it off. | devops | Open |
| 25-Oct 9:07 AM | Agent blackboard (dev's proposal, owner asked): approved, outside the repo, feeds the status board. 9:12 AM owner: build now; operator-session fixes come first. PM wrote the blackboard skill. | PM, dev | In progress |
| 25-Oct 9:08 AM | Page-view logs no longer keep the visitor IP (X-Forwarded-For dropped, checked with a fresh request). VM stays on (about $12/month). | devops | Done |
| 25-Oct 9:10 AM | Turn off Cloudflare Web Analytics in the dashboard (no API token, so devops can't) | Product owner | Open |
| 25-Oct 9:15 AM | Agent blackboard live (dev built it, 23 tests pass, PM checked). Seeded with 19 entries; all agents told to use it instead of messages. Owner's read-only view: DAY1/TLM-Project/blackboard/board.html | dev, PM | Done |
