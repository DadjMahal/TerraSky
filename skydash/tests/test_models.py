"""Tests for models — the provider-independent Instance dataclass."""
from __future__ import annotations

import os
import sys
from dataclasses import asdict

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import models  # noqa: E402


# --------------------------------------------------------------------------- #
# slugify                                                                      #
# --------------------------------------------------------------------------- #
def test_slugify_lowercases_and_hyphenates():
    assert models.slugify("My Instance Name") == "my-instance-name"


def test_slugify_strips_non_alnum():
    assert models.slugify("a!b@c#d") == "a-b-c-d"


def test_slugify_strips_leading_trailing_hyphens():
    assert models.slugify("--hello--") == "hello"


def test_slugify_empty_and_none():
    assert models.slugify("") == ""
    assert models.slugify(None) == ""


def test_slugify_handles_unicode_and_digits():
    assert models.slugify("Web 2.0 Server") == "web-2-0-server"


# --------------------------------------------------------------------------- #
# Provider metadata                                                            #
# --------------------------------------------------------------------------- #
def test_provider_icon_map_has_all_providers():
    for provider in (models.AWS, models.AZURE, models.ORACLE,
                     models.ALIBABA, models.DIGITALOCEAN):
        assert provider in models.PROVIDER_ICONS
        assert provider in models.PROVIDER_LABELS


def test_provider_icons_are_bootstrap_classes():
    for icon in models.PROVIDER_ICONS.values():
        assert icon.startswith("bi-")


def test_status_constants_distinct():
    statuses = {models.STATUS_RUNNING, models.STATUS_STOPPED,
                models.STATUS_STARTING, models.STATUS_STOPPING,
                models.STATUS_ERROR, models.STATUS_UNKNOWN,
                models.STATUS_LOADING}
    assert len(statuses) == 7


# --------------------------------------------------------------------------- #
# Instance dataclass                                                           #
# --------------------------------------------------------------------------- #
def test_instance_defaults():
    inst = models.Instance()
    assert inst.slug == ""
    assert inst.status == models.STATUS_UNKNOWN
    assert inst.tags == {}
    assert inst.security_groups == []
    assert inst.extra == {}


def test_instance_accepts_known_fields():
    inst = models.Instance(
        slug="aws-hermes",
        name="hermes",
        provider=models.AWS,
        region="us-east-1",
        instance_type="t3.micro",
        public_ip="1.2.3.4",
        tags={"env": "prod"},
    )
    assert inst.slug == "aws-hermes"
    assert inst.tags == {"env": "prod"}


def test_instance_icon_known_provider():
    assert models.Instance(provider=models.AWS).icon == "bi-amazon"
    assert models.Instance(provider=models.AZURE).icon == "bi-microsoft"


def test_instance_icon_unknown_provider_falls_back():
    assert models.Instance(provider="gcp").icon == "bi-question-circle"
    assert models.Instance(provider="").icon == "bi-question-circle"


def test_instance_to_dict_contains_all_fields_and_icon():
    inst = models.Instance(slug="s1", name="n1", provider=models.AWS)
    data = inst.to_dict()
    # to_dict serializes all dataclass fields + the computed icon
    assert data["icon"] == "bi-amazon"
    assert data["slug"] == "s1"
    for field_name in models.Instance.__dataclass_fields__:
        assert field_name in data


def test_instance_to_dict_matches_asdict():
    inst = models.Instance(slug="x", provider=models.ALIBABA, tags={"a": "b"})
    expected = asdict(inst)
    expected["icon"] = "bi-cloud"
    assert inst.to_dict() == expected


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
