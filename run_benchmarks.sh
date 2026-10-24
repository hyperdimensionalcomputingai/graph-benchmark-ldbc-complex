#!/usr/bin/env bash
# Run the IC1-IC14 benchmark for each engine and save pytest-benchmark's output to results/.
# Neo4j must be running (see neo4j/README.md); the embedded engines need build_graph.py first.
# lance-csr runs twice, with its Lance datasets in memory and read lazily from disk.
set -u
cd "$(dirname "$0")"
# The machine and date the results were measured on, for anyone quoting them.
{
  echo "date: $(date -u +%F)"
  echo "machine: $(sysctl -n machdep.cpu.brand_string 2>/dev/null || uname -m), $(( $(sysctl -n hw.memsize 2>/dev/null || echo 0) / 1073741824 )) GB"
  echo "os: $(sw_vers -productName 2>/dev/null || uname -s) $(sw_vers -productVersion 2>/dev/null || uname -r)"
} > results/environment.yml
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
for run in "kuzu kuzu-0.11.3" "ladybugdb ladybug-0.21.2" "neo4j neo4j-2026.09.0" \
  "lance_csr lance-csr-0.2.0-memory memory" "lance_csr lance-csr-0.2.0-lazy lazy"; do
  read -r dir name mode <<< "$run"
  (cd "$dir" && LANCE_CSR_MODE="${mode:-}" uv run --frozen pytest benchmark_query.py -p no:faulthandler "${FLAGS[@]}" > "../results/$name.txt" 2>&1)
  echo "$name: $(tail -1 "results/$name.txt")"
done
