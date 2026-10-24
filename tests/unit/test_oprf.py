"""OPRF tests.

``tests/data/oprf_voprf_ts.json`` holds outputs of Cloudflare's independent
RFC 9497 implementation (voprf-ts 1.0.0, noble provider), produced by
``scripts/oprf_crosscheck.mjs``. Matching them byte for byte checks key
derivation, hash-to-group, scalar encoding and the Finalize hash.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from finmesh.matching import oprf

REFERENCE = Path(__file__).resolve().parent.parent / "data" / "oprf_voprf_ts.json"


def _cases() -> list[dict[str, object]]:
    data: list[dict[str, object]] = json.loads(REFERENCE.read_text())
    return data


@pytest.mark.parametrize("case", _cases(), ids=lambda c: str(c["seed"])[:8])
def test_matches_cloudflare_voprf_ts(case: dict[str, object]) -> None:
    kp = oprf.derive_key_pair(bytes.fromhex(str(case["seed"])), bytes.fromhex(str(case["info"])))
    assert kp.secret.hex() == case["sk"]
    inputs = case["inputs"]
    evals = case["evals"]
    assert isinstance(inputs, list) and isinstance(evals, list)
    for x, expected in zip(inputs, evals, strict=True):
        if expected is None:
            continue
        assert oprf.evaluate(kp.secret, bytes.fromhex(x)).hex() == expected


def test_rfc9497_reference_key() -> None:
    # skSm of RFC 9497 Appendix A.1.1 (seed a3..a3, info "test key"); also reproduced
    # by voprf-ts above.
    kp = oprf.derive_key_pair(bytes([0xA3]) * 32, b"test key")
    assert kp.secret.hex() == "5ebcea5ee37023ccb9fc2d2019f9d7737be85591ae8652ffa9ef0f4d37063b0e"


def test_blind_protocol_equals_direct_evaluation() -> None:
    kp = oprf.generate_key_pair()
    for x in (b"10:8000EBD30", b"", b"\x00" * 64):
        r, blinded = oprf.blind(x)
        evaluated = oprf.blind_evaluate(kp.secret, blinded)
        assert oprf.finalize(x, r, evaluated) == oprf.evaluate(kp.secret, x)


def test_blinding_hides_the_input() -> None:
    x = b"10:8000EBD30"
    _, b1 = oprf.blind(x)
    _, b2 = oprf.blind(x)
    assert b1 != b2  # fresh blinds: the server sees unlinkable elements
    assert b1 != oprf.hash_to_group(x)


def test_keys_separate_tokens() -> None:
    k1, k2 = oprf.generate_key_pair(), oprf.generate_key_pair()
    assert oprf.evaluate(k1.secret, b"acct") != oprf.evaluate(k2.secret, b"acct")
    assert "secret" not in repr(k1) and k1.secret.hex() not in repr(k1)


def test_invalid_elements_rejected() -> None:
    kp = oprf.generate_key_pair()
    with pytest.raises(oprf.OprfError):
        oprf.blind_evaluate(kp.secret, bytes(32))  # identity
    with pytest.raises(oprf.OprfError):
        oprf.blind_evaluate(kp.secret, b"\xff" * 32)  # not a valid encoding
    with pytest.raises(oprf.OprfError):
        oprf.derive_key_pair(b"short", b"")
    with pytest.raises(oprf.OprfError):
        oprf.blind(b"x", blind_scalar=bytes(32))


def test_expand_message_xmd_lengths() -> None:
    out = oprf.expand_message_xmd(b"abc", b"DST", 64)
    assert len(out) == 64
    assert oprf.expand_message_xmd(b"abc", b"DST", 200)[:64] != out  # length is bound in
    with pytest.raises(oprf.OprfError):
        oprf.expand_message_xmd(b"abc", b"D" * 256, 64)
    with pytest.raises(oprf.OprfError):
        oprf.i2osp(256, 1)
