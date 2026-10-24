# Proposal amendments

Changes to `FinMesh_Proposal_v2.md` after it was finalised. Each is made before the results it affects exist, records who decided it, and is marked in the proposal text.

| ID | Date | Section | Change | Reason | Decided by |
| --- | --- | --- | --- | --- | --- |
| A1 | 24 Oct 2026 | 7.1, 9 | Model and evaluate on the dense period only (1–10 Sep 2022). The window is found by a label-free rule: longest run of days with at least 5% of the median daily row count. | Week-1 finding 1: the sparse tail (11–18 Sep) is about 60% laundering because licit traffic has stopped; including it would inflate precision. | Owner, on week-1 findings |
| A2 | 24 Oct 2026 | 7.2 | Rank banks by number of accounts, not transaction volume. | Week-1 finding 4: bank 70 has 15 accounts and 9% of traffic. | Owner, on week-1 findings |
| A3 | 24 Oct 2026 | 7.1 | "Most laundering transactions carry no pattern label" corrected to 38% unlabelled (HI-Small) and 71% (LI-Small). | Week-1 finding 5; factual correction. | Correction |
| A4 | 24 Oct 2026 | 7.2, 7.3 | Federation membership compared across real-bank (top *k*) and grouped-institution options on train and validation schemes only, with a selection rule fixed in code before real numbers exist; test schemes counted only for the chosen option. | Week-1 finding 3: four to eight real banks hold under 4% of accounts. | Rule proposed in week 2; **final choice at Gate G0** |
