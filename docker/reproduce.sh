#!/usr/bin/env bash
# FinMesh: the whole pipeline in stages, as the run logs list it (docs/runlog/).
#
#   docker compose --profile pipeline run --rm pipeline <stage> [--dry-run]
#   (or natively: bash docker/reproduce.sh <stage>, from the repository root)
#
# Stages, in order. The commit column is the code each stage must run on: the sealed-test
# stages refuse to open a test unless the code is identical to the commit the owner signed
# (finmesh test-preflight), so check out that commit first (docs/containers.md, step 3).
#
#   smoke            fixture end to end in a few minutes (any commit)            no real data
#   data             AMLworld -> Parquet, profiles, Large windows, Gate G0       c5fba52
#   validation       weeks 3-14: labels, features, baselines, X1-X6, gates      c5fba52
#   validation-llm   weeks 14: narratives on validation (needs Ollama)          c5fba52
#   primary          week 18: the primary sealed tests on HI/LI-Medium + Small  c5fba52
#   primary-llm      week 18: the narrative test (needs Ollama)                 c5fba52
#   replication      A25: validation selections and the Large replication tests c10fea8
#   replication-llm  A25: narrative model comparison and the Large narratives   c10fea8
#   paper            the paper's result figures and tables (no data needed)     any (HEAD)
#
# Every step whose artifact already exists under $FINMESH_DATA/artifacts is skipped, so a
# stage can be rerun after a stop. A sealed test is never opened twice: rerunning a stage
# skips finished openings, and a crash after an opening needs a deliberate --allow-repeat by
# hand (docs/runlog/week-18.md). --dry-run prints the commands without running them.
set -euo pipefail

STAGE="${1:-}"
DRY="${2:-}"
ROOT="${FINMESH_SRC_IN_CONTAINER:-$(pwd)}"
cd "$ROOT"
[ -f pyproject.toml ] || { echo "run from the repository root (pyproject.toml not found in $ROOT)"; exit 2; }

FM=(uv run finmesh)
if [ "$DRY" = "--dry-run" ]; then
  ART='$FINMESH_DATA/artifacts'
else
  ART="$(uv run python -c 'from finmesh.paths import artifacts_dir; print(artifacts_dir())')"
fi
MODEL="${MODEL:-llama3.2:3b}"            # the narrative model of weeks 14 and 18
A25_MODEL="${A25_MODEL:-qwen3:8b}"       # the model the A25 rule selected (N4 built on it)
OLLAMA="${OLLAMA_URL:-http://localhost:11434}"
FLAG="S1F[gate=2]"                       # the protected flag selected on validation (A25 P3)
EXPECT_PRIMARY="c5fba52"
EXPECT_REPLICATION="c10fea8"

run() {  # run <command...>
  echo; echo "==> $(date '+%H:%M') $*"
  [ "$DRY" = "--dry-run" ] && return 0
  local t0=$SECONDS
  "$@"
  echo "    done in $(( (SECONDS - t0) / 60 )) min"
}
step() {  # step <artifact> <command...>: skipped when the artifact exists
  local artifact="$1"; shift
  if [ "$DRY" != "--dry-run" ] && [ -f "$artifact" ]; then
    echo; echo "==> skip ($(basename "$artifact") exists): $*"
    return 0
  fi
  run "$@"
}
need_ollama() {
  [ "$DRY" = "--dry-run" ] && return 0
  if ! curl -sf "$OLLAMA/api/tags" >/dev/null; then
    echo "Ollama is not reachable at $OLLAMA."
    echo "Run this stage with the llm profile (docs/containers.md, step 5):"
    echo "  docker compose --profile llm up -d ollama"
    echo "  docker compose --profile llm exec ollama ollama pull <model>"
    echo "  docker compose --profile llm run --rm pipeline-llm $STAGE"
    exit 1
  fi
}
need_model() {  # need_model <model>
  [ "$DRY" = "--dry-run" ] && return 0
  if ! curl -sf "$OLLAMA/api/tags" | grep -q "\"$1\""; then
    echo "Model $1 is not pulled. Run: docker compose --profile llm exec ollama ollama pull $1"
    exit 1
  fi
}
check_commit() {  # check_commit <expected short sha>: warn, the preflight enforces it
  [ "$DRY" = "--dry-run" ] && return 0
  local head; head="$(git rev-parse --short=7 HEAD 2>/dev/null || echo unknown)"
  if [ "$head" != "$1" ]; then
    echo "NOTE: this checkout is at $head; the stage '$STAGE' was run at $1."
    echo "      The sealed-test openings will refuse to start unless the code matches the"
    echo "      signed commit. See docs/containers.md, step 3."
  fi
}

case "$STAGE" in
  smoke)
    # The pipeline on the synthetic fixture: proves the image, the mounts and the data
    # volume work, in a few minutes. Nothing here can feed a gate (fixture artifacts are
    # marked and refused).
    run "${FM[@]}" fixture
    run "${FM[@]}" week1 --dataset FIXTURE-Small
    run "${FM[@]}" g0 --dataset FIXTURE-Small
    run "${FM[@]}" labels --dataset FIXTURE-Small
    run "${FM[@]}" harness-check --dataset FIXTURE-Small --reps 50
    run "${FM[@]}" features --dataset FIXTURE-Small
    run "${FM[@]}" features --dataset FIXTURE-Small --view pooled
    run "${FM[@]}" baselines --dataset FIXTURE-Small --reps 50 --draws 2
    run "${FM[@]}" share --dataset FIXTURE-Small --reps 50
    run "${FM[@]}" x1 --dataset FIXTURE-Small --seeds 0 --reps 50 --no-sweeps --no-audit
    run "${FM[@]}" check
    ;;

  data)
    check_commit "$EXPECT_PRIMARY"
    # Raw AMLworld files: `finmesh download` (Kaggle API token in KAGGLE_USERNAME and
    # KAGGLE_KEY) for the Small and Medium sets; the Large files by browser into
    # $FINMESH_DATA/raw/HI-Large and raw/LI-Large (docs/runlog/a25.md).
    for ds in HI-Small LI-Small HI-Medium LI-Medium; do
      if [ "$DRY" != "--dry-run" ] && [ -n "${KAGGLE_USERNAME:-}" ] \
        && [ -z "$(ls -A "${FINMESH_DATA:-data}/raw/$ds" 2>/dev/null)" ]; then
        run "${FM[@]}" download --dataset "$ds"
      fi
      run "${FM[@]}" week1 --dataset "$ds"
    done
    run "${FM[@]}" g0 --dataset HI-Small --dataset LI-Small --dataset HI-Medium --dataset LI-Medium
    run "${FM[@]}" feature-timing --dataset HI-Small
    for src in HI-Large LI-Large; do
      run "${FM[@]}" large-window --source "$src" --days 16
      run "${FM[@]}" week1 --dataset "$src-W16"
      run "${FM[@]}" g0 --dataset "$src-W16"
    done
    ;;

  validation)
    check_commit "$EXPECT_PRIMARY"
    # Weeks 3-5: labels, features, baselines and Gate G1.
    for ds in HI-Small LI-Small HI-Medium LI-Medium; do
      run "${FM[@]}" labels --dataset "$ds"
      run "${FM[@]}" features --dataset "$ds"
      run "${FM[@]}" features --dataset "$ds" --view pooled
    done
    for ds in HI-Medium LI-Medium HI-Small; do
      run "${FM[@]}" harness-check --dataset "$ds"
      run "${FM[@]}" feature-report --dataset "$ds"
      run "${FM[@]}" diagnose --dataset "$ds"
    done
    for ds in HI-Medium LI-Medium HI-Small LI-Small; do
      run "${FM[@]}" baselines --dataset "$ds"
    done
    run "${FM[@]}" g1
    # Weeks 6-9: the sharing protocol, X1-X3 with the audit, the demo slice and Gate G2.
    for ds in HI-Medium LI-Medium; do
      run "${FM[@]}" share --dataset "$ds"
      run "${FM[@]}" x1 --dataset "$ds"
      run "${FM[@]}" demo-slice --dataset "$ds"
    done
    run "${FM[@]}" g2
    # Weeks 10-12: the federated DP track and Gate G3 (week 12 retunes under A19).
    for ds in HI-Medium LI-Medium; do
      run "${FM[@]}" x4 --dataset "$ds"
      run "${FM[@]}" features --dataset "$ds" --degree-cap 16
      run "${FM[@]}" influence --dataset "$ds"
    done
    run bash scripts/week12.sh
    # Week 13: X6 attribution and the real-bank federation (A64).
    run bash scripts/week13.sh
    # Week 14: the coverage curve (the narratives are in validation-llm).
    run env SKIP_NARRATIVE=1 bash scripts/week14.sh
    ;;

  validation-llm)
    check_commit "$EXPECT_PRIMARY"
    need_ollama; need_model "$MODEL"
    run env MODEL="$MODEL" OLLAMA_URL="$OLLAMA" bash scripts/week14_a23.sh
    ;;

  primary)
    check_commit "$EXPECT_PRIMARY"
    # The plan's order: HI-Medium, LI-Medium, then the Small replication sets and the
    # results page (docs/protocol/test_plan.md). Each opening is logged once.
    run bash scripts/week18.sh HI-Medium
    run bash scripts/week18.sh LI-Medium
    run bash scripts/week18.sh small
    ;;

  primary-llm)
    check_commit "$EXPECT_PRIMARY"
    need_ollama; need_model "$MODEL"
    run env MODEL="$MODEL" OLLAMA_URL="$OLLAMA" bash scripts/week18.sh narrative
    run bash scripts/week18.sh report
    ;;

  replication)
    check_commit "$EXPECT_REPLICATION"
    # A25 validation work (nothing opens a test): labels and features of the Large windows,
    # their token budgets, the protected-flag selection, the stronger detector, the
    # benchmark anchor and the adaptive-budget replay.
    for w in HI-Large-W16 LI-Large-W16; do
      run "${FM[@]}" labels --dataset "$w"
      run "${FM[@]}" features --dataset "$w"
      run "${FM[@]}" features --dataset "$w" --view pooled
      run "${FM[@]}" size-budget --dataset "$w"
    done
    for ds in HI-Medium LI-Medium; do
      step "$ART/a25/flag_frontier_$ds.json" "${FM[@]}" flag-frontier --dataset "$ds"
    done
    run "${FM[@]}" flag-select
    for ds in HI-Medium LI-Medium; do
      step "$ART/a25/plus_validation_$ds.json" "${FM[@]}" plus-validation --dataset "$ds"
      step "$ART/a25/budget_replay_${ds}_cap4x.json" \
        "${FM[@]}" budget-replay --dataset "$ds" --seeds 0,1,2 --cap-factor 4
    done
    for s in HI-Small LI-Small HI-Medium LI-Medium; do
      run "${FM[@]}" benchmark-dataset --source "$s"
      run "${FM[@]}" week1 --dataset "$s-FULL"
      run "${FM[@]}" g0 --dataset "$s-FULL"
      run "${FM[@]}" labels --dataset "$s-FULL"
      run "${FM[@]}" features --dataset "$s-FULL"
      run "${FM[@]}" features --dataset "$s-FULL" --view pooled
      step "$ART/a25/benchmark_$s.json" "${FM[@]}" benchmark --dataset "$s-FULL"
    done
    run "${FM[@]}" benchmark-table
    # The replication tests: three tracks per window, each its own logged opening.
    for w in HI-Large-W16 LI-Large-W16; do
      run "${FM[@]}" test-preflight --dataset "$w" --only x1
      step "$ART/week18/x1_test_$w.json" "${FM[@]}" test-x1 --dataset "$w" --flag "$FLAG"
      step "$ART/week18/x1_test_${w}_noart.json" "${FM[@]}" test-x1 --dataset "$w" --noart
      step "$ART/week18/x1_test_${w}_plus.json" "${FM[@]}" test-x1 --dataset "$w" --plus
      step "$ART/a25/budget_replay_${w}_cap4x.json" \
        "${FM[@]}" budget-replay --dataset "$w" --seeds 0,1,2 --cap-factor 4
      run "${FM[@]}" sealed-log --dataset "$w"
    done
    run "${FM[@]}" a25-report
    ;;

  replication-llm)
    check_commit "$EXPECT_REPLICATION"
    need_ollama
    # Model comparison on HI-Medium validation (A25N), then N4 on the selected model.
    case_dir="$ART/a25/narrative_cases"
    [ "$DRY" = "--dry-run" ] || mkdir -p "$case_dir"
    step "$case_dir/cases_HI-Medium_val.json" "${FM[@]}" narrative-export --dataset HI-Medium \
      --protocol A25N --out "$case_dir/cases_HI-Medium_val.json"
    for m in llama3.2:3b qwen2.5:7b llama3.1:8b "$A25_MODEL"; do
      need_model "$m"
      tag="${m//:/-}"
      step "$case_dir/result_$tag.json" "${FM[@]}" narrative-cases \
        --cases "$case_dir/cases_HI-Medium_val.json" --model "$m" --url "$OLLAMA" \
        --out "$case_dir/result_$tag.json"
      run "${FM[@]}" narrative-render --result "$case_dir/result_$tag.json"
    done
    run "${FM[@]}" narrative-render --result "$case_dir/result_${A25_MODEL//:/-}.json" --select
    # The Large narrative tests (each export is a logged opening).
    for w in HI-Large-W16 LI-Large-W16; do
      step "$case_dir/cases_${w}_test.json" "${FM[@]}" narrative-export --dataset "$w" \
        --protocol A25N --test --out "$case_dir/cases_${w}_test.json"
      step "$case_dir/result_${w}_${A25_MODEL//:/-}.json" "${FM[@]}" narrative-cases \
        --cases "$case_dir/cases_${w}_test.json" --model "$A25_MODEL" --url "$OLLAMA" \
        --out "$case_dir/result_${w}_${A25_MODEL//:/-}.json"
      run "${FM[@]}" narrative-render --result "$case_dir/result_${w}_${A25_MODEL//:/-}.json" --select
    done
    run "${FM[@]}" a25-report
    ;;

  paper)
    run "${FM[@]}" paper-assets
    ;;

  *)
    sed -n '2,24p' "$0"
    exit 2
    ;;
esac
echo; echo "stage '$STAGE': all steps done"
