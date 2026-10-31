#!/usr/bin/env bash
# Runs exactly the steps of .github/workflows/ci.yml, in order, and stops at
# the first failure. Run it before every push:  bash scripts/ci_local.sh
set -euo pipefail
cd "$(dirname "$0")/.."
step() { echo; echo "==> $*"; "$@"; }
step uv sync --locked
step uv run ruff check .
step uv run ruff format --check .
step uv run mypy
step uv run pytest --cov --cov-report=term-missing --cov-fail-under=80
step uv run finmesh fixture
step uv run finmesh week1 --dataset FIXTURE-Small
step uv run finmesh g0 --dataset FIXTURE-Small
step uv run finmesh feature-timing --dataset FIXTURE-Small
step uv run finmesh labels --dataset FIXTURE-Small
step uv run finmesh harness-check --dataset FIXTURE-Small --reps 200
step uv run finmesh sealed-log --dataset FIXTURE-Small
step uv run finmesh features --dataset FIXTURE-Small
step uv run finmesh feature-report --dataset FIXTURE-Small
step uv run finmesh diagnose --dataset FIXTURE-Small
step uv run finmesh features --dataset FIXTURE-Small --view pooled
step uv run finmesh baselines --dataset FIXTURE-Small --reps 200 --draws 5
step uv run finmesh share --dataset FIXTURE-Small --reps 200
step uv run finmesh x1 --dataset FIXTURE-Small --seeds 0,1 --reps 200
step uv run finmesh demo-slice --dataset FIXTURE-Small --alerts 20
step uv run finmesh g2
step uv run finmesh x4 --dataset FIXTURE-Small --seeds 0 --reps 50 --rounds 5 --local-steps 5
step uv run finmesh dp-tune --dataset FIXTURE-Small --quick --rounds 5 --local-steps 5
step uv run finmesh features --dataset FIXTURE-Small --degree-cap 16
step uv run finmesh influence --dataset FIXTURE-Small --sample 20
step uv run finmesh x5 --dataset FIXTURE-Small --seeds 0 --reps 50 --rounds 5 --local-steps 5
step uv run finmesh membership --dataset FIXTURE-Small --reps 50 --rounds 5 --local-steps 5
step uv run finmesh ensemble --dataset FIXTURE-Small --reps 50
step uv run finmesh g3
step uv run finmesh x6 --dataset FIXTURE-Small --seeds 0 --reps 100
step uv run finmesh federation --dataset FIXTURE-Small --option A8 --force
step uv run finmesh labels --dataset FIXTURE-Small --option A8
step uv run finmesh features --dataset FIXTURE-Small --option A8
step uv run finmesh features --dataset FIXTURE-Small --option A8 --view pooled
step uv run finmesh x1 --dataset FIXTURE-Small --option A8 --seeds 0 --reps 50 --no-sweeps --no-audit
step uv run finmesh federation --dataset FIXTURE-Small --option B8c50 --force
step uv run finmesh labels --dataset FIXTURE-Small --option B8c50
step uv run finmesh features --dataset FIXTURE-Small --option B8c50
step uv run finmesh features --dataset FIXTURE-Small --option B8c50 --view pooled
step uv run finmesh x1 --dataset FIXTURE-Small --option B8c50 --seeds 0 --reps 50 --no-sweeps --no-audit
step uv run finmesh coverage --dataset FIXTURE-Small
step uv run finmesh check
echo; echo "local CI: all steps passed"
