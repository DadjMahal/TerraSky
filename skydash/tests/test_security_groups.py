"""Unit tests for the normalized security-group helpers and the AWS provider's
get_security_groups method (Task 4).

Uses unittest.mock so no real cloud credentials or network calls are needed.
"""
from __future__ import annotations

import os
import sys
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from providers.security_groups import (  # noqa: E402
    make_group,
    make_rule,
    normalize_port,
)


# --------------------------------------------------------------------------- #
# providers/security_groups.py — pure helpers                                 #
# --------------------------------------------------------------------------- #
def test_normalize_port_single():
    assert normalize_port(22, 22) == "22"


def test_normalize_port_range():
    assert normalize_port(8000, 9000) == "8000-9000"


def test_normalize_port_all():
    assert normalize_port(None, None) == "all"
    assert normalize_port("", "") == "all"


def test_make_rule_shape():
    r = make_rule("tcp", 22, 22, "10.0.0.0/8", "inbound", "allow", "ssh")
    assert r["protocol"] == "tcp"
    assert r["port"] == "22"
    assert r["port_from"] == 22
    assert r["port_to"] == 22
    assert r["source"] == "10.0.0.0/8"
    assert r["direction"] == "inbound"
    assert r["action"] == "allow"
    assert r["description"] == "ssh"


def test_make_rule_default_source():
    r = make_rule("all", None, None, None, "outbound", "allow")
    assert r["source"] == "0.0.0.0/0"
    assert r["port"] == "all"


def test_make_rule_deny_action():
    r = make_rule("tcp", 80, 80, "0.0.0.0/0", "inbound", "deny")
    assert r["action"] == "deny"


def test_make_group_shape():
    sg = make_group("sg-1", "web", "AWS SecurityGroup", "aws",
                    [{"protocol": "tcp"}], [{"protocol": "all"}])
    assert sg["id"] == "sg-1"
    assert sg["name"] == "web"
    assert sg["type"] == "AWS SecurityGroup"
    assert sg["provider"] == "aws"
    assert sg["inbound"] == [{"protocol": "tcp"}]
    assert sg["outbound"] == [{"protocol": "all"}]


# --------------------------------------------------------------------------- #
# AWS provider.get_security_groups — mocked boto3                              #
# --------------------------------------------------------------------------- #
def _make_provider():
    from providers.aws import AwsProvider
    return AwsProvider()


@mock.patch("boto3.client")
def test_aws_get_security_groups_with_credentials(mock_client):
    os.environ["AWS_ACCESS_KEY_ID"] = "test"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "test"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
    try:
        ec2 = mock.Mock()
        mock_client.return_value = ec2
        ec2.describe_instances.return_value = {
            "Reservations": [{
                "Instances": [{
                    "NetworkInterfaces": [{
                        "Groups": [{"GroupId": "sg-from-eni"}]
                    }]
                }]
            }]
        }
        paginator = mock.Mock()
        paginator.paginate.return_value = [{
            "SecurityGroups": [{
                "GroupId": "sg-from-eni",
                "GroupName": "web-sg",
                "IpPermissions": [{
                    "IpProtocol": "tcp",
                    "FromPort": 22,
                    "ToPort": 22,
                    "IpRanges": [{"CidrIp": "10.0.0.0/8", "Description": "office"}],
                    "UserIdGroupPairs": [{"GroupId": "sg-other"}],
                }],
                "IpPermissionsEgress": [{
                    "IpProtocol": "-1",
                    "FromPort": None,
                    "ToPort": None,
                    "IpRanges": [{"CidrIp": "0.0.0.0/0"}],
                }],
            }]
        }]
        ec2.get_paginator.return_value = paginator

        from models import Instance
        inst = Instance(slug="t", name="t", provider="aws", instance_id="i-1")
        inst.security_groups = []
        prov = _make_provider()
        groups = prov.get_security_groups(inst)

        assert len(groups) == 1
        g = groups[0]
        assert g["id"] == "sg-from-eni"
        assert g["name"] == "web-sg"
        assert g["type"] == "AWS SecurityGroup"
        assert len(g["inbound"]) == 2
        assert g["inbound"][0]["port"] == "22"
        assert g["inbound"][0]["source"] == "10.0.0.0/8"
        assert g["inbound"][1]["source"] == "sg-other"
        assert g["outbound"][0]["action"] == "allow"
    finally:
        for k in ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_DEFAULT_REGION"):
            os.environ.pop(k, None)


@mock.patch("boto3.client")
def test_aws_get_security_groups_without_credentials(mock_client):
    os.environ.pop("AWS_ACCESS_KEY_ID", None)
    os.environ.pop("AWS_SECRET_ACCESS_KEY", None)
    os.environ.pop("AWS_DEFAULT_REGION", None)
    from models import Instance
    inst = Instance(slug="t", name="t", provider="aws", instance_id="i-1")
    inst.security_groups = ["sg-1", "sg-2"]
    prov = _make_provider()
    groups = prov.get_security_groups(inst)
    # Without creds the provider gracefully returns the TF-state hints as a list
    # (raw ids, not fully normalized) and never calls boto3.
    assert isinstance(groups, list)
    mock_client.assert_not_called()


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
