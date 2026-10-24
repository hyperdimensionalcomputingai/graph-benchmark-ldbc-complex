# lance-csr

This section describes how to run the LDBC SNB Interactive complex queries on [lance-csr](https://github.com/hyperdimensionalcomputingai/lance-csr), an embedded Cypher engine over [Lance](https://lancedb.github.io/lance/) datasets with a CSR adjacency index. See [results](../README.md#results) for saved benchmark output.

## Setup

lance-csr is embedded: it runs inside the Python process, with no server. The project pins `lance-csr` to `0.2.0`; run `uv sync --frozen` from the repository root to install the benchmark dependencies.

## Build graph

`build_graph.py` reads the CSV files in `../csv` and writes one Lance dataset per node and relationship file to `graph_lance/`, with a BTREE index on each node table's `id`. Empty CSV fields load as null, as in the other engines.

```sh
uv run build_graph.py
```

## Execute queries

`query.py` runs Neo4j's IC1–IC13 Cypher text and parameters from [`../neo4j/query.py`](../neo4j/query.py) unchanged. IC14's official text uses `reduce()`, which is outside openCypher's [standardisation scope](https://github.com/opencypher/openCypher/blob/master/docs/standardisation-scope.adoc), so it is ported with pattern comprehensions; the module docstring describes the port. Run them all once and print the results:

```sh
uv run query.py
```

`LANCE_CSR_MODE` selects how the engine reads the datasets. Both modes use CSR traversal (`use_csr=True`).

| Mode | Inputs |
| --- | --- |
| `memory` (default) | every table loaded into memory as Arrow before the first query |
| `lazy` | Lance datasets read from disk as queries need them |

lance-csr has no query timeout, so `QUERY_TIMEOUT_SECONDS` doesn't apply.

### Run benchmark

From the repository root, `./run_benchmarks.sh` runs every engine, lance-csr in both modes, with the settings in the [root README](../README.md#benchmark-settings) and writes the output to `results/`. To run just this engine:

```sh
LANCE_CSR_MODE=memory uv run --frozen pytest benchmark_query.py --benchmark-min-rounds=5 --benchmark-disable-gc
```

Each test checks its result against the golden answer in `../expected/`. lance-csr returns lowercased column names, so the check compares keys in lowercase.
