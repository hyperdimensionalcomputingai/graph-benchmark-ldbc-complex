# Neo4j

This section describes how to run the LDBC SNB Interactive complex queries on Neo4j. Neo4j's results are the golden answers the other engines are checked against. See [results](../README.md#results) for saved benchmark output.

## Setup

Neo4j runs as a server, so you need a running instance (for example via Docker)
reachable at `bolt://localhost:7687`. Configure credentials via environment
variables:

- `NEO4J_URI` (optional, defaults to `bolt://localhost:7687`)
- `NEO4J_USER`
- `NEO4J_PASSWORD`
- `NEO4J_DATABASE` (optional, defaults to `neo4j`)
- `QUERY_TIMEOUT_SECONDS` (optional, defaults to `10`)

## Build graph

The script `build_graph.py` contains the necessary methods to connect to the Neo4j DB and ingest the data from the CSV files, in batches for large amounts of data.

```sh
uv run build_graph.py
```

## Visualize graph

You can visualize the graph in the Neo4j browser by a) downloading the Neo4j Desktop tool, or b) in the browser via `http://localhost:7474`.

## Execute queries

`query.py` holds the LDBC SNB Interactive complex queries IC1–IC14 adapted to this engine. The module docstring lists every way the queries differ from the [official Cypher](https://github.com/ldbc/ldbc_snb_interactive_v1_impls/tree/main/cypher/queries). Run them all once and print the results:

```sh
uv run query.py
```

### Run benchmark

From the repository root, `./run_benchmarks.sh` runs every engine with the settings in the [root README](../README.md#benchmark-settings) and writes the output to `results/`. To run just this engine:

```sh
uv run --frozen pytest benchmark_query.py --benchmark-min-rounds=5 --benchmark-disable-gc
```

Each test checks its result against the golden answer in `../expected/`.
