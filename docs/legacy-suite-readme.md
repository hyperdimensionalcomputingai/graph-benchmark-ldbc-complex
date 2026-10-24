> Historical snapshot from `ldbc-suite-test`, imported on 2026-10-24. Its MIT-only licensing and compliance statements describe the source document, not the current distribution; see the [current README](../README.md) and [notices](../THIRD_PARTY_NOTICES.md). Timings and correctness claims have not been reverified.

# Graph benchmarks: LDBC SNB Interactive complex queries on SF1

This repo runs the 14 complex read queries (IC1–IC14) of the [LDBC Social Network Benchmark](https://ldbcouncil.org/benchmarks/snb/) (SNB) Interactive workload on graph systems, using the scale factor 1 (SF1) dataset. Queries are timed with [pytest-benchmark](https://pytest-benchmark.readthedocs.io/) rather than the official LDBC driver, and each result is checked against a golden answer. It's a companion to [graph-benchmark-ldbc](https://github.com/prrao87/graph-benchmark-ldbc), which runs a custom 30-query suite on the same dataset. This project complies with [LDBC's fair use policies](https://ldbcouncil.org/benchmarks/fair-use-policies/).

LDBC's policy calls for attribution in accordance with the [Creative Commons Attribution 4.0 International (CC BY 4.0) license](https://creativecommons.org/licenses/by/4.0/). We credit LDBC/GDC for the SNB dataset, data model and query definitions used here. This repository's original code is licensed under [MIT](../LICENSE). LDBC materials retain their applicable upstream licenses and are not relicensed under MIT.

> [!NOTE]
> The queries are adapted from the [official Cypher implementations](https://github.com/ldbc/ldbc_snb_interactive_v1_impls/tree/main/cypher/queries), but this is not an audited LDBC benchmark run. Each query runs with one fixed parameter set instead of the official driver's generated parameters and workload mix, and the results reported here are not "official" LDBC Benchmark Results.

The following systems are compared:
- Neo4j
- Kuzu (now archived)
- Ladybug

## Setup

We use [uv](https://docs.astral.sh/uv/getting-started/installation/) to manage the dependencies.

```sh
uv sync
```

This also installs `ldbc_ic`, the small shared module that holds the query parameters and the golden-answer check.

## Dataset

Download the LDBC SNB SF1 dataset (`CsvBasic`, `StringDateFormatter`) into `csv/`:

```bash
uv run download_dataset.py
```

The schema is shown below: 8 node types and 23 relationship types, with 3.18M nodes and 17.3M relationships in SF1.

![](../assets/ldbc-snb-schema.png)

## Ingest the data as a graph

Each engine directory has a `build_graph.py` that loads the CSVs; see the engine READMEs ([Neo4j](../neo4j/README.md), [Kuzu](../kuzu/README.md), [Ladybug](../ladybugdb/README.md)). The graph schema is the same as in graph-benchmark-ldbc: one relationship type per source/destination pair (for example `postHasCreator` and `commentHasCreator`), and `Place` and `Organisation` nodes with a `type` property.

## Queries

Each `query.py` holds IC1–IC14 for its engine. The official Cypher is written for a different schema, so every engine needs some translation:
- `Message` (Post or Comment) becomes a label or relationship-type alternation, for example `<-[:postHasCreator|commentHasCreator]-`.
- `City`, `Country`, `University` and `Company` become `Place` and `Organisation` nodes.
- Person emails and languages aren't loaded, so IC1 omits them.
- Kuzu and Ladybug need further changes, such as `* SHORTEST` / `* ALL SHORTEST` instead of `shortestPath()`, and `EXISTS` subqueries instead of pattern predicates.

Each `query.py` docstring lists its changes. The Kuzu and Ladybug query text is identical.

One change fixes a bug in the official query rather than translating it. IC1's `CASE uni.name WHEN null` never matches, because `null = null` is null, so a friend with no university comes back as `[[null, null, null]]`. Here it tests `uni IS NULL`, which gives the empty list the specification intends.

### Parameters

The person IDs in the official example parameters don't exist in this SF1 dataset, so person 1131 is the starting person for every query. Person 1131 has 30 `knows` edges (the median is 21). The other values come from the official examples, except IC3's countries, which give no rows for person 1131. All parameters are in the former `ldbc_ic` module.

| Query | Parameters |
| --- | --- |
| IC1 | person 1131, firstName `Jose` |
| IC2 | person 1131, maxDate 2010-10-16 12:00 UTC |
| IC3 | person 1131, `Panama` and `South_Africa`, 2010-06-01 12:00 to 2010-06-29 12:00 UTC |
| IC4 | person 1131, 2010-06-01 to 2010-06-30 UTC |
| IC5 | person 1131, minDate 2010-11-01 12:00 UTC |
| IC6 | person 1131, tag `Carl_Gustaf_Emil_Mannerheim` |
| IC7, IC8 | person 1131 |
| IC9 | person 1131, maxDate 2010-11-16 12:00 UTC |
| IC10 | person 1131, month 5 |
| IC11 | person 1131, `Hungary`, workFromYear 2011 |
| IC12 | person 1131, tag class `Monarch` |
| IC13, IC14 | person 1131 and person 19791209300775 (4 hops apart, 58 shortest paths) |

### Golden answers

`expected/ic*.json` holds each query's expected result, written from Neo4j with `WRITE_GOLDEN=1`. Each benchmark test compares its result against it after normalising engine-specific types: timestamps become UTC ISO strings, and lists built by `collect()` are sorted. IC14 orders only by path weight, so its rows are compared in any order. Kuzu matches all 14 golden answers. IC1, IC9 and IC13, and IC3's row count, were also checked against independent computations over the raw CSVs.

## High-level results

All three engines were measured on **2026-10-22** on the same machine, one after another:

| | |
| --- | --- |
| Machine | Apple M5 MacBook Pro (`Mac17,2`), 10 CPU cores (4 performance + 6 efficiency), 24 GiB unified memory |
| OS | macOS 26.6.2 (25G83) |
| Python | 3.13.14, pytest 9.1.1, pytest-benchmark 5.3.0 |
| Embedded engines | Run natively in-process |
| Neo4j | Docker Desktop (engine 29.9.2), native arm64 Linux VM with 10 CPUs and 19.3 GiB RAM, using the heap/page-cache settings in `neo4j/docker-compose.yml` |

Engine versions:

- **Neo4j 2026.09.0** Community Edition. The database is the one built by graph-benchmark-ldbc's `neo4j/build_graph.py`, which is the same script as here. Dates are stored as the CSV's ISO strings.
- **Kuzu 0.11.3**
- **Ladybug 0.21.2**, with `ANALYZE` run at connection time and the six ART secondary indexes from `build_graph.py`

Kuzu and Ladybug were rebuilt from the CSVs before timing. Neo4j and Kuzu passed all 14 golden-answer checks, and Ladybug passed 12, all with at least five measured rounds per query. These runs compare the stated deployment configurations: Neo4j runs as a server inside a VM, while Kuzu and Ladybug run embedded. Resource limits are not equal, and caches are not controlled cold.

### Benchmark settings

`./run_benchmarks.sh` runs every engine with these settings and writes the output to `results/`. To run one engine, use this command from its directory:

```sh
uv run --frozen pytest benchmark_query.py \
  --benchmark-min-rounds=5 \
  --benchmark-min-time=0.000005 \
  --benchmark-max-time=1.0 \
  --benchmark-timer=time.perf_counter \
  --benchmark-calibration-precision=10 \
  --benchmark-warmup=off \
  --benchmark-warmup-iterations=5 \
  --benchmark-disable-gc \
  --benchmark-sort=fullname
```

Five rounds is a minimum, not an exact count. Converting the query result (to a list of dicts or a Polars DataFrame) happens inside the timed function. The golden-answer check runs after timing.

Every query has a 10-second timeout; set `QUERY_TIMEOUT_SECONDS` to change it. A query that takes longer fails with `TimeoutError` instead of being timed. Neo4j applies the limit as a transaction timeout, and Kuzu and Ladybug use `Connection.set_query_timeout`.

### Mean query latency

Times are in milliseconds, from `uv run results/compare.py`. The ratio in parentheses is Neo4j mean / engine mean, so a value above 1 means the engine was faster than this Neo4j setup. `n/a` means the query failed and wasn't timed.

| Query | neo4j-2026.09.0 (ms) | kuzu-0.11.3 (ms) | ladybug-0.21.2 (ms) |
| --- | ---: | ---: | ---: |
| IC1 | 20.5 | 11.4 (1.80x) | n/a |
| IC2 | 56.6 | 21.0 (2.70x) | 17.3 (3.27x) |
| IC3 | 924.8 | 91.9 (10.07x) | 97.5 (9.49x) |
| IC4 | 12.9 | 28.9 (0.45x) | 10.7 (1.20x) |
| IC5 | 1142.6 | 679.5 (1.68x) | 274.2 (4.17x) |
| IC6 | 199.7 | 1020.5 (0.20x) | 235.3 (0.85x) |
| IC7 | 3.5 | 433.3 (0.01x) | 318.3 (0.01x) |
| IC8 | 2.3 | 69.3 (0.03x) | 4.4 (0.52x) |
| IC9 | 725.1 | 120.1 (6.04x) | 57.0 (12.71x) |
| IC10 | 96.7 | 71.5 (1.35x) | 12.6 (7.66x) |
| IC11 | 9.6 | 4.6 (2.11x) | 2.4 (4.00x) |
| IC12 | 110.1 | 90.4 (1.22x) | 122.9 (0.90x) |
| IC13 | 0.9 | 14.2 (0.06x) | 44.1 (0.02x) |
| IC14 | 518.8 | 1885.8 (0.28x) | n/a |

The full pytest-benchmark output for each engine is in [`results/`](../results/).

Ladybug's two `n/a` results:
- **IC1** returns a wrong row. When a node is matched with an inline property map such as `(f:Person {firstName: ...})`, an `OPTIONAL MATCH` from it that finds nothing turns all of `f`'s properties into NULL. Writing the filter as `WHERE f.firstName = ...` avoids it. The query is left as it is, so the bug stays visible. Kuzu 0.11.3, with the same query, is not affected.
- **IC14** fails with `Buffer manager exception: Unable to allocate memory! The buffer pool is full`. Run on its own without the time limit, it grows to 11.5 GB of resident memory before failing after about 18 s. Kuzu runs the same query text in 1.9 s.
