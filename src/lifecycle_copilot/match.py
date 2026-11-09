"""M2: deterministic matching, spec §6.

1. Normalise serial and hostname. Placeholder serials count as blank.
2. Exact serial match. A serial that appears more than once in either file
   never auto-matches; those rows go to review.
3. Hostname fallback only when the hostname is unique in both files and at
   least one side has a blank serial.
4. Same hostname with two different serials is replaced hardware: no match.
5. Anything else is a new asset. Unmatched prior rows are dropped.

Exact comparisons only. No similarity scores, no closest match (I1).
"""
from collections import Counter
from dataclasses import dataclass, field

from .dq import DQIssue
from .ingest import Row


@dataclass
class Edge:
    current: Row
    prior: Row | None
    method: str  # "serial" | "hostname" | "none" | "review"
    reason: str


@dataclass
class Dropped:
    prior: Row
    reason: str


@dataclass
class MatchResult:
    current: list[Row]
    prior: list[Row]
    edges: list[Edge]  # one per current row, in file order
    dropped: list[Dropped]  # prior rows with no match and not in review
    prior_review: list[Row]  # prior rows held back by a duplicate serial
    dq: list[DQIssue] = field(default_factory=list)

    @property
    def counts(self) -> dict:
        by_method = Counter(e.method for e in self.edges)
        return {
            "current_rows": len(self.current),
            "prior_rows": len(self.prior),
            "serial": by_method["serial"],
            "hostname": by_method["hostname"],
            "new": by_method["none"],
            "review": by_method["review"],
            "matched": sum(1 for e in self.edges if e.prior is not None),
            "dropped": len(self.dropped),
            "prior_review": len(self.prior_review),
        }


def _index(rows: list[Row], key: str) -> dict[str, list[Row]]:
    out: dict[str, list[Row]] = {}
    for r in rows:
        value = getattr(r, key)
        if value:
            out.setdefault(value, []).append(r)
    return out


def _rows(rows: list[Row]) -> str:
    return ", ".join(str(r.row_no) for r in rows)


def run(current: list[Row], prior: list[Row]) -> MatchResult:
    dq: list[DQIssue] = []
    cur_by_serial = _index(current, "serial_norm")
    pri_by_serial = _index(prior, "serial_norm")
    cur_by_host = _index(current, "hostname_norm")
    pri_by_host = _index(prior, "hostname_norm")

    for rows in (current, prior):
        for r in rows:
            if r.placeholder_serial:
                dq.append(DQIssue("info", "placeholder_serial", r.source, r.row_no, str(r.fields.get("serial")),
                                  f"placeholder serial on {r.hostname_norm or 'a row with no hostname'}, treated as blank"))

    dup_serials = {s for s, rs in cur_by_serial.items() if len(rs) > 1} | {
        s for s, rs in pri_by_serial.items() if len(rs) > 1
    }
    for s in sorted(dup_serials):
        c, p = cur_by_serial.get(s, []), pri_by_serial.get(s, [])
        dq.append(DQIssue("warning", "duplicate_serial", "both", (c or p)[0].row_no, s,
                          f"serial in {len(c)} current row(s) [{_rows(c)}] and {len(p)} prior row(s) [{_rows(p)}]. "
                          "Not auto-matched. All rows kept and sent to review."))

    edges: dict[int, Edge] = {}  # keyed by id(current row)
    matched_prior: set[int] = set()
    reused_hosts: set[str] = set()
    not_unique_hosts: set[str] = set()

    # Step 2: serial
    for c in current:
        s = c.serial_norm
        if not s:
            continue
        if s in dup_serials:
            edges[id(c)] = Edge(c, None, "review", f"duplicate serial {s}, needs review")
        elif s in pri_by_serial:
            p = pri_by_serial[s][0]
            edges[id(c)] = Edge(c, p, "serial", f"serial {s}")
            matched_prior.add(id(p))

    prior_review = [p for p in prior if p.serial_norm in dup_serials]
    held = {id(p) for p in prior_review}

    # Steps 3 to 5: hostname fallback, else new
    for c in current:
        if id(c) in edges:
            continue
        h = c.hostname_norm
        candidates = pri_by_host.get(h, []) if h else []
        if not candidates:
            why = "serial and hostname not in prior" if h else "no serial match and no hostname"
            edges[id(c)] = Edge(c, None, "none", f"new asset: {why}")
            continue
        if len(cur_by_host.get(h, [])) > 1 or len(candidates) > 1:
            n_cur, n_pri = len(cur_by_host.get(h, [])), len(candidates)
            dq.append(DQIssue("warning", "hostname_not_unique", "both", c.row_no, h,
                              f"hostname in {n_cur} current row(s) and {n_pri} prior row(s) [{_rows(candidates)}]. "
                              "Hostname fallback needs a unique name, so no match."))
            not_unique_hosts.add(h)
            edges[id(c)] = Edge(c, None, "none", f"new asset: hostname {h} not unique ({n_cur} current, {n_pri} prior)")
            continue
        p = candidates[0]
        if c.serial_norm and p.serial_norm:
            # Both serials present and different (equal serials matched in step 2).
            dq.append(DQIssue("warning", "hostname_reuse", "both", c.row_no, h,
                              f"same hostname, different serials: current {c.serial_norm}, prior {p.serial_norm} "
                              f"(prior row {p.row_no}). Treated as replaced hardware."))
            reused_hosts.add(h)
            edges[id(c)] = Edge(c, None, "none", f"new asset: hostname {h} reused, serial changed from {p.serial_norm}")
            continue
        if id(p) in matched_prior or id(p) in held:
            edges[id(c)] = Edge(c, None, "none", f"new asset: prior row {p.row_no} with hostname {h} is already matched or in review")
            continue
        blank = "both serials blank" if not (c.serial_norm or p.serial_norm) else (
            "current serial blank" if not c.serial_norm else "prior serial blank")
        edges[id(c)] = Edge(c, p, "hostname", f"hostname {h}, unique in both files, {blank}")
        matched_prior.add(id(p))

    # Step 6: dropped
    dropped = []
    for p in prior:
        if id(p) in matched_prior or id(p) in held:
            continue
        if p.hostname_norm and p.hostname_norm in reused_hosts:
            reason = f"hostname {p.hostname_norm} now on a different serial (replaced hardware)"
        elif p.hostname_norm and p.hostname_norm in not_unique_hosts:
            reason = f"hostname {p.hostname_norm} not unique, could not be matched safely"
        else:
            reason = "not in current export"
        dropped.append(Dropped(p, reason))

    return MatchResult(
        current=current,
        prior=prior,
        edges=[edges[id(c)] for c in current],
        dropped=dropped,
        prior_review=prior_review,
        dq=dq,
    )
