"""A25 P3: protecting the S1 alert flag, measured on Medium validation only.

On LI-Medium test, the plain S1 flag lets a peer infer "fan-in in the top decile" (attack
minus prior TPR at 1% FPR +0.092; H1c margin 0.05). The candidates, fixed in
`docs/protocol/improvement_plan_A25.md` before any result:

* ``S1F[eps=e]``: binary randomised response on the flag of **every** queried account
  (with or without a record), e in {0.5, 1, 2, 4}: e-local DP for the bit;
* ``S1F[gate=t]``: the flag is answered only when the requester's own score bucket is at
  least t in {2, 3};
* ``S1F[gate=2,eps=e]``: both, e in {1, 2}.

:func:`run_flag_frontier` measures, on one dataset's validation, each candidate's linked
detection (seeds 0-2, as share of plain S1's gain over S0) and the A2/A3 attacks on seed 0
(the H1c margin per target). :func:`select_flag` applies the frozen rule across HI- and
LI-Medium: among candidates within the margin on every assessable target of **both**,
the largest mean share of S1's gain; ties to the smaller e, then ungated; none if none.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

from finmesh.paths import DatasetPaths
from finmesh.sysinfo import AnonPeak

PLAIN = "S1/stacker"


def candidates() -> list[str]:
    from finmesh.training.x1 import flag_runs

    return [name for name, _, _ in flag_runs()]


def run_flag_frontier(
    paths: DatasetPaths,
    option: str = "B8",
    seeds: tuple[int, ...] = (0, 1, 2),
    reps: int = 1000,
    window_reps: int = 200,
    progress: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    from finmesh.training.sealed_runs import _load, _save
    from finmesh.training.x1 import _recovery, _Stack, combine, run_seed

    ckpt_dir = paths.root / "artifacts" / "a25"
    names = candidates()
    only = frozenset({"S0", PLAIN, *(f"{n}/stacker" for n in names)})
    t0 = time.perf_counter()
    per_seed = []
    with AnonPeak() as anon:
        for seed in seeds:
            ckpt = ckpt_dir / f"flag_frontier_{paths.name}_seed{seed}.pkl"
            if ckpt.exists():  # a rerun reuses finished seeds (validation only)
                per_seed.append(_load(ckpt))
                if progress:
                    progress(f"seed {seed}: kept from {ckpt.name}")
                continue
            r = run_seed(
                paths,
                option,
                seed,
                reps,
                window_reps,
                anon,
                sweeps=False,
                audit=seed == seeds[0],
                only=only,
                flags=True,
            )
            _save(ckpt, r)
            per_seed.append(r)
            if progress:
                progress(f"seed {seed}: {r['seconds']['total']:.0f} s")
        summary = combine(per_seed, reps)
        stack = _Stack(per_seed)
    audit = per_seed[0]["audit"] or {}
    within = (audit.get("H1c") or {}).get("within_by_target", {})
    rows: dict[str, Any] = {}
    for n in [PLAIN.split("/")[0], *names]:
        cfg = f"{n}/stacker"
        share = {"estimate": 1.0} if cfg == PLAIN else _recovery(stack, cfg, reps, ceiling=PLAIN)
        by_target = within.get(n, {})
        assessable = [v for v in by_target.values() if v is not None]
        rows[n] = {
            "linked": summary[cfg]["linked"],
            "gain_over_S0": summary[cfg].get("linked_gain", {}).get("difference"),
            "share_of_S1_gain": share,
            "within_by_target": by_target,
            "within_margin": bool(assessable) and all(assessable),
        }
    return {
        "dataset": paths.name,
        "option": option,
        "split": "val",
        "seeds": list(seeds),
        "candidates": rows,
        "attacks": audit.get("attacks"),
        "seconds": round(time.perf_counter() - t0, 1),
        "peak_anon_mb": anon.mb,
    }


def _order(name: str) -> tuple[float, int]:
    eps = 99.0
    for part in name.removeprefix("S1F[").removesuffix("]").split(","):
        if part.startswith("eps="):
            eps = float(part[4:])
    return (eps, int("gate=" in name))


def select_flag(frontiers: list[dict[str, Any]]) -> dict[str, Any]:
    """The frozen A25 P3 rule over the Medium validation frontiers."""
    names = candidates()
    ok = [n for n in names if all(f["candidates"][n]["within_margin"] for f in frontiers)]

    def share(n: str) -> float:
        vals = [f["candidates"][n]["share_of_S1_gain"].get("estimate") for f in frontiers]
        return float(sum(v for v in vals if v is not None) / len(vals))

    table = {
        n: {
            "within_margin_all": n in ok,
            "mean_share_of_S1_gain": share(n),
        }
        for n in names
    }
    if not ok:
        return {"chosen": None, "reason": "no candidate within the margin on both", "table": table}
    best = max(share(n) for n in ok)
    tied = [n for n in ok if abs(share(n) - best) < 1e-9]
    chosen = sorted(tied, key=_order)[0]
    return {"chosen": chosen, "mean_share_of_S1_gain": best, "table": table}


__all__ = ["PLAIN", "candidates", "run_flag_frontier", "select_flag"]
