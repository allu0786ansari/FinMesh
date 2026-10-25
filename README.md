# FinMesh

Privacy-preserving cross-bank financial-crime detection. FinMesh measures **what banks should share, and what each piece of shared information costs in privacy**: a utility–leakage frontier for cross-bank evidence exchange, built and evaluated on the public synthetic AMLworld data.

The full research design is in [`docs/proposal/FinMesh_Proposal_v2.md`](docs/proposal/FinMesh_Proposal_v2.md). Work follows a 20-week plan; each finished week has a run log in [`docs/runlog/`](docs/runlog/) with the exact commands to reproduce it.

## Status

| Week | Dates | Focus | State |
| --- | --- | --- | --- |
| 1 | 26 Oct – 1 Nov 2026 | Repository, CI, AMLworld ingestion, data profile | Done; verified on real data 24 Oct ([run log](docs/runlog/week-01.md)) |
| 2 | 2 – 8 Nov | Visibility model, federation, splits, Gate G0 | Done; **G0 passed** with amendments A5–A7 ([decision](docs/gates/G0.md)) |
| 3 | 9 – 15 Nov | Labels, sealed test, metrics, budgets, bootstrap | Done; harness verified on real data 25 Oct ([run log](docs/runlog/week-03.md)) |
| 4 | 16 – 22 Nov | Behaviour, graph and neighbourhood features | Done on real data 25 Oct; diagnostics led to A8–A11 ([run log](docs/runlog/week-04.md)) |
| 5 | 23 – 29 Nov | Baselines, preregistration, Gate G1 | Done; **G1 passed** (oracle − S0 linked +0.51), preregistration frozen, tag `g1` ([decision](docs/gates/G1.md)) |
| 6 | 30 Nov – 6 Dec | Token service, evidence records, S1 and S2 | Code done; awaiting real-data run ([run log](docs/runlog/week-06.md)) |
| 7–9 | 7 – 27 Dec | Fusion, triage, S3, progressive disclosure, attacks, Gate G2 | Not started |
| 10–12 | 28 Dec – 17 Jan | Federated DP detection, Gate G3 | Not started |
| 13–14 | 18 – 31 Jan | Attribution and narrative | Not started |
| 15–17 | 1 – 21 Feb | Demo path and analyst console | Not started |
| 18–20 | 22 Feb – 14 Mar 2027 | Sealed-test runs, paper, release, Gate G4 | Not started |

## Quick start

Requirements: Python 3.11–3.13 (3.12 recommended), [uv](https://docs.astral.sh/uv/), git, about 8 GB of RAM and 5 GB of free disk.

```bash
git clone https://github.com/allu0786ansari/FinMesh.git
cd FinMesh
uv sync                      # installs locked dependencies into .venv
uv run pytest                # unit tests on the synthetic fixture
uv run finmesh fixture       # write the synthetic test dataset
uv run finmesh week1 --dataset FIXTURE-Small   # full week-1 pipeline on it
uv run finmesh check         # what is installed and which data is present
bash scripts/ci_local.sh     # exactly what GitHub CI runs
```

To run on the real data, follow [`docs/runlog/week-01.md`](docs/runlog/week-01.md): download AMLworld, then `uv run finmesh week1 --dataset HI-Small` and the same for `LI-Small`.

## Repository layout

```
finmesh/          research harness (all experiments run in-process here)
  data/           ingestion, scheme linking, manifests, fixture, profile
  eval/           provenance stamps (week 1); metrics and budgets (week 3)
  features/ models/ federation/ sharing/ matching/ fusion/ attacks/ attribution/ schemas/
services/         demo-path services (weeks 15–17)
console/          analyst console (week 17)
experiments/      one config + runner per experiment X1–X7
docs/             proposal, run logs, gates, protocol, data card, literature matrix
scripts/          utilities (scale check)
tests/            unit, integration (real data, skipped if absent), contract
```

Data never enters git. Everything large lives under `data/` (or wherever `FINMESH_DATA` points).

## Ground rules

- **Validation before test.** The sealed test split is opened once, in week 18.
- **Every number has provenance.** Results are JSON artifacts stamped with code commit, data manifest hash, parameters and seed. Anything built from the synthetic fixture is marked and can never pass a gate.
- **Missed targets are findings.** Gates decide whether to continue, adjust or cut; they are never skipped.

## Licence

Code: [MIT](LICENSE). Data: the IBM AMLworld datasets are under [CDLA-Permissive-2.0](docs/data_License.md); see the [data card](docs/data_card.md).
