# Weekly status log

Newest week first. Template:

```markdown
## Week NN · <dates>

Planned: <the week's goal line>
Done: <ticked items, with artifact paths>
Not done: <items and why>
Numbers this week: <key validation results, with intervals>
Risks or blockers: <what could slip, and which fallback applies>
Next week: <first two tasks>
On track for next gate? yes / at risk / no
```

## Week 12 · 11 – 17 Jan 2027

Planned: membership inference on the trained model, the IID arm of X5, the stacked ensemble, Gate G3.
Done: week 11 reviewed. A18 picked its own corner (clip 1, batch 512 = the A17 defaults): AUPRC still rose at the largest clip, and the fixed example budget gave batch 8,192 only 50 updates, so the batch comparison measured training length. H2a fails (HI 0.49, LI 0.38 of centralised at ε = 10); H2b not supported (the account unit is as good or better except HI at ε = 1). The degree cap cuts the worst-case group size from about 3,500 to about 10 accounts and helps under DP on HI. The owner chose to retune inside week 12 and to deploy the account unit + cap. A19 pre-registered and pushed before any code (`9997684`). Built: the A19 grid (clip × batch × lr at equal updates), the X5 IID arm with saved models, the membership audit on the federated model, the stacked ensemble, the G3 evidence page and rule, and a one-shot resumable runner. Details in `docs/runlog/week-12.md`.
Done on real data (owner, 30–31 Oct, all steps passed): A19 retune lifted proxy AUPRC at ε = 3 from 0.42 to 0.65 (HI) and 0.15 to 0.30 (LI), mainly through the learning rate; X5 window DP at ε = 10 now 0.78 (HI) and 0.96 (LI) of centralised; H2a and H2b hold on LI, not on HI; membership attacks at chance even for the non-private model; the DP scorer adds nothing to the local ensemble on HI. **G3 passed** (`docs/gates/G3.md`): detector stays local, DP scorer reported as a finding.
Numbers this week: see `docs/gates/G3_evidence.md`.
Risks or blockers: the retune may land on the grid's edge again (reported, not extended); if the DP scorer adds nothing to the local ensemble, the deployed detector stays local (G3 rule).
Next week: write G3 from your run; then week 13, attribution (typology catalogue, supervised attributor, baselines).
On track for next gate? yes (G3 this week, on your run).

## Week 11 · 4 – 10 Jan 2027

Planned: account unit, degree cap, indirect influence, X5.
Done: week 10 reviewed. The non-private MLP is close to the GBDT (HI 0.310 vs 0.337; LI 0.087 vs 0.085) and FedAvg beats local-only, but DP-SGD collapsed (HI ε = 10: 0.153) because the a-priori clip norm was far above the gradients (3% clipped). The owner chose to tune DP on the Small federations as public proxy data (A18). Built: `dp-tune` (15-setting grid, frozen per regime), the account unit (bags of 8), degree-capped features (D = 16, partitioned to bound memory), the indirect-influence measurement by feature recomputation with 200 accounts removed, and X5 (units × cap × ε, H2a tuned, H2b). Details in `docs/runlog/week-11.md`.
Not done: tuning, influence and X5 on real data (run-log steps 2–4).
Numbers this week: engineering only. Stress: capped build 8 min and 2.0 GB after partitioning (was out of memory); influence 28 min and 3.4 GB (group size median 9, max 393 uncapped; median 2.5, max 11 capped, synthetic graph); X5 36 min per seed at 2.6 GB; the tuning grid now gives every setting the same example budget.
Risks or blockers: the proxy-tuned settings may transfer imperfectly to the Medium sets; the cap may remove fan patterns the detector needs.
Next week: week 12, membership inference on the trained model, the IID arm, the stacked ensemble, Gate G3.
On track for next gate? yes (G3, week 12).

## Week 10 · 28 Dec 2026 – 3 Jan 2027

Planned: Gate G2 decision; the federated DP neural scorer, window unit, ε sweep, X4 on validation.
Done: G2 passed (`docs/gates/G2.md`): H1a and H1b hold on both datasets; H1c fails on validation for two identified reasons (S1's flags leak fan-in on LI; one rare target's upper bound on HI), with no further amendment recommended; PT2 holds on HI (11.0×), fails on LI (7.8×). The owner chose a NumPy DP-SGD stack (A17): fixed piecewise-linear encoding (no privacy cost for normalisation), MLP without batch normalisation, exact per-unit clipping, dp-accounting RDP accountant with persistence and a budget guard, privacy ledger, in-process FedAvg; X4 part 1 (centralised, local, FedAvg, FedAvg + DP at ε 1, 3, 10, GBDT reference). Details in `docs/runlog/week-10.md`.
Not done: real-data X4 part 1 (run-log step 3).
Numbers this week: synthetic DP check, AUPRC 0.99 non-private, 0.98 / 0.97 / 0.87 at ε 10 / 3 / 1; stress: 13 min per seed, 2.3 GB; scoring all models in one pass halved the scoring time.
Risks or blockers: the MLP may trail the GBDT (expected in the risk register); fixed clip norm and learning rate may be far from good under DP on the real class balance.
Next week: week 11, the account unit, the degree cap and the indirect-influence measurement.
On track for next gate? yes (G3, week 12).

## Week 09 · 21 – 27 Dec 2026

Planned: attacks A4–A6, Gate G2 evidence and the thin demo slice.
Done: week 8 reviewed. H1b holds against the relational oracle (S2 recovers 0.98 on HI-Medium, 0.83 on LI-Medium; 0.78 against the stronger pooled configuration on LI). S3 and PD cost almost no detection; S1 alone gets 0.94–0.98 of S2's gain. Two problems surfaced: S3 answered "no record" in the clear, so its leakage did not fall with ε; and the 250,000 token budget made the OPRF only 2× safer than hashing. The owner chose to fix S3 and to size budgets to twice the legitimate peak (A16). A4 found a second S3 flaw (memo per record links across rotations), fixed by memoising per record and epoch. Built: A4–A6, the G2 evidence page, the thin demo slice. Details in `docs/runlog/week-09.md`.
Not done: real-data rerun of X1–X3 with A1–A6, demo slice and G2 evidence (run-log steps 2–5); G2 decision note.
Numbers this week: week-8 validation as above; stress scale (32 M rows, one seed): 119 min for everything; S3 releases vectorised (376 → 15 µs) and responses chunked with 16-bit records (S3 phase 5.4 → 2.8 GB); A4 confirms S3 is at chance after the fix.
Risks or blockers: PT2 is likely to fail on LI-Medium (7.8× at the sized budget). S1's flags leak fan-in beyond the margin on LI-Medium, so H1c may fail at test for S1 itself. Both are findings, reported either way.
Next week: week 10, the federated DP neural scorer (G3 track), after the G2 note.
On track for next gate? yes (G2 evidence pending the owner's run).

## Week 08 · 14 – 20 Dec 2026

Planned: S3 (local DP), progressive disclosure, the X3 curves and the leakage audit A1–A3.
Done: week 7 reviewed. Every sharing level and plaintext propagation beat the preregistered oracle in linked detection on validation (HI-Medium S2 0.736, oracle 0.672), so H1b would pass trivially. The owner chose a relational oracle as the ceiling (A14). S2 adds little over S1 (+0.009 HI, +0.032 LI); S4 is slightly below S2. Built: the relational oracle; S3 (k-RR per field, memoised releases, per-account ε cap 8) and PD (τ on the requester bucket); X3 sweeps; attacks A1–A3 with a strong adversary and prior-only baselines; the utility–leakage frontier. S3, PD and attack specifications, and the H1c margin (0.05), were fixed before results as A15. Token work is shared across levels within a seed. Details in `docs/runlog/week-08.md`.
Not done: real-data X1–X3 and audit (run-log step 3); owner confirmation of A15.
Numbers this week: engineering only. Stress scale (32 M rows, one seed): 86 min for 25 configurations, 11 protocol runs and the audit; peak 4.1 GB, cut by streaming A1 per adversary; token reuse saves about 40% per later level.
Risks or blockers: A1 may show that the deployed token budget (250,000 per epoch) does not limit re-identification when candidate lists are smaller; the sized budget and query logging are then the protection, which week 9 should state plainly. If S1 is nearly as useful as S2, H1d is uninformative, and the frontier's best operating point may be S1 or PD.
Next week: week 9, attacks A4–A6, Gate G2 evidence and the thin demo slice.
On track for next gate? yes (G2, week 9).

## Week 07 · 7 – 13 Dec 2026

Planned: fusion and triage, S4, plaintext propagation, X1 on validation and the first frontier.
Done: week 6 reviewed (S1 reaches the pooled-linking bound: 0.604 linked on HI-Medium, 0.85 of the oracle gain; 0.68 on LI-Medium; no token refusals). Fusion rule fixed before results as amendment A13: candidates (probability ≥ 0.01 or alerted) ask before alerting; a per-member logistic stacker cross-fitted on validation halves re-ranks each queue; noisy-OR and k-of-n secondary; pooled linking at S1+. S4 records with autoencoder embeddings; inbound-request tracking; plaintext propagation; `finmesh x1` with seeds, scheme bootstrap, paired gains, H1b recovery and the frontier figure. Details in `docs/runlog/week-07.md`.
Not done: real-data X1 on HI-Medium and LI-Medium (run-log step 3); owner confirmation of A13.
Numbers this week: engineering only. Stress scale (32 M rows, one seed): 2,472 s, peak 3.6 GB (first attempt 4.3 GB), 1.49 M requests per level, no token refusals, 0.12% rate-limited.
Risks or blockers: if S2 does not beat S1 on validation, H1b rests on S1-level evidence; week 8's S3 noise would then cost little, which is itself a finding.
Next week: week 8, S3 (randomised response on records) and the leakage audit A1–A3.
On track for next gate? yes.

## Week 06 · 30 Nov – 6 Dec 2026

Planned: banks can match accounts through OPRF tokens and exchange S1 and S2 evidence in the harness.
Done: closed G1 (preregistration frozen; A12 ablation and decomposition added to the baselines runner). Built the token service (per-epoch keys, budgets, count-only log), token client, shared-key hashing control, CC5 contract tests, local autoencoder with top-3 deviations, evidence schema and records, signed one-time requests with rate limits and retention, allowlisted messages and bus, S0/S1/S2 responses, and the in-process protocol run (`finmesh share`). Details in `docs/runlog/week-06.md`.
Not done: real-data protocol run (run-log steps 2–4); the `g1` tag must be pushed from the owner's machine.
Numbers this week: engineering only (hand-built cases, fixture, stress run).
Risks or blockers: S1 should approach the pooled-linking upper bound; if not, the epoch split or the rate limits lose links.
Next week: week 7, fusion, triage, S4 and the first validation frontier.
On track for next gate? yes (G2, week 9).

## Week 05 · 23 – 29 Nov 2026

Planned: the local-only (S0) and pooled-oracle reference points exist, and targets are frozen.
Done: reviewed the week-4 diagnostics; the owner decided A9 (mask incidental positives), A10 (primary operating point 1 alert per 1,000 accounts per day) and A11 (schema v3, 72 h neighbourhood lookback). Built labels with incidental masking, the pooled feature view for the oracle, local and pooled incident linking, a random baseline for linked detection, LightGBM, Isolation Forest and PCA baselines with isotonic calibration, the baselines runner and the G1 evidence page. Drafted the preregistration. Details in `docs/runlog/week-05.md`.
Not done: real-data baselines and G1 evidence (run-log steps 2–6); preregistration section 9 and the `g1` tag follow.
Numbers this week: engineering only (stress set). Member-view features 1,393 s at 3.0 GB; neighbourhood pass made about 1.5x faster, still exact.
Risks or blockers: if the oracle − S0 gap is under 5 points, RQ1's headline needs rethinking before week 6.
Next week: week 6, the evidence-sharing levels.
On track for next gate? yes, pending the G1 run.

G1 (26 Oct, real data): passed. HI-Medium oracle − S0 linked detection 0.508 [0.465, 0.550]; LI-Medium 0.538. The gain is almost all cross-member linking (any-alert detection S0 0.864, oracle 0.886). PT4b direction positive. Thresholds unchanged; artefact ablation and linking decomposition added (A12); preregistration frozen, tag `g1`.

## Week 04 · 16 – 22 Nov 2026

Planned: every account-window at every bank has its behaviour and graph features, within the memory budget.
Done: reviewed the week-3 real-data results (G0 closed on HI-Medium with 480 test schemes; harness calibrated; findings on FPR-budget drift, activity as a top-only signal, scheme coverage, probe grounding). Froze feature schema v1: 47 features (19 behaviour, 12 graph, 5 history, 11 neighbourhood). Built the edge table with data-derived exchange rates, account features in hash slices, member-view neighbourhood features (cycles 2–4, scatter-gather, hub indicators) over a 24 h lookback, and a single-feature report as a leakage smoke test. Label files are now sorted to line up with features. Details in `docs/runlog/week-04.md`.
Not done: real-data build (run-log steps 2–5).
Numbers this week: engineering only. On a 32 M-row heavy-tailed stress set (41 M account-windows): whole build 622 s, peak 2.0 GB (first attempt 5.9 GB; fixed). Feature report 101 s, 1.0 GB.
Risks or blockers: FPR budgets drift between periods; primary operating point to be decided at G1 (recommendation: alerts per 1,000 accounts per day).
Next week: week 5, local and pooled baselines, preregistration, Gate G1.
On track for next gate? yes (G1, week 5).

Follow-up (25 Oct, after the real-data run): history features drifted by construction; replaced by schema v2 before any model (amendment A8). Added `finmesh diagnose`: incidental positives (busy accounts touched once by a scheme), pattern visibility per member, feature drift. Two G1 decisions now pending the diagnostics: primary operating point and the treatment of incidental positives.

## Week 03 · 9 – 15 Nov 2026

Planned: a harness that can score any detector at any budget, with test data locked away.
Done: G0 decided from the week-2 evidence (`docs/gates/G0.md`): headline on HI-Medium with B8 (amendments A5, A6); a bias in my week-2 selection rule found and disclosed; H3b redefined (A7); llama3.2:3b chosen. Built account-window labels with masking, frozen split plans, sealed test entry point with access log, label guard (types plus static check), metrics, per-member budgets with deterministic tie-breaking, scheme detection and linked detection, exact random-alert baseline, bootstrap and Holm. Details in `docs/runlog/week-03.md`.
Not done: real-data run (G0 under A5, labels, harness check, free LLM probe; run-log steps 2–7).
Numbers this week: engineering only. At HI-Medium scale: labels 111 s and 1.3 GB, harness check 163 s and 2.4 GB; random scorer AUPRC 0.001158 against prevalence 0.001164, budgets met per member.
Risks or blockers: none new. HI-Medium account-windows (about 24 M) will need negative subsampling for training (week 5).
Next week: week 4, the graph feature extractor on member views.
On track for next gate? yes (G1, week 5).

## Week 02 · 2 – 8 Nov 2026

Planned: the bank federation is chosen, splits are drafted, and the go/no-go count is known.
Done: CI fixed (lint failure from a week-1 edit) and a local CI mirror added; observation window (dense-period rule, amendment A1), 6 h window rule, 60/20/20 splits with gaps, scheme assignment and masking; visibility model; federation options A (real banks ranked by accounts, amendment A2) and B (grouped institutions); G0 evidence with a selection rule fixed before real numbers; memory-safe data layer for HI-Medium; RFC 9497 OPRF matching Cloudflare's implementation; feature-timing spike; local LLM probe. Details in `docs/runlog/week-02.md`.
Not done: real-data G0 counts, feature timing and LLM probe (owner's machine, run-log steps 3–9); G0 decision note.
Numbers this week: engineering only. At HI-Medium size (32 M synthetic rows): ingest 929 MB (was 5.3 GB), G0 1.2 GB in 78 s. 52 unit tests, coverage 90.5%.
Risks or blockers: G0 likely lands in the case-study or fallback band on the Small sets (week-1 estimate); HI-Medium is ready as the fallback. WSL may have only about 4 GB of RAM; every step now stays under 1.3 GB.
Next week: write the G0 decision from the pushed evidence; then week 3 (sealed test entry point, label guard, metrics, alert budgets, random-alert baseline, bootstrap).
On track for next gate? yes for the gate itself; the RQ1 band is at risk.

## Week 01 · 26 Oct – 1 Nov 2026

Planned: a clean repository with CI, and both datasets loaded, hashed and profiled.
Done: repository layout and tooling; CI with secret scan; transaction loader, pattern parser and scheme linking, accounts loader, SHA-256 manifest, provenance stamps with the fixture gate guard; synthetic fixture; data profile; CLI; scale check; data card, literature matrix, venues note. Details in `docs/runlog/week-01.md`.
Done on real data (24 Oct, owner's machine): HI-Small and LI-Small ingested and profiled; row counts, laundering rates and scheme counts match the published values exactly; all 4,232 pattern lines linked, none ambiguous; peak memory 3.6 GB.
Not done: dataset licence variant; code licence; venue deadlines (no 2027 calls published yet).
Numbers this week: HI-Small 5,078,345 rows, 5,177 laundering, 370 schemes (366 multi-bank), 62% of laundering rows pattern-labelled; LI-Small 6,924,049 rows, 3,565 laundering, 117 schemes, 29% labelled. Dense period 1–10 Sep plus a sparse, about 60%-laundering tail to 17–18 Sep.
Risks or blockers: G0 is at risk. Roughly 70 (HI) and 23 (LI) test schemes exist across all banks, before restricting to federation members; a 4–8 real-bank federation would hold under 4% of accounts. Fallbacks: grouped-institution federation, HI-Medium. See findings in `docs/runlog/week-01.md`.
Next week: visibility model and per-bank views; G0 counts for federation options A, B and C on train and validation schemes; chunked ingestion for HI-Medium.
On track for next gate? at risk; the G0 decision rule already covers this case.
