"""Shared golden-answer checks for the engine benchmark tests."""

import json
import os
import re
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import pytest

EXPECTED_DIR = Path(__file__).parent / "expected"

_TIMESTAMP = re.compile(r"^\d{4}-\d\d-\d\dT")


def _canon(value: Any) -> Any:
    if isinstance(value, str) and _TIMESTAMP.match(value):
        value = datetime.fromisoformat(value)
    if isinstance(value, datetime):
        # Naive timestamps from the embedded engines are already UTC
        if value.tzinfo is not None:
            value = value.astimezone(timezone.utc).replace(tzinfo=None)
        return value.isoformat(timespec="milliseconds")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, list):
        # Lists of tuples like [uni.name, classYear, city] and of names come from collect(),
        # whose order is unspecified; lists of IDs are paths, whose order matters
        if value and all(isinstance(v, (list, tuple)) for v in value):
            return sorted([str(_canon(x)) for x in v] for v in value)
        if value and all(isinstance(v, str) for v in value):
            return sorted(value)
        return [_canon(v) for v in value]
    return value


def canonical_rows(result: Any) -> list[dict[str, Any]]:
    rows = result.to_dicts() if hasattr(result, "to_dicts") else result
    return [{k: _canon(v) for k, v in row.items()} for row in rows]


# IC14 orders only by path weight, so paths with equal weight can come back in any order
UNORDERED = {"ic14"}


def assert_golden(name: str, result: Any, *, lowercase_keys: bool = False) -> None:
    rows = canonical_rows(result)
    path = EXPECTED_DIR / f"{name}.json"
    if os.environ.get("WRITE_GOLDEN") == "1":
        path.write_text(json.dumps(rows, indent=2) + "\n")
    expected = json.loads(path.read_text())
    if lowercase_keys:
        expected = [{k.lower(): v for k, v in row.items()} for row in expected]
    if name in UNORDERED:
        rows, expected = (sorted(r, key=lambda row: json.dumps(row, sort_keys=True)) for r in (rows, expected))
    assert len(rows) == len(expected), f"{name}: {len(rows)} rows, expected {len(expected)}"
    for i, (row, want) in enumerate(zip(rows, expected)):
        assert row == want, f"{name} row {i}: {row} != {want}"


@pytest.fixture
def check_result():
    "Provide the same golden-answer check to each engine harness."
    return assert_golden
