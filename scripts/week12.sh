#!/usr/bin/env bash
# Week 12 on real data, every step in order, unattended:
#   bash scripts/week12.sh 2>&1 | tee week12.log
# Re-run the same command to resume after an interruption: a step whose
# artifact already exists is skipped (delete the artifact to redo that step).
# An interrupted training is not resumed; its privacy spend stays in the ledger.
set -euo pipefail
cd "$(dirname "$0")/.."
ART="$(uv run python -c 'from finmesh.paths import artifacts_dir; print(artifacts_dir())' 2>/dev/null)/week12"

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

# 1. A19 retune on the proxy federations (writes finmesh/schemas/dp_hparams.json)
for ds in HI-Small LI-Small; do
  step "$ART/dp_tune_$ds.json" uv run finmesh dp-tune --dataset "$ds" --grid A19
done
# 2. X5 with the retuned settings and the IID arm (saves every model)
for ds in HI-Medium LI-Medium; do
  step "$ART/x5_$ds.json" uv run finmesh x5 --dataset "$ds"
done
# 3. Membership inference on the federated model (deployed setup)
for ds in HI-Medium LI-Medium; do
  step "$ART/membership_$ds.json" uv run finmesh membership --dataset "$ds"
done
# 4. Stacked ensemble on X5's saved models
for ds in HI-Medium LI-Medium; do
  step "$ART/ensemble_$ds.json" uv run finmesh ensemble --dataset "$ds"
done
# 5. Gate G3 evidence and the rule's outcome; real-data checks
echo; echo "==> $(date '+%H:%M') finmesh g3"
uv run finmesh g3
echo; echo "==> $(date '+%H:%M') pytest -m real_data"
uv run pytest -m real_data -q
echo; echo "week 12: all steps done"
