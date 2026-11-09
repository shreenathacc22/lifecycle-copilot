"""Command line for the demo.

  lifecycle-copilot sample [--out data/sample]
  lifecycle-copilot ingest --current C.xlsx --prior P.xlsx [--ack-provenance]
  lifecycle-copilot match  --current C.xlsx --prior P.xlsx [--ack-provenance]
  lifecycle-copilot run    --current C.xlsx --prior P.xlsx [--out output/] [--policy CSV] [--ack-provenance]
"""
import argparse
import sys
import time
from pathlib import Path

from . import export, ingest, lifecycle, match, sample
from .policy import Policy


def _print_issues(issues, limit=20):
    shown = [i for i in issues if i.severity in ("error", "warning")]
    for i in shown[:limit]:
        where = f" row {i.row_no}" if i.row_no else ""
        print(f"  [{i.severity}] {i.category} ({i.source}{where}) {i.identifier}: {i.detail}")
    if len(shown) > limit:
        print(f"  ... {len(shown) - limit} more on the Data Quality sheet")


def _print_counts(c):
    print(f"current rows {c['current_rows']}: serial {c['serial']}, hostname {c['hostname']}, "
          f"new {c['new']}, needs review {c['review']}")
    print(f"prior rows   {c['prior_rows']}: matched {c['matched']}, dropped {c['dropped']}, "
          f"needs review {c['prior_review']}")


def cmd_sample(args):
    current, prior = sample.make(args.out)
    print(f"wrote {current}\nwrote {prior}")


def cmd_ingest(args):
    current, prior, issues = ingest.load_pair(args.current, args.prior, ack_provenance=args.ack_provenance)
    for sheet in (current, prior):
        extra = f", {sheet.skipped_blank_rows} blank rows skipped" if sheet.skipped_blank_rows else ""
        print(f"{sheet.source}: {sheet.path.name}, {len(sheet.rows)} rows{extra}")
        print(f"  mapped: {', '.join(sheet.columns)}")
        if sheet.unmapped:
            print(f"  kept as extra columns: {', '.join(sheet.unmapped)}")
    _print_issues(issues)


def cmd_match(args):
    current, prior, issues = ingest.load_pair(args.current, args.prior, ack_provenance=args.ack_provenance)
    result = match.run(current.rows, prior.rows)
    _print_counts(result.counts)
    _print_issues(issues + result.dq)


def cmd_run(args):
    started = time.perf_counter()
    current, prior, issues = ingest.load_pair(args.current, args.prior, ack_provenance=args.ack_provenance)
    result = match.run(current.rows, prior.rows)
    policy = Policy.load(args.policy) if args.policy else Policy.load()
    filled = lifecycle.fill(result, policy, ingest_dq=issues, peer_asset_dates=args.peer_asset_dates)
    path = export.write(filled, args.out, current_path=args.current, prior_path=args.prior)
    _print_counts(result.counts)
    f = filled.fill_counts
    source = sum(1 for r in filled if r.basis.get("os_eos") == "source")
    print(f"OS EOS: {source} from source, {f.get('os_eos_policy', 0)} from policy, {f.get('os_eos_carried', 0)} carried, "
          f"{f.get('os_eos_peer', 0)} from peers, {f.get('os_eos_blank', 0)} still blank")
    _print_issues(issues + result.dq + filled.dq)
    print(f"wrote {path} in {time.perf_counter() - started:.2f}s")


def main(argv=None):
    parser = argparse.ArgumentParser(prog="lifecycle-copilot", description="Lifecycle Copilot (synthetic-data build)")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("sample", help="write the synthetic sample workbooks")
    p.add_argument("--out", default="data/sample")
    p.set_defaults(func=cmd_sample)

    for name, func, help_text in (
        ("ingest", cmd_ingest, "read and check both files"),
        ("match", cmd_match, "read, check and match both files"),
        ("run", cmd_run, "full run: match, fill and write the six-sheet workbook"),
    ):
        p = sub.add_parser(name, help=help_text)
        p.add_argument("--current", required=True, type=Path, help="this period's CMDB export (.xlsx)")
        p.add_argument("--prior", required=True, type=Path, help="last period's TLM sheet (.xlsx)")
        p.add_argument("--ack-provenance", action="store_true",
                       help="continue past a positional-copy warning (it stays on the Data Quality sheet)")
        if name == "run":
            p.add_argument("--out", default="output", type=Path, help="folder or .xlsx path")
            p.add_argument("--policy", type=Path, help="policy CSV (default data/policy/windows_os.csv)")
            p.add_argument("--peer-asset-dates", action="store_true",
                           help="fill blank Asset EOL/EOS from same-model peers (off until the ITAM team confirms)")
        p.set_defaults(func=func)

    args = parser.parse_args(argv)
    try:
        args.func(args)
    except ingest.IngestError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
