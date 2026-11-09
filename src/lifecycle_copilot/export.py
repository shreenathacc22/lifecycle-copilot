"""M6: the six-sheet workbook.

Report keeps every current row in the legacy column layout, with real Excel
dates. The other five sheets explain the run: totals, rules, per-row match
detail, dropped prior rows and the data quality register.
"""
from datetime import date, datetime
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from .lifecycle import FillRun
from .match import MatchResult
from .schema import DATE_FIELDS, EXPORT_LABELS

SHEETS = ["Report", "Summary", "Matching Logic", "Match Detail", "Dropped", "Data Quality"]
DATE_FORMAT = "dd-mmm-yyyy"
HEADER_FILL = PatternFill("solid", fgColor="DCE3F0")
DEFAULT_NAME = "lifecycle-copilot-report.xlsx"

MATCHING_RULES = [
    ("1", "Normalise", "Serial and hostname are trimmed, upper-cased and stripped of zero-width characters. Placeholder serials (N/A, 0, To be filled by O.E.M. and similar) count as blank."),
    ("2", "Serial match", "Exact match on the normalised serial. A serial that appears more than once in either file is never auto-matched: those rows go to review."),
    ("3", "Hostname fallback", "Only when the row did not match by serial, the hostname is unique in both files, and at least one side has a blank serial."),
    ("4", "Replaced hardware", "Same hostname with two different non-blank serials is not a match. The current row is new, the prior row is dropped, and Data Quality logs hostname reuse."),
    ("5", "New", "Anything else is a new asset."),
    ("6", "Dropped", "Prior rows with no match are listed on the Dropped sheet with the reason."),
    ("-", "Never", "Exact comparisons only: no approximate matching, similarity scores or closest match. AI is not used for matching."),
    ("-", "Carry forward", "Matched rows inherit lifecycle dates, disposition, org fields and remarks into blank cells only. OS dates are not carried when the OS product, version or edition changed."),
    ("-", "Fill blanks", "OS EOS: approved policy table keyed on product + version + edition, then same-OS peers. {asset} Existing values are never overwritten."),
    ("-", "OS EOL", "Not filled in this build. Whether the TLM sheet's OS EOL differs from OS EOS for Windows is still to confirm with the ITAM team. For LTSC releases OS EOS is the end of extended support."),
    ("-", "Status", "Report column. Matched and New rows are complete as far as the evidence goes. Needs review rows (duplicate serials) were not matched and got no peer values; check them before sending."),
    ("-", "Not in this build", "Manage/Renew/Retire decision rules, review screen and AI date research. Pending the ITAM team session."),
]
REVIEW_FILL = PatternFill("solid", fgColor="FBE3B5")


def _style_header(ws):
    for cell in ws[1]:
        cell.font = Font(bold=True)
        cell.fill = HEADER_FILL
        cell.alignment = Alignment(vertical="top", wrap_text=True)
    ws.freeze_panes = "A2"


def _widths(ws, max_width=60):
    for idx, col in enumerate(ws.iter_cols(values_only=True), start=1):
        longest = max((len(str(v)) if v is not None else 0 for v in col), default=8)
        ws.column_dimensions[get_column_letter(idx)].width = min(max(10, longest + 2), max_width)


def _date_cells(ws, columns):
    for col in columns:
        for row in ws.iter_rows(min_row=2, min_col=col, max_col=col):
            for cell in row:
                if isinstance(cell.value, (date, datetime)):
                    cell.number_format = DATE_FORMAT


def _report(ws, run: FillRun):
    fields = list(EXPORT_LABELS)
    extras = []
    for r in run.rows:
        for k in r.row.extras:
            if k not in extras:
                extras.append(k)
    ws.append([EXPORT_LABELS[f] for f in fields] + ["Status", "Match Method"] + extras)
    status_col = len(fields) + 1
    for r in run.rows:
        values = []
        for f in fields:
            v = r.remarks if f == "remarks" else r.values.get(f)
            if isinstance(v, str) and f in DATE_FIELDS:
                v = None if not v.strip() else v  # unparseable source text stays as text, flagged in DQ
            values.append(v)
        ws.append(values + [r.status, r.edge.method] + [r.row.extras.get(k) for k in extras])
        if r.status == "Needs review":
            ws.cell(ws.max_row, status_col).fill = REVIEW_FILL
    _style_header(ws)
    _date_cells(ws, [i + 1 for i, f in enumerate(fields) if f in DATE_FIELDS])


def _summary(ws, run: FillRun, current_path, prior_path, issues):
    c = run.match.counts
    f = run.fill_counts
    sev = {s: sum(1 for i in issues if i.severity == s) for s in ("error", "warning", "info")}
    rows = [
        ("Run at", datetime.now().replace(microsecond=0)),
        ("Current file", str(current_path or "")),
        ("Prior file", str(prior_path or "")),
        ("Current rows in", c["current_rows"]),
        ("Report rows out", len(run.rows)),
        ("Matched by serial", c["serial"]),
        ("Matched by hostname", c["hostname"]),
        ("New", c["new"]),
        ("Needs review (duplicate serial)", c["review"]),
        ("Check: serial + hostname + new + review = current rows",
         "OK" if c["serial"] + c["hostname"] + c["new"] + c["review"] == c["current_rows"] else "MISMATCH"),
        ("Prior rows in", c["prior_rows"]),
        ("Prior rows matched", c["matched"]),
        ("Prior rows dropped", c["dropped"]),
        ("Prior rows in review", c["prior_review"]),
        ("Check: matched + dropped + review = prior rows",
         "OK" if c["matched"] + c["dropped"] + c["prior_review"] == c["prior_rows"] else "MISMATCH"),
        ("Report rows needing review", sum(1 for r in run.rows if r.status == "Needs review")),
        ("OS EOS from source file", sum(1 for r in run.rows if r.basis.get("os_eos") == "source")),
        ("OS EOS from policy", f.get("os_eos_policy", 0)),
        ("OS EOS carried forward", f.get("os_eos_carried", 0)),
        ("OS EOS from peers", f.get("os_eos_peer", 0)),
        ("OS EOS still blank", f.get("os_eos_blank", 0)),
        ("Asset EOS carried forward", f.get("asset_eos_carried", 0)),
        ("Asset EOS from peers", f.get("asset_eos_peer", 0) if run.peer_asset_dates else "off"),
        ("Asset EOS still blank", f.get("asset_eos_blank", 0)),
        ("Data quality errors", sev["error"]),
        ("Data quality warnings", sev["warning"]),
        ("Data quality info", sev["info"]),
    ]
    ws.append(["Measure", "Value"])
    for row in rows:
        ws.append(list(row))
    _style_header(ws)
    ws["B2"].number_format = "dd-mmm-yyyy hh:mm"


def _logic(ws, run: FillRun):
    ws.append(["Step", "Rule", "Detail"])
    asset = ("Asset EOL/EOS: same-model peers (at least 2, all agreeing)." if run.peer_asset_dates else
             "Asset EOL/EOS: carried forward only. Peer fill is off for this run (--peer-asset-dates turns it on).")
    for row in MATCHING_RULES:
        ws.append([cell.replace("{asset}", asset) for cell in row])
    used = {}
    for r in run.rows:
        if r.policy_row is not None:
            used[id(r.policy_row)] = r.policy_row
    if used:
        ws.append([])
        ws.append(["Policy rows used", "OS EOS", "Source (checked)"])
        for p in sorted(used.values(), key=lambda p: (p.product, p.version, p.edition_group)):
            ws.append([f"{p.product} {p.version} {p.edition_group}", p.os_eos, f"{p.source_url} ({p.asserted_at})"])
            ws.cell(ws.max_row, 2).number_format = DATE_FORMAT
    _style_header(ws)


def _detail(ws, match: MatchResult, run: FillRun):
    ws.append(["Current row", "Name", "Serial", "Method", "Prior row", "Prior name", "Prior serial",
               "Hostname changed", "OS changed", "Reason"])
    by_row = {id(r.row): r for r in run.rows}
    for e in match.edges:
        p = e.prior
        fr = by_row.get(id(e.current))
        ws.append([
            e.current.row_no,
            e.current.hostname_norm,
            e.current.fields.get("serial"),
            e.method,
            p.row_no if p else None,
            p.hostname_norm if p else None,
            p.fields.get("serial") if p else None,
            ("yes" if p.hostname_norm != e.current.hostname_norm else "no") if p else None,
            (fr.os_changed or "no") if (fr and p) else None,
            e.reason,
        ])
    _style_header(ws)


def _dropped(ws, match: MatchResult):
    ws.append(["Prior row", "Name", "Serial", "Operating System", "OS Version", "Status", "Reason"])
    for d in match.dropped:
        p = d.prior
        ws.append([p.row_no, p.hostname_norm, p.fields.get("serial"), p.fields.get("operating_system"),
                   p.fields.get("os_version"), "dropped", d.reason])
    for p in match.prior_review:
        ws.append([p.row_no, p.hostname_norm, p.fields.get("serial"), p.fields.get("operating_system"),
                   p.fields.get("os_version"), "needs review", "duplicate serial, not auto-matched"])
    _style_header(ws)


def _dq(ws, issues):
    ws.append(["Severity", "Category", "File", "Row", "Identifier", "Detail"])
    order = {"error": 0, "warning": 1, "info": 2}
    for i in sorted(issues, key=lambda i: (order.get(i.severity, 3), i.category, i.row_no or 0)):
        ws.append([i.severity, i.category, i.source, i.row_no, i.identifier, i.detail])
    _style_header(ws)


def write(run: FillRun, out, current_path=None, prior_path=None) -> Path:
    """Writes the workbook. `out` is a folder (file gets the default name) or a
    path ending in .xlsx. Returns the file path."""
    out = Path(out)
    path = out if out.suffix.lower() == ".xlsx" else out / DEFAULT_NAME
    path.parent.mkdir(parents=True, exist_ok=True)

    issues = list(run.ingest_dq) + list(run.match.dq) + list(run.dq)
    wb = Workbook()
    wb.remove(wb.active)
    sheets = {name: wb.create_sheet(name) for name in SHEETS}
    _report(sheets["Report"], run)
    _summary(sheets["Summary"], run, current_path, prior_path, issues)
    _logic(sheets["Matching Logic"], run)
    _detail(sheets["Match Detail"], run.match, run)
    _dropped(sheets["Dropped"], run.match)
    _dq(sheets["Data Quality"], issues)
    for ws in wb.worksheets:
        _widths(ws)
    wb.save(path)
    return path
