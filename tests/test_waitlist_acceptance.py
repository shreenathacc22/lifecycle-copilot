"""Waitlist acceptance checks W-A1 to W-A6 and W-A8 (docs/09-waitlist.md).

W-A7 and W-A9 are devops' server checks, and W-A10 is PM's.
Every test uses a temp database. WAITLIST_DB is also pointed at the temp path,
so a code path that ignores db_path still can't reach the real file.
"""
import csv
import re
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))  # waitlist/ lives at the repo root, not under src/

app_mod = pytest.importorskip("waitlist.app", reason="waitlist package not built yet")
store = pytest.importorskip("waitlist.store")
cli = pytest.importorskip("waitlist.cli")
TestClient = pytest.importorskip("fastapi.testclient").TestClient

OK = {"ok": True, "message": "You're on the list."}
HP = "lc_hp"  # honeypot field name (renamed from "website", spec 09)
SPY_IP, SPY_UA = "203.0.113.77", "QA-Agent/9.9"


@pytest.fixture
def db(tmp_path, monkeypatch):
    path = tmp_path / "waitlist.db"
    monkeypatch.setenv("WAITLIST_DB", str(path))
    return path


@pytest.fixture
def client(db):
    return TestClient(app_mod.create_app(db_path=str(db)))


def rows(db):
    if not db.exists():
        return []
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    try:
        return [dict(r) for r in con.execute("SELECT * FROM signup ORDER BY id")]
    finally:
        con.close()


def join(client, html=False, **fields):
    if html:
        return client.post("/api/waitlist", data=fields, headers={"Accept": "text/html"})
    return client.post("/api/waitlist", json=fields)


class _Text(HTMLParser):
    """Text as a reader sees it: inline tags (<a>, <strong>) add no space,
    block tags (<p>, <button>, <label>) do."""

    BLOCK = {"p", "div", "br", "li", "ul", "ol", "form", "label", "button", "select",
             "option", "input", "h1", "h2", "h3", "h4", "section", "main", "header",
             "footer", "title", "tr", "td", "th", "table"}

    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag in self.BLOCK:
            self.parts.append(" ")

    handle_endtag = lambda self, tag: self.handle_starttag(tag, None)

    def handle_data(self, data):
        self.parts.append(data)


def visible_text(html):
    html = re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", html)
    p = _Text()
    p.feed(html)
    return re.sub(r"\s+", " ", "".join(p.parts)).strip()


# W-A1


def test_wa1_valid_email_stored_once_normalised_with_consent_and_utc_time(client, db):
    r = join(client, email="  Alice@Example.COM  ")
    assert r.status_code == 200 and r.json() == OK
    [row] = rows(db)
    assert row["email"] == "alice@example.com"
    assert row["consent_text"] == store.CONSENT_TEXT
    when = datetime.fromisoformat(row["created_at"].replace("Z", "+00:00"))
    assert when.utcoffset() == timedelta(0), "created_at must be UTC with an offset"
    assert abs(datetime.now(timezone.utc) - when) < timedelta(minutes=1)


def test_wa1_allowed_role_is_stored(client, db):
    assert join(client, email="bob@example.com", role="itam_analyst").status_code == 200
    assert rows(db)[0]["role"] == "itam_analyst"
    assert set(store.ROLES) == {"itam_analyst", "infra_lead", "cmdb_admin", "other"}


def test_wal_mode(client, db):
    join(client, email="wal@example.com")
    assert sqlite3.connect(db).execute("PRAGMA journal_mode").fetchone()[0].lower() == "wal"


# W-A2


def test_wa2_repeat_email_same_answer_one_row_nothing_updated(client, db):
    first = join(client, email="carol@example.com", role="infra_lead")
    before = rows(db)
    for variant in ("carol@example.com", "  CAROL@Example.com", "Carol@EXAMPLE.COM "):
        again = join(client, email=variant, role="other")
        assert again.status_code == first.status_code == 200
        assert again.json() == first.json() == OK
    assert rows(db) == before, "a repeated email must not change the stored row"


def test_wa2_repeat_on_the_html_page_looks_the_same(client):
    first = join(client, html=True, email="dan@example.com")
    again = join(client, html=True, email="DAN@example.com")
    assert first.status_code == again.status_code == 200
    assert visible_text(first.text) == visible_text(again.text)


# W-A3


@pytest.mark.parametrize("email", [
    "", "   ", "not-an-email", "a@", "@example.com", "a b@example.com",
    "a@@example.com", "x" * 245 + "@example.com",  # 257 characters, over the 254 limit
])
def test_wa3_invalid_email_is_422_and_stores_nothing(client, db, email):
    r = join(client, email=email)
    assert r.status_code == 422
    assert r.json().get("message")
    assert "Traceback" not in r.text and "sqlite" not in r.text.lower()
    assert rows(db) == []


def test_wa3_missing_email_is_422(client, db):
    r = client.post("/api/waitlist", json={})
    assert r.status_code == 422 and rows(db) == []


@pytest.mark.parametrize("role", ["ceo", "ITAM_ANALYST", "itam_analyst; DROP TABLE signup", "x" * 500])
def test_wa3_unknown_role_is_422_and_stores_nothing(client, db, role):
    r = join(client, email="erin@example.com", role=role)
    assert r.status_code == 422
    assert rows(db) == []


def test_wa3_error_message_says_what_to_fix(client):
    r = join(client, html=True, email="nope")
    assert r.status_code == 422
    assert "name@company.com" in visible_text(r.text)


# W-A4


def test_wa4_honeypot_returns_success_and_stores_nothing(client, db):
    r = join(client, email="bot@example.com", **{HP: "http://spam.example"})
    assert r.status_code == 200 and r.json() == OK
    assert rows(db) == []


def test_wa4_honeypot_html_page_is_indistinguishable(client, db):
    real = join(client, html=True, email="real@example.com")
    bot = join(client, html=True, email="bot@example.com", **{HP: "x"})
    assert bot.status_code == real.status_code == 200
    assert visible_text(bot.text) == visible_text(real.text)
    assert [r["email"] for r in rows(db)] == ["real@example.com"]


# W-A5


def test_wa5_no_ip_or_user_agent_anywhere_in_the_database(client, db):
    headers = {
        "User-Agent": SPY_UA, "X-Forwarded-For": SPY_IP, "X-Real-IP": SPY_IP,
        "CF-Connecting-IP": SPY_IP,
    }
    client.post("/api/waitlist", json={"email": "frank@example.com"}, headers=headers)
    client.post("/api/waitlist", data={"email": "gina@example.com"}, headers=headers)
    assert len(rows(db)) == 2

    con = sqlite3.connect(db)
    columns = {c[1].lower() for c in con.execute("PRAGMA table_info(signup)")}
    tables = [t[0] for t in con.execute("SELECT name FROM sqlite_master WHERE type='table'")]
    con.close()
    assert not {c for c in columns if "ip" in c.split("_") or "agent" in c or c == "ua"}, columns
    assert tables == ["signup"], f"unexpected tables: {tables}"

    for f in db.parent.glob(db.name + "*"):  # the db file plus -wal and -shm
        blob = f.read_bytes()
        assert SPY_IP.encode() not in blob, f"IP found in {f.name}"
        assert SPY_UA.encode() not in blob, f"user agent found in {f.name}"


# W-A6


def test_wa6_export_has_every_row_and_delete_removes_exactly_one(client, db, tmp_path):
    emails = ["h1@example.com", "h2@example.com", "h3@example.com"]
    for e in emails:
        join(client, email=e, role="other")

    out = tmp_path / "export.csv"
    assert cli.export_csv(str(db), str(out)) == 3
    with out.open(newline="") as f:
        exported = list(csv.DictReader(f))
    assert sorted(r["email"] for r in exported) == emails
    assert all(r.get("consent_text") for r in exported)

    assert cli.delete(str(db), "  H2@Example.com ") == 1
    assert [r["email"] for r in rows(db)] == ["h1@example.com", "h3@example.com"]
    assert cli.delete(str(db), "h2@example.com") == 0
    assert cli.delete(str(db), "nobody@example.com") == 0
    assert len(rows(db)) == 2


def test_wa6_export_is_never_reachable_over_http(client):
    for path in ("/api/waitlist/export", "/api/waitlist.csv", "/export", "/api/waitlist?format=csv"):
        r = client.get(path)
        assert r.status_code in (404, 405), f"{path} answered {r.status_code}"
        assert "@example.com" not in r.text


def test_health_returns_ok_and_no_counts(client):
    join(client, email="i@example.com")
    r = client.get("/api/waitlist/health")
    assert r.status_code == 200 and r.json() == {"ok": True}


# W-A8


def _form_html(client):
    r = client.get("/waitlist-form")
    if r.status_code == 200:
        return r.text
    form = pytest.importorskip("waitlist.form", reason="no form route or waitlist.form yet")
    return form.render()


def test_wa8_form_works_without_javascript(client, db):
    html = _form_html(client)
    form = re.search(r"(?is)<form\b[^>]*>", html)
    assert form, "no <form> element"
    assert re.search(r'(?i)method\s*=\s*"?post', form.group(0))
    assert re.search(r'(?i)action\s*=\s*"?/api/waitlist"?', form.group(0))
    for name in ("email", "role", HP):
        assert re.search(rf'(?i)name\s*=\s*"{name}"', html), f"no {name} field"
    assert re.search(r'(?i)type\s*=\s*"email"', html)
    assert "Join the waitlist" in visible_text(html)

    r = join(client, html=True, email="jo@example.com", role="cmdb_admin", **{HP: ""})
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    assert "You're on the list" in visible_text(r.text)
    assert rows(db)[0]["role"] == "cmdb_admin"


def test_wa8_consent_sentence_shown_is_exactly_what_is_stored(client):
    text = visible_text(_form_html(client))
    assert store.CONSENT_TEXT in text, "the stored consent_text isn't what the visitor sees"
    assert "privacy" in text.lower()


def test_wa8_honeypot_is_hidden_from_people_but_not_from_bots(client):
    html = _form_html(client)
    field = re.search(r'(?is)<input\b[^>]*name\s*=\s*"' + HP + r'"[^>]*>', html).group(0)
    assert 'type="hidden"' not in field.lower(), "bots skip type=hidden, so it catches nothing"
    assert re.search(r'(?i)tabindex\s*=\s*"-1"', field), "keyboard users could tab into the honeypot"
    assert re.search(r'(?i)autocomplete\s*=\s*"off"', field), "browser autofill could fill the honeypot"


def test_wa4_old_website_field_is_not_a_trap(client, db):
    """Browsers autofill "website". It must no longer drop a real person."""
    r = join(client, email="autofill@example.com", website="https://example.com")
    assert r.status_code == 200 and r.json() == OK
    assert [r["email"] for r in rows(db)] == ["autofill@example.com"]


def test_wa8_success_page_says_what_happens_next(client):
    r = join(client, html=True, email="next@example.com")
    assert "We'll email you when Lifecycle Copilot is ready." in visible_text(r.text)
    assert join(client, email="next2@example.com").json() == OK  # JSON body unchanged


def test_wa8_error_shown_once_on_the_no_js_page(client):
    text = visible_text(join(client, html=True, email="nope").text)
    assert text.count("name@company.com") == 1, text


# 500: forced server errors (ux sign-off, PM 24-Oct)

GENERIC_500 = "Something went wrong on our side. Try again in a few minutes."
SECRET_PATH = "/var/lib/lifecycle-waitlist/waitlist.db"


def _assert_nothing_internal(body):
    for leak in ("Traceback", "sqlite3", "OperationalError", SECRET_PATH, "waitlist.db",
                 "/var/lib", "/Users/", "/tmp", "readonly database", 'File "'):
        assert leak not in body, f"500 body leaks {leak!r}"


@pytest.fixture
def broken_store(monkeypatch):
    def boom(*a, **k):
        raise sqlite3.OperationalError(f"unable to open database file {SECRET_PATH}")
    monkeypatch.setattr(app_mod, "add_signup", boom)


@pytest.mark.parametrize("html", [False, True], ids=["json", "no-js"])
def test_500_when_the_store_raises(client, db, broken_store, html):
    r = join(client, html=html, email="err@example.com")
    assert r.status_code == 500
    _assert_nothing_internal(r.text)
    if html:
        assert "text/html" in r.headers["content-type"]
        title = re.search(r"(?is)<title>(.*?)</title>", r.text).group(1)
        assert "Something went wrong" in title, title
        assert GENERIC_500 in visible_text(r.text)
        assert 'href="/"' in r.text, "no way back from the error page"
    else:
        assert r.json() == {"ok": False, "message": GENERIC_500}
    assert rows(db) == []


@pytest.mark.parametrize("html", [False, True], ids=["json", "no-js"])
def test_500_when_the_database_is_read_only(client, db, html):
    """A real failure, not a mock: the db file can't be written."""
    import os
    import stat

    client.get("/api/waitlist/health")  # make sure the file exists first
    os.chmod(db, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
    try:
        r = join(client, html=html, email="ro@example.com")
    finally:
        os.chmod(db, stat.S_IRUSR | stat.S_IWUSR)
    assert r.status_code == 500
    _assert_nothing_internal(r.text)
    assert GENERIC_500 in (visible_text(r.text) if html else r.json()["message"])
    assert rows(db) == []
