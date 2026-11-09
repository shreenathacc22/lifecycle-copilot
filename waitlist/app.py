"""FastAPI service for the waitlist (W3). Listens on 127.0.0.1 behind nginx.

POST /api/waitlist        JSON or form-encoded: email, role (optional), lc_hp (honeypot)
GET  /api/waitlist/health {"ok": true}

Error bodies only ever carry one of the fixed messages below. No docs or
OpenAPI routes, no stack traces, no IP or user agent stored (W4).
"""
import json
import logging
from urllib.parse import parse_qs

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response

from . import form
from .store import InvalidSignup, add_signup, connect, db_path_from_env

log = logging.getLogger("waitlist")

MAX_BODY = 4096
GENERIC_ERROR = "Something went wrong on our side. Try again in a few minutes."
BAD_REQUEST = "Send the form as JSON or a normal form post."


def _wants_html(request: Request, is_form: bool) -> bool:
    accept = request.headers.get("accept", "")
    if "application/json" in accept and "text/html" not in accept:
        return False
    return is_form or "text/html" in accept


def _reply(html: bool, status: int, message: str, ok: bool, form_html: str = "", title: str = "") -> Response:
    if html:
        return HTMLResponse(form.result_page(message, ok, form_html, title), status_code=status)
    return JSONResponse({"ok": ok, "message": message}, status_code=status)


async def _read_fields(request: Request) -> tuple[dict, bool] | None:
    """Returns (fields, is_form) or None if the body can't be read."""
    body = await request.body()
    if len(body) > MAX_BODY:
        return None
    ctype = request.headers.get("content-type", "").split(";")[0].strip().lower()
    try:
        if ctype == "application/json":
            data = json.loads(body or b"{}")
            if not isinstance(data, dict):
                return None
            return {k: data.get(k) for k in ("email", "role", "lc_hp")}, False
        if ctype == "application/x-www-form-urlencoded":
            parsed = parse_qs(body.decode("utf-8"), keep_blank_values=True, max_num_fields=10)
            return {k: (parsed.get(k) or [""])[0] for k in ("email", "role", "lc_hp")}, True
    except (ValueError, UnicodeDecodeError):
        return None
    return None


def create_app(db_path=None) -> FastAPI:
    path = db_path or db_path_from_env()
    connect(path).close()  # create the file and table at start-up, so a bad path fails early

    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

    @app.exception_handler(Exception)
    async def _unexpected(request: Request, exc: Exception):
        log.exception("waitlist error")
        return JSONResponse({"ok": False, "message": GENERIC_ERROR}, status_code=500)

    @app.get("/api/waitlist/health")
    def health():
        return {"ok": True}

    @app.post("/api/waitlist")
    async def join(request: Request):
        read = await _read_fields(request)
        if read is None:
            return _reply("text/html" in request.headers.get("accept", ""), 422, BAD_REQUEST, False)
        fields, is_form = read
        html = _wants_html(request, is_form)

        trap = fields.get("lc_hp")
        if trap not in (None, "") and str(trap).strip():
            return _reply(html, 200, form.SUCCESS, True)  # honeypot: look normal, store nothing

        email, role = fields.get("email"), fields.get("role")
        try:
            conn = connect(path)
            try:
                add_signup(conn, email, role)
            finally:
                conn.close()
        except InvalidSignup as exc:
            field = "role" if "role" in str(exc).lower() else "email"
            typed = email.strip()[:254] if isinstance(email, str) else ""
            again = form.render(email=typed, role=role if field == "email" and isinstance(role, str) else "",
                                error=str(exc), error_field=field)
            title = "Check your role" if field == "role" else "Check your email address"
            return _reply(html, 422, str(exc), False, again, title)
        except Exception:
            log.exception("waitlist store failed")
            return _reply(html, 500, GENERIC_ERROR, False)
        return _reply(html, 200, form.SUCCESS, True)

    return app


_app = None


def __getattr__(name):
    # `uvicorn waitlist.app:app` builds the app on first use, from $WAITLIST_DB.
    # Importing the module (tests, CLI) never opens the default path.
    global _app
    if name == "app":
        if _app is None:
            _app = create_app()
        return _app
    raise AttributeError(name)
