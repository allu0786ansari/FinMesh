# Thin demo slice · LI-Medium

One bank node, one alert, one evidence request, one attribution, end to end (proposal section 13). Setup (detectors, evidence stores, token indexes) is not timed: 81 s. Each session runs: counterparties at other members → tokens through the token service → signed S2 requests answered by the responders' nodes → noisy-OR fusion → rule-based typology (placeholder until weeks 13–14) → incident card and ledger entry. Token budget 87,580 per bank and epoch.

**Latency over 50 sessions:** p50 0.004 s, p95 0.011 s, max 0.031 s. PT6 (p95 ≤ 3 s): **met**.

Typologies (placeholder rules): {'cycle': 8, 'fan-in': 8, 'unknown': 34}. Actions: {'open case': 11, 'monitor': 39}. Ledger entries: 50.

## Example incident card

```json
{
  "member": 0,
  "account": 5409904459517881008,
  "window": 42,
  "own_probability": 0.0479,
  "counterparties_asked": 13,
  "requests": 13,
  "refused": 0,
  "peer_alerts": 0,
  "peer_records": 1,
  "fused_score": 0.0765,
  "typology": "fan-in",
  "typology_reason": "14 payers into one account",
  "action": "monitor"
}
```

The card names only the member's own account-window; counterparties at other members appear as counts.
