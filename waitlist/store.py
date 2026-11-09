"""SQLite storage for the waitlist. One table, WAL mode, no IP or user agent (W4)."""
import os
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_DB = "/var/lib/lifecycle-waitlist/waitlist.db"

# The sentence shown under the button, stored with each row (W7). The page
# links "privacy policy"; the stored text is the plain sentence.
CONSENT_TEXT = (
    "We'll only email you about Lifecycle Copilot. Unsubscribe or ask us to delete "
    "your email any time. See the privacy policy."
)

ROLES = {
    "itam_analyst": "IT asset / ITAM analyst",
    "infra_lead": "Infrastructure or IT operations lead",
    "cmdb_admin": "CMDB or ServiceNow admin",
    "other": "Something else",
}

SCHEMA = """
CREATE TABLE IF NOT EXISTS signup (
  id            INTEGER PRIMARY KEY,
  email         TEXT NOT NULL UNIQUE,
  role          TEXT,
  consent_text  TEXT NOT NULL,
  source        TEXT NOT NULL DEFAULT 'landing',
  created_at    TEXT NOT NULL
);
"""

MAX_EMAIL = 254
# Address shape only: something@something.tld, no spaces or control characters.
EMAIL_RE = re.compile(r"[^@\s\x00-\x1f\x7f]{1,64}@[^@\s\x00-\x1f\x7f]+\.[^@\s\x00-\x1f\x7f.]{2,}")


class InvalidSignup(ValueError):
    """Bad email or role. The message is safe to show to the visitor."""


def db_path_from_env() -> Path:
    return Path(os.environ.get("WAITLIST_DB") or DEFAULT_DB)


def connect(db_path=None) -> sqlite3.Connection:
    path = Path(db_path) if db_path else db_path_from_env()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=5)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.executescript(SCHEMA)
    return conn


def normalise_email(value) -> str:
    if value is not None and not isinstance(value, str):
        raise InvalidSignup("Enter an email address like name@company.com")
    email = (value or "").strip().lower()
    if not email:
        raise InvalidSignup("Enter an email address like name@company.com")
    if len(email) > MAX_EMAIL or not EMAIL_RE.fullmatch(email) or ".." in email:
        raise InvalidSignup("Enter an email address like name@company.com")
    return email


def normalise_role(value) -> str | None:
    if value is not None and not isinstance(value, str):
        raise InvalidSignup("Choose a role from the list, or leave it blank")
    role = (value or "").strip()
    if not role:
        return None
    if role not in ROLES:
        raise InvalidSignup("Choose a role from the list, or leave it blank")
    return role


def add_signup(conn: sqlite3.Connection, email, role=None, source="landing") -> bool:
    """Stores a signup. Returns True if new, False if the email was already there.
    A repeat changes nothing (W5)."""
    email = normalise_email(email)
    role = normalise_role(role)
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    with conn:
        cur = conn.execute(
            "INSERT INTO signup (email, role, consent_text, source, created_at) VALUES (?, ?, ?, ?, ?) "
            "ON CONFLICT(email) DO NOTHING",
            (email, role, CONSENT_TEXT, source, now),
        )
    return cur.rowcount == 1
