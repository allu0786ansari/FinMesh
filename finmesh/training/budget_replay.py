"""A25 P4: replay of the adaptive token budget on recorded legitimate token use.

Rule (fixed in the A25 plan): each bank's budget for an epoch is ``factor`` (2) times its
largest legitimate use in the previous epoch; the first epoch, and any epoch without a
previous one, uses the A16 value, which is also a floor. An optional ``cap`` is reported
alongside (see the ratchet below); the rule as signed has none.

Inputs are label-free: the token service's per-bank, per-epoch use, recorded at test in
the X1 checkpoints (``token_use``) and on validation (``token_use_val`` in runs made after
this module, or recomputed from the validation phase alone). An epoch that straddles the
validation/test boundary counts both partitions' use (an upper bound: the two services did
not share caches).

Reported:

- the share of legitimate token requests the rule would refuse, against the frozen budget;
- A1 re-identification and PT2 (hashing / OPRF) at each budget, recomputed from the
  audit's per-adversary rows with the audit's own formula
  (``hash x min(1, spare / candidates)``), the adversary using its best epoch;
- the ratchet: an adversary that spends its whole budget each epoch grows it by ``factor``
  per epoch; the epochs it needs to tokenise every candidate, and PT2 after k epochs.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any

from finmesh.paths import DatasetPaths

ADAPTIVE_FACTOR = 2.0
PT2_TARGET = 10.0
REFUSAL_TARGET = 0.01
RATCHET_EPOCHS = (0, 1, 2, 3, 4, 6, 8)

Use = dict[tuple[int, int], int]


def as_use(rows: Iterable[dict[str, Any]]) -> Use:
    """Rows ``{"bank", "epoch", "used"}`` (the X1 checkpoint format) to a use map."""
    return {(int(r["bank"]), int(r["epoch"])): int(r["used"]) for r in rows}


def merge(*uses: Use) -> Use:
    out: Use = {}
    for u in uses:
        for k, v in u.items():
            out[k] = out.get(k, 0) + int(v)
    return out


def adaptive_budgets(
    use: Use, floor: int, factor: float = ADAPTIVE_FACTOR, cap: int | None = None
) -> dict[tuple[int, int], int]:
    """Budget per (bank, epoch) under the rule; epochs with no previous use get the floor."""
    out = {}
    for b, e in use:
        prev = use.get((b, e - 1))
        budget = floor if prev is None else max(floor, math.floor(factor * prev))
        out[(b, e)] = min(budget, cap) if cap is not None else budget
    return out


def refusals(use: Use, budgets: dict[tuple[int, int], int] | int) -> dict[str, Any]:
    def bud(k: tuple[int, int]) -> int:
        return budgets if isinstance(budgets, int) else budgets[k]

    total = sum(use.values())
    over = {k: max(0, u - bud(k)) for k, u in use.items()}
    return {
        "share_refused": (sum(over.values()) / total) if total else 0.0,
        "bank_epochs_over": sum(v > 0 for v in over.values()),
        "bank_epochs": len(use),
        "requests": total,
    }


def a1_at(
    per_adversary: list[dict[str, Any]], spare: Callable[[int], int]
) -> dict[str, float | None]:
    """Pooled A1 (hashing and OPRF) with ``spare(adversary)`` attack queries."""
    tot = sum(r["targets"] for r in per_adversary)
    if not tot:
        return {"hash": 0.0, "oprf": 0.0, "ratio": None}
    h = o = 0.0
    for r in per_adversary:
        n_c = r["candidates"]
        h += r["hash"] * r["targets"]
        if n_c:
            o += r["hash"] * min(1.0, max(0, spare(int(r["adversary"]))) / n_c) * r["targets"]
    h, o = h / tot, o / tot
    return {"hash": h, "oprf": o, "ratio": (h / o) if o else None}


def best_spare(use: Use, budgets: dict[tuple[int, int], int] | int, bank: int) -> int:
    """The adversary's largest spare budget over the epochs it was active in."""
    spares = [
        (budgets if isinstance(budgets, int) else budgets[(b, e)]) - u
        for (b, e), u in use.items()
        if b == bank
    ]
    return max(spares, default=budgets if isinstance(budgets, int) else 0)


def ratchet(
    per_adversary: list[dict[str, Any]],
    floor: int,
    factor: float = ADAPTIVE_FACTOR,
    cap: int | None = None,
    epochs: tuple[int, ...] = RATCHET_EPOCHS,
) -> dict[str, Any]:
    """An adversary spending its whole budget each epoch: budget floor x factor^k (capped).
    Its own legitimate need (the audit's ``legit_queries``) still comes out of it."""

    def budget(k: int) -> int:
        b = int(floor * factor**k)
        return min(b, cap) if cap is not None else b

    def spare_at(k: int) -> Callable[[int], int]:
        return lambda a: budget(k) - _legit(per_adversary, a)

    steps = {k: {"budget": budget(k), **a1_at(per_adversary, spare_at(k))} for k in epochs}
    need = max((r["candidates"] + r["legit_queries"] for r in per_adversary), default=0)
    if cap is not None and cap < need:
        full = None
    else:
        full = max(0, math.ceil(math.log(max(need, 1) / floor, factor))) if need > floor else 0
    return {"steps": steps, "epochs_to_every_candidate": full, "largest_need": need}


def _legit(rows: list[dict[str, Any]], adv: int) -> int:
    return next((int(r["legit_queries"]) for r in rows if int(r["adversary"]) == adv), 0)


def replay(
    use_test: Use,
    use_val: Use | None,
    floor: int,
    per_adversary: list[dict[str, Any]] | None,
    factor: float = ADAPTIVE_FACTOR,
    cap: int | None = None,
) -> dict[str, Any]:
    """The P4 replay for one seed."""
    use = merge(use_val or {}, use_test)
    adaptive = adaptive_budgets(use, floor, factor, cap)
    test_keys = set(use_test)
    on_test = {k: use[k] for k in test_keys}
    out: dict[str, Any] = {
        "floor": floor,
        "factor": factor,
        "cap": cap,
        "with_validation_history": use_val is not None,
        "frozen": refusals(on_test, floor),
        "adaptive": refusals(on_test, {k: adaptive[k] for k in test_keys}),
        "per_bank_epoch": [
            {
                "bank": b,
                "epoch": e,
                "used": use[(b, e)],
                "test": (b, e) in test_keys,
                "adaptive_budget": adaptive[(b, e)],
            }
            for b, e in sorted(use)
        ],
    }
    if per_adversary:
        out["A1"] = {
            "frozen": a1_at(per_adversary, lambda a: best_spare(on_test, floor, a)),
            "adaptive": a1_at(per_adversary, lambda a: best_spare(on_test, adaptive, a)),
            "audit_convention_frozen": a1_at(
                per_adversary, lambda a: floor - _legit(per_adversary, a)
            ),
            "ratchet": ratchet(per_adversary, floor, factor, cap),
        }
    return out


# --------------------------------------------------------------------------- inputs
def validation_token_use(
    paths: DatasetPaths, option: str, seed: int, only: frozenset[str] | None = None
) -> Use:
    """Recompute validation token use with the configurations the saved test run used
    (the validation phase only; never the test). Week-18 checkpoints predate the record."""
    from finmesh.training.x1 import _phase, _train

    t, seconds = _train(paths, option, seed, False, lambda _p: None)
    val = _phase(paths, option, seed, t, "val", seconds, lambda _p: None, True, False, only)
    return {(int(b), int(e)): int(u) for (b, e), u in val.tokens.service.used.items()}


def checkpoints(paths: DatasetPaths, option: str, prefix: str = "x1") -> dict[int, Path]:
    from finmesh.training.sealed_runs import test_dir

    d = test_dir(paths, option)
    out = {}
    for p in sorted(d.glob(f"{prefix}_seed*.pkl")):
        try:
            out[int(p.stem.rsplit("seed", 1)[1])] = p
        except ValueError:
            continue
    return out


def run_budget_replay(
    paths: DatasetPaths,
    option: str = "B8",
    seeds: tuple[int, ...] | None = None,
    cap: int | None = None,
    recompute_validation: bool = True,
    cap_factor: float | None = None,
    progress: Callable[[str], None] = lambda _m: None,
) -> dict[str, Any]:
    """Replay over the saved X1 test checkpoints (read only; nothing opens the test)."""
    from finmesh.matching.tokens import token_budget
    from finmesh.training.sealed_runs import _load

    floor = token_budget(paths.name)
    if cap_factor is not None:
        cap = int(cap_factor * floor)
    found = checkpoints(paths, option)
    if not found:
        raise FileNotFoundError(
            f"no X1 test checkpoints under {paths.root / 'test'}; P4 replays recorded runs"
        )
    use_seeds = sorted(found) if seeds is None else [s for s in seeds if s in found]
    per_seed = {}
    for s in use_seeds:
        r = _load(found[s])
        tu = r.get("token_use") or {}
        use_test = as_use(tu.get("per_bank_epoch", []))
        use_val = as_use(r["token_use_val"]) if r.get("token_use_val") is not None else None
        if use_val is None and recompute_validation:
            progress(f"seed {s}: recomputing validation token use (validation phase only)")
            from finmesh.training.sealed_runs import OTHER_SEEDS, X1_HEADLINE

            only = None if s in OTHER_SEEDS else frozenset(X1_HEADLINE)
            use_val = validation_token_use(paths, option, s, only)
        a1 = ((r.get("audit") or {}).get("A1") or {}).get("per_adversary")
        per_seed[s] = replay(use_test, use_val, floor, a1, cap=cap)
        progress(
            f"seed {s}: refused {per_seed[s]['adaptive']['share_refused']:.2%} adaptive, "
            f"{per_seed[s]['frozen']['share_refused']:.2%} frozen"
        )
    shares = [v["adaptive"]["share_refused"] for v in per_seed.values()]
    return {
        "dataset": paths.name,
        "option": option,
        "floor": floor,
        "cap": cap,
        "seeds": per_seed,
        "summary": {
            "adaptive_share_refused_max": max(shares, default=0.0),
            "frozen_share_refused_max": max(
                (v["frozen"]["share_refused"] for v in per_seed.values()), default=0.0
            ),
            "refusal_target": REFUSAL_TARGET,
            "refusal_met": max(shares, default=0.0) < REFUSAL_TARGET,
        },
    }


def render(result: dict[str, Any]) -> str:
    def pct(x: float | None) -> str:
        return "—" if x is None else f"{x:.2%}"

    def num(x: float | None) -> str:
        return "—" if x is None else f"{x:.3g}"

    cap = result["cap"]
    lines = [
        f"# A25 P4 adaptive token budget replay · {result['dataset']}",
        "",
        f"Rule: budget = max(A16 {result['floor']:,}, 2 × the bank's use in the previous "
        "epoch)" + (f", capped at {cap:,}" if cap else " (no cap, as signed)") + ". Recorded "
        "legitimate use of the X1 test runs (label-free); validation history included.",
        "",
        "| Seed | Refused, frozen A16 | Refused, adaptive | Bank-epochs over (frozen → adaptive) "
        "| PT2 frozen | PT2 adaptive |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for s, v in result["seeds"].items():
        a1 = v.get("A1") or {}
        lines.append(
            f"| {s} | {pct(v['frozen']['share_refused'])} | {pct(v['adaptive']['share_refused'])}"
            f" | {v['frozen']['bank_epochs_over']} → {v['adaptive']['bank_epochs_over']} of "
            f"{v['adaptive']['bank_epochs']} | {num((a1.get('frozen') or {}).get('ratio'))} | "
            f"{num((a1.get('adaptive') or {}).get('ratio'))} |"
        )
    sm = result["summary"]
    lines += [
        "",
        f"Largest adaptive refusal **{pct(sm['adaptive_share_refused_max'])}** (target under "
        f"{pct(sm['refusal_target'])}: **{'met' if sm['refusal_met'] else 'missed'}**). PT2 "
        "asks hashing ÷ OPRF ≥ 10; the adversary uses its best epoch.",
        "",
    ]
    ratchets = [v["A1"]["ratchet"] for v in result["seeds"].values() if v.get("A1")]
    if ratchets:
        r = ratchets[0]
        lines += [
            "## Ratchet: an adversary spending its whole budget every epoch",
            "",
            "| Epochs of full spending | Budget | OPRF re-identification | PT2 |",
            "| --- | --- | --- | --- |",
        ]
        for k, st in r["steps"].items():
            lines.append(f"| {k} | {st['budget']:,} | {num(st['oprf'])} | {num(st['ratio'])} |")
        full = r["epochs_to_every_candidate"]
        lines += [
            "",
            (
                f"It can tokenise every candidate after **{full}** epochs ({full * 7} days)."
                if full is not None
                else "The cap stops it before it can tokenise every candidate."
            ),
            "",
        ]
    return "\n".join(lines)


__all__ = [
    "ADAPTIVE_FACTOR",
    "a1_at",
    "adaptive_budgets",
    "ratchet",
    "refusals",
    "render",
    "replay",
    "run_budget_replay",
]
