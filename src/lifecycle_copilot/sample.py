"""M0: synthetic EUC Windows sample, built to tests/sample_manifest.md.

All values are made up: serials start SN-, hostnames start WKS-, domains are
example.test. No real assets, people or companies.
"""
from datetime import date
from pathlib import Path

from openpyxl import Workbook

CURRENT_HEADERS = [
    "Name", "FQDN", "Managed By Group", "Operating System", "OS Version", "OS EOS",
    "Manufacturer", "Model ID", "Serial Number", "Location", "Assigned To", "Operational Status",
]
PRIOR_HEADERS = [
    "Name", "FQDN", "Product Tribe", "Exec Owner", "Managed By Group", "Operating System", "OS Version",
    "Asset EOL", "Asset EOS", "OS EOL", "Operating System  EOS", "Manufacturer", "Model ID", "Serial Number",
    "Location", "Assigned To", "Disposition Strategy", "Disposition Date", "Remarks",
]

W11E = "Microsoft Windows 11 Enterprise"
W11P = "Microsoft Windows 11 Pro"
OPTI = "OptiPlex 7010"
LAT = "Latitude 5440"
ASSET_EOS = date(2027, 1, 31)
ASSET_EOL = date(2026, 1, 31)


def _fqdn(host):
    return f"{host.strip().lower()}.corp.example.test"


def _cur(case, host, serial, os_name, version, model=OPTI, os_eos=None, fqdn=True):
    return {
        "_case": case,
        "Name": host,
        "FQDN": _fqdn(host) if fqdn else None,
        "Managed By Group": "EUC Support",
        "Operating System": os_name,
        "OS Version": version,
        "OS EOS": os_eos,
        "Manufacturer": "Dell Inc.",
        "Model ID": model,
        "Serial Number": serial,
        "Location": "Site A",
        "Assigned To": f"euc-user-{host.strip()[-3:].lower()}",
        "Operational Status": "Operational",
    }


def _pri(case, host, serial, os_name, version, model=OPTI, os_eos=None, disposition="Manage", remarks=None):
    return {
        "_case": case,
        "Name": host,
        "FQDN": _fqdn(host),
        "Product Tribe": "Workplace Tech",
        "Exec Owner": "Infrastructure leadership",
        "Managed By Group": "EUC Support",
        "Operating System": os_name,
        "OS Version": version,
        "Asset EOL": ASSET_EOL if model == OPTI else None,
        "Asset EOS": ASSET_EOS if model == OPTI else None,
        "OS EOL": None,
        "Operating System  EOS": os_eos,
        "Manufacturer": "Dell Inc.",
        "Model ID": model,
        "Serial Number": serial,
        "Location": "Site A",
        "Assigned To": f"euc-user-{host[-3:].lower()}",
        "Disposition Strategy": disposition,
        "Disposition Date": None,
        "Remarks": remarks,
    }


def current_rows():
    return [
        _cur("CLEAN", " wks-0001 ", "SN-CLEAN-001", W11E, "23H2"),
        _cur("HOST_ONLY", "WKS-0002", None, W11E, "23H2", fqdn=False),
        _cur("HOST_REUSE", "WKS-0003", "SN-NEW-003", W11E, "24H2"),
        _cur("DUP_SERIAL", "WKS-0004A", "SN-DUP-004", W11E, "23H2"),
        _cur("DUP_SERIAL", "WKS-0004B", "SN-DUP-004", W11E, "23H2"),
        _cur("PLACEHOLDER", "WKS-0005", "To be filled by O.E.M.", W11E, "10.0.22631.4317"),
        _cur("HOST_DUP_PRIOR", "WKS-0006", None, W11E, "23H2"),
        _cur("EDITION_CHANGE", "WKS-0007", "SN-ED-007", W11E, "23H2"),
        _cur("NEW", "WKS-0008", "SN-NEW-008", W11E, "24H2"),
        _cur("SOURCE_VALUE", "WKS-0010", "SN-SRC-010", W11E, "24H2", model=LAT, os_eos=date(2030, 1, 1)),
        _cur("NO_EVIDENCE", "WKS-0011", "SN-NOEV-011", W11E, "28H2", model=LAT),
    ]


def prior_rows():
    return [
        _pri("CLEAN", "WKS-0001", "SN-CLEAN-001", W11E, "23H2", os_eos=date(2026, 11, 10), disposition="Renew",
             remarks="Renew before 23H2 Enterprise end of servicing"),
        _pri("HOST_ONLY", "WKS-0002", "SN-HOST-002", W11E, "23H2", os_eos=date(2026, 11, 10)),
        _pri("HOST_REUSE", "WKS-0003", "SN-OLD-003", W11E, "23H2", os_eos=date(2026, 11, 10)),
        _pri("DUP_SERIAL", "WKS-0004A", "SN-DUP-004", W11E, "23H2", os_eos=date(2026, 11, 10)),
        _pri("PLACEHOLDER", "WKS-0005", "N/A", W11E, "23H2", os_eos=date(2026, 11, 10)),
        _pri("HOST_DUP_PRIOR", "WKS-0006", "SN-H6A-006", W11E, "23H2", os_eos=date(2026, 11, 10)),
        _pri("HOST_DUP_PRIOR", "WKS-0006", "SN-H6B-006", W11E, "23H2", os_eos=date(2026, 11, 10)),
        _pri("EDITION_CHANGE", "WKS-0007", "SN-ED-007", W11P, "23H2", os_eos=date(2025, 11, 11)),
        _pri("DROPPED", "WKS-0009", "SN-GONE-009", W11E, "23H2", os_eos=date(2026, 11, 10)),
        _pri("SOURCE_VALUE", "WKS-0010", "SN-SRC-010", W11E, "24H2", model=LAT, os_eos=date(2027, 10, 12)),
    ]


def write_workbook(path, headers, rows, sheet_title="EUC-Windows"):
    """Writes rows (dicts keyed by header) to a one-sheet workbook. Keys that
    start with '_' are notes for humans and are not written."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    wb = Workbook()
    ws = wb.active
    ws.title = sheet_title
    ws.append(headers)
    for r in rows:
        ws.append([r.get(h) for h in headers])
    for col in ws.iter_cols(min_row=2):
        for cell in col:
            if isinstance(cell.value, date):
                cell.number_format = "dd-mmm-yyyy"
    # Fixed metadata so two runs produce the same cells.
    wb.properties.creator = "lifecycle-copilot sample"
    wb.save(path)
    return path


def make(out_dir) -> tuple[Path, Path]:
    out_dir = Path(out_dir)
    current = write_workbook(out_dir / "current.xlsx", CURRENT_HEADERS, current_rows())
    prior = write_workbook(out_dir / "prior.xlsx", PRIOR_HEADERS, prior_rows())
    return current, prior


def make_provenance_pair(out_dir, copied=True) -> tuple[Path, Path]:
    """Two files for the A7 check. Twelve assets, current rows in reverse order
    so serials don't line up by position.

    copied=True: current FQDN is pasted by row position from the prior file,
    so each asset gets another asset's FQDN. The check must stop the run.
    copied=False: every column is simply unchanged per asset (Manufacturer,
    FQDN, Model). The check must not fire.
    """
    out_dir = Path(out_dir)
    hosts = [f"WKS-{n:04d}" for n in range(101, 113)]
    prior = [_pri("PROV", h, f"SN-PROV-{h[-3:]}", W11E, "23H2", os_eos=date(2026, 11, 10)) for h in hosts]
    current = [_cur("PROV", h, f"SN-PROV-{h[-3:]}", W11E, "23H2") for h in reversed(hosts)]
    if copied:
        for c, p in zip(current, prior):
            c["FQDN"] = p["FQDN"]
    cur_path = write_workbook(out_dir / "current.xlsx", CURRENT_HEADERS, current)
    pri_path = write_workbook(out_dir / "prior.xlsx", PRIOR_HEADERS, prior)
    return cur_path, pri_path
