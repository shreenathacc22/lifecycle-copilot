"""Canonical fields for the EUC Windows tower and how headers map onto them.

Input headers are matched after normalising (lower case, punctuation and
repeated spaces removed), so "Operating System  EOS" and "operating system eos"
land on the same field. Export uses EXPORT_LABELS so the Report sheet looks like
the sheet the ITAM team already reads.

TO CONFIRM with the ITAM team: the exact legacy labels and column order in the
TLM Data Gathering Template. These follow the build spec §5.
"""
import re

# Canonical field -> label written on the Report sheet, in column order.
EXPORT_LABELS = {
    "name": "Name",
    "fqdn": "FQDN",
    "product_tribe": "Product Tribe",
    "exec_owner": "Exec Owner",
    "product_line": "Product Line",
    "product_team": "Product Team",
    "email_dg": "Email DG",
    "managed_by_group": "Managed By Group",
    "operating_system": "Operating System",
    "os_version": "OS Version",
    "os_edition": "OS Edition",
    "asset_eol": "Asset EOL",
    "asset_eos": "Asset EOS",
    "warranty": "Warranty Expiration- Aseet",
    "os_eol": "OS EOL",
    "os_eos": "OS EOS",
    "location": "Location",
    "assigned_to": "Assigned To",
    "manufacturer": "Manufacturer",
    "model_id": "Model ID",
    "serial": "Serial Number",
    "operational_status": "Operational Status",
    "ship_date": "Ship Date",
    "disposition_strategy": "Disposition Strategy",
    "disposition_date": "Disposition Date",
    "remarks": "Remarks",
}

CANONICAL_FIELDS = tuple(EXPORT_LABELS)

DATE_FIELDS = frozenset(
    {"asset_eol", "asset_eos", "warranty", "os_eol", "os_eos", "ship_date", "disposition_date"}
)

# Normalised header -> canonical field. Anything not listed is kept as an
# unmapped column and passed through to the export untouched.
ALIASES = {
    "name": "name",
    "hostname": "name",
    "host name": "name",
    "computer name": "name",
    "fqdn": "fqdn",
    "fully qualified domain name": "fqdn",
    "hostname fqdn": "fqdn",
    "product tribe": "product_tribe",
    "exec owner": "exec_owner",
    "gap leader": "exec_owner",
    "product line": "product_line",
    "product team": "product_team",
    "email dg": "email_dg",
    "managed by group": "managed_by_group",
    "operating system": "operating_system",
    "os": "operating_system",
    "os name": "operating_system",
    "os version": "os_version",
    "operating system version": "os_version",
    "os edition": "os_edition",
    "edition": "os_edition",
    "asset eol": "asset_eol",
    "asset eos": "asset_eos",
    "warranty": "warranty",
    "warranty expiration": "warranty",
    "warranty expiration asset": "warranty",
    "warranty expiration aseet": "warranty",
    "os eol": "os_eol",
    "operating system eol": "os_eol",
    "os eos": "os_eos",
    "operating system eos": "os_eos",
    "location": "location",
    "assigned to": "assigned_to",
    "manufacturer": "manufacturer",
    "mfr": "manufacturer",
    "model id": "model_id",
    "model": "model_id",
    "serial": "serial",
    "serial number": "serial",
    "serial no": "serial",
    "operational status": "operational_status",
    "ship date": "ship_date",
    "disposition strategy": "disposition_strategy",
    "disposition date": "disposition_date",
    "remarks": "remarks",
    "remarks comment": "remarks",
    "comment": "remarks",
}

REQUIRED_ALWAYS = ("name", "serial")
REQUIRED_CURRENT = ("name", "serial", "operating_system", "os_version")


def normalise_header(header) -> str:
    text = str(header).replace(" ", " ")
    text = re.sub(r"[^0-9a-zA-Z]+", " ", text)
    return " ".join(text.lower().split())


def is_junk_header(header) -> bool:
    """Blank headers and pandas-style 'Unnamed: 26' columns are dropped at ingest."""
    if header is None:
        return True
    text = str(header).strip()
    return not text or bool(re.fullmatch(r"Unnamed:?\s*\d+", text, flags=re.IGNORECASE))
