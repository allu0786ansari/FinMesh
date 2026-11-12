# Convenience targets. Every target is a plain `uv run ...` command, listed in
# docs/runlog so the same steps work on Windows without make.
DATASET ?= HI-Small

.PHONY: setup check lint typecheck test cov smoke scale ingest profile week1 all ci \
        docker-build docker-smoke docker-stage docker-paper docker-ci

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

ci:           ## exactly what GitHub Actions runs; use before every push
	bash scripts/ci_local.sh

# Containers (docs/containers.md). Files are written as you: FINMESH_UID/GID default to
# your ids here. STAGE is a docker/reproduce.sh stage: make docker-stage STAGE=validation
STAGE ?= smoke
DOCKER_IDS = FINMESH_UID=$$(id -u) FINMESH_GID=$$(id -g)

docker-build: ## build both images (finmesh:local and finmesh:full)
	docker build --target runtime -t finmesh:local .
	docker build --target full -t finmesh:full .

docker-smoke: ## X7 in the runtime image, then the pipeline smoke stage in the full image
	docker run --rm finmesh:local x7 --smoke --node-timeout 1
	$(DOCKER_IDS) docker compose --profile pipeline run --rm pipeline smoke

docker-stage: ## one pipeline stage in the container: make docker-stage STAGE=data
	$(DOCKER_IDS) docker compose --profile pipeline run --rm pipeline $(STAGE)

docker-paper: ## the paper's figures and tables, in the container
	$(DOCKER_IDS) docker compose --profile paper run --rm paper

docker-ci: ## scripts/ci_local.sh inside the full image
	$(DOCKER_IDS) docker compose --profile ci run --rm ci
