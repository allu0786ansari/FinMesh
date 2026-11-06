# Review of the A23 narratives by an LLM judge · HI-Medium (validation, 30 cases)

**This is not a human review.** The owner and the second rater are students without anti-money-laundering expertise, and no banking analyst was available. On 6 Nov the owner asked Claude (Opus 5.5) to rate the 30-case sheet in place of the planned human raters. The ratings are in `narrative_HI-Medium_A23_review_claude.csv`. Every claim was checked against the evidence column only, with the rubric of the sheet, and the key was opened only after all 30 rows were rated.

**Limits, to state with any use of these numbers:**

- There is one rater, so there is no inter-rater agreement.
- The judge is not blind to the source: the template's fixed wording ("The linked case holds…") is recognisable.
- The judge wrote the template and the automatic claim rules, so its view is not independent of the checker it is compared with.
- Usefulness is judged without domain expertise. Here 1 means no help (sizes only, repetitive or wrong), 2 a correct factual summary, and 3 a correct summary that points to the decisive signal.

## Ratings

| Text | Faithful: yes | Partly | No | Useful (mean, 1–3) |
| --- | --- | --- | --- | --- |
| Delivered model text (27 written by the model, 3 template fallbacks) | 33% (10 of 30) | 0% | 67% (20 of 30) | 1.20 |
| Template | 100% | 0% | 0% | 2.00 |

Preferred: template 26, model 1, same 3 (the 3 cases where the model's text had fallen back to the template).

Excluding the 3 fallbacks, **7 of the 27 texts the model wrote are faithful (26%)**: 7 of 23 retries and 0 of 4 first replies.

## The automatic claim check against this judge

The A23 claim check accepted all 30 delivered texts as consistent. The judge rated 10 faithful: agreement 33%, Cohen's kappa 0.00.

**Why they disagree:**

- **Own bank vs whole case (12 of the 20 failures):** the model gives counts of the linked case as if they were at the analyst's own bank ("two case accounts at the bank" when one is).
- **Flows the evidence denies (4):** the account "received" money when it has no payers, or a second payer appears.
- **Other banks' figures attributed to the case (2).**
- **Invented structure (2):** intermediates or a relay chain that the fan sizes and pass-through deny.

The A23 rules cover typology-style claims (pass-through, many payers or payees, cycles, gathering, splitting, layering). They do not check counts attributed to the wrong scope, so "delivered text 100% claim-consistent" measures the rules, not faithfulness.

## Reading for the paper

The small local model (llama3.2:3b) does not produce faithful case narratives, even after the strict check and retry. In this sample the fixed template is both faithful and preferred. Report H3b (raw grounding 0.86 on HI-Medium test) together with this judgement, and do not claim that delivered text is faithful on the strength of the claim check. A scope check (own bank vs linked case vs other members) is the obvious next rule, but adding it now would be post hoc; it belongs in future work.
