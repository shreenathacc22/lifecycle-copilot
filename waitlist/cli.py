"""Owner commands, run on the VM only (W8, W9, W10). Nothing here is reachable over HTTP.

  python -m waitlist export --out signups.csv [--db PATH]
  python -m waitlist delete someone@example.com [--db PATH]
  python -m waitlist backup --dir /var/backups/lifecycle-waitlist [--keep 7] [--db PATH]
  python -m waitlist serve [--host 127.0.0.1] [--port 8081] [--db PATH]
"""
import argparse
import csv
import ipaddress
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

from .store import InvalidSignup, connect, db_path_from_env, normalise_email

COLUMNS = ("id", "email", "role", "consent_text", "source", "created_at")


def export_csv(db_path, out_path) -> int:
    """Writes every row to CSV. Returns the row count."""
    conn = connect(db_path)
    try:
        rows = conn.execute(f"SELECT {', '.join(COLUMNS)} FROM signup ORDER BY id").fetchall()
    finally:
        conn.close()
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(COLUMNS)
        writer.writerows(rows)
    return len(rows)


def delete(db_path, email) -> int:
    """Removes one address. Returns the number of rows removed (0 or 1)."""
    try:
        email = normalise_email(email)
    except InvalidSignup:
        return 0
    conn = connect(db_path)
    try:
        with conn:
            return conn.execute("DELETE FROM signup WHERE email = ?", (email,)).rowcount
    finally:
        conn.close()


def backup(db_path, out_dir, keep=7) -> Path:
    """Copies the database with SQLite's online backup to a dated file and
    keeps the newest `keep` copies. The source is opened read-only, so a
    backup can never create or change the live database."""
    db_path = Path(db_path)
    if not db_path.exists():
        raise FileNotFoundError(f"no waitlist database at {db_path}")
    out_dir = Path(out_dir)
    out_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    target = out_dir / f"waitlist-{stamp}.db"
    src = sqlite3.connect(db_path.resolve().as_uri() + "?mode=ro", uri=True)
    dst = sqlite3.connect(target)
    try:
        src.backup(dst)
    finally:
        dst.close()
        src.close()
    copies = sorted(out_dir.glob("waitlist-*.db"))
    for old in copies[:-keep] if keep > 0 else []:
        old.unlink()
    return target


def _serve(host, port, db_path):
    if not ipaddress.ip_address(host).is_loopback:
        print("error: the waitlist only listens on a loopback address (W3). nginx proxies to it.", file=sys.stderr)
        return 2
    import uvicorn

    from .app import create_app

    uvicorn.run(create_app(db_path), host=host, port=port, proxy_headers=False, server_header=False,
                date_header=False, access_log=False)
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="python -m waitlist")
    parser.add_argument("--db", type=Path, help="database path (default $WAITLIST_DB or /var/lib/lifecycle-waitlist/waitlist.db)")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("export", help="write every signup to CSV")
    p.add_argument("--out", required=True, type=Path)
    p = sub.add_parser("delete", help="remove one email address")
    p.add_argument("email")
    p = sub.add_parser("backup", help="dated copy of the database, keep the newest N")
    p.add_argument("--dir", required=True, type=Path)
    p.add_argument("--keep", type=int, default=7)
    p = sub.add_parser("serve", help="run the service (loopback only)")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8081)
    args = parser.parse_args(argv)
    db = args.db or db_path_from_env()

    if args.command == "export":
        n = export_csv(db, args.out)
        print(f"wrote {n} row(s) to {args.out}")
    elif args.command == "delete":
        n = delete(db, args.email)
        print(f"removed {n} row(s)")
    elif args.command == "backup":
        try:
            print(f"wrote {backup(db, args.dir, args.keep)}")
        except FileNotFoundError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
    elif args.command == "serve":
        return _serve(args.host, args.port, db)
    return 0
