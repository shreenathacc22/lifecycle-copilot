"""Adapter between the acceptance tests and dev's package.

The tests only call the functions below. When dev's API settles, change this
file and nothing else. Until a milestone's code exists, its tests skip with
the milestone named, so `pytest` stays green on an empty package.
"""
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "data" / "sample"


def _need(module: str, milestone: str):
    try:
        return __import__(f"lifecycle_copilot.{module}", fromlist=["*"])
    except ImportError:
        pytest.skip(f"{milestone} not built yet (lifecycle_copilot.{module})")


@pytest.fixture
def sample_paths():
    current, prior = SAMPLE / "current.xlsx", SAMPLE / "prior.xlsx"
    if not current.exists() or not prior.exists():
        pytest.skip("M0 sample not generated yet (scripts/make_sample.py)")
    return current, prior


@pytest.fixture
def ingest():
    """Returns load(path) -> list of rows. Each row exposes .serial and .hostname."""
    mod = _need("ingest", "M1")
    return mod.load


@pytest.fixture
def match():
    """Returns run(current_rows, prior_rows) -> result with .edges, .counts, .dq."""
    mod = _need("match", "M2")
    return mod.run


@pytest.fixture
def fill():
    """Returns fill(match_result, policy) -> rows with lifecycle values and remarks."""
    mod = _need("lifecycle", "M4")
    return mod.fill


@pytest.fixture
def export():
    """Returns write(result, out_dir) -> path to the six-sheet workbook."""
    mod = _need("export", "M6")
    return mod.write
