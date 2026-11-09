"""Approved Windows OS lifecycle policy, keyed on product + version + edition.

Edition is part of the key: the same build under Pro and Enterprise ends on
different dates. OS strings are parsed with exact rules only. An edition or
version this module doesn't recognise gives no date and a reason, never a guess.
"""
import csv
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

DEFAULT_POLICY = Path(__file__).resolve().parents[2] / "data" / "policy" / "windows_os.csv"

# Microsoft's two servicing groups for Windows 11 feature updates.
EDITION_GROUPS = {
    "home": "home_pro",
    "pro": "home_pro",
    "pro education": "home_pro",
    "pro for workstations": "home_pro",
    "se": "home_pro",
    "enterprise": "enterprise_education",
    "education": "enterprise_education",
    "iot enterprise": "enterprise_education",
    "enterprise multi session": "enterprise_education",
    "enterprise ltsc": "ltsc",
    "enterprise ltsb": "ltsc",
    "iot enterprise ltsc": "iot_ltsc",
}

EDITION_LABELS = {
    "home_pro": "Home/Pro",
    "enterprise_education": "Enterprise/Education",
    "ltsc": "Enterprise LTSC",
    "iot_ltsc": "IoT Enterprise LTSC",
    "all": "all editions",
}


@dataclass(frozen=True)
class PolicyRow:
    product: str
    version: str
    build: str
    edition_group: str
    os_eos: date
    source_url: str
    asserted_at: str
    status: str
    note: str = ""


@dataclass(frozen=True)
class OSKey:
    product: str
    version: str
    edition_group: str
    edition: str  # as written, for remarks
    edition_parsed: bool = True  # False when no edition was found (Windows 10 "all" fallback)


LTSC_GROUPS = ("ltsc", "iot_ltsc")
GA_GROUPS = ("home_pro", "enterprise_education", "all")
# LTSC 2019 has no 1809 row of its own in the GA table, so its release code is listed here.
RELEASE_BUILDS = {("Windows 10", "1809"): "17763"}


class Policy:
    def __init__(self, rows: list[PolicyRow]):
        self.rows = [r for r in rows if r.status == "approved"]
        self._by_key = {(r.product, r.version, r.edition_group): r for r in self.rows}
        # Builds are shared across channels (26100 is both 24H2 and LTSC 2024),
        # so build lookups are keyed on the channel as well.
        self._build_to_version = {}
        for r in self.rows:
            channel = r.edition_group if r.edition_group in LTSC_GROUPS else "ga"
            self._build_to_version[(r.product, r.build, channel)] = r.version
        self._release_to_build = dict(RELEASE_BUILDS)
        for r in self.rows:
            if r.edition_group in GA_GROUPS:
                self._release_to_build[(r.product, r.version)] = r.build

    @classmethod
    def load(cls, path=None) -> "Policy":
        path = Path(path or DEFAULT_POLICY)
        with path.open(newline="") as fh:
            rows = [
                PolicyRow(
                    product=r["product"].strip(),
                    version=r["version"].strip().upper(),
                    build=r["build"].strip(),
                    edition_group=r["edition_group"].strip(),
                    os_eos=date.fromisoformat(r["os_eos"].strip()),
                    source_url=r["source_url"].strip(),
                    asserted_at=r["asserted_at"].strip(),
                    status=r["status"].strip(),
                    note=(r.get("note") or "").strip(),
                )
                for r in csv.DictReader(fh)
            ]
        return cls(rows)

    def parse(self, operating_system, os_version, os_edition=None) -> tuple[OSKey | None, str]:
        """Returns (key, "") or (None, reason)."""
        os_text = " ".join(str(operating_system or "").split())
        m = re.search(r"\bWindows\s+(10|11)\b", os_text, flags=re.IGNORECASE)
        if not m:
            return None, f"OS '{os_text or 'blank'}' is not Windows 10 or 11, no policy in v1"
        product = f"Windows {m.group(1)}"

        edition_text = os_edition or os_text[m.end():]
        year = re.search(r"\b(20\d{2})\b", str(edition_text))
        edition_norm = re.sub(r"[^a-z ]+", " ", str(edition_text).lower())
        edition_norm = " ".join(w for w in edition_norm.split() if w not in ("microsoft", "edition"))
        # N and KN editions follow the same lifecycle as their base edition.
        edition_norm = re.sub(r"\s+k?n$", "", edition_norm)
        group = EDITION_GROUPS.get(edition_norm)
        parsed = group is not None
        if group is None:
            if product == "Windows 10" and not edition_norm:
                group = "all"
            elif not edition_norm:
                return None, f"no edition in '{os_text}', can't pick the Pro or Enterprise date"
            else:
                return None, f"edition '{edition_text.strip()}' not recognised"
        edition = " ".join(str(edition_text).split()) if parsed else EDITION_LABELS[group]

        version_text = str(os_version or "").strip().upper()
        release = version_text if re.fullmatch(r"\d{2}H\d|\d{4}", version_text) else None
        build_m = re.fullmatch(r"(?:10\.0\.)?(\d{5})(?:\.\d+)?", version_text)
        build = build_m.group(1) if build_m else None

        if group in LTSC_GROUPS:
            prefix = "IOT LTSC" if group == "iot_ltsc" else "LTSC"
            if year:
                version = f"{prefix} {year.group(1)}"
            else:
                build = build or (release and self._release_to_build.get((product, release)))
                version = build and self._build_to_version.get((product, build, group))
                if not version:
                    return None, f"{EDITION_LABELS[group]} release not given and version '{version_text or 'blank'}' doesn't identify one"
            return OSKey(product, version, group, edition, parsed), ""

        if release and re.fullmatch(r"\d{2}H\d", release):
            version = release
        elif build:
            version = self._build_to_version.get((product, build, "ga"))
            if version is None:
                return None, f"build {build} not in the {product} policy table"
        else:
            return None, f"OS version '{version_text or 'blank'}' not readable as a release (e.g. 23H2) or build"
        return OSKey(product, version, group, edition, parsed), ""

    def lookup(self, key: OSKey) -> tuple[PolicyRow | None, str]:
        row = self._by_key.get((key.product, key.version, key.edition_group))
        if row is None and key.edition_group not in LTSC_GROUPS:
            row = self._by_key.get((key.product, key.version, "all"))
        if row is None:
            return None, f"{key.product} {key.version} {EDITION_LABELS.get(key.edition_group, key.edition_group)} not in the policy table"
        return row, ""
