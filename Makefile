# Convenience targets. Every target is a plain `uv run ...` command, listed in
# docs/runlog so the same steps work on Windows without make.
DATASET ?= HI-Small

.PHONY: setup check lint typecheck test cov smoke scale ingest profile week1 all

setup:        ## install locked dependencies (dev tools included)
	uv sync

check:        ## environment and data status
	uv run finmesh check

lint:         ## style and static checks
	uv run ruff check .
	uv run ruff format --check .

typecheck:
	uv run mypy

test:
	uv run pytest

cov:
	uv run pytest --cov --cov-report=term-missing --cov-fail-under=80

smoke:        ## full week-1 pipeline on the synthetic fixture
	uv run finmesh fixture
	uv run finmesh week1 --dataset FIXTURE-Small

scale:        ## ingestion time and memory on 5M synthetic rows
	uv run python scripts/scale_check.py --rows 5000000

ingest:
	uv run finmesh ingest --dataset $(DATASET)

profile:
	uv run finmesh profile --dataset $(DATASET)

week1:        ## ingest + profile a real dataset: make week1 DATASET=HI-Small
	uv run finmesh week1 --dataset $(DATASET)

all: lint typecheck cov smoke
