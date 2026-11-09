"""Dev unit checks for the waitlist (docs/09). qa's acceptance checks are separate."""
import csv
import os
import re
import sqlite3
from datetime import datetime
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx2")
from fastapi.testclient import TestClient  # noqa: E402

from waitlist import cli, form, store  # noqa: E402
from waitlist.app import create_app  # noqa: E402

# The site moves into the repo as site/ (G2). Until then it sits next to the repo.
_REPO = Path(__file__).resolve().parents[1]
LANDING = next((p for p in (_REPO / "site" / "index.html", _REPO.parent / "landing" / "index.html") if p.exists()),
               _REPO / "site" / "index.html")
FORM_HDR = {"content-type": "application/x-www-form-urlencoded"}


def landing_text():
    """The landing page, or a skip when it isn't in this checkout. REQUIRE_LANDING=1
    (set on the VM run) turns the skip into a failure, so form drift can't hide."""
    if not LANDING.exists():
        if os.environ.get("REQUIRE_LANDING") == "1":
            pytest.fail(f"REQUIRE_LANDING=1 but no landing page at {LANDING}")
        pytest.skip("landing page not in this checkout")
    return LANDING.read_text()


@pytest.fixture
def db(tmp_path):
    return tmp_path / "wl" / "waitlist.db"


@pytest.fixture
def client(db):
    return TestClient(create_app(db), raise_server_exceptions=False)


def rows(db):
    conn = sqlite3.connect(db)
    try:
        return conn.execute("SELECT email, role, consent_text, source, created_at FROM signup ORDER BY id").fetchall()
    finally:
        conn.close()


# Storage


def test_db_is_created_in_wal_mode(db):
    store.connect(db).close()
    conn = sqlite3.connect(db)
    assert conn.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
    cols = [r[1] for r in conn.execute("PRAGMA table_info(signup)")]
    assert cols == ["id", "email", "role", "consent_text", "source", "created_at"]


def test_db_path_defaults_from_env(monkeypatch, tmp_path):
    monkeypatch.setenv("WAITLIST_DB", str(tmp_path / "x.db"))
    assert store.db_path_from_env() == tmp_path / "x.db"
    monkeypatch.delenv("WAITLIST_DB")
    assert str(store.db_path_from_env()) == "/var/lib/lifecycle-waitlist/waitlist.db"


@pytest.mark.parametrize("bad", ["", "   ", "plainaddress", "a@b", "a@b.c", "a b@c.com", "a@@b.com",
                                 "a..b@c.com", "x" * 65 + "@example.com", "a@" + "b" * 250 + ".com", "a@b.com\nx@y.com", 42])
def test_bad_emails_are_rejected(db, bad):
    with pytest.raises(store.InvalidSignup):
        store.add_signup(store.connect(db), bad)


def test_unknown_role_is_rejected(db):
    with pytest.raises(store.InvalidSignup, match="role"):
        store.add_signup(store.connect(db), "a@example.com", "ceo")


def test_repeat_is_not_new_and_changes_nothing(db):
    conn = store.connect(db)
    assert store.add_signup(conn, "Ana@Example.com", "itam_analyst") is True
    assert store.add_signup(conn, "  ana@example.COM ", "other") is False
    assert [r[:2] for r in rows(db)] == [("ana@example.com", "itam_analyst")]


# API: JSON


def test_signup_stores_one_clean_row(client, db):
    r = client.post("/api/waitlist", json={"email": "  Pat@Example.COM ", "role": "infra_lead"})
    assert r.status_code == 200 and r.json() == {"ok": True, "message": "You're on the list."}
    [(email, role, consent, source, created)] = rows(db)
    assert (email, role, consent, source) == ("pat@example.com", "infra_lead", store.CONSENT_TEXT, "landing")
    assert datetime.fromisoformat(created).utcoffset().total_seconds() == 0


def test_repeat_gets_the_same_response(client, db):
    first = client.post("/api/waitlist", json={"email": "pat@example.com"})
    second = client.post("/api/waitlist", json={"email": "PAT@example.com "})
    assert first.status_code == second.status_code == 200
    assert first.json() == second.json()
    assert len(rows(db)) == 1


def test_role_is_optional(client, db):
    assert client.post("/api/waitlist", json={"email": "pat@example.com", "role": ""}).status_code == 200
    assert rows(db)[0][1] is None


@pytest.mark.parametrize("payload", [{"email": "nope"}, {}, {"email": "pat@example.com", "role": "boss"},
                                     {"email": ["a@b.com"]}])
def test_bad_input_is_422_and_stores_nothing(client, db, payload):
    r = client.post("/api/waitlist", json=payload)
    assert r.status_code == 422 and r.json()["ok"] is False
    assert rows(db) == []


def test_email_error_wording(client):
    assert client.post("/api/waitlist", json={"email": "nope"}).json()["message"] == form.EMAIL_ERROR


def test_honeypot_looks_normal_and_stores_nothing(client, db):
    r = client.post("/api/waitlist", json={"email": "bot@example.com", "lc_hp": "http://spam.test"})
    assert r.status_code == 200 and r.json()["message"] == "You're on the list."
    assert rows(db) == []


def test_unreadable_bodies_are_422(client, db):
    assert client.post("/api/waitlist", content=b"{not json", headers={"content-type": "application/json"}).status_code == 422
    assert client.post("/api/waitlist", content=b"[1,2]", headers={"content-type": "application/json"}).status_code == 422
    assert client.post("/api/waitlist", content=b"email=a", headers={"content-type": "text/plain"}).status_code == 422
    big = b'{"email": "' + b"a" * 5000 + b'@example.com"}'
    assert client.post("/api/waitlist", content=big, headers={"content-type": "application/json"}).status_code == 422
    assert rows(db) == []


def test_store_failure_is_a_generic_500(client, db, monkeypatch):
    def boom(*a, **k):
        raise sqlite3.OperationalError("disk I/O error at /var/lib/secret/path")
    monkeypatch.setattr("waitlist.app.add_signup", boom)
    r = client.post("/api/waitlist", json={"email": "pat@example.com"})
    assert r.status_code == 500
    assert "sqlite" not in r.text.lower() and "/var/lib" not in r.text and "disk" not in r.text


def test_health_has_no_counts(client):
    r = client.get("/api/waitlist/health")
    assert r.status_code == 200 and r.json() == {"ok": True}


def test_no_docs_or_extra_routes(client):
    for path in ("/docs", "/redoc", "/openapi.json", "/api/waitlist/export", "/"):
        assert client.get(path).status_code == 404
    assert client.get("/api/waitlist").status_code == 405


def test_nothing_about_the_request_is_stored(client, db):
    client.post("/api/waitlist", json={"email": "pat@example.com"},
                headers={"user-agent": "UA-MARKER/1.0", "x-forwarded-for": "203.0.113.77", "cf-connecting-ip": "203.0.113.77"})
    blob = Path(db).read_bytes() + b"".join(p.read_bytes() for p in Path(db).parent.glob("*-wal"))
    assert b"UA-MARKER" not in blob and b"203.0.113.77" not in blob


# API: no-JavaScript form post (W-A8)


def test_form_post_gets_a_result_page(client, db):
    r = client.post("/api/waitlist", content=b"email=sam%40example.com&role=cmdb_admin&lc_hp=", headers=FORM_HDR)
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/html")
    assert "You&#x27;re on the list." in r.text and 'href="/"' in r.text and "Back to Lifecycle Copilot" in r.text
    assert rows(db)[0][:2] == ("sam@example.com", "cmdb_admin")


def test_form_post_error_shows_the_form_again_with_the_email(client, db):
    r = client.post("/api/waitlist", content=b"email=sam%40nowhere&role=", headers=FORM_HDR)
    assert r.status_code == 422 and "text/html" in r.headers["content-type"]
    assert form.EMAIL_ERROR in r.text
    assert 'value="sam@nowhere"' in r.text and 'aria-invalid="true"' in r.text
    assert rows(db) == []


def test_result_page_escapes_what_was_typed(client):
    r = client.post("/api/waitlist", content=b'email=%22%3E%3Cscript%3Ealert(1)%3C%2Fscript%3E', headers=FORM_HDR)
    assert r.status_code == 422 and "<script>alert(1)" not in r.text


def test_json_accept_on_a_form_post_gets_json(client):
    r = client.post("/api/waitlist", content=b"email=sam%40example.com", headers={**FORM_HDR, "accept": "application/json"})
    assert r.json()["ok"] is True


# Form markup


def test_form_fields_and_consent_order():
    html = form.render()
    names = re.findall(r'name="([a-z_]+)"', html)
    assert names == ["email", "role", "lc_hp"]
    assert html.index("Join the waitlist") < html.index("We'll only email you")
    plain = re.sub(r"<[^>]+>", "", form.CONSENT_HTML)
    assert plain == store.CONSENT_TEXT
    for label in store.ROLES.values():
        assert escape_text(label) in html


def escape_text(s):
    from html import escape
    return escape(s)


def test_honeypot_is_out_of_reach():
    html = form.render()
    hp = html[html.index('class="wl-hp"') - 5: html.index('name="lc_hp"') + 80]
    assert 'aria-hidden="true"' in hp and 'tabindex="-1"' in hp and 'autocomplete="off"' in hp
    assert "display:none" not in form.FORM_CSS.replace(" ", "")


def test_landing_page_carries_the_same_form():
    page = landing_text()
    assert form.render() in page, "landing/index.html form is out of date: paste waitlist.form.render() into it"


# CLI


def test_export_and_delete(db, tmp_path):
    conn = store.connect(db)
    for e in ("a@example.com", "b@example.com", "c@example.com"):
        store.add_signup(conn, e)
    out = tmp_path / "out" / "signups.csv"
    assert cli.export_csv(db, out) == 3
    data = list(csv.DictReader(out.open()))
    assert [r["email"] for r in data] == ["a@example.com", "b@example.com", "c@example.com"]
    assert set(data[0]) == {"id", "email", "role", "consent_text", "source", "created_at"}
    assert cli.delete(db, " B@Example.com ") == 1
    assert cli.delete(db, "b@example.com") == 0
    assert cli.delete(db, "not an email") == 0
    assert [r[0] for r in rows(db)] == ["a@example.com", "c@example.com"]


def test_cli_main(db, tmp_path, capsys):
    store.add_signup(store.connect(db), "a@example.com")
    assert cli.main(["--db", str(db), "export", "--out", str(tmp_path / "e.csv")]) == 0
    assert cli.main(["--db", str(db), "delete", "a@example.com"]) == 0
    assert "removed 1 row(s)" in capsys.readouterr().out


def test_backup_keeps_the_newest(db, tmp_path, monkeypatch):
    store.add_signup(store.connect(db), "a@example.com")
    out = tmp_path / "bk"
    for i in range(9):
        (out).mkdir(exist_ok=True)
        (out / f"waitlist-2026010{i}-000000.db").write_bytes(b"")
    target = cli.backup(db, out, keep=7)
    copies = sorted(out.glob("waitlist-*.db"))
    assert len(copies) == 7 and target in copies
    assert sqlite3.connect(target).execute("SELECT email FROM signup").fetchall() == [("a@example.com",)]


def test_serve_refuses_public_interfaces(db, capsys):
    assert cli.main(["--db", str(db), "serve", "--host", "0.0.0.0"]) == 2
    assert "loopback" in capsys.readouterr().err


def test_module_level_app_for_uvicorn(monkeypatch, tmp_path):
    import importlib

    import waitlist.app as mod

    mod = importlib.reload(mod)
    monkeypatch.setenv("WAITLIST_DB", str(tmp_path / "env.db"))
    r = TestClient(mod.app).post("/api/waitlist", json={"email": "env@example.com"})
    assert r.status_code == 200 and (tmp_path / "env.db").exists()


def test_no_outbound_network_code():
    src = "".join(p.read_text() for p in (Path(__file__).resolve().parents[1] / "waitlist").glob("*.py"))
    for word in ("urllib.request", "http.client", "requests", "httpx", "socket.", "smtplib"):
        assert word not in src, word


def test_backup_is_read_only_and_never_creates_the_db(tmp_path):
    missing = tmp_path / "none" / "waitlist.db"
    with pytest.raises(FileNotFoundError):
        cli.backup(missing, tmp_path / "bk")
    assert not missing.exists()
    db = tmp_path / "w.db"
    store.add_signup(store.connect(db), "a@example.com")
    before = db.stat().st_mtime_ns
    cli.backup(db, tmp_path / "bk2")
    assert db.stat().st_mtime_ns == before


def test_backup_handles_spaces_in_paths(tmp_path):
    db = tmp_path / "with space" / "waitlist.db"
    store.add_signup(store.connect(db), "a@example.com")
    target = cli.backup(db, tmp_path / "out dir")
    assert sqlite3.connect(target).execute("SELECT count(*) FROM signup").fetchone()[0] == 1


def test_button_is_described_by_the_consent_sentence():
    html = form.render()
    assert 'aria-describedby="wl-consent"' in html[html.index("<button"):html.index("</button>")]
    assert '<p class="wl-consent" id="wl-consent">' in html


def test_old_honeypot_name_is_not_a_trap(client, db):
    # A browser autofilling a field called "website" must never drop a real person.
    r = client.post("/api/waitlist", json={"email": "real@example.com", "website": "https://example.com"})
    assert r.status_code == 200 and len(rows(db)) == 1


def test_honeypot_label_does_not_invite_autofill():
    html = form.render()
    assert "website" not in html.lower()


def test_success_page_says_what_happens_next(client):
    r = client.post("/api/waitlist", content=b"email=next%40example.com", headers=FORM_HDR)
    assert "We&#x27;ll email you when Lifecycle Copilot is ready." in r.text
    err = client.post("/api/waitlist", content=b"email=bad", headers=FORM_HDR)
    assert "We&#x27;ll email you when" not in err.text


def test_error_page_button_is_described_by_consent(client):
    r = client.post("/api/waitlist", content=b"email=bad", headers=FORM_HDR)
    assert 'aria-describedby="wl-consent"' in r.text and 'id="wl-consent"' in r.text


def test_landing_page_carries_the_same_form_css():
    assert form.FORM_CSS in landing_text(), "landing/index.html CSS is out of date: paste waitlist.form.FORM_CSS"


def test_error_page_shows_the_error_once(client):
    r = client.post("/api/waitlist", content=b"email=bad", headers=FORM_HDR)
    assert r.text.count(form.EMAIL_ERROR) == 1
    assert "<title>Check your email address" in r.text


def test_error_page_titles_per_case(client, monkeypatch):
    r = client.post("/api/waitlist", content=b"email=a%40example.com&role=boss", headers=FORM_HDR)
    assert r.status_code == 422 and "<h1>Check your role</h1>" in r.text
    monkeypatch.setattr("waitlist.app.add_signup", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("x")))
    r = client.post("/api/waitlist", content=b"email=a%40example.com", headers=FORM_HDR)
    assert r.status_code == 500 and "<h1>Something went wrong</h1>" in r.text and "wl-bad" in r.text
