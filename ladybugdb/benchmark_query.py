from __future__ import annotations

from pathlib import Path

import ladybug as lb
import pytest

import query

DB_PATH = Path(__file__).with_name("ldbc_snb_sf1.lbdb")


@pytest.fixture(scope="session")
def connection():
    db = lb.Database(str(DB_PATH))
    conn = lb.Connection(db)
    conn.execute("ANALYZE")
    conn.set_query_timeout(int(query.QUERY_TIMEOUT_SECONDS * 1000))
    yield conn


def test_benchmark_query1(benchmark, connection, check_result):
    result = benchmark(query.run_query1, connection)
    check_result("ic1", result)


def test_benchmark_query2(benchmark, connection, check_result):
    result = benchmark(query.run_query2, connection)
    check_result("ic2", result)


def test_benchmark_query3(benchmark, connection, check_result):
    result = benchmark(query.run_query3, connection)
    check_result("ic3", result)


def test_benchmark_query4(benchmark, connection, check_result):
    result = benchmark(query.run_query4, connection)
    check_result("ic4", result)


def test_benchmark_query5(benchmark, connection, check_result):
    result = benchmark(query.run_query5, connection)
    check_result("ic5", result)


def test_benchmark_query6(benchmark, connection, check_result):
    result = benchmark(query.run_query6, connection)
    check_result("ic6", result)


def test_benchmark_query7(benchmark, connection, check_result):
    result = benchmark(query.run_query7, connection)
    check_result("ic7", result)


def test_benchmark_query8(benchmark, connection, check_result):
    result = benchmark(query.run_query8, connection)
    check_result("ic8", result)


def test_benchmark_query9(benchmark, connection, check_result):
    result = benchmark(query.run_query9, connection)
    check_result("ic9", result)


def test_benchmark_query10(benchmark, connection, check_result):
    result = benchmark(query.run_query10, connection)
    check_result("ic10", result)


def test_benchmark_query11(benchmark, connection, check_result):
    result = benchmark(query.run_query11, connection)
    check_result("ic11", result)


def test_benchmark_query12(benchmark, connection, check_result):
    result = benchmark(query.run_query12, connection)
    check_result("ic12", result)


def test_benchmark_query13(benchmark, connection, check_result):
    result = benchmark(query.run_query13, connection)
    check_result("ic13", result)


def test_benchmark_query14(benchmark, connection, check_result):
    result = benchmark(query.run_query14, connection)
    check_result("ic14", result)
