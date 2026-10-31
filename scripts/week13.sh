#!/usr/bin/env bash
# Week 13 on real data, every step in order, unattended:
#   bash scripts/week13.sh 2>&1 | tee week13.log
# Re-run the same command to resume: a step whose artifact already exists is skipped.
# Before the first run: record your review (pass 2) in docs/protocol/attribution_mapping.md.
set -euo pipefail
cd "$(dirname "$0")/.."
ART="$(uv run python -c 'from finmesh.paths import artifacts_dir; print(artifacts_dir())' 2>/dev/null)"
PQ="$(uv run python -c 'from finmesh.paths import data_root; print(data_root())' 2>/dev/null)/parquet"

step() {  # step <artifact> <command...>
  local artifact="$1"; shift
  if [ -f "$artifact" ]; then
    echo; echo "==> skip ($(basename "$artifact") exists): $*"
    return
  fi
  echo; echo "==> $(date '+%H:%M') $*"
  local t0=$SECONDS
  "$@"
  echo "    done in $(( (SECONDS - t0) / 60 )) min"
}

for ds in HI-Medium LI-Medium; do
  # 1. X6: pattern attribution by sharing level (B8, the frozen levels)
  step "$ART/week13/x6_$ds.json" uv run finmesh x6 --dataset "$ds"
  # 2. The real-bank check: A64 membership, labels, features, X1 (no sweeps, no audit)
  uv run finmesh federation --dataset "$ds" --option A64
  step "$PQ/$ds/eval_w6_A64/meta.json" uv run finmesh labels --dataset "$ds" --option A64
  step "$ART/week04/features_${ds}_A64.json" uv run finmesh features --dataset "$ds" --option A64
  step "$ART/week04/features_${ds}_A64_pooled.json" \
    uv run finmesh features --dataset "$ds" --option A64 --view pooled
  step "$ART/week09/x1_${ds}_A64.json" \
    uv run finmesh x1 --dataset "$ds" --option A64 --no-sweeps --no-audit
done
echo; echo "==> $(date '+%H:%M') pytest -m real_data"
uv run pytest -m real_data -q
echo; echo "week 13: all steps done"
