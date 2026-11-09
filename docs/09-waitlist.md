# 09. Waitlist

Asked for by the product owner, 24-Oct-2026: "implement the waitlist properly, choose SQLite".
Owner: PM (this spec). Build: dev. Tests: qa. Server and deploy: devops. Form look: ux.

## What it does

A visitor to memorymanager.stream leaves their email to hear when Lifecycle Copilot is ready. The owner can export the list. Nothing else.

## Decisions

| # | Decision | Why |
|---|---|---|
| W1 | Collect email (required) and role (optional, a short fixed list). Nothing else: no name, no company, no free text. | Collect as little as possible. Role tells us whether sign-ups are ITAM people. |
| W2 | Store in SQLite on the VM, at `/var/lib/lifecycle-waitlist/waitlist.db`, outside the web root. | Owner chose SQLite. One small file, no extra service, fits the t2.micro. |
| W3 | Small Python service (FastAPI + uvicorn), listening on `127.0.0.1:8081` only. nginx proxies `POST /api/waitlist` to it. | Same stack as the product. The app is never reachable directly from the internet. |
| W4 | Don't store IP addresses or user agents in the database. Turn access logging off for `/api/waitlist` in nginx (`access_log off;`) and run uvicorn with `--no-access-log`. | Not needed for a waitlist, and the privacy policy stays short. The nginx error log can still record the IP of a rate-limited request. The policy's server-log paragraph (about 10 days) covers that. |
| W5 | Same answer for a new email and a repeated one ("You're on the list"). | Nobody can use the form to check whether an address is already signed up. |
| W6 | Spam protection: a hidden honeypot field, an nginx rate limit (5 requests a minute per visitor IP), and Cloudflare in front. No captcha this weekend. The rate limit must use the visitor's real IP: `set_real_ip_from` for every Cloudflare range plus `real_ip_header CF-Connecting-IP`. Otherwise all visitors behind one Cloudflare edge share one limit. | Cheap and invisible to real people. Turnstile can come later if spam shows up. |
| W7 | No confirmation email this weekend. Store `consent_text` with each row so we know exactly what each person agreed to. | Sending email needs a mail service and DNS work. Double opt-in comes later, before any bulk mailing. |
| W8 | Export only on the VM, via a CLI command that writes CSV. Never over HTTP. | The list is personal data, so no download URL. |
| W9 | Delete on request: CLI command `delete <email>`. | Matches the privacy policy promise. |
| W10 | Daily SQLite backup on the VM (`.backup` to a dated file, keep 7). | A single file can be lost. Seven days is enough for a waitlist. |

## Data

```sql
CREATE TABLE IF NOT EXISTS signup (
  id            INTEGER PRIMARY KEY,
  email         TEXT NOT NULL UNIQUE,     -- trimmed, lower-cased
  role          TEXT,                     -- one of the allowed values, or NULL
  consent_text  TEXT NOT NULL,            -- the sentence shown next to the button
  source        TEXT NOT NULL DEFAULT 'landing',
  created_at    TEXT NOT NULL             -- ISO 8601 UTC
);
```

The database runs in WAL mode. A repeated email updates nothing and returns the same success response.

Allowed roles: `itam_analyst` ("IT asset / ITAM analyst"), `infra_lead` ("Infrastructure or IT operations lead"), `cmdb_admin` ("CMDB or ServiceNow admin"), `other` ("Something else").

## API

`POST /api/waitlist`, JSON or form-encoded:

| Field | Rule |
|---|---|
| `email` | required, valid address shape, at most 254 characters |
| `role` | optional, one of the allowed values |
| `lc_hp` | honeypot (renamed from `website`, which browsers can autofill). Must be empty. If filled in, return the normal success response and store nothing. |

Responses: `200 {"ok": true, "message": "You're on the list."}` for both new and repeated emails. `422` with a plain message for an invalid email or role. `429` from nginx when the rate limit is hit. Any other error is `500` with a generic message and nothing internal in the body.

`GET /api/waitlist/health` returns `200 {"ok": true}` for devops checks. It returns no counts.

## The form (landing page)

- Section intro: "We'll email you when it's ready, and only about Lifecycle Copilot. We never share your address." It must never promise less than the consent sentence and the privacy policy allow.
- Its own `#waitlist` section, after `#proof` and before `#agents`. The hero's primary button says "Join the waitlist" and links to it.
- Labels: "Work email" and "Your role (optional)". Any valid address is accepted, not only work domains. One button: "Join the waitlist".
- The button has `aria-describedby` pointing at the consent sentence, so screen readers hear it before submitting.
- The consent sentence sits right under the button, at 14px or larger and normal contrast. The honeypot is hidden from the keyboard and screen readers. On phones the fields stack full width.
- Under the button: "We'll only email you about Lifecycle Copilot. Unsubscribe or ask us to delete your email any time. See the [privacy policy](/privacy.html)." The service stores this exact sentence as `consent_text`.
- Works without JavaScript (a plain form POST that shows a simple result page). With JavaScript, it submits in place and shows the message without a reload.
- Messages: success "You're on the list. We'll email you when Lifecycle Copilot is ready."; invalid email "Enter an email address like name@company.com"; rate-limited "Too many tries. Wait a minute and try again."; server error "Something went wrong on our side. Try again in a few minutes."
- The honeypot's no-JS result page looks exactly like the success page.
- No-JS result pages show each error once, with a title that fits the error (not "Check your email address" for a 500). A rate-limited no-JS visitor gets a styled 429 page from nginx, not nginx's default.

## Privacy policy and llms.txt (PM)

These change in the same deploy as the form, never before or after:
- The privacy policy gets a "Waitlist" section: what's stored (email, optional role, time, consent sentence), where (SQLite on our AWS server), why (only to tell you about Lifecycle Copilot), how long (until you ask us to remove it or the waitlist closes), no sharing or selling, how to delete. It loses the "nothing to type into" lines.
- llms.txt: "the site collects nothing itself" becomes "the site has a waitlist form that stores email and optional role".

## Acceptance checks (qa)

| # | Check |
|---|---|
| W-A1 | A valid email is stored once, lower-cased and trimmed, with `consent_text` and a UTC timestamp |
| W-A2 | The same email again (in any case or spacing) returns the same 200 response, and the table still has one row |
| W-A3 | An invalid email or unknown role returns 422 and stores nothing |
| W-A4 | A filled honeypot returns 200 and stores nothing |
| W-A5 | No IP address or user agent is written anywhere in the database |
| W-A6 | Export writes a CSV with every row. Delete removes exactly one row. |
| W-A7 | The service doesn't answer on any public interface, only on 127.0.0.1 (devops checks this on the VM) |
| W-A8 | Without JavaScript, the form still works and shows a result page |
| W-A9 | After 5 quick requests from one IP, the next one gets 429 (nginx, devops checks this) |
| W-A10 | The live privacy policy describes the waitlist on the day the form goes live |

## Where the code lives

`waitlist/` at the repo root (`Lifecycle_copilot/waitlist/`). It's a separate small package so it doesn't drag the product's code onto the web server. Tests are in `tests/test_waitlist*.py` (qa) plus dev's unit tests. The form goes into the landing page, owned by devops once the site moves into the repo (G2). Until then, dev makes the change, and devops reviews it before deploying.

## Release

Through the git process (`08`), as the third PR, after the baseline and ops PRs (see "First three PRs" in `08`). Form, policy, llms.txt, code, tests and server config merge in one PR. Going live is blocked until the owner accepts the Xcode license and agrees to G2.

## Appendix: policy text to apply at release (PM)

Apply to `landing/privacy.html` and `landing/llms.txt` in the same PR as the form. Move the policy's effective date to the release day.

**privacy.html: replace the short-version box text with:**
> **Short version:** this site has one form, the Lifecycle Copilot waitlist. If you join, we store your email, the role you picked (if any), when you joined, and the sentence you agreed to. We use it only to tell you about Lifecycle Copilot. No analytics, no advertising, no selling or sharing. Like every website, the services that deliver it see your IP address and basic request details. This page explains which.

**privacy.html: replace the first paragraph of "What we collect" with:**
> **If you join the waitlist:** your email address, the role you chose from the list (optional), the date and time you joined, and the exact consent sentence shown next to the button. That's all. We don't store your IP address or browser details with it. We don't use cookies of our own, tracking pixels, analytics tools or browser storage.

**privacy.html: add a section after "What we collect":**
> **The waitlist**
> We keep the waitlist in a database on our own server (hosted by Amazon Web Services in the US), not with a mailing-list company. We use it only to email you about Lifecycle Copilot: when there's something to try, and the occasional update. We don't sell it, share it or add you to anything else. Before we send any bulk email, we'll ask you to confirm your address, and every email will have an unsubscribe link. We keep your entry until you ask us to remove it or we close the waitlist. A daily backup is kept for 7 days, so a deleted email is gone from backups within a week. To be removed, email the address below. We'll delete it and confirm within 30 days.

**privacy.html: in "Your choices and rights", replace "Because we hold almost nothing (short-lived server logs at most), the honest answer is usually "nothing tied to you"." with:**
> If you joined the waitlist, we hold your email and optional role. Otherwise we hold nothing tied to you beyond short-lived server logs.

**llms.txt: replace the Privacy policy line with:**
> - [Privacy policy](https://memorymanager.stream/privacy.html): the only data collected is the waitlist (email and optional role), stored on the operator's own server. Cloudflare, AWS and Google Fonts see standard request data.

**terms.html:** no change needed. The terms already say nothing on the site is an offer to sell or provide the tool.

## Server plan (devops, accepted 24-Oct)

Files: `deploy/waitlist/` (systemd service and backup timer, nginx blocks, README with install, checks and rollback).
- The service runs as a `waitlist` system user with no outbound network and is capped at 150 MB of memory. Code lives in `/opt/lifecycle-waitlist`, data in `/var/lib/lifecycle-waitlist` (0700).
- Real visitor IPs are used only inside `/api/waitlist`, for the rate limit. The error log there is set to `crit`, so rate-limited IPs aren't logged. The app never receives client IP headers.
- Backups: a systemd timer at 03:30 UTC keeps 7 copies on the same disk.
- nginx adds security headers to every waitlist response (nosniff, a strict CSP with frame-ancestors 'none', no-referrer, no-store).
- Later: an off-box backup copy, Cloudflare Authenticated Origin Pulls, and optionally growing the disk to 16 GB (about $0.64 a month).
