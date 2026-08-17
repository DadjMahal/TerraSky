"""Tests for cli — argparse subcommands + instance operations (§63).

Uses unittest.mock for the state_reader lookups, provider registry and policy
engine, and capsys to capture stdout/stderr. No real CLI effects or provider
I/O are executed: mutating/status handlers are either patched or driven with
mock providers/instances.
"""
from __future__ import annotations

import os
import sys
from unittest import mock

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cli
from models import Instance


def _inst(**overrides) -> Instance:
    """Build a realistic Instance, overriding any field for a given test."""
    values = dict(
        slug="web-1",
        name="web one",
        display_name="web-one",
        provider="aws",
        provider_label="AWS",
        instance_id="i-123",
        region="us-east-1",
        status="running",
        public_ip="1.2.3.4",
        private_ip="10.0.0.5",
        tags={},
    )
    values.update(overrides)
    return Instance(**values)


def _available_provider(**overrides) -> mock.Mock:
    provider = mock.Mock()
    provider.available.return_value = True
    provider.start_instance.return_value = (True, "started")
    provider.stop_instance.return_value = (True, "stopped")
    for key, val in overrides.items():
        setattr(provider, key, val)
    return provider


# --------------------------------------------------------------------------- #
# _print_inst / cmd_list                                                      #
# --------------------------------------------------------------------------- #
def test_print_inst_prints_tsv(capsys):
    cli._print_inst(_inst(slug="web-1", provider_label="AWS",
                          status="running", name="Web"))
    out = capsys.readouterr().out
    assert "web-1\tAWS\trunning\tWeb" in out


def test_cmd_list_prints_header_and_rows(capsys):
    insts = [_inst(slug="a"), _inst(slug="b")]
    with mock.patch.object(cli, "get_instances", return_value=insts):
        rc = cli.cmd_list(mock.Mock())
    assert rc == 0
    out = capsys.readouterr().out
    assert "SLUG" in out and "PROVIDER" in out and "NAME" in out
    assert "a" in out and "b" in out


def test_cmd_list_empty(capsys):
    with mock.patch.object(cli, "get_instances", return_value=[]):
        rc = cli.cmd_list(mock.Mock())
    assert rc == 0
    assert "SLUG" in capsys.readouterr().out


# --------------------------------------------------------------------------- #
# cmd_status                                                                  #
# --------------------------------------------------------------------------- #
def test_cmd_status_not_found(capsys):
    with mock.patch.object(cli, "get_instance_by_slug", return_value=None):
        rc = cli.cmd_status(mock.Mock(slug="missing"))
    assert rc == 2
    assert "not found" in capsys.readouterr().err


def test_cmd_status_refreshes_and_prints_fields(capsys):
    inst = _inst(slug="web-1", region="us-east-1", status="running",
                 public_ip="1.2.3.4", private_ip="10.0.0.5")
    provider = _available_provider()
    with mock.patch.object(cli, "get_instance_by_slug", return_value=inst), \
         mock.patch.object(cli, "get_provider", return_value=provider):
        rc = cli.cmd_status(mock.Mock(slug="web-1"))
    assert rc == 0
    provider.get_instance_details.assert_called_once_with(inst)
    out = capsys.readouterr().out
    for token in ("slug", "web-1", "provider", "AWS", "us-east-1",
                  "running", "1.2.3.4", "10.0.0.5"):
        assert token in out


def test_cmd_status_warns_when_refresh_fails(capsys):
    inst = _inst()
    provider = _available_provider()
    provider.get_instance_details.side_effect = RuntimeError("boom")
    with mock.patch.object(cli, "get_instance_by_slug", return_value=inst), \
         mock.patch.object(cli, "get_provider", return_value=provider):
        rc = cli.cmd_status(mock.Mock(slug="web-1"))
    assert rc == 0
    err = capsys.readouterr().err
    assert "warn" in err and "boom" in err


def test_cmd_status_provider_unavailable_skips_refresh(capsys):
    inst = _inst()
    provider = mock.Mock()
    provider.available.return_value = False
    with mock.patch.object(cli, "get_instance_by_slug", return_value=inst), \
         mock.patch.object(cli, "get_provider", return_value=provider):
        rc = cli.cmd_status(mock.Mock(slug="web-1"))
    assert rc == 0
    provider.get_instance_details.assert_not_called()


# --------------------------------------------------------------------------- #
# _mutating                                                                   #
# --------------------------------------------------------------------------- #
def test_mutating_instance_not_found(capsys):
    with mock.patch.object(cli, "get_instance_by_slug", return_value=None):
        rc = cli._mutating(mock.Mock(slug="missing", approve=False), "start")
    assert rc == 2
    assert "not found" in capsys.readouterr().err


def test_mutating_prod_shield_denied_without_approve(capsys):
    inst = _inst(slug="prod-1")
    with mock.patch.object(cli, "get_instance_by_slug", return_value=inst), \
         mock.patch.object(cli.policy_engine, "DESTRUCTIVE_ACTIONS", frozenset({"stop"})), \
         mock.patch.object(cli.policy_engine, "is_prod_resource", return_value=True):
        rc = cli._mutating(mock.Mock(slug="prod-1", approve=False), "stop")
    assert rc == 3
    err = capsys.readouterr().err
    assert "PROD_SHIELD" in err and "prod-1" in err


def test_mutating_prod_shield_allowed_with_approve(capsys):
    inst = _inst(slug="prod-1")
    provider = _available_provider()
    with mock.patch.object(cli, "get_instance_by_slug", return_value=inst), \
         mock.patch.object(cli, "get_provider", return_value=provider), \
         mock.patch.object(cli.policy_engine, "DESTRUCTIVE_ACTIONS", frozenset({"stop"})), \
         mock.patch.object(cli.policy_engine, "is_prod_resource", return_value=True):
        rc = cli._mutating(mock.Mock(slug="prod-1", approve=True), "stop")
    assert rc == 0
    provider.stop_instance.assert_called_once_with(inst)
    assert "ok:" in capsys.readouterr().out


def test_mutating_provider_unavailable(capsys):
    inst = _inst()
    provider = mock.Mock()
    provider.available.return_value = False
    with mock.patch.object(cli, "get_instance_by_slug", return_value=inst), \
         mock.patch.object(cli, "get_provider", return_value=provider):
        rc = cli._mutating(mock.Mock(slug="web-1", approve=False), "start")
    assert rc == 3
    assert "provider not available" in capsys.readouterr().err


def test_mutating_start_ok(capsys):
    inst = _inst()
    provider = _available_provider()
    with mock.patch.object(cli, "get_instance_by_slug", return_value=inst), \
         mock.patch.object(cli, "get_provider", return_value=provider):
        rc = cli._mutating(mock.Mock(slug="web-1", approve=False), "start")
    assert rc == 0
    provider.start_instance.assert_called_once_with(inst)
    assert "ok:" in capsys.readouterr().out


def test_mutating_stop_failure(capsys):
    inst = _inst()
    provider = _available_provider()
    provider.stop_instance.return_value = (False, "no creds")
    with mock.patch.object(cli, "get_instance_by_slug", return_value=inst), \
         mock.patch.object(cli, "get_provider", return_value=provider):
        rc = cli._mutating(mock.Mock(slug="web-1", approve=False), "stop")
    assert rc == 1
    assert "fail:" in capsys.readouterr().out


# --------------------------------------------------------------------------- #
# main / argparse dispatch                                                    #
# --------------------------------------------------------------------------- #
def test_main_dispatches_to_cmd_list():
    with mock.patch.object(cli, "cmd_list", return_value=9) as m:
        assert cli.main(["list"]) == 9
        m.assert_called_once()


def test_main_dispatches_to_cmd_status():
    with mock.patch.object(cli, "cmd_status", return_value=9) as m:
        assert cli.main(["status", "web-1"]) == 9
        assert m.call_args[0][0].slug == "web-1"


def test_main_start_dispatches_to_mutating_start():
    with mock.patch.object(cli, "_mutating", return_value=9) as m:
        assert cli.main(["start", "web-1", "--approve"]) == 9
        args, action = m.call_args[0]
        assert action == "start"
        assert args.slug == "web-1"
        assert args.approve is True


def test_main_stop_dispatches_to_mutating_stop():
    with mock.patch.object(cli, "_mutating", return_value=9) as m:
        assert cli.main(["stop", "web-1"]) == 9
        assert m.call_args[0][1] == "stop"


def test_main_start_reaches_mutating(capsys):
    """End-to-end: missing instance short-circuits before any provider call."""
    with mock.patch.object(cli, "get_instance_by_slug", return_value=None):
        rc = cli.main(["start", "missing"])
    assert rc == 2


def test_main_unknown_command_exits():
    with pytest.raises(SystemExit):
        cli.main(["frobnicate", "x"])


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))

