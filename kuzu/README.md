# Kuzu

This section describes how to run the LDBC SNB Interactive complex queries on Kuzu, using its [Python API](https://github.com/kuzudb/kuzu). See [results](../README.md#results) for saved benchmark output.

## Setup

Because Kuzu is an embedded graph database, the database is tightly coupled with the application layer -- there is no server to set up and run. Simply install the Kuzu Python library (`uv add kuzu`) and you're good to go!

> [!NOTE]
> The Kuzu project has officially been archived, and it's now succeeded by a fork, [Ladybug](https://github.com/LadybugDB/ladybug).

## Build graph

The script `build_graph.py` contains the necessary methods to connect to the Kuzu and ingest the data from the CSV files, in batches for large amounts of data.

```sh
uv run build_graph.py
```

## Visualize graph

The provided `docker-compose.yml` allows you to run [Kuzu Explorer](https://github.com/kuzudb/explorer), an open source visualization
tool for Kuzu. To run Kuzu Explorer, install Docker and run the following command:

```sh
docker compose up
```

This allows you to access to visualize the graph on the browser at `http://localhost:8000`.

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
