"""Writes data/sample/current.xlsx and data/sample/prior.xlsx (synthetic only).

Usage: python scripts/make_sample.py [out_dir]
"""
import sys
from pathlib import Path

from lifecycle_copilot.sample import make

ROOT = Path(__file__).resolve().parents[1]

if __name__ == "__main__":
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "data" / "sample"
    current, prior = make(out)
    print(f"wrote {current}")
    print(f"wrote {prior}")
