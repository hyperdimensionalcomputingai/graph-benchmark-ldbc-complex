# Graph benchmarks: LDBC SNB SF1 Interactive complex queries

This repository hosts 14 complex read queries (IC1–IC14) adapted from the [LDBC Social Network Benchmark (SNB) Interactive v1 workload](https://github.com/ldbc/ldbc_snb_interactive_v1_impls), using the scale factor 1 (SF1) dataset.

It is maintained by [HDC Labs](https://hyperdimensionalcomputing.ai/) and complements [graph-benchmark-ldbc](https://github.com/hyperdimensionalcomputingai/graph-benchmark-ldbc), which contains a separate, custom 30-query workload. This is **not** an official LDBC benchmark and is not endorsed by GDC/LDBC in any way.

<details>
<summary>Licensing, provenance and benchmark status</summary>

The project adopts [Apache License 2.0](LICENSE) for this derivative and future contributions. Inherited MIT-covered software retains its original grant and [MIT copyright and permission notice](LICENSES/MIT.txt). Package metadata uses `Apache-2.0 AND MIT`; preserve both licences when redistributing the combined software. This does not assign earlier contributors' copyright or imply new Apache patent grants from them.

We credit the Linked Data Benchmark Council (LDBC), now the Graph Data Council (GDC), for the SNB dataset, data model and query definitions. The adapted official Cypher implementations are Apache-2.0 licensed; their [original licence](LICENSES/LDBC-Apache-2.0.txt) and [notice](NOTICE.txt) are retained. Dataset, data-model and image rights remain separate from the software licence. See [third-party provenance and review gaps](THIRD_PARTY_NOTICES.md) and [contribution guidance](CONTRIBUTING.md).

**These are not LDBC Benchmark Results.** This project is unaudited and is not approved or endorsed by LDBC/GDC. It uses adapted queries, one fixed parameter set per query and `pytest-benchmark`, rather than the official driver's workload mix and generated parameters. See the [Fair Use Policy](https://ldbcouncil.org/benchmarks/fair-use-policies/).

</details>

## Setup

Use Python 3.13 or newer and [uv](https://docs.astral.sh/uv/getting-started/installation/):

```sh
uv sync --locked
```

This installs the engine dependencies; no project package needs to be built or installed. Dependencies and resolved versions are recorded in `pyproject.toml` and `uv.lock`.

## Dataset

The downloader uses the SNB Interactive v1 initial SF1 dataset (`CsvBasic`, `StringDateFormatter`) from the [official dataset collection](https://ldbcouncil.org/benchmarks/snb/datasets/). Install `curl`, `tar` and either `zstd` or `unzstd` before downloading:

```sh
uv run download_dataset.py
```

The script extracts data to ignored `csv/` and skips downloading when that directory already exists. It prints a SHA-256 hash but does not check it against an upstream expected digest.

## Ingest the data as a graph

![Graph schema](assets/ldbc-snb-schema.png)

Each engine directory contains its ingestion script, queries and benchmark harness:

| Engine | Instructions | Execution model |
| --- | --- | --- |
| Neo4j | [Setup and ingestion](neo4j/README.md) | Server, with Docker configuration included |
| Kuzu | [Setup and ingestion](kuzu/README.md) | Embedded |
| Ladybug | [Setup and ingestion](ladybugdb/README.md) | Embedded |
| lance-csr | [Setup and ingestion](lance_csr/README.md) | Embedded, over Lance datasets |

The schema uses separate relationship types such as `postHasCreator` and `commentHasCreator`, and `Place` and `Organisation` nodes with a `type` property. Configure Neo4j using `neo4j/.env.example`; local credentials and database files are ignored by Git.

## Queries and correctness

These queries are complex on several counts: they traverse multiple hops, join different node and relationship types, preserve partial results through optional matches, aggregate nested results, and rank the final output. The examples below show how those operations combine in a single query.

### Example: Q1 — friends, universities and employers

Q1 (IC1) finds people named `Jose` within three friendship hops of person `1131`, selects the nearest 20, and enriches their profiles with their city, universities and employers. Here is the full query from the [Neo4j implementation](neo4j/query.py):

```cypher
MATCH (p:Person {ID: $personId}), (friend:Person {firstName: $firstName})
WHERE NOT p = friend
WITH p, friend
MATCH path = shortestPath((p)-[:knows*1..3]-(friend))
WITH min(length(path)) AS distance, friend
ORDER BY distance ASC, friend.lastName ASC, friend.ID ASC
LIMIT 20

MATCH (friend)-[:personIsLocatedIn]->(friendCity:Place)
OPTIONAL MATCH (friend)-[studyAt:studyAt]->(uni:Organisation)-[:organisationIsLocatedIn]->(uniCity:Place)
WITH friend, collect(
    CASE WHEN uni IS NULL THEN null
        ELSE [uni.name, studyAt.classYear, uniCity.name]
    END) AS unis, friendCity, distance

OPTIONAL MATCH (friend)-[workAt:workAt]->(company:Organisation)-[:organisationIsLocatedIn]->(companyCountry:Place)
WITH friend, collect(
    CASE WHEN company IS NULL THEN null
        ELSE [company.name, workAt.workFrom, companyCountry.name]
    END) AS companies, unis, friendCity, distance

RETURN
    friend.ID AS friendId,
    friend.lastName AS friendLastName,
    distance AS distanceFromPerson,
    friend.birthday AS friendBirthday,
    friend.creationDate AS friendCreationDate,
    friend.gender AS friendGender,
    friend.browserUsed AS friendBrowserUsed,
    friend.locationIP AS friendLocationIp,
    friendCity.name AS friendCityName,
    unis AS friendUniversities,
    companies AS friendCompanies
ORDER BY distanceFromPerson ASC, friendLastName ASC, friendId ASC
LIMIT 20
```

The two `OPTIONAL MATCH` clauses keep a person in the result even when they have no matching university or employer. Each education or employment match also traverses to the organization's location. The intervening `WITH` and `collect()` clauses group education records before expanding employment records, avoiding a cross-product of the two lists. Null handling produces empty lists for missing records, while the final sort restores the requested distance, name and ID order.

This query combines bounded shortest-path search, filtering, a top-20 selection, optional multi-hop joins, nested-list aggregation and final ordering.

### Example: Q14 — trusted connection paths

Given two people, Q14 (IC14) finds **every shortest friendship path** between them, then ranks those paths by how much neighbouring people have interacted. In this suite, the endpoints are person `1131` and person `19791209300775`.

The Neo4j query starts by finding paths through `knows` relationships in either direction:

```cypher
MATCH path = allShortestPaths(
    (person1:Person {ID: $person1Id})-[:knows*0..]-(person2:Person {ID: $person2Id})
)
```

For each adjacent pair of people along each path, it counts replies in both directions:

| Interaction between the pair | Contribution to path weight |
| --- | ---: |
| A comment replying to the other person's post | 1.0 |
| A comment replying to the other person's comment | 0.5 |

It sums these contributions across the path and returns the ordered person IDs and total weight, highest weight first. “Shortest” means fewest friendship hops; interaction weights rank those shortest paths afterwards.

This combines variable-length traversal, enumeration of all shortest paths, additional traversals through comments and posts for every friendship step, aggregation and sorting. See `run_query14` in the [Neo4j implementation](neo4j/query.py) for the complete query.

### Query adaptations and checks

Each engine's `query.py` implements IC1–IC14. The module docstrings describe the adaptations from the official Cypher:

- `Message` becomes Post/Comment label or relationship alternatives.
- City/Country and University/Company become Place and Organisation.
- IC1 omits person emails and languages, which ingestion does not load, and uses an explicit null check for missing universities.
- Kuzu and Ladybug use their shortest-path syntax and `EXISTS` subqueries where required.
- lance-csr runs Neo4j's text unchanged, except IC14, which replaces `reduce()` with pattern comprehensions.

Each engine exposes `run_query1` through `run_query14`, with fixed parameters beside the query text. Its benchmark harness calls each query directly and checks the result after timing. Shared golden-answer checks live in [`conftest.py`](conftest.py). Most queries start from person 1131; IC13 and IC14 use person 1131 and person 19791209300775. These are a single fixture, not a representative parameter workload.

[`expected/`](expected/) contains 14 golden-answer JSON files originally generated using Neo4j. Comparisons normalize timestamps and unordered collected values; IC14 rows are compared without row-order dependence. `WRITE_GOLDEN=1` overwrites these fixtures and should only be used when deliberately regenerating them. Agreement with these fixtures is not independent verification of the LDBC specification.

## Benchmark settings

Follow the engine setup instructions, then run the benchmark from that engine directory:

```sh
uv run pytest benchmark_query.py --benchmark-min-rounds=5 --benchmark-disable-gc
```

The optional `./run_benchmarks.sh` runs every engine (lance-csr with its data in memory and read lazily) and overwrites their named output files in `results/`.

The runner uses at least five measured rounds per query, `time.perf_counter`, disabled garbage collection and warmup off. Query result conversion happens within the timed call; golden-answer comparison happens afterwards. The default query timeout is 10 seconds, configurable through `QUERY_TIMEOUT_SECONDS`. Server and embedded deployments have different resource boundaries, so a future comparison needs a documented machine and database configuration.

## Results

[`results/`](results/) contains saved benchmark output, and [`results/compare.py`](results/compare.py) prints a comparison table. Results apply to the engine versions and deployment configurations recorded with each run. Before comparing systems, use a documented machine, database configuration and benchmark protocol.

The latest runs (Apple M5, 24 GB, macOS 26.6.2) give these mean latencies in milliseconds. Neo4j, Kuzu and Ladybug ran on 2026-10-24; lance-csr 0.3.1 was re-run on its own with `./run_benchmarks.sh lance_csr` on 2026-10-27, on battery power, which can throttle the CPU (see [`results/environment.yml`](results/environment.yml)). Each number in brackets is Neo4j's latency divided by that engine's (higher is faster than Neo4j); `n/a` marks a wrong answer or error. Ladybug's IC1 returned a wrong answer and its IC14 ran out of buffer-manager memory.

| Query | neo4j-2026.09.0 (ms) | kuzu-0.11.3 (ms) | ladybug-0.21.2 (ms) | lance-csr-0.3.1-lazy (ms) | lance-csr-0.3.1-memory (ms) |
| --- | ---: | ---: | ---: | ---: | ---: |
| IC1 | 51.4 | 13.5 (3.80x) | n/a | 32.8 (1.57x) | 26.3 (1.95x) |
| IC2 | 44.7 | 25.0 (1.79x) | 15.6 (2.87x) | 26.2 (1.70x) | 2.6 (17.12x) |
| IC3 | 894.9 | 105.2 (8.51x) | 100.2 (8.94x) | 417.8 (2.14x) | 58.7 (15.25x) |
| IC4 | 13.1 | 29.7 (0.44x) | 11.8 (1.10x) | 13.2 (0.99x) | 6.2 (2.10x) |
| IC5 | 1022.6 | 747.7 (1.37x) | 309.0 (3.31x) | 110.0 (9.29x) | 77.1 (13.27x) |
| IC6 | 231.2 | 1114.8 (0.21x) | 234.2 (0.99x) | 26.2 (8.83x) | 23.0 (10.07x) |
| IC7 | 7.1 | 453.7 (0.02x) | 370.6 (0.02x) | 32.7 (0.22x) | 21.0 (0.34x) |
| IC8 | 3.0 | 73.4 (0.04x) | 4.9 (0.61x) | 3.1 (0.97x) | 2.0 (1.48x) |
| IC9 | 802.3 | 131.0 (6.13x) | 62.1 (12.91x) | 819.6 (0.98x) | 38.2 (21.02x) |
| IC10 | 91.7 | 74.9 (1.22x) | 13.7 (6.70x) | 138.4 (0.66x) | 105.0 (0.87x) |
| IC11 | 11.0 | 4.7 (2.34x) | 2.5 (4.40x) | 5.9 (1.86x) | 3.7 (3.01x) |
| IC12 | 133.9 | 92.3 (1.45x) | 133.8 (1.00x) | 28.9 (4.63x) | 19.9 (6.72x) |
| IC13 | 0.9 | 14.2 (0.06x) | 47.5 (0.02x) | 1.5 (0.62x) | 1.1 (0.86x) |
| IC14 | 522.6 | 1871.2 (0.28x) | n/a | 48.6 (10.76x) | 47.7 (10.96x) |
