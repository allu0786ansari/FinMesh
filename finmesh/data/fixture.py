"""Deterministic synthetic dataset in exact AMLworld file format.

Used by tests, CI and the smoke pipeline so every step can run without the
real data. It is NOT a research dataset: the manifest marks it ``fixture``
and :func:`finmesh.eval.provenance.assert_gate_eligible` refuses anything
built from it.

What it contains, so tests can assert exact numbers:

* six banks, a few hundred accounts, about ten days of licit traffic;
* one or two schemes for each of the eight AMLworld patterns, several of them
  crossing banks, written to both the transactions CSV and the pattern file;
* a handful of laundering transactions that belong to no pattern (as in the
  real data, where most laundering rows carry no pattern label);
* one exact duplicate licit row;
* bank identifiers written zero-padded in the pattern file and plain in the
  CSV, to exercise bank-id normalisation.
"""

from __future__ import annotations

import csv
import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

from finmesh.data.schema import FIXTURE_DATASET, RAW_TRANSACTION_HEADER, dataset_files

BANKS: tuple[int, ...] = (1, 10, 12, 70, 220, 1124)
BANK_WEIGHTS: tuple[int, ...] = (30, 25, 20, 12, 8, 5)
CURRENCIES: tuple[str, ...] = ("US Dollar", "US Dollar", "US Dollar", "Euro", "UK Pound")
FORMATS: tuple[str, ...] = ("ACH", "Cheque", "Credit Card", "Wire", "Cash", "Reinvestment")
START = datetime(2022, 9, 1, 0, 0)
DAYS = 10


@dataclass(frozen=True)
class Account:
    bank: int
    account: str
    entity: str


@dataclass
class Tx:
    when: datetime
    src: Account
    dst: Account
    amount: float
    currency: str
    fmt: str
    laundering: int

    def cells(self, padded_banks: bool = False) -> list[str]:
        def bank(b: int) -> str:
            return f"{b:03d}" if padded_banks else str(b)

        amount = f"{self.amount:.2f}"
        return [
            self.when.strftime("%Y/%m/%d %H:%M"),
            bank(self.src.bank),
            self.src.account,
            bank(self.dst.bank),
            self.dst.account,
            amount,
            self.currency,
            amount,
            self.currency,
            self.fmt,
            str(self.laundering),
        ]


@dataclass
class FixtureTruth:
    """Facts about the generated files that tests assert against."""

    rows: int = 0
    laundering_rows: int = 0
    pattern_rows: int = 0
    schemes: int = 0
    schemes_by_pattern: dict[str, int] = field(default_factory=dict)
    multi_bank_schemes: int = 0
    unlabelled_laundering_rows: int = 0
    duplicate_extra_rows: int = 0
    banks: int = len(BANKS)


def _make_accounts(rng: random.Random, n: int) -> list[Account]:
    accounts: list[Account] = []
    seen: set[tuple[int, str]] = set()
    entity = 0
    while len(accounts) < n:
        entity += 1
        # About one entity in eight holds accounts at two different banks.
        n_banks = 2 if rng.random() < 0.125 else 1
        banks = (
            rng.sample(BANKS, n_banks)
            if n_banks == 2
            else [rng.choices(BANKS, weights=BANK_WEIGHTS)[0]]
        )
        for bank in banks:
            acct = f"{rng.getrandbits(36):09X}"
            if (bank, acct) in seen:
                continue
            seen.add((bank, acct))
            accounts.append(Account(bank=bank, account=acct, entity=f"E{entity:05d}"))
    return accounts


def _licit(rng: random.Random, accounts: list[Account], n: int) -> list[Tx]:
    out = []
    for _ in range(n):
        src, dst = rng.sample(accounts, 2)
        when = START + timedelta(minutes=rng.randrange(DAYS * 24 * 60))
        amount = round(rng.lognormvariate(6.0, 1.6), 2)
        out.append(Tx(when, src, dst, amount, rng.choice(CURRENCIES), rng.choice(FORMATS), 0))
    return out


def _edges(
    pattern: str, rng: random.Random, pool: list[Account]
) -> tuple[list[tuple[Account, Account]], str | None]:
    """Edges of one scheme; ``pool`` holds accounts drawn across several banks."""
    k = rng.randint(3, 5)
    if pattern == "FAN-OUT":
        hub, rest = pool[0], pool[1 : 1 + k]
        return [(hub, t) for t in rest], f"Max {k}-degree Fan-Out"
    if pattern == "FAN-IN":
        hub, rest = pool[0], pool[1 : 1 + k]
        return [(s, hub) for s in rest], f"Max {k}-degree Fan-In"
    if pattern == "GATHER-SCATTER":
        hub, ins, outs = pool[0], pool[1 : 1 + k], pool[1 + k : 1 + 2 * k]
        return [(s, hub) for s in ins] + [(hub, t) for t in outs], f"Max {k}-degree Fan-In"
    if pattern == "SCATTER-GATHER":
        src, sink, mids = pool[0], pool[1], pool[2 : 2 + k]
        return [(src, m) for m in mids] + [(m, sink) for m in mids], None
    if pattern == "CYCLE":
        ring = pool[:k]
        return [(ring[i], ring[(i + 1) % k]) for i in range(k)], f"Max {k} hops"
    if pattern == "RANDOM":
        walk = pool[: k + 1]
        return [(walk[i], walk[i + 1]) for i in range(k)], f"Max {k} hops"
    if pattern == "BIPARTITE":
        left, right = pool[:3], pool[3:6]
        return [(a, b) for a in left for b in right if rng.random() < 0.7] or [
            (left[0], right[0])
        ], None
    if pattern == "STACK":
        a, b, c = pool[:2], pool[2:4], pool[4:6]
        return [(x, y) for x in a for y in b] + [(y, z) for y in b for z in c], None
    raise ValueError(pattern)


def write_fixture(out_dir: Path, seed: int = 7) -> FixtureTruth:
    """Write the three AMLworld-format files for ``FIXTURE-Small`` into ``out_dir``."""
    rng = random.Random(seed)
    out_dir.mkdir(parents=True, exist_ok=True)
    files = dataset_files(FIXTURE_DATASET)
    truth = FixtureTruth()

    accounts = _make_accounts(rng, 360)
    launderers = accounts[:120]
    licit = _licit(rng, accounts, 4000)
    licit.append(Tx(**{**licit[17].__dict__}))  # one exact duplicate row
    truth.duplicate_extra_rows = 1

    schemes: list[tuple[str, str | None, list[Tx]]] = []
    plan = [
        "FAN-OUT",
        "FAN-IN",
        "GATHER-SCATTER",
        "SCATTER-GATHER",
        "CYCLE",
        "RANDOM",
        "BIPARTITE",
        "STACK",
        "FAN-OUT",
        "CYCLE",
        "SCATTER-GATHER",
    ]
    home_bank = [a for a in launderers if a.bank == BANKS[0]]
    for i, pattern in enumerate(plan):
        # The last three schemes stay inside one bank, as many real schemes do.
        single_bank = i >= len(plan) - 3
        pool = rng.sample(home_bank if single_bank else launderers, 12)
        edges, detail = _edges(pattern, rng, pool)
        t0 = START + timedelta(hours=rng.randrange((DAYS - 2) * 24))
        base = round(rng.uniform(2_000, 20_000), 2)
        txs = []
        for i, (src, dst) in enumerate(edges):
            when = t0 + timedelta(minutes=37 * i + rng.randrange(30))
            amount = round(base * rng.uniform(0.85, 1.0), 2)
            txs.append(Tx(when, src, dst, amount, "US Dollar", rng.choice(("ACH", "Wire")), 1))
        schemes.append((pattern, detail, txs))
        truth.schemes_by_pattern[pattern] = truth.schemes_by_pattern.get(pattern, 0) + 1
        banks = {t.src.bank for t in txs} | {t.dst.bank for t in txs}
        truth.multi_bank_schemes += int(len(banks) >= 2)

    unlabelled = []
    for _ in range(15):
        src, dst = rng.sample(launderers, 2)
        when = START + timedelta(minutes=rng.randrange(DAYS * 24 * 60))
        unlabelled.append(
            Tx(when, src, dst, round(rng.uniform(500, 9000), 2), "US Dollar", "Cash", 1)
        )
    truth.unlabelled_laundering_rows = len(unlabelled)

    all_tx = licit + unlabelled + [t for _, _, txs in schemes for t in txs]
    all_tx.sort(key=lambda t: t.when)  # AMLworld files are in time order

    with (out_dir / files.transactions).open("w", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(RAW_TRANSACTION_HEADER)
        for t in all_tx:
            writer.writerow(t.cells())

    with (out_dir / files.patterns).open("w", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        for pattern, detail, txs in schemes:
            head = f"BEGIN LAUNDERING ATTEMPT - {pattern}"
            handle.write(f"{head}:  {detail}\n" if detail else f"{head}\n")
            for t in txs:
                writer.writerow(t.cells(padded_banks=True))
            handle.write(f"END LAUNDERING ATTEMPT - {pattern}\n\n")

    with (out_dir / files.accounts).open("w", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["Bank Name", "Bank ID", "Account Number", "Entity ID", "Entity Name"])
        for a in accounts:
            writer.writerow(
                [f"Bank #{a.bank}", f"{a.bank:03d}", a.account, a.entity, f"Entity {a.entity}"]
            )

    truth.rows = len(all_tx)
    truth.laundering_rows = sum(t.laundering for t in all_tx)
    truth.pattern_rows = sum(len(txs) for _, _, txs in schemes)
    truth.schemes = len(schemes)
    return truth
