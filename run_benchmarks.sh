#!/usr/bin/env bash
# Run the IC1-IC14 benchmark for each engine and save pytest-benchmark's output to results/.
# Neo4j must be running (see neo4j/README.md); the embedded engines need build_graph.py first.
set -u
cd "$(dirname "$0")"
FLAGS=(
  --benchmark-min-rounds=5
  --benchmark-min-time=0.000005
  --benchmark-max-time=1.0
  --benchmark-timer=time.perf_counter
  --benchmark-calibration-precision=10
  --benchmark-warmup=off
  --benchmark-warmup-iterations=5
  --benchmark-disable-gc
  --benchmark-sort=fullname
)
for pair in "kuzu kuzu-0.11.3" "ladybugdb ladybug-0.21.2" "neo4j neo4j-2026.09.0"; do
  read -r dir name <<< "$pair"
  (cd "$dir" && uv run --frozen pytest benchmark_query.py -p no:faulthandler "${FLAGS[@]}" > "../results/$name.txt" 2>&1)
  echo "$name: $(tail -1 "results/$name.txt")"
done
