#!/usr/bin/env python3
"""
Print a Markdown table of mean latency per query and engine from the pytest-benchmark
outputs in this directory (one `<engine>-<version>.txt` per engine).

A query that failed shows as `timeout` if it hit the query time limit and `n/a` if it
failed any other way (wrong answer, error) or was skipped; its timing isn't reported.
"""

from __future__ import annotations

import re
from pathlib import Path

HEADER_RE = re.compile(r"Name \(time in (?P<unit>[^)]+)\)")
FAILED_RE = re.compile(r"^FAILED \S+::(?P<name>\S+) - (?P<error>\w+)")
UNIT_TO_MS = {"s": 1000.0, "ms": 1.0, "us": 0.001, "µs": 0.001, "ns": 0.000001}
# Column order; unlisted engines go last, alphabetically.
ENGINE_ORDER = ["neo4j", "kuzu", "ladybug"]


def engine_sort_key(path: Path) -> tuple[int, str]:
    stem = path.stem.lower()
    for idx, engine in enumerate(ENGINE_ORDER):
        if stem.startswith(engine):
            return (idx, stem)
    return (len(ENGINE_ORDER), stem)


def parse_benchmark_file(path: Path) -> tuple[dict[str, float], dict[str, str]]:
    "Return mean ms per passing test, and 'timeout' or 'n/a' per failing test."
    lines = path.read_text().splitlines()
    failures = {
        f"ic{query_number(m['name'])}": "timeout" if m["error"] == "TimeoutError" else "n/a"
        for m in map(FAILED_RE.match, lines)
        if m
    }
    unit_scale: float | None = None
    means_ms: dict[str, float] = {}
    for line in lines:
        if unit_scale is None:
            if match := HEADER_RE.search(line):
                unit_scale = UNIT_TO_MS[match["unit"].strip()]
            continue
        if not line.startswith("test_"):
            continue
        columns = re.split(r"\s{2,}", line.strip())
        name = f"ic{query_number(columns[0])}"
        # A failing test can still have timings, if it failed after being measured
        if name not in failures:
            means_ms[name] = float(columns[3].split()[0].replace(",", "")) * unit_scale
    return means_ms, failures


def query_number(name: str) -> int:
    return int(re.search(r"(?:ic|query)(\d+)", name)[1])


def main() -> None:
    results_dir = Path(__file__).resolve().parent
    files = sorted(results_dir.glob("*.txt"), key=engine_sort_key)
    if not files:
        raise SystemExit("No .txt files found in results directory.")

    systems = [path.stem for path in files]
    parsed = {path.stem: parse_benchmark_file(path) for path in files}
    queries = sorted({q for means, failures in parsed.values() for q in [*means, *failures]}, key=query_number)
    neo4j = next((s for s in systems if s.startswith("neo4j")), None)

    print("| Query | " + " | ".join(f"{s} (ms)" for s in systems) + " |")
    print("| --- |" + " ---: |" * len(systems))
    for query in queries:
        neo4j_ms = parsed[neo4j][0].get(query) if neo4j else None
        cells = []
        for system in systems:
            means, failures = parsed[system]
            ms = means.get(query)
            if ms is None:
                cells.append(failures.get(query, "n/a"))
            elif system != neo4j and neo4j_ms:
                cells.append(f"{ms:.1f} ({neo4j_ms / ms:.2f}x)")
            else:
                cells.append(f"{ms:.1f}")
        print(f"| IC{query_number(query)} | " + " | ".join(cells) + " |")


if __name__ == "__main__":
    main()
