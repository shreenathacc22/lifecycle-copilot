"""M4: carry forward on match, then fill blanks. Never overwrite (I2), and every
value the tool writes says where it came from (I3).

Order for OS dates: carried (unless the OS changed), approved policy, peers.
Order for asset dates: carried, peers.

OS EOL is not filled in v1. Whether the TLM sheet's OS EOL differs from OS EOS
for Windows is an open question for the ITAM team, so the row gets a remark.
"""
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date

from .dq import DQIssue
from .ingest import Row
from .match import Edge, MatchResult
from .normalize import norm_key
from .policy import EDITION_LABELS, OSKey, Policy
from .schema import EXPORT_LABELS

CARRY_FIELDS = (
    "asset_eol", "asset_eos", "warranty", "os_eol", "os_eos", "ship_date",
    "disposition_strategy", "disposition_date",
    "product_tribe", "exec_owner", "product_line", "product_team", "email_dg",
)
OS_DATE_FIELDS = ("os_eol", "os_eos")
ASSET_PEER_FIELDS = ("asset_eol", "asset_eos")
MIN_PEERS = 2


@dataclass
class FilledRow:
    row: Row
    edge: Edge
    values: dict  # canonical field -> final value
    basis: dict  # canonical field -> source|carried|policy|peer
    notes: list[str] = field(default_factory=list)
    os_changed: str = ""  # what changed, e.g. "edition Pro -> Enterprise"
    os_key: OSKey | None = None
    policy_row: object = None  # PolicyRow used for OS EOS, if any

    STATUS = {"serial": "Matched", "hostname": "Matched", "none": "New", "review": "Needs review"}

    @property
    def status(self) -> str:
        return self.STATUS[self.edge.method]

    @property
    def remarks(self) -> str:
        parts = []
        original = self.values.get("remarks")
        if original:
            parts.append(str(original).strip())
        parts.extend(self.notes)
        return " | ".join(parts) if parts else ""

    def __getattr__(self, name):
        if name.startswith("_") or name in ("row", "values", "basis", "notes", "edge", "os_key", "policy_row", "os_changed"):
            raise AttributeError(name)
        if name == "serial":
            return self.row.serial
        if name == "hostname":
            return self.row.hostname
        return self.values.get(name)


@dataclass
class FillRun:
    """Iterates over FilledRow in current-file order. Also carries the match
    result and every DQ issue so export has the whole run."""

    rows: list[FilledRow]
    match: MatchResult
    policy: Policy
    dq: list[DQIssue]
    ingest_dq: list[DQIssue] = field(default_factory=list)
    peer_asset_dates: bool = False

    def __iter__(self):
        return iter(self.rows)

    def __len__(self):
        return len(self.rows)

    @property
    def fill_counts(self) -> dict:
        counts = defaultdict(int)
        for r in self.rows:
            for f, b in r.basis.items():
                if b != "source":
                    counts[f"{f}_{b}"] += 1
        counts["os_eos_blank"] = sum(1 for r in self.rows if r.values.get("os_eos") is None)
        counts["asset_eos_blank"] = sum(1 for r in self.rows if r.values.get("asset_eos") is None)
        return dict(counts)


def _blank(value) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def _os_change(cur: Row, prior: Row, policy: Policy) -> str:
    """Describes how the OS changed between periods, or "" if it didn't."""
    ck, _ = policy.parse(cur.get("operating_system"), cur.get("os_version"), cur.get("os_edition"))
    pk, _ = policy.parse(prior.get("operating_system"), prior.get("os_version"), prior.get("os_edition"))
    if ck and pk:
        changes = []
        if ck.product != pk.product:
            changes.append(f"product {pk.product} -> {ck.product}")
        if ck.version != pk.version:
            changes.append(f"version {pk.version} -> {ck.version}")
        if ck.edition_group != pk.edition_group:
            changes.append(f"edition {pk.edition} -> {ck.edition}")
        return ", ".join(changes)
    # Fall back to comparing the text exactly when either side can't be parsed.
    before = (norm_key(prior.get("operating_system")), norm_key(prior.get("os_version")), norm_key(prior.get("os_edition")))
    after = (norm_key(cur.get("operating_system")), norm_key(cur.get("os_version")), norm_key(cur.get("os_edition")))
    if before != after and any(before):
        return f"OS '{' '.join(filter(None, before))}' -> '{' '.join(filter(None, after))}'"
    return ""


def _fmt(d) -> str:
    return d.strftime("%d-%b-%Y") if isinstance(d, date) else str(d)


def fill(match_result: MatchResult, policy: Policy | None = None, ingest_dq: list[DQIssue] | None = None,
         peer_asset_dates: bool = False) -> FillRun:
    """peer_asset_dates is off by default: whether a new or replaced device may
    take Asset EOL/EOS from same-model peers depends on how the ITAM team bases
    Asset EOS (ship date or model), which is still open."""
    policy = policy or Policy.load()
    dq: list[DQIssue] = []
    rows: list[FilledRow] = []

    # 1. Start from the source values, then carry forward on match.
    for edge in match_result.edges:
        cur = edge.current
        values = dict(cur.fields)
        basis = {f: "source" for f, v in values.items() if not _blank(v)}
        fr = FilledRow(row=cur, edge=edge, values=values, basis=basis)
        prior = edge.prior
        if prior is not None:
            fr.os_changed = _os_change(cur, prior, policy)
            for f in CARRY_FIELDS:
                pv = prior.get(f)
                if _blank(pv) or not _blank(values.get(f)):
                    continue
                if f in OS_DATE_FIELDS and fr.os_changed:
                    continue
                values[f] = pv
                basis[f] = "carried"
            if fr.os_changed:
                fr.notes.append(f"OS changed ({fr.os_changed}); prior OS dates not carried")
                if basis.get("disposition_strategy") == "carried":
                    dq.append(DQIssue("warning", "disposition_carried_os_change", cur.source, cur.row_no, cur.hostname_norm,
                                      f"disposition '{values['disposition_strategy']}' carried from prior row {prior.row_no} "
                                      f"although the OS changed ({fr.os_changed}). Check it still applies."))
            if _blank(values.get("fqdn")) and not _blank(prior.get("fqdn")):
                if cur.hostname_norm and cur.hostname_norm == prior.hostname_norm:
                    values["fqdn"] = prior.get("fqdn")
                    basis["fqdn"] = "carried"
            if not _blank(prior.get("remarks")) and _blank(values.get("remarks")):
                values["remarks"] = prior.get("remarks")
                basis["remarks"] = "carried"
            carried = [EXPORT_LABELS[f] for f in CARRY_FIELDS + ("fqdn",) if basis.get(f) == "carried"]
            if carried:
                fr.notes.append(f"Carried from prior row {prior.row_no} ({edge.method} match): {', '.join(carried)}")
        rows.append(fr)

    # 2. Approved policy for OS EOS.
    for fr in rows:
        key, why = policy.parse(fr.values.get("operating_system"), fr.values.get("os_version"), fr.values.get("os_edition"))
        fr.os_key = key
        if key and key.edition_parsed and _blank(fr.values.get("os_edition")):
            fr.values["os_edition"] = key.edition
            fr.basis["os_edition"] = "parsed"
        policy_row, miss = (policy.lookup(key) if key else (None, why))
        current_eos = fr.values.get("os_eos")
        if _blank(current_eos):
            if policy_row:
                fr.values["os_eos"] = policy_row.os_eos
                fr.basis["os_eos"] = "policy"
                fr.notes.append(f"OS EOS from policy ({key.product} {key.version} {EDITION_LABELS[policy_row.edition_group]})")
                if policy_row.note:
                    fr.notes.append(policy_row.note + " OS EOL left blank until EOL vs EOS is confirmed")
                fr.policy_row = policy_row
            else:
                fr.notes.append(f"OS EOS: {miss}")
        elif policy_row and isinstance(current_eos, date) and current_eos != policy_row.os_eos:
            dq.append(DQIssue("warning", "policy_mismatch", fr.row.source, fr.row.row_no, fr.row.hostname_norm,
                              f"OS EOS {_fmt(current_eos)} ({fr.basis.get('os_eos', 'source')}) differs from policy "
                              f"{_fmt(policy_row.os_eos)} for {key.product} {key.version} {EDITION_LABELS[policy_row.edition_group]}. "
                              "Existing value kept."))
            fr.notes.append(f"Source OS EOS differs from Microsoft {_fmt(policy_row.os_eos)}; kept")

    # 3. Peers: same model for asset dates, same OS key for OS EOS still blank.
    def peer_fill(fields, group_of, label):
        groups = defaultdict(list)
        for fr in rows:
            g = group_of(fr)
            if g and fr.edge.method != "review":
                groups[g].append(fr)
        for g, members in groups.items():
            for f in fields:
                known = [m.values[f] for m in members if m.basis.get(f) in ("source", "carried") and isinstance(m.values.get(f), date)]
                if len(known) < MIN_PEERS:
                    continue
                distinct = sorted(set(known))
                if len(distinct) > 1:
                    dq.append(DQIssue("info", "peer_conflict", "current", None, f"{label} {g}",
                                      f"{f}: peers disagree ({', '.join(_fmt(d) for d in distinct)}). No peer fill."))
                    continue
                for m in members:
                    if _blank(m.values.get(f)):
                        m.values[f] = distinct[0]
                        m.basis[f] = "peer"
                        m.notes.append(f"{EXPORT_LABELS[f]} from {len(known)} peers with {label} {g}")

    if peer_asset_dates:
        peer_fill(ASSET_PEER_FIELDS, lambda fr: norm_key(fr.values.get("model_id")), "model")
    peer_fill(("os_eos",), lambda fr: fr.os_key and f"{fr.os_key.product} {fr.os_key.version} {fr.os_key.edition_group}", "OS")

    for fr in rows:
        if _blank(fr.values.get("asset_eos")):
            if fr.edge.method == "review":
                why = "needs review first"
            elif peer_asset_dates:
                why = "no carried value and fewer than 2 agreeing peers"
            else:
                why = "no carried value; peer fill for asset dates is off"
            fr.notes.append(f"Asset EOS blank: {why}")

    return FillRun(rows=rows, match=match_result, policy=policy, dq=dq, ingest_dq=list(ingest_dq or []),
                   peer_asset_dates=peer_asset_dates)
