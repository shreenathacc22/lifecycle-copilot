"""Dev unit checks for M0, M1, M2, M4 and M6. QA's acceptance checks live in
test_acceptance.py; these cover the edges underneath them."""
from datetime import date

import pytest
from openpyxl import Workbook, load_workbook

from lifecycle_copilot import export, ingest, lifecycle, match, sample
from lifecycle_copilot.ingest import IngestError, ProvenanceError
from lifecycle_copilot.policy import Policy


@pytest.fixture
def sample_dir(tmp_path):
    sample.make(tmp_path)
    return tmp_path


def _run(sample_dir, **kw):
    cur, pri, issues = ingest.load_pair(sample_dir / "current.xlsx", sample_dir / "prior.xlsx")
    return lifecycle.fill(match.run(cur.rows, pri.rows), ingest_dq=issues, **kw)


def _by_serial(run, serial):
    return next(r for r in run if r.serial == serial)


# M0


def test_sample_is_repeatable(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    sample.make(a)
    sample.make(b)
    for name in ("current.xlsx", "prior.xlsx"):
        rows_a = list(load_workbook(a / name).active.iter_rows(values_only=True))
        rows_b = list(load_workbook(b / name).active.iter_rows(values_only=True))
        assert rows_a == rows_b


def test_sample_has_no_real_looking_identifiers(sample_dir):
    for name in ("current.xlsx", "prior.xlsx"):
        for row in ingest.load(sample_dir / name):
            assert row.hostname_norm.startswith("WKS-")
            assert not row.serial_norm or row.serial_norm.startswith("SN-")
            assert row.fqdn is None or row.fqdn.endswith(".example.test")


# M1: provenance (A7)


def test_a7_positional_copy_stops_the_run(tmp_path):
    cur, pri = sample.make_provenance_pair(tmp_path, copied=True)
    with pytest.raises(ProvenanceError) as exc:
        ingest.load_pair(cur, pri)
    assert [i.identifier for i in exc.value.issues] == ["fqdn"]
    assert "--ack-provenance" in str(exc.value)


def test_a7_ack_continues_and_keeps_the_warning(tmp_path):
    cur, pri = sample.make_provenance_pair(tmp_path, copied=True)
    _, _, issues = ingest.load_pair(cur, pri, ack_provenance=True)
    assert any(i.category == "positional_copy" and i.severity == "error" for i in issues)


def test_a7_unchanged_columns_do_not_trip_the_check(tmp_path):
    cur, pri = sample.make_provenance_pair(tmp_path, copied=False)
    _, _, issues = ingest.load_pair(cur, pri)
    assert not [i for i in issues if i.category == "positional_copy"]


def test_a7_same_order_unchanged_file_does_not_trip(tmp_path):
    # Same assets, same order, every value unchanged: aligned by position and by serial.
    hosts = [f"WKS-{n:04d}" for n in range(200, 212)]
    rows = [sample._cur("SAME", h, f"SN-SAME-{h[-3:]}", sample.W11E, "23H2") for h in hosts]
    cur = sample.write_workbook(tmp_path / "c.xlsx", sample.CURRENT_HEADERS, rows)
    pri = sample.write_workbook(tmp_path / "p.xlsx", sample.CURRENT_HEADERS, rows)
    _, _, issues = ingest.load_pair(cur, pri)
    assert not [i for i in issues if i.category == "positional_copy"]


def test_a7_fleet_wide_upgrade_does_not_trip(tmp_path):
    # 20 assets in the same order. Two were on 23H2 last period and moved to
    # 24H2, the rest were already on 24H2. Position and serial agree equally.
    hosts = [f"WKS-{n:04d}" for n in range(300, 320)]
    prior = [sample._cur("UPG", h, f"SN-UPG-{h[-3:]}", sample.W11E, "23H2" if i < 2 else "24H2") for i, h in enumerate(hosts)]
    current = [sample._cur("UPG", h, f"SN-UPG-{h[-3:]}", sample.W11E, "24H2") for h in hosts]
    cur = sample.write_workbook(tmp_path / "c.xlsx", sample.CURRENT_HEADERS, current)
    pri = sample.write_workbook(tmp_path / "p.xlsx", sample.CURRENT_HEADERS, prior)
    _, _, issues = ingest.load_pair(cur, pri)
    assert not [i for i in issues if i.category == "positional_copy"]


def test_a7_too_few_serial_pairs_warns_instead_of_stopping(tmp_path):
    # Positions agree, but no serials pair, so the check can't tell.
    hosts = [f"WKS-{n:04d}" for n in range(400, 410)]
    prior = [sample._cur("FEW", h, f"SN-OLD-{h[-3:]}", sample.W11E, "23H2") for h in hosts]
    current = [sample._cur("FEW", h, f"SN-NEW-{h[-3:]}", sample.W11E, "23H2") for h in hosts]
    cur = sample.write_workbook(tmp_path / "c.xlsx", sample.CURRENT_HEADERS, current)
    pri = sample.write_workbook(tmp_path / "p.xlsx", sample.CURRENT_HEADERS, prior)
    _, _, issues = ingest.load_pair(cur, pri)
    assert not [i for i in issues if i.category == "positional_copy"]
    assert [i for i in issues if i.category == "provenance_not_checkable"]


# M1: bad files


def test_empty_workbook_fails_cleanly(tmp_path):
    path = tmp_path / "empty.xlsx"
    Workbook().save(path)
    with pytest.raises(IngestError, match="empty"):
        ingest.load(path)


def test_csv_renamed_to_xlsx_fails_cleanly(tmp_path):
    path = tmp_path / "fake.xlsx"
    path.write_text("Name,Serial Number\nWKS-1,SN-1\n")
    with pytest.raises(IngestError, match="can't open"):
        ingest.load(path)


def test_wrong_extension_fails_cleanly(tmp_path):
    path = tmp_path / "export.csv"
    path.write_text("Name,Serial Number\n")
    with pytest.raises(IngestError, match="expected an .xlsx"):
        ingest.load(path)


def test_missing_required_column_is_named(tmp_path):
    path = sample.write_workbook(tmp_path / "c.xlsx", ["Name", "Operating System"], [{"Name": "WKS-1", "Operating System": "x"}])
    with pytest.raises(IngestError, match="serial"):
        ingest.load(path)


def test_headers_are_normalised_and_junk_columns_dropped(tmp_path):
    headers = ["Name", "serial  number", "Operating System  EOS", "Unnamed: 26", "Custom Field"]
    rows = [{"Name": "WKS-1", "serial  number": "SN-1", "Operating System  EOS": date(2026, 11, 10),
             "Unnamed: 26": "junk", "Custom Field": "kept"}]
    sheet = ingest.read_sheet(sample.write_workbook(tmp_path / "c.xlsx", headers, rows))
    assert sheet.columns == ["name", "serial", "os_eos"]
    assert sheet.unmapped == ["Custom Field"]
    assert sheet.rows[0].os_eos == date(2026, 11, 10)
    assert sheet.rows[0].extras == {"Custom Field": "kept"}


def test_blank_rows_are_skipped_but_duplicates_kept(tmp_path):
    rows = [{"Name": "WKS-1", "Serial Number": "SN-1"}, {}, {"Name": "WKS-1", "Serial Number": "SN-1"}]
    sheet = ingest.read_sheet(sample.write_workbook(tmp_path / "c.xlsx", ["Name", "Serial Number"], rows))
    assert len(sheet.rows) == 2 and sheet.skipped_blank_rows == 1


def test_unreadable_date_is_kept_as_text_and_flagged(tmp_path):
    rows = [{"Name": "WKS-1", "Serial Number": "SN-1", "OS EOS": "sometime next year"}]
    sheet = ingest.read_sheet(sample.write_workbook(tmp_path / "c.xlsx", ["Name", "Serial Number", "OS EOS"], rows))
    assert sheet.rows[0].os_eos == "sometime next year"
    assert [i.category for i in sheet.issues] == ["date_unparseable"]


# M2


def test_every_current_row_has_exactly_one_edge(sample_dir):
    cur, pri, _ = ingest.load_pair(sample_dir / "current.xlsx", sample_dir / "prior.xlsx")
    result = match.run(cur.rows, pri.rows)
    assert [e.current.row_no for e in result.edges] == [r.row_no for r in cur.rows]
    matched = [id(e.prior) for e in result.edges if e.prior is not None]
    assert len(matched) == len(set(matched)), "a prior row was matched twice"


def test_dropped_reasons_are_specific(sample_dir):
    cur, pri, _ = ingest.load_pair(sample_dir / "current.xlsx", sample_dir / "prior.xlsx")
    reasons = {d.prior.serial_norm: d.reason for d in match.run(cur.rows, pri.rows).dropped}
    assert "replaced hardware" in reasons["SN-OLD-003"]
    assert "not unique" in reasons["SN-H6A-006"]
    assert reasons["SN-GONE-009"] == "not in current export"


# M4


def test_policy_parses_release_build_and_edition():
    p = Policy.load()
    key, _ = p.parse("Microsoft Windows 11 Enterprise", "10.0.22631.4317")
    assert (key.product, key.version, key.edition_group) == ("Windows 11", "23H2", "enterprise_education")
    key, _ = p.parse("Windows 11 Pro for Workstations", "24H2")
    assert p.lookup(key)[0].os_eos == date(2026, 10, 13)
    key, _ = p.parse("Windows 11 Enterprise N", "24H2")
    assert p.lookup(key)[0].os_eos == date(2027, 10, 12)
    key, _ = p.parse("Microsoft Windows 10 Enterprise", "22H2")
    assert p.lookup(key)[0].os_eos == date(2025, 10, 14)


def test_policy_refuses_to_guess():
    p = Policy.load()
    assert p.parse("Windows 11 Enterprise Evaluation", "24H2")[0] is None
    assert p.parse("Windows 11", "24H2")[0] is None
    assert p.parse("Windows 11 Pro", "build 99999")[0] is None
    assert p.parse("Windows 10 Enterprise LTSC", "")[0] is None
    key, _ = p.parse("Windows 10 Enterprise", "21H1")
    assert p.lookup(key)[0] is None


def test_same_version_two_editions_two_dates():
    p = Policy.load()
    pro = p.lookup(p.parse("Windows 11 Pro", "23H2")[0])[0]
    ent = p.lookup(p.parse("Windows 11 Enterprise", "23H2")[0])[0]
    assert pro.os_eos != ent.os_eos


def test_carry_forward_keeps_disposition_and_remarks(sample_dir):
    row = _by_serial(_run(sample_dir), "SN-CLEAN-001")
    assert row.disposition_strategy == "Renew" and row.basis["disposition_strategy"] == "carried"
    assert row.os_eos == date(2026, 11, 10) and row.basis["os_eos"] == "carried"
    assert row.remarks.startswith("Renew before 23H2")


def test_fqdn_carried_only_when_hostname_unchanged(sample_dir):
    row = next(r for r in _run(sample_dir) if r.row.hostname_norm == "WKS-0002")
    assert row.fqdn == "wks-0002.corp.example.test" and row.basis["fqdn"] == "carried"


def test_peer_fill_for_asset_dates_when_switched_on(sample_dir):
    row = _by_serial(_run(sample_dir, peer_asset_dates=True), "SN-NEW-008")  # OptiPlex peers carry 31-Jan-2027
    assert row.asset_eos == date(2027, 1, 31) and row.basis["asset_eos"] == "peer"
    assert "peers" in row.remarks


def test_u1_peer_asset_fill_is_off_by_default(sample_dir):
    for serial in ("SN-NEW-003", "SN-NEW-008"):  # replaced and new hardware
        row = _by_serial(_run(sample_dir), serial)
        assert row.asset_eos is None and row.asset_eol is None
        assert "peer fill for asset dates is off" in row.remarks


def test_u2_review_rows_get_no_peer_values(sample_dir):
    run = _run(sample_dir, peer_asset_dates=True)
    for r in run:
        if r.status == "Needs review":
            assert "peer" not in r.basis.values()
            assert "needs review first" in r.remarks


def test_source_value_mismatch_is_reported_not_changed(sample_dir):
    run = _run(sample_dir)
    assert _by_serial(run, "SN-SRC-010").os_eos == date(2030, 1, 1)
    assert any(i.category == "policy_mismatch" for i in run.dq)


def test_os_eol_is_not_filled_and_explained_once(sample_dir, tmp_path):
    run = _run(sample_dir)
    assert all(r.os_eol is None for r in run)
    logic = [r[1] for r in load_workbook(export.write(run, tmp_path))["Matching Logic"].iter_rows(values_only=True)]
    assert "OS EOL" in logic


def test_u5_remarks_have_no_urls(sample_dir):
    assert not [r.serial for r in _run(sample_dir) if "http" in r.remarks]


def test_u5_policy_sources_listed_once_on_matching_logic(sample_dir, tmp_path):
    rows = list(load_workbook(export.write(_run(sample_dir), tmp_path))["Matching Logic"].iter_rows(values_only=True))
    sources = [r for r in rows if r[2] and "learn.microsoft.com" in str(r[2])]
    assert sources and len(sources) == len({r[0] for r in sources})


def test_u3_policy_mismatch_is_a_warning(sample_dir):
    issues = [i for i in _run(sample_dir).dq if i.category == "policy_mismatch"]
    assert issues and all(i.severity == "warning" for i in issues)


def test_u6_disposition_carried_across_os_change_is_flagged(sample_dir):
    issues = [i for i in _run(sample_dir).dq if i.category == "disposition_carried_os_change"]
    assert [i.identifier for i in issues] == ["WKS-0007"]
    assert issues[0].severity == "warning"


def test_u8_os_edition_filled_from_os_name(sample_dir):
    row = _by_serial(_run(sample_dir), "SN-ED-007")
    assert row.os_edition == "Enterprise" and row.basis["os_edition"] == "parsed"


def test_u7_ltsc_shares_a_build_but_not_a_date():
    p = Policy.load()
    ent = p.lookup(p.parse("Windows 11 Enterprise", "10.0.26100")[0])[0]
    ltsc = p.lookup(p.parse("Windows 11 Enterprise LTSC 2024", "10.0.26100")[0])[0]
    iot = p.lookup(p.parse("Windows 11 IoT Enterprise LTSC 2024", "10.0.26100")[0])[0]
    assert (ent.os_eos, ltsc.os_eos, iot.os_eos) == (date(2027, 10, 12), date(2029, 10, 9), date(2034, 10, 10))
    # LTSC with no year in the name is identified from its build within the LTSC channel.
    key, _ = p.parse("Windows 10 Enterprise LTSC", "10.0.19044.5247")
    assert key.version == "LTSC 2021" and p.lookup(key)[0].os_eos == date(2027, 1, 12)
    key, _ = p.parse("Windows 10 Enterprise LTSC", "1809")
    assert key.version == "LTSC 2019"
    # The GA build of the same number stays on the GA date.
    w10 = p.lookup(p.parse("Windows 10 Enterprise", "10.0.19044")[0])[0]
    assert w10.os_eos == date(2024, 6, 11)


def test_u7_ltsc_extended_date_is_noted(tmp_path):
    rows = [sample._cur("LTSC", "WKS-0901", "SN-LTSC-901", "Microsoft Windows 10 Enterprise LTSC 2019", "10.0.17763")]
    cur = sample.write_workbook(tmp_path / "c.xlsx", sample.CURRENT_HEADERS, rows)
    pri = sample.write_workbook(tmp_path / "p.xlsx", sample.PRIOR_HEADERS, sample.prior_rows())
    c, p, issues = ingest.load_pair(cur, pri)
    row = next(iter(lifecycle.fill(match.run(c.rows, p.rows), ingest_dq=issues)))
    assert row.os_eos == date(2029, 1, 9) and row.os_eol is None
    assert "Mainstream ended 2024-01-09" in row.remarks


# M6


def test_summary_checks_add_up(sample_dir, tmp_path):
    path = export.write(_run(sample_dir), tmp_path / "out.xlsx")
    summary = dict(load_workbook(path)["Summary"].iter_rows(min_row=2, values_only=True))
    assert summary["Check: serial + hostname + new + review = current rows"] == "OK"
    assert summary["Check: matched + dropped + review = prior rows"] == "OK"
    assert summary["Report rows out"] == summary["Current rows in"] == 11
    os_eos = ("OS EOS from source file", "OS EOS from policy", "OS EOS carried forward", "OS EOS from peers", "OS EOS still blank")
    assert sum(summary[k] for k in os_eos) == 11  # U4


def test_u2_report_has_status_with_review_fill(sample_dir, tmp_path):
    ws = load_workbook(export.write(_run(sample_dir), tmp_path))["Report"]
    headers = [c.value for c in ws[1]]
    col = headers.index("Status") + 1
    statuses = {ws.cell(r, 1).value.strip().upper(): ws.cell(r, col) for r in range(2, ws.max_row + 1)}
    assert statuses["WKS-0004A"].value == statuses["WKS-0004B"].value == "Needs review"
    assert statuses["WKS-0004A"].fill.fgColor.rgb.endswith("FBE3B5")
    assert statuses["WKS-0001"].value == "Matched" and statuses["WKS-0008"].value == "New"
    assert statuses["WKS-0001"].fill.fgColor.rgb in (None, "00000000")


def test_dropped_sheet_lists_dropped_and_review_rows(sample_dir, tmp_path):
    path = export.write(_run(sample_dir), tmp_path)
    rows = list(load_workbook(path)["Dropped"].iter_rows(min_row=2, values_only=True))
    statuses = sorted(r[5] for r in rows)
    assert statuses == ["dropped"] * 4 + ["needs review"]


def test_report_keeps_extra_columns(tmp_path):
    headers = sample.CURRENT_HEADERS + ["Cost Center"]
    rows = [dict(sample.current_rows()[0], **{"Cost Center": "CC-1"})]
    cur = sample.write_workbook(tmp_path / "c.xlsx", headers, rows)
    pri = sample.write_workbook(tmp_path / "p.xlsx", sample.PRIOR_HEADERS, sample.prior_rows())
    c, p, issues = ingest.load_pair(cur, pri)
    path = export.write(lifecycle.fill(match.run(c.rows, p.rows), ingest_dq=issues), tmp_path)
    ws = load_workbook(path)["Report"]
    headers_out = [cell.value for cell in ws[1]]
    assert headers_out[-1] == "Cost Center" and ws.cell(2, len(headers_out)).value == "CC-1"


def test_n1_fill_rule_text_follows_the_switch(sample_dir, tmp_path):
    def rule(run, out):
        rows = load_workbook(export.write(run, out))["Matching Logic"].iter_rows(values_only=True)
        return next(r[2] for r in rows if r[1] == "Fill blanks")
    assert "Peer fill is off" in rule(_run(sample_dir), tmp_path / "off.xlsx")
    assert "same-model peers" in rule(_run(sample_dir, peer_asset_dates=True), tmp_path / "on.xlsx")


def test_u3_policy_mismatch_shows_in_report_remarks(sample_dir):
    row = _by_serial(_run(sample_dir), "SN-SRC-010")
    assert "Source OS EOS differs from Microsoft 12-Oct-2027; kept" in row.remarks
