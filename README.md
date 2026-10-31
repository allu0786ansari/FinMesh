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
| 6 | 30 Nov – 6 Dec | Token service, evidence records, S1 and S2 | Done on real data 26 Oct; S1 reaches the pooled-linking bound (0.85 of the oracle gain on HI-Medium) ([run log](docs/runlog/week-06.md)) |
| 7 | 7 – 13 Dec | Fusion and triage, S4, propagation, X1 and the first frontier | Done on real data 26 Oct; sharing beats the pooled oracle, so A14 adds a relational oracle ([run log](docs/runlog/week-07.md)) |
| 8 | 14 – 20 Dec | Relational oracle, S3 (local DP), progressive disclosure, X3, audit A1–A3 | Done on real data 29 Oct; H1b 0.98 (HI) and 0.83 (LI) of the relational ceiling; S3 existence leak and token budget led to A16 ([run log](docs/runlog/week-08.md)) |
| 9 | 21 – 27 Dec | S3 fix, sized budgets, attacks A4–A6, Gate G2 evidence, demo slice | Done on real data 29 Oct; **G2 passed** ([decision](docs/gates/G2.md), [run log](docs/runlog/week-09.md)) |
| 10 | 28 Dec – 3 Jan | Neural scorer, DP-SGD with persistent accounting, FedAvg, X4 part 1 | Done on real data 30 Oct; MLP near the GBDT without privacy, DP collapsed with the a-priori clip norm, which led to A18 ([run log](docs/runlog/week-10.md)) |
| 11 | 4 – 10 Jan | DP tuning on the proxy, account unit, degree cap, indirect influence, X5 | Done on real data 30 Oct; the degree cap cuts the worst-case influence from about 3,500 accounts to about 10 at almost no cost; the A18 grid's flaws led to A19 ([run log](docs/runlog/week-11.md)) |
| 12 | 11 – 17 Jan | DP retune (A19), IID arm, membership audit, stacked ensemble, Gate G3 | Done on real data 31 Oct; **G3 passed**: retuned DP reaches 0.78 (HI) and 0.96 (LI) of centralised, but adds nothing to the local GBDT on HI, so the detector stays local ([decision](docs/gates/G3.md), [run log](docs/runlog/week-12.md)) |
| 13 | 18 – 24 Jan | Attribution by sharing level (X6), real-bank X1 check (A64) | Done on real data 31 Oct; **H3a met on HI-Medium** (S2 − S0 +0.042 [0.016, 0.068]), the gain comes from cross-bank structure; A64 covers only 4.7% of accounts, which led to A21 ([run log](docs/runlog/week-13.md)) |
| 14 | 25 – 31 Jan | Coverage curve (A21), constrained narrative with abstention, grounding (H3b) | Code done (A21); awaiting real-data run with Ollama (`scripts/week14.sh`, [run log](docs/runlog/week-14.md)) |
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
