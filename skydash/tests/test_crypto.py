"""Tests for crypto — AES-256-GCM encryption at rest (§31).

All functions are pure; we exercise happy paths plus edge cases (bad keys,
tampered tokens, wrong passphrases, unset env key, missing dependency).
"""
from __future__ import annotations

import base64
import os
import sys
from unittest import mock

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import crypto

pytest.importorskip("cryptography")


# --------------------------------------------------------------------------- #
# _require / availability                                                      #
# --------------------------------------------------------------------------- #
def test_crypto_available():
    assert crypto.CRYPTO_AVAILABLE is True


def test_require_raises_import_error_when_unavailable():
    with mock.patch.object(crypto, "CRYPTO_AVAILABLE", False):
        with pytest.raises(ImportError, match="pip install cryptography"):
            crypto._require()


# --------------------------------------------------------------------------- #
# generate_salt / derive_key_sha256                                            #
# --------------------------------------------------------------------------- #
def test_generate_salt_default_length():
    salt = crypto.generate_salt()
    assert len(salt) == 16


def test_generate_salt_custom_length():
    assert len(crypto.generate_salt(32)) == 32


def test_generate_salt_unique():
    assert crypto.generate_salt() != crypto.generate_salt()


def test_derive_key_sha256_deterministic_32_bytes():
    k1 = crypto.derive_key_sha256("my pass")
    k2 = crypto.derive_key_sha256("my pass")
    assert k1 == k2
    assert len(k1) == 32


def test_derive_key_sha256_accepts_bytes():
    assert crypto.derive_key_sha256(b"my pass") == crypto.derive_key_sha256("my pass")


def test_derive_key_sha256_differs_by_passphrase():
    assert crypto.derive_key_sha256("a") != crypto.derive_key_sha256("b")


def test_derive_key_length_and_salt_sensitivity():
    key = crypto.derive_key("pw", b"0123456789abcdef")
    assert len(key) == 32
    other = crypto.derive_key("pw", b"0123456789abcdeg")
    assert key != other


def test_derive_key_stable_with_same_salt():
    salt = b"0123456789abcdef"
    assert crypto.derive_key("pw", salt) == crypto.derive_key("pw", salt)

def test_with_key_roundtrip_unicode(key32):
    token = crypto.encrypt_with_key("héllo — 世界 🚀", key32)
    assert crypto.decrypt_with_key(token, key32) == "héllo — 世界 🚀"


def test_with_key_nonce_is_random(key32):
    t1 = crypto.encrypt_with_key("same", key32)
    t2 = crypto.encrypt_with_key("same", key32)
    assert t1 != t2


def test_with_key_wrong_key_rejected(key32):
    token = crypto.encrypt_with_key("secret", key32)
    wrong = os.urandom(32)
    with pytest.raises(Exception):
        crypto.decrypt_with_key(token, wrong)


def test_with_key_aad_required_for_decrypt(key32):
    token = crypto.encrypt_with_key("secret", key32, aad=b"header")
    with pytest.raises(Exception):
        crypto.decrypt_with_key(token, key32)  # missing AAD
    assert crypto.decrypt_with_key(token, key32, aad=b"header") == "secret"


def test_with_key_wrong_aad_rejected(key32):
    token = crypto.encrypt_with_key("secret", key32, aad=b"one")
    with pytest.raises(Exception):
        crypto.decrypt_with_key(token, key32, aad=b"two")


def test_with_key_rejects_wrong_key_length():
    with pytest.raises(ValueError, match="AES-256 requires a 32-byte key"):
        crypto.encrypt_with_key("x", b"short")
    with pytest.raises(ValueError, match="AES-256 requires a 32-byte key"):
        crypto.decrypt_with_key("abc", b"short")


def test_with_key_rejects_short_token(key32):
    with pytest.raises(ValueError, match="too short"):
        crypto.decrypt_with_key(base64.urlsafe_b64encode(b"abc").decode(), key32)


# --------------------------------------------------------------------------- #
# encrypt / decrypt (envelope form)                                            #
# --------------------------------------------------------------------------- #
def test_envelope_roundtrip():
    token = crypto.encrypt("top secret", "passphrase")
    assert crypto.decrypt(token, "passphrase") == "top secret"


def test_envelope_roundtrip_unicode():
    token = crypto.encrypt("señor 🚀 ünïcode", "pw")
    assert crypto.decrypt(token, "pw") == "señor 🚀 ünïcode"


def test_envelope_random_salt_produces_distinct_tokens():
    assert crypto.encrypt("x", "pw") != crypto.encrypt("x", "pw")


def test_envelope_wrong_passphrase_rejected():
    token = crypto.encrypt("secret", "correct")
    with pytest.raises(Exception):
        crypto.decrypt(token, "wrong")


def test_envelope_aad_roundtrip():
    token = crypto.encrypt("secret", "pw", aad=b"ctx")
    with pytest.raises(Exception):
        crypto.decrypt(token, "pw")
    assert crypto.decrypt(token, "pw", aad=b"ctx") == "secret"


def test_envelope_rejects_short_token():
    with pytest.raises(ValueError, match="too short"):
        crypto.decrypt(base64.urlsafe_b64encode(b"abc").decode(), "pw")


def test_envelope_tampered_token_rejected():
    token = crypto.encrypt("secret", "pw")
    raw = bytearray(base64.urlsafe_b64decode(token))
    raw[-1] ^= 0x01
    tampered = base64.urlsafe_b64encode(bytes(raw)).decode("ascii")
    with pytest.raises(Exception):
        crypto.decrypt(tampered, "pw")


# --------------------------------------------------------------------------- #
# master_key                                                                   #
# --------------------------------------------------------------------------- #
def test_master_key_reads_env(monkeypatch):
    monkeypatch.setenv("SKYDASH_SECRETS_KEY", "  secret-key  ")
    assert crypto.master_key() == "secret-key"


def test_master_key_custom_env_var(monkeypatch):
    monkeypatch.setenv("MY_KEY", "abc")
    assert crypto.master_key("MY_KEY") == "abc"


def test_master_key_raises_when_unset(monkeypatch):
    monkeypatch.delenv("SKYDASH_SECRETS_KEY", raising=False)
    with pytest.raises(crypto.SecretKeyNotConfigured):
        crypto.master_key()


def test_master_key_raises_when_blank(monkeypatch):
    monkeypatch.setenv("SKYDASH_SECRETS_KEY", "   ")
    with pytest.raises(crypto.SecretKeyNotConfigured):
        crypto.master_key()


# --------------------------------------------------------------------------- #
# selftest                                                                     #
# --------------------------------------------------------------------------- #
def test_selftest_ok():
    result = crypto.selftest()
    assert result["ok"] is True
    assert result["roundtrip"] is True
    assert result["tamper_rejected"] is True
    assert result["cipher"] == "AES-256-GCM"
    assert "PBKDF2" in result["kdf"]


def test_selftest_reports_unavailable_when_missing_dep():
    with mock.patch.object(crypto, "CRYPTO_AVAILABLE", False):
        result = crypto.selftest()
        assert result["ok"] is False
        assert "not installed" in result["reason"]


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))

    with pytest.raises(ValueError, match="too short"):
        crypto.decrypt_with_key(base64.urlsafe_b64encode(b"abc").decode(), key32)



# --------------------------------------------------------------------------- #
# encrypt_with_key / decrypt_with_key                                          #
# --------------------------------------------------------------------------- #
@pytest.fixture()
def key32():
    return os.urandom(32)


def test_with_key_roundtrip(key32):
    token = crypto.encrypt_with_key("hello world", key32)
    assert crypto.decrypt_with_key(token, key32) == "hello world"
