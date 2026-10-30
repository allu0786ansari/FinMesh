# Indirect influence of an account · LI-Medium

200 training accounts (half with a laundering row, each half by a fixed hash) are removed and every feature is rebuilt; another account counts as influenced when any of its training rows changes and it lies within two hops of the removed account. **Group size** = 1 + influenced accounts at the same member: the number of account-unit bags one account moves, so the account-unit guarantee including indirect influence is the group guarantee (g ε, g e^((g−1)ε) δ). The capped view keeps at most 16 distinct counterparties per account. Total 708 s.

| Features | Accounts changed (all removals) | Group size, median | p90 | p99 | max | Influenced at any member, median | Rows changed per account, median | Group ε at ε = 1, median | Group ε at ε = 1, max |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| member | 44,430 | 2.00 | 2,234.00 | 3,633.01 | 3,643.00 | 4.00 | 42.50 | 2.00 | 3,643.00 |
| cap16 | 706 | 2.00 | 4.00 | 7.01 | 9.00 | 3.00 | 30.00 | 2.00 | 9.00 |

Formal group bounds grow with g (δ by e^((g−1)ε)), so for g above a few they say little; the measured sizes are what the cap changes.
