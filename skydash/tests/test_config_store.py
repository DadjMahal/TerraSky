"""Tests for config_store — JSON-backed site settings, admin profile,
hidden instances, instance overrides, custom instances and domain mappings.

Pure stdlib: CONFIG_FILE is redirected to a temp path and werkzeug's
password hashing functions are mocked so nothing touches real disk or crypto.
"""
from __future__ import annotations

import copy
import json
import os
import sys
from unittest import mock

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config_store

# Pristine deep copy used to reset DEFAULT_CONFIG per test. config_store's
# load_config() shallow-copies DEFAULT_CONFIG, so add_*/set_* helpers mutate
# the shared nested lists/dicts in place; resetting the module default keeps
# state from leaking between tests.
_PRISTINE_DEFAULT = copy.deepcopy(config_store.DEFAULT_CONFIG)


# --------------------------------------------------------------------------- #
# Fixtures                                                                    #
# --------------------------------------------------------------------------- #
@pytest.fixture(autouse=True)
def _isolated_config(tmp_path, monkeypatch):
    """Redirect CONFIG_FILE to a temp path, clear env password, and reset the
    in-memory DEFAULT_CONFIG so no test sees another test's writes."""
    monkeypatch.setattr(config_store, "DEFAULT_CONFIG", copy.deepcopy(_PRISTINE_DEFAULT))
    monkeypatch.setattr(config_store, "CONFIG_FILE", str(tmp_path / "skydash_config.json"))
    monkeypatch.delenv("SKYDASH_ADMIN_PASSWORD", raising=False)
    yield tmp_path


# --------------------------------------------------------------------------- #
# load_config / save_config                                                   #
# --------------------------------------------------------------------------- #
def test_load_config_creates_defaults_when_file_missing(tmp_path):
    cfg = config_store.load_config()
    assert cfg == config_store.DEFAULT_CONFIG
    # a fresh file should now exist on disk
    assert (tmp_path / "skydash_config.json").exists()


def test_load_config_returns_copy_not_shared_ref():
    cfg = config_store.load_config()
    cfg["site_name"] = "mutated"
    assert config_store.DEFAULT_CONFIG["site_name"] == "SkyDash"
    again = config_store.load_config()
    assert again["site_name"] == "SkyDash"


def test_load_config_merges_saved_values_over_defaults():
    config_store.save_config({"site_name": "Acme Cloud"})
    cfg = config_store.load_config()
    assert cfg["site_name"] == "Acme Cloud"
    # fields absent from the file keep their defaults
    assert cfg["site_description"] == config_store.DEFAULT_CONFIG["site_description"]
    assert cfg["hidden_instances"] == []


def test_load_config_falls_back_on_corrupt_json(tmp_path):
    (tmp_path / "skydash_config.json").write_text("{not valid json!!")
    cfg = config_store.load_config()
    assert cfg == config_store.DEFAULT_CONFIG


def test_save_config_writes_json_file(tmp_path):
    config_store.save_config({"site_name": "Terra", "hidden_instances": ["a"]})
    raw = (tmp_path / "skydash_config.json").read_text()
    assert json.loads(raw) == {"site_name": "Terra", "hidden_instances": ["a"]}


# --------------------------------------------------------------------------- #
# Site settings                                                               #
# --------------------------------------------------------------------------- #
def test_get_site_settings_defaults():
    settings = config_store.get_site_settings()
    assert settings == {
        "site_name": "SkyDash",
        "site_description": "Multi-Cloud Infrastructure Management Panel",
        "favicon_url": "",
        "logo_url": "",
    }


def test_update_site_settings_and_read_back():
    config_store.update_site_settings(site_name="Nimbus", logo_url="/static/logo.png")
    settings = config_store.get_site_settings()
    assert settings["site_name"] == "Nimbus"
    assert settings["logo_url"] == "/static/logo.png"
    assert settings["favicon_url"] == ""


def test_update_site_settings_partial_keeps_other_fields():
    config_store.update_site_settings(site_name="A")
    config_store.update_site_settings(site_description="B")
    settings = config_store.get_site_settings()
    assert settings["site_name"] == "A"
    assert settings["site_description"] == "B"


# --------------------------------------------------------------------------- #
# Admin profile / password                                                    #
# --------------------------------------------------------------------------- #
def test_get_admin_profile_defaults():
    profile = config_store.get_admin_profile()
    assert profile == {"username": "admin", "email": ""}


def test_update_profile_sets_username_and_email():
    config_store.update_profile(username="ops", email="ops@example.com")
    profile = config_store.get_admin_profile()
    assert profile == {"username": "ops", "email": "ops@example.com"}


def test_update_profile_partial_keeps_other_fields():
    config_store.update_profile(username="ops")
    config_store.update_profile(email="ops@example.com")
    profile = config_store.get_admin_profile()
    assert profile == {"username": "ops", "email": "ops@example.com"}


def test_verify_password_env_fallback(monkeypatch):
    monkeypatch.setenv("SKYDASH_ADMIN_PASSWORD", "s3cret")
    assert config_store.verify_password("s3cret") is True
    assert config_store.verify_password("wrong") is False


def test_verify_password_env_default_admin():
    with mock.patch.dict(os.environ, {"SKYDASH_ADMIN_PASSWORD": "admin"}, clear=False):
        assert config_store.verify_password("admin") is True
        assert config_store.verify_password("nope") is False


def test_verify_password_prefers_stored_hash_over_env(monkeypatch):
    monkeypatch.setenv("SKYDASH_ADMIN_PASSWORD", "env-pass")
    config_store.save_config({"admin_password_hash": "pbkdf2:stored"})
    with mock.patch.object(config_store, "check_password_hash", return_value=True) as check:
        assert config_store.verify_password("whatever") is True
    check.assert_called_once_with("pbkdf2:stored", "whatever")


def test_verify_password_uses_stored_hash():
    config_store.save_config({"admin_password_hash": "pbkdf2:abc"})
    with mock.patch.object(config_store, "check_password_hash", return_value=False) as check:
        assert config_store.verify_password("x") is False
    check.assert_called_once_with("pbkdf2:abc", "x")


def test_set_password_stores_generated_hash():
    with mock.patch.object(config_store, "generate_password_hash", return_value="hash:123"):
        config_store.set_password("new-pass")
    cfg = config_store.load_config()
    assert cfg["admin_password_hash"] == "hash:123"
    # a stored hash now takes precedence over the env fallback
    with mock.patch.dict(os.environ, {"SKYDASH_ADMIN_PASSWORD": "env-pass"}), \
            mock.patch.object(config_store, "check_password_hash", return_value=True):
        assert config_store.verify_password("new-pass") is True


# --------------------------------------------------------------------------- #
# Role                                                                        #
# --------------------------------------------------------------------------- #
def test_get_user_role_defaults_to_admin():
    assert config_store.get_user_role() == "admin"
    assert config_store.get_user_role("anyone") == "admin"


def test_set_user_role_valid_role_persisted():
    assert config_store.set_user_role("operator") == "operator"
    assert config_store.get_user_role() == "operator"


def test_set_user_role_invalid_falls_back_to_admin():
    assert config_store.set_user_role("superuser") == "admin"
    assert config_store.get_user_role() == "admin"


# --------------------------------------------------------------------------- #
# Hidden instances                                                            #
# --------------------------------------------------------------------------- #
def test_hide_and_get_hidden_instances():
    assert config_store.get_hidden_instances() == []
    config_store.hide_instance("web-1")
    config_store.hide_instance("db-1")
    assert config_store.get_hidden_instances() == ["web-1", "db-1"]


def test_hide_instance_is_idempotent():
    config_store.hide_instance("web-1")
    config_store.hide_instance("web-1")
    assert config_store.get_hidden_instances() == ["web-1"]


def test_unhide_instance_removes_slug():
    config_store.hide_instance("web-1")
    config_store.hide_instance("db-1")
    config_store.unhide_instance("web-1")
    assert config_store.get_hidden_instances() == ["db-1"]
    # unhiding a slug that is not hidden is a no-op
    config_store.unhide_instance("ghost")
    assert config_store.get_hidden_instances() == ["db-1"]


# --------------------------------------------------------------------------- #
# Instance overrides                                                          #
# --------------------------------------------------------------------------- #
def test_get_instance_overrides_default_empty():
    assert config_store.get_instance_overrides() == {}
    assert config_store.get_instance_override("web-1") == {}


def test_set_instance_override_all_fields():
    config_store.set_instance_override("web-1", display_name="Web One",
                                       description="frontend", tags={"env": "dev"})
    override = config_store.get_instance_override("web-1")
    assert override == {"display_name": "Web One", "description": "frontend",
                        "tags": {"env": "dev"}}


def test_set_instance_override_partial_merge():
    config_store.set_instance_override("web-1", display_name="Web One")
    config_store.set_instance_override("web-1", description="frontend")
    override = config_store.get_instance_override("web-1")
    assert override["display_name"] == "Web One"
    assert override["description"] == "frontend"
    assert "tags" not in override


def test_delete_instance_override():
    config_store.set_instance_override("web-1", display_name="Web One")
    config_store.delete_instance_override("web-1")
    assert config_store.get_instance_override("web-1") == {}
    # deleting a missing override is a no-op
    config_store.delete_instance_override("ghost")


# --------------------------------------------------------------------------- #
# Custom instances                                                            #
# --------------------------------------------------------------------------- #
def test_add_custom_instance_builds_slug_and_readonly_flag():
    inst = config_store.add_custom_instance("aws", "i-123", "Web Server",
                                            region="us-east-1",
                                            instance_type="t3.micro",
                                            description="web tier",
                                            readonly=True)
    assert inst["slug"] == "aws-web-server"
    assert inst["instance_id"] == "i-123"
    assert inst["readonly"] is True
    assert inst["region"] == "us-east-1"
    assert config_store.get_custom_instances() == [inst]


def test_add_custom_instance_defaults():
    inst = config_store.add_custom_instance("gcp", "g-1", "Batch")
    assert inst["region"] == ""
    assert inst["instance_type"] == ""
    assert inst["description"] == ""
    assert inst["readonly"] is False
    assert inst["slug"] == "gcp-batch"


def test_add_custom_instance_deduplicates_by_instance_id():
    first = config_store.add_custom_instance("aws", "i-123", "First")
    second = config_store.add_custom_instance("aws", "i-123", "Second")
    instances = config_store.get_custom_instances()
    assert len(instances) == 1
    # the stored entry is the originally added one, not the duplicate attempt
    assert instances[0] == first
    assert instances[0]["instance_id"] == "i-123"
    assert second["instance_id"] == "i-123"


def test_remove_custom_instance():
    config_store.add_custom_instance("aws", "i-123", "Web")
    config_store.add_custom_instance("gcp", "g-1", "Batch")
    config_store.remove_custom_instance("i-123")
    ids = [i["instance_id"] for i in config_store.get_custom_instances()]
    assert ids == ["g-1"]


def test_remove_custom_instance_missing_is_noop():
    config_store.add_custom_instance("aws", "i-123", "Web")
    config_store.remove_custom_instance("ghost")
    assert len(config_store.get_custom_instances()) == 1


# --------------------------------------------------------------------------- #
# Domain mappings                                                             #
# --------------------------------------------------------------------------- #
def test_get_domain_mappings_default_empty():
    assert config_store.get_domain_mappings() == []


def test_add_domain_mapping_normalizes_domain_and_records_created():
    with mock.patch("config_store.time.time", return_value=1700000000.0) as fake_time:
        entry = config_store.add_domain_mapping("Example.COM", "web-1")
    assert entry == {"domain": "example.com", "slug": "web-1", "created": 1700000000.0}
    assert config_store.get_domain_mappings() == [entry]
    fake_time.assert_called()


def test_add_domain_mapping_replaces_existing_domain():
    with mock.patch("config_store.time.time", return_value=1.0):
        config_store.add_domain_mapping("a.example.com", "web-1")
    with mock.patch("config_store.time.time", return_value=2.0):
        entry = config_store.add_domain_mapping("A.EXAMPLE.COM", "db-1")
    mappings = config_store.get_domain_mappings()
    assert len(mappings) == 1
    assert mappings[0]["domain"] == "a.example.com"
    assert mappings[0]["slug"] == "db-1"
    assert mappings[0]["created"] == 2.0


def test_add_domain_mapping_empty_values_return_empty_dict():
    assert config_store.add_domain_mapping("", "web-1") == {}
    assert config_store.add_domain_mapping("   ", "web-1") == {}
    assert config_store.add_domain_mapping("example.com", "") == {}
    assert config_store.get_domain_mappings() == []


def test_remove_domain_mapping():
    config_store.add_domain_mapping("a.example.com", "web-1")
    config_store.add_domain_mapping("b.example.com", "db-1")
    config_store.remove_domain_mapping("A.EXAMPLE.COM")  # normalization applies
    domains = [m["domain"] for m in config_store.get_domain_mappings()]
    assert domains == ["b.example.com"]
    config_store.remove_domain_mapping("b.example.com")
    assert config_store.get_domain_mappings() == []


if __name__ == "__main__":
    import pytest as _pytest
    sys.exit(_pytest.main([__file__, "-v"]))
