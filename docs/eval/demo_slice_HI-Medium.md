# Thin demo slice · HI-Medium

One bank node, one alert, one evidence request, one attribution, end to end (proposal section 13). Setup (detectors, evidence stores, token indexes) is not timed: 106 s. Each session runs: counterparties at other members → tokens through the token service → signed S2 requests answered by the responders' nodes → noisy-OR fusion → rule-based typology (placeholder until weeks 13–14) → incident card and ledger entry. Token budget 74,510 per bank and epoch.

**Latency over 50 sessions:** p50 0.006 s, p95 0.023 s, max 0.121 s. PT6 (p95 ≤ 3 s): **met**.

Typologies (placeholder rules): {'cycle': 7, 'unknown': 41, 'pass-through': 2}. Actions: {'monitor': 11, 'open case': 39}. Ledger entries: 50.

## Example incident card

```json
{
  "member": 0,
  "account": 7370143027392186960,
  "window": 48,
  "own_probability": 0.1178,
  "counterparties_asked": 2,
  "requests": 2,
  "refused": 0,
  "peer_alerts": 0,
  "peer_records": 2,
  "fused_score": 0.1699,
  "typology": "unknown",
  "typology_reason": "no rule fired",
  "action": "monitor"
}
```

The card names only the member's own account-window; counterparties at other members appear as counts.
