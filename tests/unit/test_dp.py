"""Week 10: neural scorer, exact per-unit clipping, DP-SGD noise, accountant, FedAvg."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from finmesh.federation.accountant import (
    Accountant,
    BudgetExceeded,
    calibrate_noise,
    epsilon_for,
)
from finmesh.federation.dpsgd import Adam, ClientData, UnitIndex, dp_step
from finmesh.federation.fedavg import fedavg
from finmesh.models.neural import (
    Encoder,
    forward_backward,
    init_params,
    kind_of,
    summed_grads,
    unit_norms,
)

COLS = ("tx_out", "amt_out", "amt_net", "cross_bank_share", "in_out_delay_min_h")


def _data(n: int = 60, seed: int = 0) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    x = np.column_stack(
        [
            rng.integers(0, 20, n),
            rng.lognormal(6, 2, n),
            rng.normal(0, 1e4, n),
            np.where(rng.random(n) < 0.2, np.nan, rng.random(n)),
            rng.exponential(5, n),
        ]
    )
    y = (rng.random(n) < 0.3).astype(float)
    w = np.where(y == 1, 10.0, 1.0)
    return x, y, w


def test_encoder_is_fixed_and_marks_missing() -> None:
    enc = Encoder(COLS)
    x, _, _ = _data()
    e = enc(x)
    assert e.shape == (len(x), enc.width) and e.min() >= 0 and e.max() <= 1
    assert np.allclose(enc(x[:5]), e[:5])  # a row's encoding never depends on other rows
    j = 0
    for name in COLS[:3]:
        j += len(kind_of(name)[1])
    k = len(kind_of("cross_bank_share")[1]) - 1
    missing = np.isnan(x[:, 3])
    assert np.array_equal(e[:, j + k] == 1, missing)
    assert kind_of("pass_through") == kind_of("fmt_wire_share")


def _loss_sum(params: list[np.ndarray], x: np.ndarray, y: np.ndarray, w: np.ndarray) -> float:
    loss, _, _ = forward_backward(params, x, y, w)
    return loss * len(y)


def test_gradient_matches_finite_differences() -> None:
    x, y, w = _data(40)
    xe = Encoder(COLS)(x)
    params = init_params(xe.shape[1], seed=1, hidden=(8, 4))
    _, acts, grads = forward_backward(params, xe, y, w)
    g = summed_grads(acts, grads)
    rng = np.random.default_rng(2)
    for layer in range(len(params)):
        for _ in range(5):
            i = rng.integers(0, params[layer].shape[0])
            j = rng.integers(0, params[layer].shape[1])
            h = 1e-6
            p_plus = [p.copy() for p in params]
            p_minus = [p.copy() for p in params]
            p_plus[layer][i, j] += h
            p_minus[layer][i, j] -= h
            num = (_loss_sum(p_plus, xe, y, w) - _loss_sum(p_minus, xe, y, w)) / (2 * h)
            assert g[layer][i, j] == pytest.approx(num, rel=1e-4, abs=1e-6)


def _explicit_unit_grads(params, xe, y, w, unit):  # type: ignore[no-untyped-def]
    out = []
    for u in range(int(unit.max()) + 1):
        rows = unit == u
        _, a, d = forward_backward(params, xe[rows], y[rows], w[rows])
        out.append(summed_grads(a, d))
    return out


@pytest.mark.parametrize("unit_kind", ["window", "account"])
def test_unit_norms_and_clipped_sum_are_exact(unit_kind: str) -> None:
    x, y, w = _data(50)
    xe = Encoder(COLS)(x)
    params = init_params(xe.shape[1], seed=3, hidden=(8, 4))
    rng = np.random.default_rng(4)
    unit = rng.permutation(50) if unit_kind == "window" else rng.integers(0, 12, 50)
    _, acts, grads = forward_backward(params, xe, y, w)
    norms = unit_norms(acts, grads, unit)
    explicit = _explicit_unit_grads(params, xe, y, w, unit)
    ref = np.array([np.sqrt(sum((g * g).sum() for g in gs)) for gs in explicit])
    assert np.allclose(norms, ref)
    clip = 0.5
    factor = np.minimum(1, clip / norms)
    clipped = summed_grads(acts, grads, factor[unit])
    want = [sum(f * gs[i] for f, gs in zip(factor, explicit, strict=True)) for i in range(3)]
    for c, r in zip(clipped, want, strict=True):
        assert np.allclose(c, r)
    for f, gs in zip(factor, explicit, strict=True):  # every clipped unit is within C
        assert f * np.sqrt(sum((g * g).sum() for g in gs)) <= clip + 1e-9


def test_accountant_calibrates_guards_and_persists(tmp_path: Path) -> None:
    q, steps, delta = 0.01, 500, 1e-6
    sigma = calibrate_noise(3.0, q, steps, delta)
    assert epsilon_for(sigma, q, steps, delta) <= 3.0
    assert epsilon_for(sigma * 0.98, q, steps, delta) > 3.0 * 0.97  # near the boundary
    assert epsilon_for(sigma, q, steps // 2, delta) < epsilon_for(sigma, q, steps, delta)
    path = tmp_path / "acc.json"
    acc = Accountant.plan(path, client=0, target_epsilon=3.0, delta=delta, rate=q, steps=steps)
    acc.step(400)
    acc.save()
    again = Accountant.plan(path, client=0, target_epsilon=3.0, delta=delta, rate=q, steps=steps)
    assert again.state.steps_done == 400  # resumed, never reset
    again.step(100)
    with pytest.raises(BudgetExceeded):
        again.step(1)
    assert again.report()["epsilon_spent"] <= 3.0


def test_dp_step_noise_scale_and_guard(tmp_path: Path) -> None:
    n = 2000
    x = np.zeros((n, len(COLS)))
    y = np.zeros(n)
    w = np.zeros(n)  # zero loss weight: the private gradient is pure noise
    data = ClientData(x, y, w, np.arange(n))
    enc = Encoder(COLS)
    params = init_params(enc.width, 0, hidden=(8, 4))
    acc = Accountant.plan(tmp_path / "a.json", 0, 10.0, 1e-5, 0.05, 1)
    opt = Adam(lr=0.0)  # inspect the gradient without moving

    captured: list[np.ndarray] = []
    original = opt.update

    def spy(p: list[np.ndarray], g: list[np.ndarray]) -> None:
        captured.extend(g)
        original(p, g)

    opt.update = spy  # type: ignore[method-assign]
    noise = 2.0
    dp_step(
        params, opt, data, UnitIndex(data.unit), enc, 0.05, noise, np.random.default_rng(0), acc
    )
    flat = np.concatenate([g.ravel() for g in captured])
    expected_sd = noise * 1.0 / (0.05 * n)
    assert np.std(flat) == pytest.approx(expected_sd, rel=0.1)
    with pytest.raises(BudgetExceeded):
        dp_step(
            params, opt, data, UnitIndex(data.unit), enc, 0.05, noise, np.random.default_rng(1), acc
        )


def test_fedavg_averages_client_weights_equally() -> None:
    x, y, w = _data(200)
    enc = Encoder(COLS)
    init = init_params(enc.width, 0, hidden=(8, 4))
    clients = {0: ClientData(x[:100], y[:100], w[:100], np.arange(100))}
    clients[1] = ClientData(x[100:], y[100:], w[100:], np.arange(100))
    a, info = fedavg(clients, enc, init, seed=0, rounds=2, local_steps=3)
    b, _ = fedavg(clients, enc, init, seed=0, rounds=2, local_steps=3)
    assert all(np.array_equal(p, q) for p, q in zip(a, b, strict=True))  # deterministic
    assert info["participation"] == [2, 2]
    assert not all(np.array_equal(p, q) for p, q in zip(a, init, strict=True))


def test_dp_fedavg_still_learns_a_clear_signal(tmp_path: Path) -> None:
    """End to end: DP-SGD at ε = 10 keeps most of a strong, rare signal."""
    from sklearn.metrics import roc_auc_score

    from finmesh.federation.dpsgd import BATCH
    from finmesh.models.neural import scores

    rng = np.random.default_rng(0)
    cols = ("tx_out", "fan_in", "pass_through")
    enc = Encoder(cols)

    def make(n: int) -> tuple[np.ndarray, np.ndarray]:
        y = (rng.random(n) < 0.02).astype(float)
        x = np.column_stack(
            [
                rng.poisson(2 + 6 * y),
                rng.poisson(1 + 5 * y),
                np.clip(rng.beta(2, 5, n) + 0.5 * y, 0, 1),
            ]
        )
        return x, y

    clients = {}
    for c in range(2):
        x, y = make(20_000)
        clients[c] = ClientData(x, y, np.where(y == 1, 10.0, 1.0), np.arange(len(y)))
    xt, yt = make(20_000)
    init = init_params(enc.width, 0)
    dp = {}
    for c, d in clients.items():
        q = BATCH / d.units
        acc = Accountant.plan(tmp_path / f"c{c}.json", c, 10.0, 0.1 / d.units, q, 600)
        dp[c] = {"rate": q, "noise": acc.state.noise, "accountant": acc}
    plain, _ = fedavg(clients, enc, init, seed=0, rounds=30, local_steps=20)
    params, _ = fedavg(clients, enc, init, seed=0, rounds=30, local_steps=20, dp=dp)
    auc_plain = roc_auc_score(yt, scores(plain, enc(xt)))
    auc_dp = roc_auc_score(yt, scores(params, enc(xt)))
    assert auc_plain > 0.95 and auc_dp > 0.9 and auc_dp > auc_plain - 0.08
    assert all(d["accountant"].report()["epsilon_spent"] <= 10.0 for d in dp.values())
