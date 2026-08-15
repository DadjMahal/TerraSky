"""Tests for security_checklist — governance controls register (§76-108).

Pure stdlib. Verifies the checklist structure, summary counts, and that
get_checklist returns a defensive (non-mutable) copy.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from security_checklist import SECURITY_CHECKLIST, get_checklist, summary

# --------------------------------------------------------------------------- #
# Structure                                                                   #
# --------------------------------------------------------------------------- #
def test_checklist_is_non_empty():
    assert len(SECURITY_CHECKLIST) > 0


def test_checklist_entry_shape():
    """Every entry has the required fields with valid values."""
    for entry in SECURITY_CHECKLIST:
        assert "id" in entry
        assert "control" in entry
        assert "section" in entry
        assert "status" in entry
        assert "note" in entry
        assert entry["status"] in ("implemented", "partial", "blocked", "pending")


def test_checklist_has_expected_controls():
    controls = {e["control"] for e in SECURITY_CHECKLIST}
    assert "Encryption at rest" in controls
    assert "RBAC roles" in controls
    assert "Audit trail" in controls
    assert "Policy engine" in controls
    assert "Environment protection" in controls


def test_checklist_has_expected_ids():
    ids = [e["id"] for e in SECURITY_CHECKLIST]
    assert "sec-001" in ids
    assert "sec-011" in ids
    assert "sec-015" in ids


def test_checklist_unique_ids():
    ids = [e["id"] for e in SECURITY_CHECKLIST]
    assert len(ids) == len(set(ids)), "Duplicate IDs found in checklist"


# --------------------------------------------------------------------------- #
# Specific control entries                                                    #
# --------------------------------------------------------------------------- #
def test_checklist_sec_001_encryption():
    entry = next(e for e in SECURITY_CHECKLIST if e["id"] == "sec-001")
    assert entry["control"] == "Encryption at rest"
    assert entry["section"] == "§31"
    assert entry["status"] == "implemented"


def test_checklist_sec_005_audit():
    entry = next(e for e in SECURITY_CHECKLIST if e["id"] == "sec-005")
    assert entry["control"] == "Audit trail"
    assert entry["section"] == "§37"
    assert entry["status"] == "implemented"


def test_checklist_sec_011_policy_engine():
    entry = next(e for e in SECURITY_CHECKLIST if e["id"] == "sec-011")
    assert entry["control"] == "Policy engine"
    assert entry["section"] == "§67-68"
    assert entry["status"] == "partial"


def test_checklist_sec_012_environment_protection():
    entry = next(e for e in SECURITY_CHECKLIST if e["id"] == "sec-012")
    assert entry["control"] == "Environment protection"
    assert entry["section"] == "§107"
    assert entry["status"] == "partial"


def test_checklist_sec_004_multi_tenancy_blocked():
    entry = next(e for e in SECURITY_CHECKLIST if e["id"] == "sec-004")
    assert entry["status"] == "blocked"


# --------------------------------------------------------------------------- #
# get_checklist — defensive copy                                              #
# --------------------------------------------------------------------------- #
def test_get_checklist_returns_list():
    result = get_checklist()
    assert isinstance(result, list)
    assert len(result) == len(SECURITY_CHECKLIST)


def test_get_checklist_returns_copy_not_original():
    """Mutating the returned list must not affect SECURITY_CHECKLIST."""
    original = get_checklist()
    result = get_checklist()
    result.clear()
    assert len(get_checklist()) == len(original)


def test_get_checklist_returns_copy_of_dicts():
    """Mutating an entry dict must not affect the original."""
    result = get_checklist()
    first = result[0]
    first["status"] = "hacked"
    original_first = SECURITY_CHECKLIST[0]
    assert original_first["status"] != "hacked"


def test_get_checklist_each_entry_is_a_dict():
    result = get_checklist()
    for entry in result:
        assert isinstance(entry, dict)


# --------------------------------------------------------------------------- #
# summary — count by status                                                  #
# --------------------------------------------------------------------------- #
def test_summary_returns_counts():
    s = summary()
    assert isinstance(s, dict)
    total = sum(s.values())
    assert total == len(SECURITY_CHECKLIST)


def test_summary_has_implemented():
    s = summary()
    assert "implemented" in s
    assert s["implemented"] >= 1


def test_summary_has_blocked():
    s = summary()
    assert "blocked" in s
    assert s["blocked"] >= 1


def test_summary_has_partial():
    s = summary()
    assert "partial" in s


def test_summary_counts_match_filtering():
    """Cross-check summary counts against SECURITY_CHECKLIST."""
    s = summary()
    for status in ("implemented", "partial", "blocked", "pending"):
        expected = sum(1 for e in SECURITY_CHECKLIST if e["status"] == status)
        if expected > 0:
            assert s.get(status, 0) == expected


def test_summary_specific_counts():
    s = summary()
    assert s.get("implemented", 0) == sum(
        1 for e in SECURITY_CHECKLIST if e["status"] == "implemented"
    )
    assert s.get("blocked", 0) == sum(
        1 for e in SECURITY_CHECKLIST if e["status"] == "blocked"
    )


# --------------------------------------------------------------------------- #
# All statuses well-formed                                                     #
# --------------------------------------------------------------------------- #
def test_all_statuses_valid():
    valid = {"implemented", "partial", "blocked", "pending"}
    for entry in SECURITY_CHECKLIST:
        assert entry["status"] in valid, f"Invalid status in {entry['id']}: {entry['status']}"


def test_all_sections_non_empty():
    for entry in SECURITY_CHECKLIST:
        assert entry["section"]
        assert entry["note"]


if __name__ == "__main__":
    failures = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"PASS  {name}")
            except Exception as exc:  # noqa: BLE001
                failures += 1
                print(f"FAIL  {name}: {exc}")
    print(f"\n{failures} failure(s)")
    sys.exit(1 if failures else 0)
