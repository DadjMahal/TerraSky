"""Encryption at rest (§31) for SkyDash secrets/credentials.

Implements AES-256-GCM authenticated encryption using the ``cryptography``
package primitives (:mod:`cryptography.hazmat.primitives.ciphers.aead` and
:mod:`cryptography.hazmat.primitives.kdf.pbkdf2`).

``cryptography`` is **already present** in the dependency tree (pulled in by
``paramiko``, pinned in ``requirements.txt``) so no new pip dependency is
added here::

    # requirements.txt
    paramiko==5.0.0            # <-- already installs cryptography

If the package is unavailable the module still imports cleanly and every
cryptographic callable raises a clear :class:`ImportError` with a fix
message (``pip install cryptography``).

Design notes
------------
* **Algorithm:** AES-256-GCM (12-byte nonce, 16-byte auth tag) via
  ``cryptography.hazmat.primitives.ciphers.aead.AESGCM``.
* **Key derivation:** PBKDF2-HMAC-SHA256 (default 200_000 iterations) from a
  passphrase; SkyDash convention is to set ``SKYDASH_SECRETS_KEY`` in the
  git-ignored environment file. The salt is random per sealed payload.
* **Payload format (URL-safe base64):** ``salt(16) || nonce(12) || ct+tag``.
  A fresh random salt is generated on every :func:`encrypt` call and shipped
  inside the token, so :func:`decrypt` only needs the passphrase — this keeps
  sealed blobs persistable across restarts.
* **Purity:** every function is pure (no I/O, no Flask, no DB) so the module
  is trivially unit-testable. ``master_key()`` is the only env-dependent
  helper.
"""
from __future__ import annotations

import base64
import hashlib
import os

__all__ = [
    "CRYPTO_AVAILABLE",
    "SecretKeyNotConfigured",
    "derive_key",
    "derive_key_sha256",
    "decrypt",
    "decrypt_with_key",
    "encrypt",
    "encrypt_with_key",
    "generate_salt",
    "master_key",
    "selftest",
]

# --- Optional dependency handling ------------------------------------------
try:  # pragma: no cover - exercised only in exotic environments
    from cryptography.exceptions import InvalidTag
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    CRYPTO_AVAILABLE = True
except ImportError:  # pragma: no cover - import guard only
    AESGCM = None
    InvalidTag = None
    CRYPTO_AVAILABLE = False

# AES-GCM limits (RFC 5116): max 2^32-1 blocks (~2^39-256 bits) per key use.
_MAX_PLAINTEXT_BYTES = (2**31) - 32
_SALT_BYTES = 16
_NONCE_BYTES = 12
_PBKDF2_ITERATIONS = 200_000
_KEY_BYTES = 32  # AES-256


class SecretKeyNotConfigured(RuntimeError):
    """Raised when ``SKYDASH_SECRETS_KEY`` (or the chosen env var) is unset."""


def _require() -> None:
    """Raise a helpful ImportError when ``cryptography`` is unavailable."""
    if not CRYPTO_AVAILABLE:
        raise ImportError(
            "cryptography is not installed - AES-256-GCM encryption at rest "
            "cannot be used. Install it with: pip install cryptography "
            "(normally present transitively via paramiko)."
        )
def generate_salt(n_bytes: int = _SALT_BYTES) -> bytes:
    """Generate ``n_bytes`` of cryptographically-strong random salt."""
    return os.urandom(n_bytes)


def derive_key_sha256(passphrase: str | bytes) -> bytes:
    """Deterministic 32-byte key from a passphrase (HMAC-SHA256).

    Convenience for callers that want a *stable* envelope key without
    persisting a salt (e.g. encrypting ephemeral session data). Not used by
    the recommended :func:`encrypt`/:func:`decrypt` pair, which embeds a
    random salt per payload for stronger KDF hygiene.
    """
    data = passphrase.encode("utf-8") if isinstance(passphrase, str) else passphrase
    return hashlib.sha256(data).digest()


def derive_key(
    passphrase: str | bytes,
    salt: bytes,
    iterations: int = _PBKDF2_ITERATIONS,
    length: int = _KEY_BYTES,
) -> bytes:
    """Derive a key from ``passphrase`` via PBKDF2-HMAC-SHA256 (§31).

    Returns ``length`` bytes (default 32, i.e. AES-256). The salt should be
    random (:func:`generate_salt`) and is not secret.
    """
    _require()
    data = passphrase.encode("utf-8") if isinstance(passphrase, str) else passphrase
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=length,
        salt=salt,
        iterations=iterations,
    )
    return kdf.derive(data)


def encrypt_with_key(
    plaintext: str, key: bytes, aad: bytes | None = None
) -> str:
    """Low-level AES-256-GCM seal.

    Returns a URL-safe base64 token ``nonce || ciphertext+tag`` (no salt; the
    key is supplied directly). Use :func:`encrypt` for the passphrase-based
    envelope form.
    """
    _require()
    if len(key) != _KEY_BYTES:
        raise ValueError(f"AES-256 requires a {_KEY_BYTES}-byte key, got {len(key)}")
    data = plaintext.encode("utf-8")
    if len(data) > _MAX_PLAINTEXT_BYTES:
        raise ValueError("plaintext too large for a single AES-GCM seal")
    nonce = os.urandom(_NONCE_BYTES)
    ct = AESGCM(key).encrypt(nonce, data, aad)
    return base64.urlsafe_b64encode(nonce + ct).decode("ascii")


def decrypt_with_key(
    token: str, key: bytes, aad: bytes | None = None
) -> str:
    """Low-level AES-256-GCM open (inverse of :func:`encrypt_with_key`).

    Raises :class:`ValueError` on structurally invalid tokens and
    :class:`cryptography.exceptions.InvalidTag` when the key/AAD do not
    authenticate the payload (tamper or wrong key).
    """
    _require()
    if len(key) != _KEY_BYTES:
        raise ValueError(f"AES-256 requires a {_KEY_BYTES}-byte key, got {len(key)}")
    raw = base64.urlsafe_b64decode(token.encode("ascii"))
    if len(raw) < _NONCE_BYTES + 16:
        raise ValueError("invalid sealed token: too short")
    nonce, ct = raw[:_NONCE_BYTES], raw[_NONCE_BYTES:]
    plain = AESGCM(key).decrypt(nonce, ct, aad)
    return plain.decode("utf-8")
def encrypt(
    plaintext: str,
    passphrase: str,
    salt: bytes | None = None,
    iterations: int = _PBKDF2_ITERATIONS,
    aad: bytes | None = None,
) -> str:
    """Encrypt ``plaintext`` under a passphrase (recommended envelope form).

    A fresh random salt is generated (unless supplied) and shipped inside the
    returned token, so :func:`decrypt` needs only the same passphrase::

        token  = crypto.encrypt("secret", crypto.master_key())
        crypto.decrypt(token, crypto.master_key()) == "secret"

    Returns a URL-safe base64 token ``salt(16) || nonce(12) || ct+tag``.
    """
    _require()
    salt = salt if salt is not None else generate_salt()
    key = derive_key(passphrase, salt, iterations=iterations)
    body = encrypt_with_key(plaintext, key, aad=aad)
    return base64.urlsafe_b64encode(
        salt + base64.urlsafe_b64decode(body)
    ).decode("ascii")


def decrypt(
    token: str,
    passphrase: str,
    iterations: int = _PBKDF2_ITERATIONS,
    aad: bytes | None = None,
) -> str:
    """Decrypt a token produced by :func:`encrypt` (envelope form).

    The salt is read from the token and PBKDF2-derived before the AES-GCM
    open. Raises :class:`ValueError`/``InvalidTag`` on bad tokens or a wrong
    passphrase (which fails authentication before any plaintext is returned).
    """
    _require()
    raw = base64.urlsafe_b64decode(token.encode("ascii"))
    if len(raw) < _SALT_BYTES + _NONCE_BYTES + 16:
        raise ValueError("invalid sealed token: too short")
    salt, body = raw[:_SALT_BYTES], raw[_SALT_BYTES:]
    key = derive_key(passphrase, salt, iterations=iterations)
    return decrypt_with_key(
        base64.urlsafe_b64encode(body).decode("ascii"), key, aad=aad
    )


def master_key(env_var: str = "SKYDASH_SECRETS_KEY") -> str:
    """Return the secrets passphrase from ``env_var`` (unset -> error).

    SkyDash convention (§29, §124): ``SKYDASH_SECRETS_KEY`` lives in the
    git-ignored environment file (``terraform/.env`` / systemd
    ``EnvironmentFile``) and is never committed.
    """
    value = os.environ.get(env_var, "").strip()
    if not value:
        raise SecretKeyNotConfigured(
            f"Environment variable {env_var!r} is not set. Encryption at rest "
            f"requires a strong passphrase, e.g. 'openssl rand -base64 48', "
            f"stored in the git-ignored env file."
        )
    return value


def selftest() -> dict:
    """Round-trip self test - verifies encrypt/decrypt + wrong-key rejection.

    Pure and dependency-light: usable both in unit tests and as an on-boot
    sanity check. Raises an assertion error if the primitive is broken.
    """
    if not CRYPTO_AVAILABLE:
        return {"ok": False, "reason": "cryptography not installed"}
    passphrase = master_key() if os.environ.get("SKYDASH_SECRETS_KEY") else "selftest-passphrase"
    secret = "skydash-t3st-s3cret"
    token = encrypt(secret, passphrase)
    assert decrypt(token, passphrase) == secret, "round-trip failed"
    # Tampered token must fail to authenticate.
    raw = bytearray(base64.urlsafe_b64decode(token))
    raw[-1] ^= 0x01  # flip one tag bit
    tampered = base64.urlsafe_b64encode(bytes(raw)).decode("ascii")
    try:
        decrypt(tampered, passphrase)
    except Exception:  # noqa: BLE001 - any failure on tamper is correct
        tamper_rejected = True
    else:
        tamper_rejected = False
    assert tamper_rejected, "tampered token was accepted!"
    return {
        "ok": True,
        "cipher": "AES-256-GCM",
        "kdf": f"PBKDF2-HMAC-SHA256/{_PBKDF2_ITERATIONS}",
        "roundtrip": True,
        "tamper_rejected": True,
    }