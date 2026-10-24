"""Check shared comparisons and compatibility with saved benchmark output."""

import importlib.util
import json
from pathlib import Path

import pytest


def test_golden_checks_all_fixtures(check_result, monkeypatch):
    monkeypatch.delenv("WRITE_GOLDEN", raising=False)
    for path in (Path(__file__).parents[1] / "expected").glob("ic*.json"):
        rows = json.loads(path.read_text())
        check_result(path.stem, rows)
        with pytest.raises(AssertionError):
            check_result(path.stem, rows + [{"unexpected": True}])


def test_golden_preserves_paths_and_ignores_ic14_row_order(check_result, monkeypatch):
    monkeypatch.delenv("WRITE_GOLDEN", raising=False)
    rows = json.loads((Path(__file__).parents[1] / "expected/ic14.json").read_text())
    check_result("ic14", rows[::-1])
    rows[0]["personIdsInPath"].reverse()
    with pytest.raises(AssertionError):
        check_result("ic14", rows)


@pytest.mark.parametrize("name", ["test_benchmark[ic1]", "test_benchmark_query1"])
def test_result_parser_accepts_both_harnesses(tmp_path, name):
    spec = importlib.util.spec_from_file_location(
        "compare", Path(__file__).parents[1] / "results/compare.py"
    )
    compare = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(compare)
    path = tmp_path / "result.txt"
    path.write_text(f"Name (time in ms)\n{name}  1.0  3.0  2.0\n")
    assert compare.parse_benchmark_file(path) == ({"ic1": 2.0}, {})
    path.write_text(path.read_text() + f"FAILED benchmark_query.py::{name} - TimeoutError\n")
    assert compare.parse_benchmark_file(path) == ({}, {"ic1": "timeout"})
