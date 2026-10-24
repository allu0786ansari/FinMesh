"""RFC 9497 OPRF (mode 0x00) over ristretto255 with SHA-512.

This is the matching primitive of proposal Section 8.4: a bank blinds an
account identifier, the token service evaluates the PRF under its key without
seeing the identifier, and the bank unblinds the result to obtain a token.
No bank ever holds the key, so a bank cannot tokenise candidate identifiers
offline; every token costs a metered, logged query (budgets arrive in week 6).

Primitives come from ``rbcl`` (libsodium's ristretto255, shipped as a wheel,
no system library needed). The protocol layer below follows RFC 9497
Sections 2-3 for the ``ristretto255-SHA512`` suite:

* contextString = "OPRFV1-" || I2OSP(mode, 1) || "-" || "ristretto255-SHA512"
* HashToGroup  = ristretto255 one-way map of expand_message_xmd(SHA-512, 64 bytes)
* HashToScalar = expand_message_xmd(SHA-512, 64 bytes), little-endian, mod L
* Finalize     = SHA-512(len(input) || input || len(N) || N || "Finalize")

Week 2 status: a spike. Correctness is checked by tests that compare against
an independent implementation (Cloudflare voprf-ts, ``scripts/oprf_crosscheck``)
and by algebraic properties. The RFC appendix vectors are added as a test when
the RFC text is available offline.
"""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass

import rbcl

MODE_OPRF = 0x00
SUITE_ID = b"ristretto255-SHA512"
CONTEXT_STRING = b"OPRFV1-" + bytes([MODE_OPRF]) + b"-" + SUITE_ID

ELEMENT_BYTES = 32  # Ne
SCALAR_BYTES = 32  # Ns
HASH_BYTES = 64  # Nh
_SHA512_BLOCK = 128  # s_in_bytes for SHA-512


class OprfError(ValueError):
    """Invalid input, element or derived key."""


def i2osp(value: int, length: int) -> bytes:
    if value < 0 or value >= 1 << (8 * length):
        raise OprfError(f"i2osp: {value} does not fit in {length} bytes")
    return value.to_bytes(length, "big")


def expand_message_xmd(msg: bytes, dst: bytes, len_in_bytes: int) -> bytes:
    """RFC 9380 Section 5.3.1 with SHA-512."""
    b_in_bytes = HASH_BYTES
    ell = -(-len_in_bytes // b_in_bytes)
    if ell > 255 or len_in_bytes > 65535 or len(dst) > 255:
        raise OprfError("expand_message_xmd: requested output too long or DST too long")
    dst_prime = dst + i2osp(len(dst), 1)
    z_pad = bytes(_SHA512_BLOCK)
    msg_prime = z_pad + msg + i2osp(len_in_bytes, 2) + i2osp(0, 1) + dst_prime
    b0 = hashlib.sha512(msg_prime).digest()
    b_vals = [hashlib.sha512(b0 + i2osp(1, 1) + dst_prime).digest()]
    for i in range(2, ell + 1):
        mixed = bytes(x ^ y for x, y in zip(b0, b_vals[-1], strict=True))
        b_vals.append(hashlib.sha512(mixed + i2osp(i, 1) + dst_prime).digest())
    return b"".join(b_vals)[:len_in_bytes]


def hash_to_group(msg: bytes) -> bytes:
    uniform = expand_message_xmd(msg, b"HashToGroup-" + CONTEXT_STRING, 64)
    return bytes(rbcl.crypto_core_ristretto255_from_hash(uniform))


def hash_to_scalar(msg: bytes, dst: bytes | None = None) -> bytes:
    """Scalar as 32 little-endian bytes, reduced mod L."""
    uniform = expand_message_xmd(msg, dst or b"HashToScalar-" + CONTEXT_STRING, 64)
    return bytes(rbcl.crypto_core_ristretto255_scalar_reduce(uniform))


def _is_zero_scalar(s: bytes) -> bool:
    return not any(s)


def _check_element(element: bytes) -> None:
    if len(element) != ELEMENT_BYTES or not rbcl.crypto_core_ristretto255_is_valid_point(element):
        raise OprfError("invalid ristretto255 element")
    if not any(element):
        raise OprfError("identity element is not allowed")


def _scalarmult(scalar: bytes, element: bytes) -> bytes:
    try:
        return bytes(rbcl.crypto_scalarmult_ristretto255(scalar, element))
    except Exception as exc:  # libsodium refuses an identity result
        raise OprfError("scalar multiplication produced the identity") from exc


@dataclass(frozen=True)
class KeyPair:
    secret: bytes  # skS, 32-byte little-endian scalar
    public: bytes  # pkS = skS * G, used by verifiable modes only

    def __repr__(self) -> str:  # never print the secret
        return f"KeyPair(public={self.public.hex()[:16]}...)"


def derive_key_pair(seed: bytes, info: bytes) -> KeyPair:
    """RFC 9497 Section 3.2.1 DeriveKeyPair."""
    if len(seed) != 32:
        raise OprfError("seed must be 32 bytes")
    derive_input = seed + i2osp(len(info), 2) + info
    dst = b"DeriveKeyPair" + CONTEXT_STRING
    for counter in range(256):
        sk = hash_to_scalar(derive_input + i2osp(counter, 1), dst)
        if not _is_zero_scalar(sk):
            pk = bytes(rbcl.crypto_scalarmult_ristretto255_base(sk))
            return KeyPair(secret=sk, public=pk)
    raise OprfError("DeriveKeyPair: no valid key after 256 attempts")


def generate_key_pair() -> KeyPair:
    return derive_key_pair(secrets.token_bytes(32), b"finmesh token service")


def random_scalar() -> bytes:
    while True:
        s = bytes(rbcl.crypto_core_ristretto255_scalar_random())
        if not _is_zero_scalar(s):
            return s


def blind(private_input: bytes, blind_scalar: bytes | None = None) -> tuple[bytes, bytes]:
    """Client: return ``(blind, blinded_element)``. ``blind_scalar`` only for tests."""
    r = blind_scalar if blind_scalar is not None else random_scalar()
    if len(r) != SCALAR_BYTES or _is_zero_scalar(r):
        raise OprfError("invalid blind")
    input_element = hash_to_group(private_input)
    if not any(input_element):
        raise OprfError("input hashed to the identity")
    return r, _scalarmult(r, input_element)


def blind_evaluate(secret: bytes, blinded_element: bytes) -> bytes:
    """Server: evaluate under ``secret`` without learning the input."""
    _check_element(blinded_element)
    return _scalarmult(secret, blinded_element)


def finalize(private_input: bytes, blind_scalar: bytes, evaluated_element: bytes) -> bytes:
    """Client: unblind and hash to the 64-byte PRF output."""
    _check_element(evaluated_element)
    inverse = bytes(rbcl.crypto_core_ristretto255_scalar_invert(blind_scalar))
    unblinded = _scalarmult(inverse, evaluated_element)
    hash_input = (
        i2osp(len(private_input), 2)
        + private_input
        + i2osp(len(unblinded), 2)
        + unblinded
        + b"Finalize"
    )
    return hashlib.sha512(hash_input).digest()


def evaluate(secret: bytes, private_input: bytes) -> bytes:
    """Server-side direct evaluation (RFC 9497 Evaluate), for tests and audits."""
    element = hash_to_group(private_input)
    issued = _scalarmult(secret, element)
    hash_input = (
        i2osp(len(private_input), 2) + private_input + i2osp(len(issued), 2) + issued + b"Finalize"
    )
    return hashlib.sha512(hash_input).digest()
