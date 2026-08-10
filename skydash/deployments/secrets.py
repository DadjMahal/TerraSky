"""Secrets management (§29-30, §31) — encrypted at rest.

Values are sealed with AES-256-GCM via :mod:`crypto` (PBKDF2 from
``SKYDASH_SECRETS_KEY``) and stored in a git-ignored JSON file. The API layer
never returns plaintext values: only key metadata plus a mask.

Vault / KMS, per-environment isolation and rotation automation are external-
service items (Iteration 10) — documented, not faked, in the module docstrings
and ``docs/security-governance-iter8.md``.
"""
from __future__ import annotations

import json
import os
import time

DEFAULT_STORE_PATH = os.environ.get("SKYDASH_SECRETS_PATH", "secrets_store.json")


class SecretStore:
    def __init__(self, path: str = DEFAULT_STORE_PATH, key: str | None = None) -> None:
        self._path = path
        self._key = key

    # --- helpers ---------------------------------------------------------
    def _master_key(self) -> str:
        if self._key:
            return self._key
        return crypto.master_key("SKYDASH_SECRETS_KEY")  # raises if unset

    def _load(self) -> dict:
        try:
            with open(self._path, "r", encoding="utf-8") as fh:
                return json.load(fh)
        except (OSError, ValueError):
            return {}

    def _save(self, data: dict) -> None:
        with open(self._path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)

    # --- operations ------------------------------------------------------
    def set_secret(self, key: str, value: str, actor: str = "") -> dict:
        import crypto

        token = crypto.encrypt(value, self._master_key())
        store = self._load()
        now = time.time()
        entry = store.get(key, {})
        store[key] = {"token": token, "created_at": entry.get("created_at", now),
                      "updated_at": now, "updated_by": actor}
        self._save(store)
        return {"key": key, "masked": True, "updated_at": now}

    def get_secret(self, key: str) -> str | None:
        import crypto

        entry = self._load().get(key)
        if not entry:
            return None
        return crypto.decrypt(entry["token"], self._master_key())

    def list_secrets(self) -> list[dict]:
        store = self._load()
        return [{"key": k, "masked": True, "created_at": e.get("created_at"),
                 "updated_at": e.get("updated_at")} for k, e in sorted(store.items())]

    def delete_secret(self, key: str) -> bool:
        store = self._load()
        if key not in store:
            return False
        del store[key]
        self._save(store)
        return True


def make_store(path: str | None = None, key: str | None = None) -> SecretStore:
    return SecretStore(path=path or DEFAULT_STORE_PATH, key=key or None)
