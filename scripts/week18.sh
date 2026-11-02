#!/usr/bin/env bash
# Week 18: the sealed test, exactly as docs/protocol/test_plan.md lists it.
#   bash scripts/week18.sh HI-Medium 2>&1 | tee week18_HI-Medium.log   # night 1
#   bash scripts/week18.sh LI-Medium 2>&1 | tee week18_LI-Medium.log   # night 2
#   bash scripts/week18.sh narrative 2>&1 | tee week18_narrative.log   # night 3 (Ollama on)
#   bash scripts/week18.sh small     2>&1 | tee week18_small.log       # replication + results
# Re-run the same command after any stop: finished steps are skipped (their artifact
# exists), a half-done X1 continues from its next seed, a half-done narrative from its next
# case. Nothing is ever deleted: every opening of the test is logged, and a run that
# crashed after opening needs a deliberate `--allow-repeat` by hand (see the run log).
set -euo pipefail
cd "$(dirname "$0")/.."
ART="$(uv run python -c 'from finmesh.paths import artifacts_dir; print(artifacts_dir())' 2>/dev/null)/week18"
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

preflight() {  # preflight <dataset> <runs>
  echo; echo "==> $(date '+%H:%M') preflight $1"
  if ! uv run finmesh test-preflight --dataset "$1" --only "$2"; then
    echo "Preflight failed for $1: fix the FAIL lines above before opening the test."
    exit 1
  fi
}

medium() {  # medium <dataset>
  local ds="$1"
  preflight "$ds" "x1,baselines,x5,ensemble"
  step "$ART/x1_test_${ds}.json" uv run finmesh test-x1 --dataset "$ds"
  step "$ART/baselines_test_${ds}.json" uv run finmesh test-baselines --dataset "$ds"
  step "$ART/x5_test_${ds}.json" uv run finmesh test-x5 --dataset "$ds"
  step "$ART/ensemble_test_${ds}.json" uv run finmesh test-ensemble --dataset "$ds"
  uv run finmesh sealed-log --dataset "$ds"
}

case "${1:-}" in
  HI-Medium|LI-Medium)
    medium "$1"
    ;;
  narrative)
    if ! curl -sf "$OLLAMA/api/tags" | grep -q "\"$MODEL\""; then
      echo "Ollama is not reachable at $OLLAMA, or $MODEL is not pulled."
      echo "Start it with:  ollama serve   (another terminal)  and  ollama pull $MODEL"
      exit 1
    fi
    for ds in HI-Medium LI-Medium; do
      preflight "$ds" "narrative"
      step "$ART/narrative_test_${ds}_A23.json" \
        uv run finmesh narrative --test --dataset "$ds" --model "$MODEL" --url "$OLLAMA"
    done
    ;;
  small)
    for ds in HI-Small LI-Small; do
      preflight "$ds" "x1"
      step "$ART/x1_test_${ds}.json" uv run finmesh test-x1 --dataset "$ds" --no-x6 --no-audit
    done
    uv run finmesh test-report
    ;;
  report)
    uv run finmesh test-report
    ;;
  *)
    echo "usage: bash scripts/week18.sh HI-Medium | LI-Medium | narrative | small | report"
    exit 2
    ;;
esac
echo; echo "week 18 ($1): all steps done"
