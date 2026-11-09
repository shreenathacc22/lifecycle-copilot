# Waitlist: server side

Owner: devops (`deploy/` is devops's in the git-flow ownership table). App: dev's `waitlist/` package. Spec: `docs/09-waitlist.md`.

Deploy only from a merged `origin/main` worktree (`docs/08`), together with the form, the privacy policy and llms.txt. Never one without the others.

## Files

| File | Installed to |
|---|---|
| `lifecycle-waitlist.service` | `/etc/systemd/system/` |
| `lifecycle-waitlist-backup.service`, `.timer` | `/etc/systemd/system/` (daily 03:30 UTC, keep 7) |
| `nginx-http.conf` | `/etc/nginx/conf.d/waitlist-zone.conf` |
| `nginx-server.conf` | `/etc/nginx/default.d/waitlist.conf` |
| `nginx-cf-realip.conf` | `/etc/nginx/waitlist-cf-realip.conf` |
| `errors/waitlist-429.html`, `.json` | `/usr/share/nginx/waitlist-errors/`. These are the rate-limit bodies, served on internal-only locations. The HTML is built from `waitlist/form.py` CSS; regenerate it if that changes |

Layout on the VM:

```
/opt/lifecycle-waitlist/app/waitlist/   dev's package only, none of lifecycle_copilot (root-owned)
/opt/lifecycle-waitlist/venv/    Python 3.12 with waitlist/requirements.txt only: fastapi, uvicorn (~32 MB)
/var/lib/lifecycle-waitlist/     0700 waitlist:waitlist, created by systemd StateDirectory
  waitlist.db                    WAL mode
  backups/waitlist-*.db          newest 7 kept
```

The service runs as the system user `waitlist`, not `ec2-user`, because `ec2-user` has passwordless sudo. It has no outbound network (`IPAddressDeny=any`, loopback allowed) and a 150 MB memory cap.

## Install (first time)

```bash
# $W = clean origin/main worktree, copied to the VM
sudo useradd --system --no-create-home --shell /sbin/nologin waitlist
sudo python3.12 -m venv /opt/lifecycle-waitlist/venv
sudo /opt/lifecycle-waitlist/venv/bin/pip install -q -r "$W/waitlist/requirements.txt"
sudo install -d -m 755 /opt/lifecycle-waitlist/app
sudo rsync -a --delete --exclude __pycache__ "$W/waitlist/" /opt/lifecycle-waitlist/app/waitlist/
sudo install -m 644 deploy/waitlist/lifecycle-waitlist*.service deploy/waitlist/lifecycle-waitlist-backup.timer /etc/systemd/system/
sudo install -m 644 deploy/waitlist/nginx-http.conf      /etc/nginx/conf.d/waitlist-zone.conf
sudo install -m 644 deploy/waitlist/nginx-server.conf    /etc/nginx/default.d/waitlist.conf
sudo install -m 644 deploy/waitlist/nginx-cf-realip.conf /etc/nginx/waitlist-cf-realip.conf
sudo install -d -m 755 /usr/share/nginx/waitlist-errors && sudo install -m 644 deploy/waitlist/errors/* /usr/share/nginx/waitlist-errors/
sudo systemctl daemon-reload && sudo systemctl enable --now lifecycle-waitlist lifecycle-waitlist-backup.timer
curl -s 127.0.0.1:8081/api/waitlist/health      # {"ok":true}
sudo nginx -t && sudo systemctl reload nginx
# then publish the landing form, privacy.html and llms.txt in the same step
```

For an update, rsync `waitlist/` again (and reinstall the requirements if they changed), then run `sudo systemctl restart lifecycle-waitlist`.

## Owner commands on the VM

```bash
cd /opt/lifecycle-waitlist/app
W="sudo -u waitlist WAITLIST_DB=/var/lib/lifecycle-waitlist/waitlist.db /opt/lifecycle-waitlist/venv/bin/python -m waitlist"
$W export --out /var/lib/lifecycle-waitlist/signups.csv && sudo mv /var/lib/lifecycle-waitlist/signups.csv ~ && sudo chown ec2-user ~/signups.csv
$W delete someone@example.com
```

## Checks after deploy

- **W-A7, loopback only.**
  - `sudo ss -ltnp | grep 8081` shows `127.0.0.1:8081` and nothing else.
  - `curl -m 3 http://<private-ip>:8081/` from the VM is refused.
  - `curl -m 5 http://<VM_IP>:8081/` from the Mac times out.
- **W-A9, rate limit.** Send 6 quick POSTs to `https://memorymanager.stream/api/waitlist` with the honeypot filled, so nothing gets stored. The 6th returns 429.
- **Real IP keying (W-A9 only passes with this).** Straight after that, POST once from the VM through Cloudflare. It must get 200 while the Mac is still limited.
- **No IPs in logs.**
  - `sudo grep -c api/waitlist /var/log/nginx/access.log` is 0.
  - The error log has no new `client:` lines from the test.
- **429 bodies.** While the Mac is still rate-limited:
  - `Accept: text/html` gets 429 with the "Too many tries" HTML page (`text/html; charset=utf-8`).
  - `Accept: application/json` gets 429 with `{"ok": false, "message": "Too many tries. Wait a minute and try again."}`.
  - The default `*/*` gets the HTML.
  - All of them carry the security headers.
  - `GET /waitlist-429.html` and `GET /waitlist-429.json` directly return 404.
  - In a browser with JS off, the page renders with fonts and styles.
- **Health.** `https://memorymanager.stream/api/waitlist/health` returns `{"ok":true}`.
- **Security headers.** These four must be present: `X-Content-Type-Options: nosniff`, the `Content-Security-Policy` from `nginx-server.conf`, `Referrer-Policy: no-referrer` and `Cache-Control: no-store`. Check all of these responses, all through Cloudflare:
  - a 200 (honeypot POST)
  - a 422 (bad email)
  - the 429 from the rate-limit test
  - a 405 (`GET /api/waitlist`)
  - a 413 (a 5 KB body)
  - the health endpoint

  If the 405 is missing them, the `if` block isn't inheriting `add_header`, so repeat the headers inside it. Also confirm the no-JS result page renders with its fonts and styles, so the CSP isn't blocking anything (check the browser console).
- **Backup.** `sudo systemctl start lifecycle-waitlist-backup` writes a file in `backups/`.

## Rollback

1. `sudo rm /etc/nginx/default.d/waitlist.conf /etc/nginx/conf.d/waitlist-zone.conf && sudo nginx -t && sudo systemctl reload nginx`. `/usr/share/nginx/waitlist-errors/` can stay, because nothing serves it without the config.
2. `sudo systemctl disable --now lifecycle-waitlist lifecycle-waitlist-backup.timer`
3. Put the previous landing page, privacy.html and llms.txt back together. Leave the DB and its backups in place.

## Known limits (logged by PM as later items)

- Backups are on the same EBS volume. They cover a corrupted DB, not a lost instance. Off-box copy comes later.
- Someone could point their own Cloudflare zone at our IP. Authenticated Origin Pulls comes later.
- Cloudflare's IP ranges are copied into the security group and into `nginx-cf-realip.conf`. If Cloudflare changes them, update both.
