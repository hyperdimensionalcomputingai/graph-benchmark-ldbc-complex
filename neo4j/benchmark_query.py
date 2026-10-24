from __future__ import annotations

import asyncio
import os

import pytest
from dotenv import load_dotenv
from neo4j import AsyncGraphDatabase, AsyncSession

import query

load_dotenv()

URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.environ.get("NEO4J_USER")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD")
NEO4J_DATABASE = os.environ.get("NEO4J_DATABASE", "neo4j")


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def session(event_loop) -> AsyncSession:
    if NEO4J_USER is None or NEO4J_PASSWORD is None:
        raise EnvironmentError("NEO4J_USER and NEO4J_PASSWORD must be set")
    driver = AsyncGraphDatabase.driver(URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    session = driver.session(database=NEO4J_DATABASE)
    yield session
    event_loop.run_until_complete(session.close())
    event_loop.run_until_complete(driver.close())


def _run(event_loop, coro):
    return event_loop.run_until_complete(coro)


def test_benchmark_query1(benchmark, session, event_loop, check_result):
    result = benchmark(lambda: _run(event_loop, query.run_query1(session)))
    check_result("ic1", result)


def test_benchmark_query2(benchmark, session, event_loop, check_result):
    result = benchmark(lambda: _run(event_loop, query.run_query2(session)))
    check_result("ic2", result)


def test_benchmark_query3(benchmark, session, event_loop, check_result):
    result = benchmark(lambda: _run(event_loop, query.run_query3(session)))
    check_result("ic3", result)


def test_benchmark_query4(benchmark, session, event_loop, check_result):
    result = benchmark(lambda: _run(event_loop, query.run_query4(session)))
    check_result("ic4", result)


def test_benchmark_query5(benchmark, session, event_loop, check_result):
    result = benchmark(lambda: _run(event_loop, query.run_query5(session)))
    check_result("ic5", result)


def test_benchmark_query6(benchmark, session, event_loop, check_result):
    result = benchmark(lambda: _run(event_loop, query.run_query6(session)))
    check_result("ic6", result)


def test_benchmark_query7(benchmark, session, event_loop, check_result):
    result = benchmark(lambda: _run(event_loop, query.run_query7(session)))
    check_result("ic7", result)


def test_benchmark_query8(benchmark, session, event_loop, check_result):
    result = benchmark(lambda: _run(event_loop, query.run_query8(session)))
    check_result("ic8", result)


def test_benchmark_query9(benchmark, session, event_loop, check_result):
    result = benchmark(lambda: _run(event_loop, query.run_query9(session)))
    check_result("ic9", result)


def test_benchmark_query10(benchmark, session, event_loop, check_result):
    result = benchmark(lambda: _run(event_loop, query.run_query10(session)))
    check_result("ic10", result)


def test_benchmark_query11(benchmark, session, event_loop, check_result):
    result = benchmark(lambda: _run(event_loop, query.run_query11(session)))
    check_result("ic11", result)


def test_benchmark_query12(benchmark, session, event_loop, check_result):
    result = benchmark(lambda: _run(event_loop, query.run_query12(session)))
    check_result("ic12", result)


def test_benchmark_query13(benchmark, session, event_loop, check_result):
    result = benchmark(lambda: _run(event_loop, query.run_query13(session)))
    check_result("ic13", result)


def test_benchmark_query14(benchmark, session, event_loop, check_result):
    result = benchmark(lambda: _run(event_loop, query.run_query14(session)))
    check_result("ic14", result)
