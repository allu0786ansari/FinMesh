#!/usr/bin/env bash
# Week 14 on real data, every step in order, unattended:
#   bash scripts/week14.sh 2>&1 | tee week14.log
# Re-run the same command to resume: a step whose artifact already exists is skipped.
# Needs Ollama running on this machine with llama3.2:3b (`ollama serve`, `ollama pull llama3.2:3b`).
# SKIP_NARRATIVE=1 runs only the coverage curve.
set -euo pipefail
cd "$(dirname "$0")/.."
ART="$(uv run python -c 'from finmesh.paths import artifacts_dir; print(artifacts_dir())' 2>/dev/null)"
PQ="$(uv run python -c 'from finmesh.paths import data_root; print(data_root())' 2>/dev/null)/parquet"
MODEL="${MODEL:-llama3.2:3b}"
OLLAMA="${OLLAMA_URL:-http://localhost:11434}"

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

# Fail fast, before hours of coverage runs, if the narrative cannot run at the end.
if [ "${SKIP_NARRATIVE:-0}" != "1" ]; then
  if ! curl -sf "$OLLAMA/api/tags" | grep -q "\"$MODEL\""; then
    echo "Ollama is not reachable at $OLLAMA, or $MODEL is not pulled."
    echo "Start it with:  ollama serve   (another terminal)  and  ollama pull $MODEL"
    echo "Or run only the coverage curve:  SKIP_NARRATIVE=1 bash scripts/week14.sh"
    exit 1
  fi
fi

for ds in HI-Medium LI-Medium; do
  # 1. Coverage curve (A21): federations holding 10-90% of accounts, largest banks first
  for p in 10 25 50 75 90; do
    opt="B8c$p"
    uv run finmesh federation --dataset "$ds" --option "$opt"
    step "$PQ/$ds/eval_w6_$opt/meta.json" uv run finmesh labels --dataset "$ds" --option "$opt"
    step "$ART/week04/features_${ds}_$opt.json" uv run finmesh features --dataset "$ds" --option "$opt"
    step "$ART/week04/features_${ds}_${opt}_pooled.json" \
      uv run finmesh features --dataset "$ds" --option "$opt" --view pooled
    step "$ART/week09/x1_${ds}_$opt.json" \
      uv run finmesh x1 --dataset "$ds" --option "$opt" --no-sweeps --no-audit
  done
  echo; echo "==> $(date '+%H:%M') coverage curve $ds"
  uv run finmesh coverage --dataset "$ds"
done

if [ "${SKIP_NARRATIVE:-0}" != "1" ]; then
  for ds in HI-Medium LI-Medium; do
    # 2. Constrained narrative and the grounding test (H3b) at S2, seed 0
    step "$ART/week14/narrative_$ds.json" \
      uv run finmesh narrative --dataset "$ds" --model "$MODEL" --url "$OLLAMA"
  done
fi
echo; echo "==> $(date '+%H:%M') pytest -m real_data"
uv run pytest -m real_data -q
echo; echo "week 14: all steps done"
