# Running FinMesh in containers

Everything FinMesh does runs in Docker: the demo path, the analyst console, every step of the research pipeline, the narratives with a local language model, the paper's figures and tables, and the CI checks. The images hold the environment; your checkout and your data folder are mounted, so results land where a native run would put them.

| Image | Target | What it is for |
| --- | --- | --- |
| `finmesh:local` | `runtime` (default) | Slim, unprivileged: the demo path, the analyst console, the X7 smoke test |
| `finmesh:full` | `full` | The research pipeline: dev tools (pytest, ruff, mypy), git (results are stamped with the code commit), curl, the paper font, and the stage runner `docker/reproduce.sh` |

| Compose profile | Service | Runs |
| --- | --- | --- |
| `smoke` | `smoke` | X7 on the synthetic smoke world (runtime image) |
| `console` | `console` | The analyst console on `127.0.0.1:8050` |
| `pipeline` | `pipeline` | One stage of the pipeline (`docker/reproduce.sh <stage>`) |
| `cli` | `finmesh` | Any single `finmesh` command |
| `paper` | `paper` | `finmesh paper-assets` (no data needed) |
| `ci` | `ci` | `scripts/ci_local.sh`, exactly what GitHub CI runs |
| `llm` | `ollama`, `pipeline-llm`, `finmesh-llm` | A local Ollama server and the stages and commands that need it |

## Requirements

- Docker Engine with the Compose plugin, or Docker Desktop. On Windows, use Docker Desktop with WSL 2 integration and run every command from your WSL shell.
- Memory: the pipeline was run on an 8 GB laptop. Give Docker (or WSL) at least 6 GB; the 8-billion-parameter narrative models need about 6 GB on their own, so run the narrative stages with little else open.
- Disk: a few GB for the images and the Small and Medium data; the `data` stage also needs the Large AMLworld files, which take tens of GB before the 16-day windows are cut from them.

## 1. Build the images

```bash
git clone https://github.com/allu0786ansari/FinMesh.git && cd FinMesh
cp .env.example .env            # then set FINMESH_UID and FINMESH_GID to the output of `id`
make docker-build               # or the two `docker build` lines in the Makefile
```

## 2. Check that everything works (a few minutes, no real data)

```bash
make docker-smoke
```

It runs X7 in the runtime image, then the pipeline's `smoke` stage in the full image: the synthetic fixture from ingestion to X1, written to `./data` as your user.

## 3. Use the right code for each stage

Results are reproduced with the code that produced them. The sealed-test stages enforce this: `finmesh test-preflight` refuses to open a test unless the working tree is clean and the code (`finmesh/`, `scripts/`, `pyproject.toml`, `uv.lock`) is identical to the commit the owner signed. The images work for every commit below, because no dependency changed after them.

| Stages | Commit | Signed in |
| --- | --- | --- |
| `data`, `validation`, `validation-llm`, `primary`, `primary-llm` | `c5fba52` | `docs/protocol/test_plan.md` |
| `replication`, `replication-llm` | `c10fea8` | `docs/protocol/improvement_plan_A25.md` (A25a) |
| `paper`, `smoke`, `ci` | any, normally the latest | — |

Make one clone per commit next to your main checkout, and share one data folder:

```bash
cd ..
git clone https://github.com/allu0786ansari/FinMesh.git FinMesh-primary && git -C FinMesh-primary checkout c5fba52
git clone https://github.com/allu0786ansari/FinMesh.git FinMesh-a25     && git -C FinMesh-a25 checkout c10fea8
cd FinMesh
```

Then point the containers at a clone with `FINMESH_SRC` (in `.env` or on the command line), and keep `FINMESH_DATA_DIR` an absolute path so every clone uses the same data:

```bash
FINMESH_SRC=../FinMesh-primary FINMESH_DATA_DIR=$PWD/data make docker-stage STAGE=validation
```

Use full clones, not `git worktree`: a worktree's `.git` points to a path on your machine that the container cannot see, so the commit stamp and the preflight would fail.

## 4. Run the pipeline, stage by stage

```bash
FINMESH_SRC=../FinMesh-primary FINMESH_DATA_DIR=$PWD/data \
  docker compose --profile pipeline run --rm pipeline <stage>
```

| Stage | What it runs | Run log | Machine time (8 GB laptop) |
| --- | --- | --- | --- |
| `data` | AMLworld → Parquet and profiles for HI/LI-Small and -Medium; the 16-day Large windows; Gate G0 | weeks 1–2, A25 P1 | hours; the Large windows are the slowest part |
| `validation` | Labels, features, baselines, G1; sharing, X1–X3 and the audit, G2; the federated DP track, G3; X6 and A64; the coverage curve | weeks 3–14 | one to two days in total (rough) |
| `validation-llm` | The A23 narratives on validation (Ollama) | week 14 | several hours |
| `primary` | The primary sealed tests: HI-Medium, LI-Medium, then the Small sets and the results page | week 18 | about two nights |
| `primary-llm` | The narrative test (Ollama) | week 18 | 10–12 h |
| `replication` | A25: Large-window labels, features and budgets; flag selection; stronger detector; benchmark; budget replay; the three tracks on both Large windows; the results page | A25 | about two nights |
| `replication-llm` | A25: the four-model narrative comparison, N4, and the Large narratives (Ollama) | A25 | many hours on CPU; much faster with a GPU |
| `paper` | The paper's result figures and tables from the committed result pages | — | seconds |

- `<stage> --dry-run` prints the commands of a stage without running them.
- A stage can be rerun after a stop: steps whose artifact exists are skipped.
- A sealed test is never opened twice. A crash after an opening needs a deliberate `--allow-repeat` by hand, as described in `docs/runlog/week-18.md`; every opening is in `finmesh sealed-log`.
- The raw files: with a Kaggle API token in `.env`, the `data` stage downloads the Small and Medium sets. Download the Large files (HI-Large, LI-Large) by browser into `data/raw/HI-Large/` and `data/raw/LI-Large/` first (`docs/runlog/a25.md`).
- Single commands: `docker compose --profile cli run --rm finmesh <command> [args]`, for example `... finmesh sealed-log --dataset HI-Medium`.

## 5. Narratives with a local model

FinMesh only talks to a model server on `localhost` (`finmesh.attribution.llm_probe`), so the narrative containers share the Ollama container's network. No text leaves your machine.

```bash
docker compose --profile llm up -d ollama
docker compose --profile llm exec ollama ollama pull llama3.2:3b     # weeks 14 and 18
docker compose --profile llm exec ollama ollama pull qwen3:8b        # A25 (and qwen2.5:7b, llama3.1:8b for the comparison)
FINMESH_SRC=../FinMesh-primary FINMESH_DATA_DIR=$PWD/data \
  docker compose --profile llm run --rm pipeline-llm primary-llm
docker compose --profile llm down                                    # models stay in the ollama-models volume
```

Ollama runs on the CPU here. With an NVIDIA GPU and the NVIDIA Container Toolkit, add a `deploy.resources.reservations.devices` entry to the `ollama` service. The A25 comparison was originally run on a Colab T4 GPU for speed; the commands are the same.

## 6. Paper figures and tables

```bash
make docker-paper
```

It rebuilds Figs. 2–5 and Tables I–VI from the committed result pages. The tables come out byte-identical; the figures match up to the font version installed in the image.

## 7. The analyst console

```bash
docker compose --profile console up --build      # then open http://127.0.0.1:8050
```

It reads the demo world under `data/demo/<dataset>` (built with `finmesh demo-build`, week 16).

## 8. CI in the container

```bash
make docker-ci
```

Runs `scripts/ci_local.sh` in the full image: ruff, mypy, pytest with coverage, and the fixture pipeline. Its fixture data goes to the container's `/tmp`, not your data folder.

## Troubleshooting

| Symptom | Cause and fix |
| --- | --- |
| `Permission denied` writing `data/` or `docs/` | The container runs as `FINMESH_UID:FINMESH_GID`. Set them to the output of `id` in `.env`. Create `data/` yourself before the first run, so Docker does not create it as root. |
| Preflight: `code identical to the signed frozen commit … FAIL` | The mounted checkout is not at the signed commit, or has local changes. Use the clone of step 3 and keep it clean. |
| Preflight: `working tree clean … FAIL` | A file in the clone was changed. `git -C ../FinMesh-primary status`, then restore it. |
| `Ollama is not reachable` | Run the stage with `--profile llm` and the `pipeline-llm` service, after `docker compose --profile llm up -d ollama`. |
| `Model … is not pulled` | `docker compose --profile llm exec ollama ollama pull <model>`. |
| The container is killed (exit 137) | Out of memory. Raise Docker's or WSL's memory limit (`.wslconfig`), and run one stage at a time. |
| `git_commit: unknown` in a result stamp | The checkout was mounted without its `.git` folder (or as a worktree). Use a full clone. |
