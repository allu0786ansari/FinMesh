# Attribution mapping protocol (amendment A20)

Written and frozen before any attribution (X6) result exists. Proposal section 7.4 asks for two review passes: **pass 1** by the researcher (31 Oct 2026), **pass 2** by the owner, recorded below before the week-13 real-data run.

## Labels

- **Candidate typologies:** the eight AMLworld patterns, one catalogue entry each (`finmesh/schemas/typology_catalogue.json`): FAN-OUT, FAN-IN, GATHER-SCATTER, SCATTER-GATHER, CYCLE, RANDOM, BIPARTITE, STACK.
- **Ground truth:** a scheme's pattern comes from the AMLworld pattern file (`schemes.parquet`, column `pattern`). No other label source is used, and no description text ever becomes a label.
- **Stages:** every entry maps to **layering**. AMLworld patterns are transfer structures between accounts; placement (cash entering the system) and integration (funds returning as legitimate) are not modelled by the generator. The stage distribution is therefore degenerate, and stage-level accuracy is **not reported**, as the proposal anticipated ("reported only if the stage distribution is not degenerate").

## Unit and evidence

- **Unit:** one pattern-labelled validation scheme. It is attributed through the incident holding most of its alerted accounts within 72 h of its first window; ties go to more rows, then the lower incident id.
- **Owner:** the member with most of the incident's rows (ties: the lower member id). The owner is the bank whose analyst attributes the case.
- **What the owner knows at each level:**

| Level | Evidence available to the attributor |
| --- | --- |
| S0 | Own account-windows only: mean and max of every member-view feature; own accounts, rows, span |
| S1 | S0 + the incident's cross-member structure from tokens and flags: accounts, members, rows, span |
| S2 | S1 + other members' evidence-record counters (10 bucketed fields, mean and max) |
| S3 (ε = 2) | S1 + the same counters through k-ary randomised response at ε/20 per field |
| Oracle | Pooled-view features (full graph) of every row: the attribution ceiling |

## Attributor and baselines

- **Attributor:** multinomial LightGBM (200 trees, learning rate 0.05, 15 leaves, at least 5 rows per leaf, balanced class weights), cross-fitted on the two time halves of validation (by scheme first window).
- **Majority:** the most frequent pattern in the training half.
- **Rule-based shape detector:** the catalogue's fixed decision list over the shape signature (below).
- **Catalogue matching:** z-score the incident's shape signature with the training half's mean and spread; pick the entry whose signature (+1 / 0 / −1 per shape feature) has the highest cosine similarity. Text-embedding retrieval is not used, because incident evidence is numeric.

**Shape signature** (from the information available at the level):

| Shape feature | Computed as |
| --- | --- |
| fan_in, fan_out | Max of `fan_in`, `fan_out` over the rows the level can see |
| gather_scatter | Max of `gs_min_fan` |
| cycles | Max of `cyc2`, `cyc3`, `cyc4` |
| scatter_gather | Max of `sg_out_max`, `sg_in_max` |
| pass_through | Mean of `pass_through` |
| accounts, members | Accounts and members in the incident visible at the level |

At S0–S3 the shape signature uses the owner's own features (records carry only bucketed counters, not the neighbourhood counts). At the oracle it uses pooled features of every row.

## Metrics

- **Primary:** end-to-end pattern accuracy over all pattern-labelled schemes (undetected = wrong).
- **Secondary:** accuracy and macro-F1 on detected schemes; per-pattern recall.
- Per-scheme correctness is averaged over seeds 0–2; 95% intervals from a 1,000-replicate scheme bootstrap, paired for differences.
- **H3a holds on validation** when S2 − S0 attributor accuracy has a CI above 0 and S2's attributor beats the majority and rule baselines with CIs above 0. Test decides.

## Review

| Pass | By | Date | Notes |
| --- | --- | --- | --- |
| 1 | Researcher | 31 Oct 2026 | Catalogue, stage mapping, shape signatures and rules written from the AMLworld pattern definitions |
| 2 | Owner | _before the week-13 run_ | agreed |
