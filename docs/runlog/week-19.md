# Week 19 · Containerised pipeline

**State (12 Nov 2026):** built and pushed. The images are built and tested in GitHub CI; the sandbox here cannot pull base images from a registry (see "What I ran here").

## 1. What was built

| File | What it is |
| --- | --- |
| `Dockerfile` | Two targets. `runtime` (default, `finmesh:local`): the slim, unprivileged image of week 17 for the demo path, console and X7 smoke. `full` (`finmesh:full`): the research pipeline, with the dev tools, git (result stamps carry the code commit), curl (the Ollama checks of the run scripts), Liberation Serif (the paper figures' font), the Kaggle client and the stage runner |
| `docker/reproduce.sh` | The pipeline as stages, taken from the run logs and the existing week scripts: `smoke`, `data`, `validation`, `validation-llm`, `primary`, `primary-llm`, `replication`, `replication-llm`, `paper`. Skips steps whose artifact exists; never opens a sealed test twice; `--dry-run` prints the commands. Baked into the full image at `/opt/finmesh/reproduce.sh`, so it also works on a clone checked out at an older, signed commit |
| `compose.yaml` | Profiles `smoke`, `console` (as before), `pipeline`, `cli`, `paper`, `ci`, and `llm` (an Ollama container plus `pipeline-llm` and `finmesh-llm`, which share its network so the model server is on `localhost`, the only kind of endpoint FinMesh accepts) |
| `.env.example` | `FINMESH_UID/GID` (files are written as you), `FINMESH_SRC` (which checkout to mount), `FINMESH_DATA_DIR`, Kaggle token, models |
| `Makefile` | `docker-build`, `docker-smoke`, `docker-stage STAGE=…`, `docker-paper`, `docker-ci` |
| `.github/workflows/ci.yml` | The container job now builds both images, runs X7 in the runtime image, checks the compose file for every profile, dry-runs every stage, runs the `smoke` stage in the full image with the checkout and a data folder mounted, and rebuilds the paper tables in the container and checks them byte-identical |
| `docs/containers.md` | The guide: build, smoke check, which commit each stage needs, every stage with its run log and machine time, narratives, paper, console, CI, troubleshooting |

Design decisions that matter:

- **The image is the environment; the checkout is mounted.** Results (`docs/eval`, `finmesh/schemas/token_budgets.json`, the data artifacts) land in your checkout and data folder exactly as a native run writes them, and `git` inside the container stamps them with the checkout's commit.
- **Stages run on the code that produced the results.** The preflight already refuses to open a sealed test unless the code equals the signed commit, so the guide uses one full clone per signed commit (`c5fba52` for the data, validation and primary stages; `c10fea8` for the replication stages) and one shared data folder. `uv.lock` and `pyproject.toml` are unchanged since both commits, so the current images serve them. The stage runner lives in `docker/`, outside the preflight's code paths.
- **Files belong to you.** The pipeline containers run as `FINMESH_UID:FINMESH_GID`; the full image's environment is usable by any uid.
- **Narratives stay local.** The `llm` profile runs Ollama in a container, and the narrative containers share its network namespace, so `localhost:11434` works and no text leaves the machine.

## 2. What I ran here

- `bash -n docker/reproduce.sh`, and every stage with `--dry-run`: all parse and list their commands.
- The `smoke` stage natively (`bash docker/reproduce.sh smoke` with a scratch data folder): all eleven steps passed, nothing written into the checkout.
- `docker compose --profile <p> config --quiet` for all seven profiles: valid.
- **Not possible here:** building the images. The sandbox's network allows package registries (PyPI, npm) but not container registries (Docker Hub, GHCR, ECR and the Google mirror all return 403), so `python:3.12-slim` cannot be pulled. GitHub CI builds and tests both images on every push instead.
- The real-data stages need the AMLworld files and many hours; they were not run in the container. Their commands are the ones in the run logs and week scripts, unchanged.

## 3. What you run on your machine

1. `git pull`, then `cp .env.example .env` and set `FINMESH_UID` and `FINMESH_GID` to the output of `id` (WSL: usually 1000 and 1000).
2. `make docker-build` (about 5–10 min the first time).
3. `make docker-smoke` (a few minutes): X7, then the fixture pipeline.
4. Optional: `make docker-ci` (about 15–20 min), the CI checks inside the container.
5. Optional, to see the full pipeline in action on your data without opening anything: `docker compose --profile cli run --rm finmesh check`, then `docker compose --profile pipeline run --rm pipeline validation --dry-run`.

Nothing in this week opens a sealed test, and none of the steps above needs the frozen-commit clones.

## 4. Troubleshooting

See the table at the end of `docs/containers.md` (permissions, preflight, Ollama, memory, commit stamps).

## 5. Checklist against the plan (weeks 19–20: packaging)

| Plan item | State |
| --- | --- |
| Containerised pipeline | Done: every stage, the narratives, the paper and CI run in containers; tested in CI |
| Full container profile (the cut-order item) | Done (`pipeline`, `cli`, `paper`, `ci`, `llm`) |
| Smoke profile always kept | Kept, and extended to the full image |
| Final figures | Done (week 18 and the paper review) |
| Paper | Content done; venue, co-author approval and submission checks remain |
| Artifact release, demo video | Open |

## 6. Open items

- Run steps 1–3 above once on your machine and tell me the result; Docker Desktop on WSL is the one environment CI does not cover.
- Next for weeks 19–20: the G4 note, the release (tag, notes, `CITATION.cff`), the demo-video script.
