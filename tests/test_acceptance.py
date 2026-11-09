"""Acceptance checks A1 to A13 from docs/05-product-spec.md §11.

Expected values come from tests/sample_manifest.md. Change the two together.

Assumed result shape (the conftest adapter can translate if dev's differs):
- match result .edges: items with .current and .prior (row or None) and .method
  in {"serial", "hostname", "none", "review"}
- .counts: dict with serial, hostname, new, review, matched, dropped, prior_review
- .dq: items with .category
"""
from datetime import date
from pathlib import Path

import pytest

PKG = Path(__file__).resolve().parents[1] / "src" / "lifecycle_copilot"


def _host(row):
    return (row.hostname or "").strip().upper()


def _edge_for(result, *, current_host=None, prior_host=None):
    for e in result.edges:
        if current_host and e.current is not None and _host(e.current) == current_host:
            return e
        if prior_host and e.prior is not None and _host(e.prior) == prior_host:
            return e
    raise AssertionError(f"no edge for current={current_host} prior={prior_host}")


@pytest.fixture
def matched(sample_paths, ingest, match):
    current, prior = sample_paths
    return match(ingest(current), ingest(prior))


def _dq(result, category):
    return [d for d in result.dq if d.category == category]


# M2: matching


def test_a1_same_hostname_different_serial_is_not_a_match(matched):
    e = _edge_for(matched, current_host="WKS-0003")
    assert e.prior is None and e.method == "none"
    assert _dq(matched, "hostname_reuse")


def test_a3_duplicate_serial_goes_to_review(matched):
    for host in ("WKS-0004A", "WKS-0004B"):
        e = _edge_for(matched, current_host=host)
        assert e.method == "review", f"{host} auto-matched"
    assert _dq(matched, "duplicate_serial")


def test_a10_hostname_fallback_when_one_serial_blank(matched):
    assert _edge_for(matched, current_host="WKS-0002").method == "hostname"


def test_a11_hostname_not_unique_in_prior_is_not_a_match(matched):
    e = _edge_for(matched, current_host="WKS-0006")
    assert e.prior is None and e.method == "none"


def test_placeholder_serials_count_as_blank(matched):
    assert _edge_for(matched, current_host="WKS-0005").method == "hostname"
    assert _dq(matched, "placeholder_serial")


def test_hostname_is_normalised_before_serial_match(matched):
    assert _edge_for(matched, current_host="WKS-0001").method == "serial"


def test_counts_match_manifest(matched):
    c = matched.counts
    assert (c["serial"], c["hostname"], c["new"], c["review"]) == (3, 2, 4, 2)
    assert (c["matched"], c["dropped"], c["prior_review"]) == (5, 4, 1)


def test_matching_is_repeatable(sample_paths, ingest, match):
    current, prior = sample_paths
    a = match(ingest(current), ingest(prior))
    b = match(ingest(current), ingest(prior))
    key = lambda r: [(e.method, e.current and e.current.serial, e.prior and e.prior.serial) for e in r.edges]
    assert key(a) == key(b)


def test_no_similarity_matching_in_package():
    if not PKG.exists():
        pytest.skip("package not created yet")
    banned = ("difflib", "fuzz", "levenshtein", "jaro", "SequenceMatcher")
    hits = [
        f"{p.name}: {word}"
        for p in PKG.rglob("*.py")
        for word in banned
        if word.lower() in p.read_text().lower()
    ]
    assert not hits, hits


@pytest.mark.skip(reason="A12 frozen Sep-2026 set: no real data on this machine")
def test_a12_frozen_test_set_counts():
    pass


# M1: ingest


def test_a4_ingest_keeps_every_row(sample_paths, ingest):
    current, prior = sample_paths
    assert len(ingest(current)) == 11
    assert len(ingest(prior)) == 10


def test_a7_positional_copy_stops_the_run(tmp_path, ingest):
    from lifecycle_copilot import ingest as ing
    from lifecycle_copilot.sample import make_provenance_pair

    current, prior = make_provenance_pair(tmp_path, copied=True)
    with pytest.raises(ing.ProvenanceError) as exc:
        ing.load_pair(current, prior)
    assert any(i.category == "positional_copy" for i in exc.value.issues)


def test_a7_unchanged_column_does_not_trip_the_check(tmp_path, ingest):
    from lifecycle_copilot import ingest as ing
    from lifecycle_copilot.sample import make_provenance_pair

    current, prior = make_provenance_pair(tmp_path, copied=False)
    ing.load_pair(current, prior)


def test_a7_low_cardinality_column_copied_by_position(tmp_path, ingest):
    """Dev skips low-cardinality columns. Check a positionally copied OS edition
    column (only Pro / Enterprise values) is still caught, since that would
    silently feed the wrong edition into the OS date lookup (A2)."""
    from openpyxl import load_workbook
    from lifecycle_copilot import ingest as ing
    from lifecycle_copilot.sample import make_provenance_pair

    current, prior = make_provenance_pair(tmp_path, copied=False)
    cur_wb, pri_wb = load_workbook(current), load_workbook(prior)
    cur, pri = cur_wb.active, pri_wb.active
    col = cur.max_column + 1
    cur.cell(1, col, "OS Edition")
    pri.cell(1, pri.max_column + 1, "OS Edition")
    pcol = pri.max_column
    n = min(cur.max_row, pri.max_row)
    # Current rows are the prior rows reversed, so the pattern must not be
    # symmetric under reversal, or every asset keeps its edition when paired
    # by serial and nothing was really copied. First third Pro, rest Enterprise.
    for r in range(2, n + 1):
        edition = "Pro" if r <= 1 + (n - 1) // 3 else "Enterprise"
        pri.cell(r, pcol, edition)
        cur.cell(r, col, edition)  # same position, but current rows are reversed
    cur_wb.save(current)
    pri_wb.save(prior)
    with pytest.raises(ing.ProvenanceError):
        ing.load_pair(current, prior)


# M4: carry forward and policy fill


def test_a2_edition_change_recomputes_os_eos(sample_paths, ingest, match, fill):
    current, prior = sample_paths
    rows = fill(match(ingest(current), ingest(prior)), policy=None)
    row = next(r for r in rows if r.serial == "SN-ED-007")
    assert row.os_eos == date(2026, 11, 10)
    assert "edition" in (row.remarks or "").lower()


def test_a6_source_value_is_never_overwritten(sample_paths, ingest, match, fill):
    current, prior = sample_paths
    rows = fill(match(ingest(current), ingest(prior)), policy=None)
    row = next(r for r in rows if r.serial == "SN-SRC-010")
    assert row.os_eos == date(2030, 1, 1)


def test_no_evidence_stays_blank_with_reason(sample_paths, ingest, match, fill):
    current, prior = sample_paths
    rows = fill(match(ingest(current), ingest(prior)), policy=None)
    row = next(r for r in rows if r.serial == "SN-NOEV-011")
    assert row.os_eos is None
    assert row.remarks


# Deferred until after the user session (M5, M7, M8)


@pytest.mark.skip(reason="A5 LLM step is M8, deferred")
def test_a5_llm_date_has_citation_and_is_reviewed():
    pass


@pytest.mark.skip(reason="A8 decision rules are M5, deferred")
def test_a8_no_evidence_is_needs_review_not_manage():
    pass


@pytest.mark.skip(reason="A9 overrides are M7, deferred")
def test_a9_override_is_applied_and_not_recomputed():
    pass


# M6: export


def test_a4_a13_export_rows_and_dates(sample_paths, ingest, match, fill, export, tmp_path):
    from openpyxl import load_workbook

    current, prior = sample_paths
    out = export(fill(match(ingest(current), ingest(prior)), policy=None), tmp_path)
    wb = load_workbook(out)
    assert wb.sheetnames == ["Report", "Summary", "Matching Logic", "Match Detail", "Dropped", "Data Quality"]
    report = wb["Report"]
    assert report.max_row - 1 == 11
    headers = [c.value for c in report[1]]
    date_cols = [i for i, h in enumerate(headers) if h and ("EOL" in h or "EOS" in h or "Date" in h)]
    for row in report.iter_rows(min_row=2):
        for i in date_cols:
            v = row[i].value
            assert v is None or isinstance(v, (date,)), f"{headers[i]} is text: {v!r}"


# Simulated operator review fixes (tests/uat-simulated-operator-2026-10-24.md).
# Fixed by dev 24-Oct. Each test names its U-item.



def _workbook(sample_paths, ingest, match, fill, export, tmp_path):
    from openpyxl import load_workbook

    current, prior = sample_paths
    return load_workbook(export(fill(match(ingest(current), ingest(prior)), policy=None), tmp_path))


def test_u2_report_flags_rows_needing_review(sample_paths, ingest, match, fill, export, tmp_path):
    report = _workbook(sample_paths, ingest, match, fill, export, tmp_path)["Report"]
    headers = [c.value or "" for c in report[1]]
    status = [i for i, h in enumerate(headers) if "status" in h.lower() and "operational" not in h.lower()]
    assert status, f"no review/match status column in Report: {headers}"
    by_name = {(r[0].value or "").strip().upper(): r[status[0]].value for r in report.iter_rows(min_row=2)}
    for host in ("WKS-0004A", "WKS-0004B"):
        assert "review" in str(by_name[host]).lower()
    assert "review" not in str(by_name["WKS-0001"]).lower()


def test_u3_policy_mismatch_is_a_warning(sample_paths, ingest, match, fill, export, tmp_path):
    dq = _workbook(sample_paths, ingest, match, fill, export, tmp_path)["Data Quality"]
    rows = [r for r in dq.iter_rows(min_row=2, values_only=True) if r[1] == "policy_mismatch"]
    assert rows and all(r[0] == "warning" for r in rows)


def test_u4_summary_os_eos_counts_add_up(sample_paths, ingest, match, fill, export, tmp_path):
    summary = dict(_workbook(sample_paths, ingest, match, fill, export, tmp_path)["Summary"].iter_rows(min_row=2, values_only=True))
    os_eos = sum(v for k, v in summary.items() if k.startswith("OS EOS") and isinstance(v, int))
    assert os_eos == summary["Current rows in"]


def test_u1_peer_asset_fill_is_off_by_default(sample_paths, ingest, match, fill):
    current, prior = sample_paths
    rows = {r.serial: r for r in fill(match(ingest(current), ingest(prior)), policy=None)}
    for serial in ("SN-NEW-003", "SN-NEW-008"):  # replaced and new hardware
        assert rows[serial].asset_eos is None, f"{serial} got a peer Asset EOS"
        assert rows[serial].remarks


# LTSC build collision: 19044 is Win10 21H2 and LTSC 2021; 26100 is Win11 24H2 and LTSC 2024.


@pytest.mark.parametrize("product_text, ltsc_text, build", [
    ("Microsoft Windows 10 Enterprise", "Microsoft Windows 10 Enterprise LTSC 2021", "10.0.19044.5011"),
    ("Microsoft Windows 11 Enterprise", "Microsoft Windows 11 Enterprise LTSC 2024", "10.0.26100.2033"),
])
def test_ltsc_and_general_channel_with_same_build_get_different_rows(product_text, ltsc_text, build):
    policy_mod = pytest.importorskip("lifecycle_copilot.policy")
    policy = policy_mod.Policy.load()
    ga_key, _ = policy.parse(product_text, build)
    ltsc_key, _ = policy.parse(ltsc_text, build)
    ltsc_row, why = policy.lookup(ltsc_key) if ltsc_key else (None, "not parsed")
    if ltsc_row is None:
        pytest.xfail(f"LTSC rows not loaded yet: {why}")
    ga_row, _ = policy.lookup(ga_key)
    assert ltsc_key.edition_group in policy_mod.LTSC_GROUPS
    assert ga_key.edition_group not in policy_mod.LTSC_GROUPS
    assert ga_row is not ltsc_row
    assert ga_row is None or ga_row.os_eos != ltsc_row.os_eos


def test_ltsc_never_falls_back_to_general_channel_date():
    """An LTSC device with no LTSC row must stay blank, not borrow the 'all' row."""
    policy_mod = pytest.importorskip("lifecycle_copilot.policy")
    policy = policy_mod.Policy.load()
    key, _ = policy.parse("Microsoft Windows 10 Enterprise LTSC 2015", "10.0.10240.1")
    if key is None:
        return  # unparsed means blank with a reason, which is also safe
    row, _ = policy.lookup(key)
    assert row is None or key.edition_group in policy_mod.LTSC_GROUPS and row.edition_group == key.edition_group


def test_u5_remarks_have_no_urls_and_sources_are_listed_once(sample_paths, ingest, match, fill, export, tmp_path):
    wb = _workbook(sample_paths, ingest, match, fill, export, tmp_path)
    report = wb["Report"]
    headers = [c.value for c in report[1]]
    remarks = [r[headers.index("Remarks")].value or "" for r in report.iter_rows(min_row=2)]
    assert not [r for r in remarks if "http" in r]
    assert not [r for r in remarks if "OS EOL left blank" in r]
    logic = " ".join(str(v) for r in wb["Matching Logic"].iter_rows(values_only=True) for v in r if v)
    assert "learn.microsoft.com" in logic


def test_u6_disposition_carried_after_os_change_is_flagged(sample_paths, ingest, match, fill, export, tmp_path):
    dq = _workbook(sample_paths, ingest, match, fill, export, tmp_path)["Data Quality"]
    hits = [r for r in dq.iter_rows(min_row=2, values_only=True) if r[1] == "disposition_carried_os_change"]
    assert hits and all(r[0] == "warning" for r in hits)
    assert any("WKS-0007" in str(r[4]) + str(r[5]) for r in hits)


def test_u8_os_edition_filled_from_name(sample_paths, ingest, match, fill, export, tmp_path):
    report = _workbook(sample_paths, ingest, match, fill, export, tmp_path)["Report"]
    headers = [c.value for c in report[1]]
    editions = {r[0].value.strip().upper(): r[headers.index("OS Edition")].value for r in report.iter_rows(min_row=2)}
    assert editions["WKS-0007"] == "Enterprise"
    assert all(editions.values()), editions


def test_review_rows_neither_give_nor_take_peer_values(sample_paths, ingest, match):
    from lifecycle_copilot import lifecycle

    current, prior = sample_paths
    rows = {(r.serial or "") + "|" + (r.hostname or "").strip().upper(): r
            for r in lifecycle.fill(match(ingest(current), ingest(prior)), peer_asset_dates=True)}
    for key in ("SN-DUP-004|WKS-0004A", "SN-DUP-004|WKS-0004B"):
        r = rows[key]
        assert r.status == "Needs review"
        assert r.basis.get("asset_eos") != "peer"
        assert "needs review first" in r.remarks.lower()


def test_no_evidence_row_is_still_planted():
    """Guards the sample against drift like C11 had (U7)."""
    from lifecycle_copilot.policy import Policy

    key, why = Policy.load().parse("Microsoft Windows 11 Enterprise", "28H2")
    row = Policy.load().lookup(key)[0] if key else None
    assert row is None
