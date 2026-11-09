"""M1: read a tower workbook into rows without losing or changing anything.

Every non-empty source row is kept, duplicates included (I4). Canonical fields
sit next to the raw cells. Columns the mapping doesn't know are kept as extras
and passed through to the export.
"""
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from openpyxl import load_workbook
from openpyxl.utils.exceptions import InvalidFileException

from .dates import parse_date
from .dq import DQIssue
from .normalize import norm_hostname, norm_serial
from .schema import ALIASES, DATE_FIELDS, REQUIRED_ALWAYS, is_junk_header, normalise_header


class IngestError(Exception):
    """The file can't be used. The message says what to fix."""


class ProvenanceError(IngestError):
    """A column looks copied by position from the prior file (I6)."""

    def __init__(self, issues: list[DQIssue]):
        self.issues = issues
        cols = ", ".join(i.identifier for i in issues)
        super().__init__(
            f"column(s) {cols} match the prior file by row position but not when rows are paired by serial. "
            "This usually means the column was pasted from the old sheet. Fix the export, "
            "or re-run with --ack-provenance to continue and keep the warning on the Data Quality sheet."
        )


@dataclass
class Row:
    source: str  # "current" | "prior"
    row_no: int  # Excel row number, header is row 1
    fields: dict  # canonical field -> value (dates parsed where possible)
    extras: dict  # unmapped header -> value
    serial_norm: str = ""
    hostname_norm: str = ""
    placeholder_serial: bool = False
    issues: list = field(default_factory=list)

    def get(self, name, default=None):
        return self.fields.get(name, default)

    @property
    def serial(self):
        value = self.fields.get("serial")
        return None if value is None else str(value).strip()

    @property
    def hostname(self):
        value = self.fields.get("name")
        return None if value is None else str(value)

    def __getattr__(self, name):
        # Lets callers write row.os_eos, row.model_id and so on.
        if name.startswith("_") or name in ("fields", "extras"):
            raise AttributeError(name)
        return self.fields.get(name)


@dataclass
class Sheet:
    path: Path
    source: str
    rows: list[Row]
    columns: list[str]  # canonical fields present
    unmapped: list[str]  # headers kept as extras, in file order
    skipped_blank_rows: int
    issues: list[DQIssue]


def _open(path: Path):
    if not path.exists():
        raise IngestError(f"{path}: file not found")
    if path.suffix.lower() not in (".xlsx", ".xlsm"):
        raise IngestError(f"{path.name}: expected an .xlsx file, got '{path.suffix or 'no extension'}'")
    try:
        return load_workbook(path, data_only=True, read_only=True)
    except (zipfile.BadZipFile, InvalidFileException, KeyError, OSError) as exc:
        raise IngestError(
            f"{path.name}: can't open as an Excel workbook. It may be password protected, "
            f"or a CSV saved with an .xlsx name. ({type(exc).__name__})"
        ) from None


def read_sheet(path, source="current", sheet_name=None, required=REQUIRED_ALWAYS) -> Sheet:
    path = Path(path)
    wb = _open(path)
    try:
        if sheet_name:
            if sheet_name not in wb.sheetnames:
                raise IngestError(f"{path.name}: no sheet named '{sheet_name}'. Sheets: {', '.join(wb.sheetnames)}")
            ws = wb[sheet_name]
        else:
            ws = wb[wb.sheetnames[0]]
        cells = list(ws.iter_rows(values_only=True))
    finally:
        wb.close()

    if not cells or all(v is None for v in cells[0]):
        raise IngestError(f"{path.name}: the first sheet is empty, no header row found")

    header = cells[0]
    mapping: dict[int, str] = {}  # column index -> canonical field
    extras: dict[int, str] = {}  # column index -> original header
    issues: list[DQIssue] = []
    for idx, raw in enumerate(header):
        if is_junk_header(raw):
            continue
        canonical = ALIASES.get(normalise_header(raw))
        if canonical and canonical not in mapping.values():
            mapping[idx] = canonical
        else:
            extras[idx] = str(raw).strip()
            if canonical:
                issues.append(
                    DQIssue("warning", "duplicate_column", source, 1, str(raw),
                            f"'{raw}' maps to {canonical}, which an earlier column already fills. Kept as an extra column.")
                )

    missing = [f for f in required if f not in mapping.values()]
    if missing:
        found = ", ".join(str(h) for h in header if h is not None)
        raise IngestError(f"{path.name}: missing required column(s): {', '.join(missing)}. Found: {found}")

    rows: list[Row] = []
    skipped = 0
    for offset, values in enumerate(cells[1:], start=2):
        if all(v is None or (isinstance(v, str) and not v.strip()) for v in values):
            skipped += 1
            continue
        fields, extra = {}, {}
        row_issues = []
        for idx, value in enumerate(values):
            if isinstance(value, str) and not value.strip():
                value = None
            if idx in mapping:
                name = mapping[idx]
                if name in DATE_FIELDS and value is not None:
                    parsed, ok = parse_date(value)
                    if ok:
                        value = parsed
                    else:
                        row_issues.append(
                            DQIssue("warning", "date_unparseable", source, offset, name,
                                    f"'{value}' is not a date this tool can read. Kept as text.")
                        )
                fields[name] = value
            elif idx in extras:
                extra[extras[idx]] = value
        serial, placeholder = norm_serial(fields.get("serial"))
        row = Row(
            source=source,
            row_no=offset,
            fields=fields,
            extras=extra,
            serial_norm=serial,
            hostname_norm=norm_hostname(fields.get("name")),
            placeholder_serial=placeholder,
            issues=row_issues,
        )
        rows.append(row)
        issues.extend(row_issues)

    # Duplicate serials and placeholders are reported by match.run, which sees both files.
    return Sheet(
        path=path,
        source=source,
        rows=rows,
        columns=[mapping[i] for i in sorted(mapping)],
        unmapped=[extras[i] for i in sorted(extras)],
        skipped_blank_rows=skipped,
        issues=issues,
    )


def load(path, source=None, sheet_name=None, required=REQUIRED_ALWAYS) -> list[Row]:
    """Rows from the first sheet (or sheet_name). Source defaults from the file name."""
    path = Path(path)
    if source is None:
        source = "prior" if "prior" in path.stem.lower() else "current"
    return read_sheet(path, source=source, sheet_name=sheet_name, required=required).rows


# Provenance (I6)

MIN_PAIRS = 5  # fewer serial pairs than this and the column can't be judged
SAME_BY_POSITION = 0.9  # share of row positions where the value equals the prior's
MIN_GAP = 0.1  # how far position agreement must beat serial-paired agreement
KEY_FIELDS = ("serial", "name")


def _norm_value(value):
    if value is None:
        return None
    return str(value).strip().upper() or None


def check_provenance(current: list[Row], prior: list[Row]) -> list[DQIssue]:
    """Flags a column whose values line up with the prior file by row position
    better than they line up with the same asset (paired by serial).

    A column that follows the asset agrees at least as well when paired by
    serial as by position, so unchanged columns never trip this, whatever their
    cardinality or row order. A fleet-wide change (say most rows moving to
    24H2) lowers both numbers together, so it doesn't trip it either. A pasted
    column agrees by position and disagrees by asset, which opens the gap.
    """
    prior_by_serial: dict[str, list[Row]] = {}
    for r in prior:
        if r.serial_norm:
            prior_by_serial.setdefault(r.serial_norm, []).append(r)

    columns = {f for r in current for f in r.fields} & {f for r in prior for f in r.fields}
    issues = []
    for col in sorted(columns - set(KEY_FIELDS)):
        positional = [
            (_norm_value(c.fields.get(col)), _norm_value(p.fields.get(col)))
            for c, p in zip(current, prior)
        ]
        positional = [(a, b) for a, b in positional if a is not None and b is not None]
        if len(positional) < MIN_PAIRS:
            continue
        same_pos = sum(a == b for a, b in positional) / len(positional)
        if same_pos < SAME_BY_POSITION:
            continue

        paired = []
        for c in current:
            match = prior_by_serial.get(c.serial_norm) if c.serial_norm else None
            if match and len(match) == 1:
                a, b = _norm_value(c.fields.get(col)), _norm_value(match[0].fields.get(col))
                if a is not None and b is not None:
                    paired.append(a == b)
        if len(paired) < MIN_PAIRS:
            issues.append(
                DQIssue("warning", "provenance_not_checkable", "both", None, col,
                        f"{same_pos:.0%} of rows equal the prior file at the same row position, but only "
                        f"{len(paired)} rows pair by serial, too few to tell a pasted column from an unchanged one.")
            )
            continue
        same_paired = sum(paired) / len(paired)
        if same_pos - same_paired < MIN_GAP:
            continue  # the values follow the asset
        issues.append(
            DQIssue("error", "positional_copy", "both", None, col,
                    f"{same_pos:.0%} of rows equal the prior file at the same row position, "
                    f"but only {same_paired:.0%} equal it when rows are paired by serial "
                    f"({len(paired)} pairs).")
        )
    return issues


def check_pair(current: Sheet, prior: Sheet) -> list[DQIssue]:
    """Run-level warnings that need both files."""
    issues = []
    if prior.rows:
        change = (len(current.rows) - len(prior.rows)) / len(prior.rows)
        if abs(change) > 0.2:
            issues.append(
                DQIssue("warning", "row_count_change", "both", None, "rows",
                        f"current has {len(current.rows)} rows, prior has {len(prior.rows)} ({change:+.0%}).")
            )
    for sheet in (current, prior):
        if not sheet.rows:
            continue
        for col in ("serial", "name"):
            blank = sum(1 for r in sheet.rows if r.fields.get(col) in (None, ""))
            if blank / len(sheet.rows) > 0.5:
                issues.append(
                    DQIssue("warning", "high_blank_rate", sheet.source, None, col,
                            f"{blank} of {len(sheet.rows)} rows have no {col}.")
                )
    return issues


def load_pair(current_path, prior_path, ack_provenance=False, sheet_name=None):
    """Reads both files and runs every check. Raises ProvenanceError on a
    positional copy unless the operator has acknowledged it."""
    from .schema import REQUIRED_CURRENT

    current = read_sheet(current_path, "current", sheet_name, REQUIRED_CURRENT)
    prior = read_sheet(prior_path, "prior", sheet_name, REQUIRED_ALWAYS)
    provenance = check_provenance(current.rows, prior.rows)
    copies = [i for i in provenance if i.severity == "error"]
    if copies and not ack_provenance:
        raise ProvenanceError(copies)
    issues = current.issues + prior.issues + check_pair(current, prior) + provenance
    return current, prior, issues
