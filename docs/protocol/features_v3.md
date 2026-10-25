# Feature schema v3

Generated from `finmesh/schemas/features_v3.json` (SHA-256 `550f9243bb6881be`); the JSON file is authoritative.

**Changes from v2:** Neighbourhood lookback 72 h (from 24 h), the same span as the history features, so every feature depends only on the current window and the previous 72 h (amendment A11). Week-4 diagnostics on HI-Medium: median scheme durations 22-52 h, only 31-51% of schemes within 24 h; cycle signatures fired on 19% of cycle schemes and scatter-gather on 2%, which would have confounded the visibility gap with the lookback. Names, order and every other definition are unchanged from v2.

**Unit:** account-window: one account held at a federation member, in one window, with at least one transaction. **Keys:** `member` (federation member holding the account), `account` (64-bit hash of the <bank>:<account> key), `window` (zero-based window number since the observation start).

## Parameters

- `lookback_hours`: 72
- `history_hours`: 72
- `hub_degree_cap`: 64
- `delay_tolerance_hours`: 24
- `reference_currency`: US Dollar
- `rate_source`: median amount_received / amount_paid per currency pair on train-partition rows, chained to the reference currency

## Conventions

- Every feature is computed from the holding member's own view (finmesh.data.visibility): rows in which one of its accounts sends or receives.
- A leg is one side of a transaction for the account: outbound (it pays) or inbound (it is paid). A self-transfer has the same account on both sides; it counts in self_tx and in history totals and is excluded from every counterparty or graph feature.
- Amounts are converted to the reference currency with data-derived rates; legs in a currency with no rate count in unconvertible_share and are left out of amount sums.
- History features (and new counterparties) depend only on the previous history_hours, so they mean the same in every period once history_hours have passed since the observation start; earlier windows are a training burn-in (meta: history_complete_from_window).
- Neighbourhood features use the member's visible graph over the lookback (the current window and the earlier ones within lookback_hours): distinct directed account pairs, timing ignored inside the lookback. Intermediate accounts in 2-paths must have visible degree at most hub_degree_cap.
- Shares and ratios are null when their denominator is empty; counts and sums are 0.

## Behaviour

| Feature | Type | Definition |
| --- | --- | --- |
| `tx_out` | u32 | outbound legs, excluding self-transfers |
| `tx_in` | u32 | inbound legs, excluding self-transfers |
| `self_tx` | u32 | self-transfers |
| `amt_out` | f32 | sum of outbound amounts (reference currency) |
| `amt_in` | f32 | sum of inbound amounts (reference currency) |
| `amt_out_max` | f32 | largest outbound amount; 0 when none |
| `amt_in_max` | f32 | largest inbound amount; 0 when none |
| `amt_net` | f32 | amt_in - amt_out |
| `active_span_h` | f32 | hours between the first and the last leg in the window |
| `currencies_n` | u32 | distinct currencies on the account's own side of its legs |
| `cross_currency_share` | f32 | share of legs whose payment and receiving currencies differ |
| `unconvertible_share` | f32 | share of legs whose amount has no reference-currency rate |
| `fmt_ach_share` | f32 | share of legs paid by ACH |
| `fmt_bitcoin_share` | f32 | share of legs paid in Bitcoin |
| `fmt_cash_share` | f32 | share of legs paid in cash |
| `fmt_cheque_share` | f32 | share of legs paid by cheque |
| `fmt_credit_card_share` | f32 | share of legs paid by credit card |
| `fmt_reinvestment_share` | f32 | share of legs that are reinvestments |
| `fmt_wire_share` | f32 | share of legs paid by wire |

## Graph

| Feature | Type | Definition |
| --- | --- | --- |
| `fan_out` | u32 | distinct counterparties paid |
| `fan_in` | u32 | distinct counterparties paying in |
| `out_amount_hhi` | f32 | Herfindahl index of outbound amounts across counterparties (1 = one counterparty) |
| `in_amount_hhi` | f32 | Herfindahl index of inbound amounts across counterparties |
| `pass_through` | f32 | min(amt_in, amt_out) / max(amt_in, amt_out) |
| `in_out_delay_min_h` | f32 | over outbound legs in the window: shortest time since the latest earlier inbound leg (within delay_tolerance_hours), in hours |
| `in_out_delay_med_h` | f32 | median of the same delays |
| `cross_bank_share` | f32 | share of legs whose counterparty is at another bank |
| `cross_member_share` | f32 | share of legs whose counterparty is at another federation member |
| `outside_share` | f32 | share of legs whose counterparty bank is outside the federation |
| `new_cp_n` | u32 | counterparties in this window not seen by the account in the previous history_hours |
| `new_cp_share` | f32 | new_cp_n / distinct counterparties in the window |

## History

| Feature | Type | Definition |
| --- | --- | --- |
| `recency_windows` | u32 | windows since the account's previous active window; history window + 1 when there is none within history_hours |
| `prior_active_windows` | u32 | windows within the previous history_hours in which the account had a leg |
| `prior_leg_rate` | f32 | legs per window over the previous history_hours (legs in that span / its length in windows) |
| `legs_vs_history` | f32 | log1p(legs in this window) - log1p(prior_leg_rate) |
| `amt_vs_history` | f32 | log1p(amt_in + amt_out) - log1p(amount per window over the previous history_hours) |

## Neighbourhood

| Feature | Type | Definition |
| --- | --- | --- |
| `nb_out_deg` | u32 | distinct accounts paid over the lookback |
| `nb_in_deg` | u32 | distinct accounts paying in over the lookback |
| `gs_min_fan` | u32 | min(nb_in_deg, nb_out_deg): gather-scatter hub indicator |
| `cyc2` | u32 | visible 2-cycles a->b->a through the account |
| `cyc3` | u32 | visible simple 3-cycles a->b->c->a through the account (b within the hub cap) |
| `cyc4` | u32 | visible simple 4-cycles a->b->c->d->a through the account (b and d within the hub cap) |
| `sg_out_max` | u32 | max over accounts c of distinct b with a->b->c: scatter-gather source indicator |
| `sg_in_max` | u32 | max over accounts c of distinct b with c->b->a: scatter-gather sink indicator |
| `cp_in_deg_max` | u32 | largest visible in-degree among accounts the account paid: feeder of a gather hub |
| `cp_out_deg_max` | u32 | largest visible out-degree among accounts that paid the account: receiver from a scatter hub |
| `hub_neighbours` | u32 | neighbours over the lookback whose visible degree exceeds the hub cap |
