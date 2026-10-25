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
step uv run finmesh check
echo; echo "local CI: all steps passed"
