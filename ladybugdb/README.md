# Ladybug

This section describes how to run the LDBC SNB Interactive complex queries on [Ladybug](https://github.com/LadybugDB/ladybug), a fork of Kuzu. See [results](../README.md#results) for saved benchmark output.

## Setup

Because Ladybug is an embedded graph database, the database is tightly coupled with the application layer -- there is no server to set up and run. The project pins Ladybug to `0.21.2`; run `uv sync --frozen` from the repository root to install the benchmark dependencies.

## Build graph

The script `build_graph.py` contains the necessary methods to connect to the Ladybug DB and ingest the data from the CSV files, in batches for large amounts of data.

```sh
uv run build_graph.py
```

## Visualize graph

The provided `docker-compose.yml` allows you to run [Ladybug Explorer](https://github.com/ladybugdb/explorer), an open source visualization
tool for Ladybug. To run Ladybug Explorer, install Docker and run the following command:

```sh
docker compose up
```

This allows you to access to visualize the graph on the browser at `http://localhost:8000`.

## Execute queries

`query.py` holds the LDBC SNB Interactive complex queries IC1–IC14 adapted to this engine (the query text is identical to `kuzu/query.py`). The module docstring lists every way the queries differ from the [official Cypher](https://github.com/ldbc/ldbc_snb_interactive_v1_impls/tree/main/cypher/queries). Run them all once and print the results:

```sh
uv run query.py
```

### Run benchmark

From the repository root, `./run_benchmarks.sh` runs every engine with the settings in the [root README](../README.md#benchmark-settings) and writes the output to `results/`. To run just this engine:

```sh
uv run --frozen pytest benchmark_query.py --benchmark-min-rounds=5 --benchmark-disable-gc
```

Each test checks its result against the golden answer in `../expected/`.
