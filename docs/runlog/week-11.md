# Week 11 run log · 4 – 10 Jan 2027 · DP tuning on the proxy, account unit, degree cap, indirect influence, X5

**Goal:**
- fix DP-SGD's settings without touching the Medium banks' data;
- add the account privacy unit and the degree cap;
- measure how far one account reaches through its neighbours' features;
- run X5 (window vs account unit, with and without the cap, ε sweep) for H2a and H2b.

**State:** code complete and tested (unit cases, fixture pipelines, stress scale). Your run produces the tuned settings, the influence numbers and X5.

## Week-10 review (your run, pushed 30 Oct)

| Validation AUPRC | HI-Medium | LI-Medium |
| --- | --- | --- |
| Local GBDT | 0.337 | 0.085 |
| MLP, centralised | 0.310 | 0.087 |
| MLP, local only | 0.252 | 0.061 |
| MLP, FedAvg | 0.287 | 0.076 |
| MLP, FedAvg + DP, ε = 1 / 3 / 10 | 0.101 / 0.132 / 0.153 | 0.028 / 0.031 / 0.033 |
| H2a: DP share of centralised at ε = 10 | 0.49 | 0.38 |

Findings:

1. **The neural scorer is competitive without privacy.** It is 0.03 below the GBDT on HI-Medium and level on LI-Medium. Federation helps: FedAvg beats local-only on both.
2. **DP collapsed, and the cause is the settings, not DP itself.**
   - Only about 3% of units ever reached the clip norm of 1, so the noise, which scales with that norm, was far larger than the gradients.
   - With 512 units per step and about 1% positives, a few positives carried the signal against noise of norm about 93.
   - **Your decision:** choose the settings on the Small federations, as public proxy data (A18).

## Amendment A18 (fixed before any of its results)

- **DP settings on the proxy.**
  - Grid: clip norm ∈ {0.01, 0.03, 0.1, 0.3, 1} × expected batch ∈ {512, 2048, 8192}, at ε = 3, window unit, seed 0, lr 1e-3.
  - Every setting gets the same example budget: 50 rounds with 20 × 512 / batch local steps (20, 5 and 1). A larger batch takes fewer, less noisy steps at the same cost; the chosen step count is frozen with the setting.
  - It runs on HI-Small and LI-Small, separate AMLworld federations, and is scored on their own training hold-out.
  - The winner per regime is frozen in `finmesh/schemas/dp_hparams.json`; HI-Medium uses the HI choice and LI-Medium the LI choice.
  - No Medium data and no validation data are used to choose.
- **Account unit:** one account's bag of at most 8 training windows (a fixed hash picks them). Accounts are Poisson-sampled and clipped as whole bags (exact, from the per-bag Gram matrices built in week 10).
- **Degree cap D = 16:**
  - Every account keeps its first 16 distinct counterparties over the observation; an edge survives only within both ends' caps.
  - All features are rebuilt from the capped graph.
  - This is the proposal's "each account's contribution to neighbour counts is clipped".
- **Indirect influence:**
  - 200 training accounts (half with a laundering row) are removed and every feature rebuilt, for both views.
  - An account's *group size* is 1 plus the other same-member training accounts within two hops whose rows change. That is how many account-unit bags it moves, so it is what the account-level guarantee needs for group privacy.
- **X5:** both units × both feature views × ε ∈ {1, 3, 10}, plus non-private references, seeds 0–2.
  - **H2a** is judged with the tuned settings.
  - **H2b** asks whether window − account has a paired 95% CI above 0.

## What was built

| Item | Where | Notes |
| --- | --- | --- |
| Tuning | `finmesh/training/dp_tune.py`, `finmesh dp-tune` | Refuses to run on anything but HI-Small, LI-Small (and the fixture) |
| Frozen DP settings | `finmesh/schemas/dp_hparams.json`, `finmesh/training/neural.py` | Written by `dp-tune`; read by every DP run; X5 refuses to run without them |
| Account unit | `client_data(..., "account")` | Bags of at most 8 windows, fixed hash |
| Degree-capped features | `finmesh/features/variants.py`, `finmesh features --degree-cap 16` | Works in 16 account-hash partitions; rows aligned with the member build (rows that lose every leg: counts and sums 0, the rest null) |
| Influence | `finmesh/training/influence.py`, `finmesh influence` | Removal rebuilds for both views, slice-by-slice comparison, 2-hop attribution, group sizes and formal group ε |
| X5 | `finmesh/training/x5.py`, `finmesh x5` | 4 non-private references + 12 DP trainings per seed; H2a, H2b, cap cost |
| Tests | `tests/unit/test_week11.py`, `tests/integration/test_real_data_week11.py` | |

### Design choices to review

- **ε = 3 is the tuning target.** One setting must serve every ε and unit; the middle of the sweep is the neutral choice. The account unit has fewer units per client, so the same expected batch means a higher sampling rate; the accountant handles this.
- **The proxy is not identical to the target.** The Small sets have fewer units per client, so the same expected batch is a larger sampling rate there. The transfer is approximate, and the honest alternative (tuning on the Medium banks' own data) would spend unaccounted privacy.
- **D = 16.** Fan patterns in AMLworld rarely exceed this degree inside a scheme, while hubs (hundreds of counterparties) are what spread one account's influence. The cap's utility cost is measured directly: the centralised MLP on capped features, and DP capped − uncapped.
- **Group privacy is reported but weak.** For a group of g accounts, (g ε, g e^((g−1)ε) δ) is meaningless beyond a few accounts. The measured group sizes are the informative result: they show how far the account guarantee is from covering an account's whole footprint, and how much the cap closes that gap.

## What I ran here (results)

| Check | Result |
| --- | --- |
| Account bags | At most 8 rows per account; the same bags every time |
| Degree cap (hand-built graph) | A hub keeps its first 3 counterparties in time; pairs within both caps survive; self-transfers kept; every account ends with at most D counterparties |
| Removal | Every leg of a removed account is gone |
| Variants line up | Capped and removal builds pass the row-for-row label check |
| Influence on the fixture (20 removed, cap 3) | Group size median 5 and max 20 without the cap; median 2 and max 4 with it |
| X5 and `dp-tune` on the fixture | All 16 configurations, accounting within target, pages render |
| CI mirror | All steps pass |

At stress scale (SCALE-Tail, 32 M rows):

| Measure | Value |
| --- | --- |
| Degree-capped feature build | About 8 min, peak 2.0 GB; the cap kept 11.2 M of 32 M edges (this synthetic graph is very hub-heavy) |
| Influence (200 removed, two removal rebuilds) | 28 min, peak 3.4 GB |
| Influence: group size without the cap | median 9, p90 67, p99 264, max 393 other same-member training accounts moved by one account |
| Influence: group size with the cap | median 2.5, p90 5, p99 6, max 11 |
| X5, one seed (batch 512) | 36 min, peak 2.6 GB: non-private about 40 s each; DP window unit about 58 s, account unit about 93 s each; scoring 8.4 min (member) and 5.6 min (capped) |

The stress graph is synthetic, so its group sizes only illustrate the method: an uncapped hub moves hundreds of other accounts' training units, the cap brings this to single digits.

Three fixes came from these runs:

- **The degree cap ran out of memory** (6 GB) when ranking every counterparty pair at once. It now works in 16 account-hash partitions and peaks under 0.8 GB.
- **The two-hop neighbourhood ran out of memory** when it built an undirected copy of every edge. It now reads only edges touching the removed accounts, then their neighbours.
- **The tuning grid kept a fixed number of steps.** With an expected batch of 8,192 that is 16 times the compute of 512, which would have put X5 at 6–9 hours per dataset. The grid now gives every setting the same example budget (20 × 512 / batch local steps per round), which is also the fairer comparison. This was fixed before any tuning result.

## What you run on your machine

About 3–4 hours of machine time; steps 2–4 can run unattended in sequence.

### 1. Update and check (5 min)

```bash
cd ~/FinMesh
git pull
uv sync
bash scripts/ci_local.sh
```

### 2. Tune DP on the proxy federations (about 30–60 min each)

```bash
uv run finmesh dp-tune --dataset HI-Small
uv run finmesh dp-tune --dataset LI-Small
```

Writes `docs/eval/dp_tune_<ds>.md` and **`finmesh/schemas/dp_hparams.json`**. Please commit that file: it freezes the choice.

### 3. Capped features and influence (about 30 min per dataset)

```bash
uv run finmesh features --dataset HI-Medium --degree-cap 16
uv run finmesh features --dataset LI-Medium --degree-cap 16
uv run finmesh influence --dataset HI-Medium
uv run finmesh influence --dataset LI-Medium
```

`influence` rebuilds the features twice more (once per view, with the 200 accounts removed) and writes `docs/eval/influence_<ds>.md`.

### 4. X5 (about 1.5–2 hours per dataset with 3 seeds)

```bash
uv run finmesh x5 --dataset HI-Medium
uv run finmesh x5 --dataset LI-Medium
```

Writes `docs/eval/x5_<ds>.md`.

**What to look for:**

- **The chosen clip norm.** Expect well below 1, with most units clipped. A large batch will likely win.
- **H2a with tuned DP.** The window unit at ε = 10 against 0.70 of the centralised MLP.
- **H2b.** The account unit's AUPRC against the window unit's at the same ε.
- **Influence.** The group size without the cap (hubs reach far) against with it.
- **The cap's cost.** The non-private centralised MLP on capped features against uncapped.

### 5. Tests and push

```bash
uv run pytest -m real_data -v
git add docs/eval/ finmesh/schemas/dp_hparams.json
git commit -m "Week 11: DP tuning, influence, X5 on real data"
git push
```

## Troubleshooting

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| `dp-tune runs on the proxy federations only` | A Medium dataset was passed | Tune on HI-Small / LI-Small only |
| `no tuned DP settings for this regime` | Step 2 not done (or the file not pulled) | Run `dp-tune` for the regime |
| `features_..._cap16_v3/meta.json missing` | Capped features not built | `finmesh features --dataset <ds> --degree-cap 16` |
| Out of memory in the capped build | Another heavy process | The build works in 16 partitions; close other programs |

## Week-11 checklist against the plan

- [x] DP settings chosen on a proxy federation, frozen per regime (A18)
- [x] Account unit (bags of at most k windows)
- [x] Degree cap: each account's contribution to neighbour counts clipped, features rebuilt
- [x] Indirect influence measured by recomputing features with accounts removed
- [x] X5: window vs account unit, with and without the cap, ε sweep; H2a (tuned), H2b
- [ ] Done when: tuning, influence and X5 on real data (your steps 2–4)
- Week 12: membership inference on the trained model, the bank-partitioned vs IID arm, the stacked ensemble, Gate G3
