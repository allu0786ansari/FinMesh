# Review of the A25N narratives by an LLM judge · HI-Medium (validation, same 30 cases as A23r)

**This is not a human review**, as in A23r. Claude (Opus 5.5) rated the same 30-case sheet for every P5 candidate on 7 Nov, after the selection rule had been applied (the ratings are reported; they are not part of the rule). Every claim was checked against the evidence column only. Ratings: `narrative_judge_A25N.csv`.

Rubric:
- **Faithful:** *yes* means every statement follows from the evidence.
- *Partly* means vague or understated, without a statement the evidence contradicts.
- *No* means at least one statement the evidence contradicts. That includes a figure given for the wrong scope (your bank, the linked case, other members) and structure the evidence does not show.
- Template fallbacks and N4 texts restate the evidence lines and are faithful by construction. The judge checked that each N4 text only restates evidence lines.

**Limits**, as in A23r:
- There is one rater, so there is no agreement measure.
- The judge is not blind: template wording is recognisable.
- The judge wrote the templates and the automatic checks.
- Usefulness was not rated this time.

## Ratings

| Candidate | Texts the model wrote (of 30) | Faithful among them: yes / partly / no | Delivered text faithful (of 30) |
| --- | --- | --- | --- |
| N0 `llama3.2:3b` | 18 | 9 / 3 / 6 (50%) | 21 (70%) |
| N1 `qwen2.5:7b` | 11 | 7 / 1 / 3 (64%) | 26 (87%) |
| N2 `llama3.1:8b` | 14 | 13 / 0 / 1 (93%) | 29 (97%) |
| N3 `qwen3:8b` | 20 | 13 / 3 / 4 (65%) | 23 (77%) |
| **N4 on N3 (chosen)** | 0 (templates from the model's selection) | — | **30 (100%)** |
| Week 18, A23, `llama3.2:3b` (A23r) | 27 | 7 / 0 / 20 (26%) | 10 (33%) |

## Reading

1. **The scope rule worked.** In A23r, the same model on the same cases had 26% of its own texts faithful. With A25N, 50% are, because the scope rule sends most own-bank vs linked-case confusions to the retry or the template. Delivered faithfulness rose from 33% to 70%.
2. **The automatic checks are conservative, not equal to faithfulness.** `llama3.1:8b` had the lowest strict grounding (0.055), yet its texts were the most faithful (13 of 14). It fails the checks mainly by citing more than four fields, not by saying false things.
3. **The remaining errors are flows and structure.** Examples: payers and payees swapped, money "passed on" when under half was, a case "linked to another case", and other members' figures for the wrong scope. These are the kinds the A23 claim rules and the scope rule do not fully cover.
4. **N4, the chosen design, is faithful on all 30 cases**, as its construction implies. The model only selects up to four evidence fields; fixed templates word them.

For the paper: report H3b and strict grounding on the Large test (the rule), together with this judge's validation ratings and their limits. Do not present the automatic checks as a measure of faithfulness.
