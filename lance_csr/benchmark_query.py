from __future__ import annotations

import pytest

import query


@pytest.fixture(scope="session")
def engine():
    return query.engine()


# lance-csr returns lowercased column names, hence lowercase_keys
def test_benchmark_query1(benchmark, engine, check_result):
    result = benchmark(query.run_query1, engine)
    check_result("ic1", result, lowercase_keys=True)


def test_benchmark_query2(benchmark, engine, check_result):
    result = benchmark(query.run_query2, engine)
    check_result("ic2", result, lowercase_keys=True)


def test_benchmark_query3(benchmark, engine, check_result):
    result = benchmark(query.run_query3, engine)
    check_result("ic3", result, lowercase_keys=True)


def test_benchmark_query4(benchmark, engine, check_result):
    result = benchmark(query.run_query4, engine)
    check_result("ic4", result, lowercase_keys=True)


def test_benchmark_query5(benchmark, engine, check_result):
    result = benchmark(query.run_query5, engine)
    check_result("ic5", result, lowercase_keys=True)


def test_benchmark_query6(benchmark, engine, check_result):
    result = benchmark(query.run_query6, engine)
    check_result("ic6", result, lowercase_keys=True)


def test_benchmark_query7(benchmark, engine, check_result):
    result = benchmark(query.run_query7, engine)
    check_result("ic7", result, lowercase_keys=True)


def test_benchmark_query8(benchmark, engine, check_result):
    result = benchmark(query.run_query8, engine)
    check_result("ic8", result, lowercase_keys=True)


def test_benchmark_query9(benchmark, engine, check_result):
    result = benchmark(query.run_query9, engine)
    check_result("ic9", result, lowercase_keys=True)


def test_benchmark_query10(benchmark, engine, check_result):
    result = benchmark(query.run_query10, engine)
    check_result("ic10", result, lowercase_keys=True)


def test_benchmark_query11(benchmark, engine, check_result):
    result = benchmark(query.run_query11, engine)
    check_result("ic11", result, lowercase_keys=True)


def test_benchmark_query12(benchmark, engine, check_result):
    result = benchmark(query.run_query12, engine)
    check_result("ic12", result, lowercase_keys=True)


def test_benchmark_query13(benchmark, engine, check_result):
    result = benchmark(query.run_query13, engine)
    check_result("ic13", result, lowercase_keys=True)


def test_benchmark_query14(benchmark, engine, check_result):
    result = benchmark(query.run_query14, engine)
    check_result("ic14", result, lowercase_keys=True)
