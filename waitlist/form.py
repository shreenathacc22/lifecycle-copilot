"""Waitlist form markup and the no-JavaScript result page (W-A8).

render() is the single source of the form. The landing page carries a copy of
render() with no values filled in, and a test checks the two stay identical.
Every colour comes from the landing page's tokens, so dark mode needs nothing extra.
"""
from html import escape

from .store import ROLES

EMAIL_ERROR = "Enter an email address like name@company.com"
SUCCESS = "You're on the list."
SUCCESS_DETAIL = "We'll email you when Lifecycle Copilot is ready."

CONSENT_HTML = (
    "We'll only email you about Lifecycle Copilot. Unsubscribe or ask us to delete your email "
    'any time. See the <a href="/privacy.html">privacy policy</a>.'
)

FORM_CSS = """
.wl-form { display: grid; gap: 14px; max-width: 760px; }
.wl-fields { display: grid; grid-template-columns: minmax(0, 1.4fr) minmax(0, 1fr) auto; gap: 12px; align-items: start; }
.wl-field { display: grid; gap: 6px; min-width: 0; }
.wl-field label { font: 500 0.85rem/1.3 var(--body); color: var(--ink); }
.wl-field input, .wl-field select {
  font: 400 1rem/1.3 var(--body); color: var(--ink); background: var(--sheet);
  border: 1px solid var(--rule); border-radius: 6px; padding: 11px 12px; min-height: 44px; width: 100%;
}
.wl-field input:focus-visible, .wl-field select:focus-visible { outline: 2px solid var(--cobalt); outline-offset: 2px; border-color: var(--cobalt); }
.wl-field input[aria-invalid="true"], .wl-field select[aria-invalid="true"] { border-color: var(--retire); }
.wl-error { margin: 0; font-size: 0.875rem; color: var(--retire); }
/* label line (0.85rem x 1.3) + field gap, so the button lines up with the inputs */
.wl-submit { min-height: 44px; justify-content: center; white-space: nowrap; margin-top: calc(0.85rem * 1.3 + 6px); }
.wl-submit:disabled { opacity: 0.7; cursor: progress; }
.wl-consent { margin: 0; font-size: 0.9rem; line-height: 1.5; color: var(--ink); max-width: 46em; }
.wl-consent a { color: var(--cobalt); text-decoration: underline; }
.wl-hp { position: absolute; left: -10000px; top: auto; width: 1px; height: 1px; overflow: hidden; }
.wl-result { font: 600 1.1rem/1.4 var(--body); color: var(--ink); padding: 16px 18px; border: 1px solid var(--rule); border-radius: 8px; background: var(--sheet); max-width: 760px; }
.wl-result:focus { outline: 2px solid var(--cobalt); outline-offset: 3px; }
.wl-result.wl-ok { border-color: var(--manage); }
.wl-result.wl-bad { border-color: var(--retire); }
.wl-detail { display: block; margin-top: 4px; font-weight: 400; font-size: 1rem; color: var(--ink); }
@media (max-width: 600px) {
  .wl-fields { grid-template-columns: minmax(0, 1fr); }
  .wl-submit { width: 100%; margin-top: 0; }
}
"""


def render(email: str = "", role: str = "", error: str = "", error_field: str = "email") -> str:
    """The form. Values and the error are escaped; the error is one of a few fixed messages."""
    email_err = error if error and error_field == "email" else ""
    role_err = error if error and error_field == "role" else ""
    options = ['<option value="">Choose one</option>'] + [
        f'<option value="{escape(k)}"{" selected" if k == role else ""}>{escape(v)}</option>'
        for k, v in ROLES.items()
    ]
    return f"""<form class="wl-form" id="waitlist-form" action="/api/waitlist" method="post">
  <div class="wl-fields">
    <div class="wl-field">
      <label for="wl-email">Work email</label>
      <input id="wl-email" name="email" type="email" autocomplete="email" required maxlength="254" value="{escape(email)}" aria-describedby="wl-email-error"{' aria-invalid="true"' if email_err else ''}>
      <p class="wl-error" id="wl-email-error"{'' if email_err else ' hidden'}>{escape(email_err)}</p>
    </div>
    <div class="wl-field">
      <label for="wl-role">Your role (optional)</label>
      <select id="wl-role" name="role" aria-describedby="wl-role-error"{' aria-invalid="true"' if role_err else ''}>
        {"".join(options)}
      </select>
      <p class="wl-error" id="wl-role-error"{'' if role_err else ' hidden'}>{escape(role_err)}</p>
    </div>
    <div class="wl-hp" aria-hidden="true">
      <label for="wl-hp">Leave this field empty</label>
      <input id="wl-hp" name="lc_hp" type="text" tabindex="-1" autocomplete="off">
    </div>
    <button type="submit" class="btn primary wl-submit" aria-describedby="wl-consent">Join the waitlist</button>
  </div>
  <p class="wl-consent" id="wl-consent">{CONSENT_HTML}</p>
</form>"""


PAGE_CSS = """
:root {
  --paper: #f2f4f6; --sheet: #ffffff; --ink: #142033; --ink-soft: #4a5668; --rule: #d7dde5;
  --cobalt: #2340b0; --manage: #1f7a4d; --retire: #b3261e;
  --display: "Bricolage Grotesque", "Avenir Next", "Segoe UI", system-ui, sans-serif;
  --body: "IBM Plex Sans", "Helvetica Neue", Arial, sans-serif;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --paper: #0f1520; --sheet: #161e2c; --ink: #e6ebf2; --ink-soft: #a3aec0; --rule: #2a3547;
    --cobalt: #8ea4ff; --manage: #5fcf95; --retire: #ff8a80; color-scheme: dark;
  }
}
:root[data-theme="dark"] {
  --paper: #0f1520; --sheet: #161e2c; --ink: #e6ebf2; --ink-soft: #a3aec0; --rule: #2a3547;
  --cobalt: #8ea4ff; --manage: #5fcf95; --retire: #ff8a80; color-scheme: dark;
}
* { box-sizing: border-box; }
body {
  margin: 0; background: var(--paper); color: var(--ink); font: 400 1rem/1.6 var(--body);
  padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px));
}
main { max-width: 760px; margin: 0 auto; padding-block: 56px; display: grid; gap: 20px; }
h1 { font: 700 clamp(1.6rem, 4vw, 2.2rem)/1.15 var(--display); margin: 0; text-wrap: balance; }
a { color: var(--cobalt); }
a:focus-visible, button:focus-visible { outline: 2px solid var(--cobalt); outline-offset: 3px; border-radius: 4px; }
.btn { display: inline-flex; align-items: center; gap: 8px; padding: 12px 18px; border-radius: 6px;
  font: 600 0.95rem/1 var(--body); text-decoration: none; border: 1px solid var(--ink); cursor: pointer; }
.btn.primary { background: var(--ink); color: var(--paper); }
.back { font-size: 0.95rem; }
"""


def result_page(message: str, ok: bool, form_html: str = "", title: str = "") -> str:
    """Full page for the no-JS path, and a link back. `message` is one of the
    fixed messages in app.py. When the form comes back with an inline error,
    the page doesn't repeat the message in a box above it."""
    title = title or ("You're on the list" if ok else "Something went wrong")
    if form_html:
        body = form_html
    else:
        detail = f'<span class="wl-detail">{escape(SUCCESS_DETAIL)}</span>' if ok else ""
        body = f'<p class="wl-result {"wl-ok" if ok else "wl-bad"}" role="status">{escape(message)}{detail}</p>'
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="robots" content="noindex">
<title>{escape(title)} · Lifecycle Copilot</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,700&family=IBM+Plex+Sans:wght@400;500;600&display=swap">
<style>{PAGE_CSS}{FORM_CSS}</style>
</head>
<body>
<main>
<h1>{escape(title)}</h1>
{body}
<p class="back"><a href="/">Back to Lifecycle Copilot</a></p>
</main>
</body>
</html>
"""
