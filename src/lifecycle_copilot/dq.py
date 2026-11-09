"""Data quality register entries. Every exception the run finds ends up here
and ships on the Data Quality sheet (I5)."""
from dataclasses import dataclass


@dataclass(frozen=True)
class DQIssue:
    severity: str  # "error" | "warning" | "info"
    category: str  # e.g. duplicate_serial, hostname_reuse, positional_copy
    source: str  # "current" | "prior" | "both" | "policy"
    row_no: int | None
    identifier: str
    detail: str
