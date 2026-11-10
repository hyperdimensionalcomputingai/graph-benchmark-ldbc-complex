# lance-csr

This section describes how to run the LDBC SNB Interactive complex queries on [lance-csr](https://github.com/hyperdimensionalcomputingai/lance-csr), an embedded Cypher engine over [Lance](https://lancedb.github.io/lance/) datasets with a CSR adjacency index. See [results](../README.md#results) for saved benchmark output.

## Setup

lance-csr is embedded: it runs inside the Python process, with no server. The project pins `lance-csr` to `0.9.1`; run `uv sync --frozen` from the repository root to install the benchmark dependencies.

## Build graph

`build_graph.py` reads the CSV files in `../csv` and writes one Lance dataset per node and relationship file to `graph_lance/`, with a BTREE index on each node table's `id`. Empty CSV fields load as null, as in the other engines.

```sh
uv run build_graph.py
```

## Execute queries

`query.py` runs Neo4j's IC1–IC14 Cypher text and parameters from [`../neo4j/query.py`](../neo4j/query.py) unchanged. Run them all once and print the results:

```sh
uv run query.py
```

`LANCE_CSR_MODE` selects how the engine reads the datasets. Both modes use CSR traversal (`use_csr=True`).

| Mode | Inputs |
| --- | --- |
| `memory` (default) | every table loaded into memory as Arrow before the first query |
| `lazy` | Lance datasets read from disk as queries need them |

### Alternative IC14 syntax

The benchmark runs IC14's official text, which weighs each path step with `reduce()` over pattern comprehensions. The query below returns the same rows (it passes the same golden-answer check) and ran about 6x faster on lance-csr 0.9.1 with data in memory (about 51 ms against 315 ms). It looks up each pair of adjacent people on the path, counts replies in each direction with `size()` of a pattern comprehension, and sums the step weights per path. It isn't used in the saved results, which keep every engine on the official text where it can run.

```cypher
MATCH path = allShortestPaths((person1:Person {ID: $person1Id})-[:knows*0..]-(person2:Person {ID: $person2Id}))
UNWIND range(0, length(path) - 1) AS i
WITH path, nodes(path)[i] AS aId, nodes(path)[i + 1] AS bId
MATCH (a:Person {ID: aId}), (b:Person {ID: bId})
WITH path,
     size([(a)<-[:commentHasCreator]-(:Comment)-[:replyOfPost]->(:Post)-[:postHasCreator]->(b) | 1])
   + size([(b)<-[:commentHasCreator]-(:Comment)-[:replyOfPost]->(:Post)-[:postHasCreator]->(a) | 1]) AS postReplies,
     size([(a)<-[:commentHasCreator]-(:Comment)-[:replyOfComment]->(:Comment)-[:commentHasCreator]->(b) | 1])
   + size([(b)<-[:commentHasCreator]-(:Comment)-[:replyOfComment]->(:Comment)-[:commentHasCreator]->(a) | 1]) AS commentReplies
RETURN [n IN nodes(path) | n.ID] AS personIdsInPath,
       sum(postReplies * 1.0 + commentReplies * 0.5) AS pathWeight
ORDER BY pathWeight DESC
```

The runner doesn't pass lance-csr's `timeout` argument, so `QUERY_TIMEOUT_SECONDS` doesn't apply and queries run without a limit.

### Run benchmark

From the repository root, `./run_benchmarks.sh` runs every engine, lance-csr in both modes, with the settings in the [root README](../README.md#benchmark-settings) and writes the output to `results/`. To run just this engine:

```sh
LANCE_CSR_MODE=memory uv run --frozen pytest benchmark_query.py --benchmark-min-rounds=5 --benchmark-disable-gc
```

Each test checks its result against the golden answer in `../expected/`. lance-csr returns lowercased column names, so the check compares keys in lowercase.
