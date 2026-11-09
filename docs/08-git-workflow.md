# 08. Git workflow

Set by the product owner, 24-Oct-2026. Agents follow it through the `git-flow` skill (`L5_training/.claude/skills/git-flow/SKILL.md`). This page is the short version for people.

## The flow

```
any agent ──commit locally──▶ dev (local)
                                   │  only devops pushes, after tests pass
                                   ▼
                              origin/dev ──devops opens PR──▶ PR: dev → main
                                                                    │  the human reviews and merges
                                                                    ▼
                                                               origin/main ──devops deploys──▶ VM / site
```

| Step | Who | Rule |
|---|---|---|
| 1. Commit | Any agent | Local commits on `dev` only. Stage your own files by path. Never push. |
| 2. Push to dev | DevOps only | Run the full test suite on the committed code first. Plain push, never force. |
| 3. Open PR dev → main | DevOps only | The PR lists the changes, the test counts, what was skipped, and the risks. DevOps never merges. |
| 4. Approve | The human | Review the PR on GitHub and click **Merge** ("Create a merge commit"). Merging is the approval. |
| 5. Deploy | DevOps only | Deploy from `origin/main`, never from `dev` or the working folder. |

## Who commits which files

Each agent commits only the files it owns. The table is in the `git-flow` skill: dev owns `src/`, `scripts/`, `pyproject.toml`, `README.md`, `data/`, `07` and `tests/test_dev_*.py`; qa owns the rest of `tests/`; ux owns `05a` and `prototype/`; PM owns the other docs and `prompts/`; devops owns `.gitignore`, `scripts/deploy-*.sh`, `deploy/` and `site/`. Others write `site/` content (PM the legal pages and llms.txt, ux and dev the page) and hand it to devops to commit.

## Why it's set up this way

- **All agents share one folder.** A broad `git add` would commit someone else's half-finished work, so everyone adds their own files by path.
- **All agents use the owner's GitHub account.** GitHub can't tell agents apart, and it doesn't let you approve your own PR. Merging is the approval step, and only the human merges.
- **The repo is private on the free plan, so branch protection isn't available.** Nothing on GitHub technically stops a push to `main`. The process is the guard. An optional local hook (below) adds a second one.
- **DevOps tests in a separate worktree,** so the tests run on exactly what was committed, not on whatever is half-edited in the shared folder.
- **Merge commits, not squash.** Squashing makes `dev` and `main` drift apart, and every later PR then conflicts.

## One-time setup (DevOps, after the owner accepts the Xcode license)

1. `cd DAY1/TLM-Project/Lifecycle_copilot && git init -b main`
2. Check `.gitignore` covers `.env`, `.venv/`, `output/`, `data/*` except `data/sample/` and `data/policy/`, and caches. Then run `git status --ignored` and read it.
3. First commit: `.gitignore` and `README.md` only, on `main`. Push `main` once. This is the only direct push to `main` ever, and it needs the owner's OK.
4. `git switch -c dev`, then commit everything else as one baseline import ("[devops] Baseline import of existing work"). Work from before git existed doesn't get per-agent commits. Run the test step, push `dev`, and open the first PR. The owner merges it.
5. Move `DAY1/deploy-vm.sh` into the repo as `scripts/deploy-vm.sh` (owned by devops). Make it take `SRC` from the environment and build its own venv with uv, so it can deploy a clean worktree of `origin/main`. Deploys then run the script version that's on `main`. This change goes through a normal PR.

## First three PRs (agreed 24-Oct, PM and devops)

Every merged `main` has to pass the VM test run with `REQUIRE_LANDING=1`, so each check ships in the same PR as the thing it checks.

| PR | Contents | Deploy result |
|---|---|---|
| 1. Baseline | The product, docs, tests (not the waitlist ones), and `site/` holding the files that are live now (no form). No `waitlist/`, no waitlist tests, no `deploy/waitlist/`. | No visible change. 69 pass, 4 skip in devops' dry run. |
| 2. Ops | `scripts/deploy-vm.sh` reads `SRC`, builds its own venv and publishes `site/` from the main worktree. Then `DAY1/deploy-vm.sh` is deleted. | The site deploys through the flow from now on. Nobody hand-copies landing files. |
| 3. Waitlist | `waitlist/`, both waitlist test files, `deploy/waitlist/`, and `site/` with the form, the new privacy section and the new llms.txt line, together. | Go-live. W-A10 holds because policy and form merge in one commit. |

The working-folder `landing/index.html` already has the form. Never copy it to the live site by hand.

## Open decisions for the owner

| # | Decision | Recommendation |
|---|---|---|
| G1 | Add a local hook that blocks `git push` to `main` and any `--force` push from every Claude session | Yes. It's the only technical guard on the free plan. |
| G2 | Move the website (`TLM-Project/landing/`) into the repo, so the site is also deployed from `main` | Yes, as `site/`. Now required: the VM test run fails without it, and the waitlist can't go live otherwise. |
| G3 | Give DevOps its own GitHub account (a bot user) so you can formally "Approve" PRs | Not this weekend. Merging as the approval is enough for now. |
