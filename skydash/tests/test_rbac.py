"""Tests for rbac — role constants, permissions, and role resolution (§33/§34).

Covers normalize_role/role_can hierarchy and the require_role /
require_permission Flask decorators (mocked session + config_store).
"""
from __future__ import annotations

import os
import sys
from unittest import mock

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import rbac


# --------------------------------------------------------------------------- #
# normalize_role                                                               #
# --------------------------------------------------------------------------- #
def test_normalize_role_valid():
    assert rbac.normalize_role("admin") == "admin"
    assert rbac.normalize_role("operator") == "operator"
    assert rbac.normalize_role("readonly") == "readonly"


def test_normalize_role_invalid_defaults_to_admin():
    assert rbac.normalize_role("superuser") == "admin"


def test_normalize_role_none_defaults_to_admin():
    assert rbac.normalize_role(None) == "admin"


def test_constants():
    assert rbac.ADMIN == "admin"
    assert rbac.OPERATOR == "operator"
    assert rbac.READONLY == "readonly"
    assert rbac.DEFAULT_ROLE == "admin"
    assert rbac.VALID_ROLES == ("admin", "operator", "readonly")


# --------------------------------------------------------------------------- #
# role_can — permission mapping + hierarchy                                    #
# --------------------------------------------------------------------------- #
def test_admin_can_everything():
    assert rbac.role_can("admin", "server.read") is True
    assert rbac.role_can("admin", "server.destroy") is True
    assert rbac.role_can("admin", "anything.at.all") is True


def test_operator_explicit_permissions():
    assert rbac.role_can("operator", "server.read") is True
    assert rbac.role_can("operator", "server.start") is True
    assert rbac.role_can("operator", "server.stop") is True
    assert rbac.role_can("operator", "server.reboot") is True
    assert rbac.role_can("operator", "server.exec") is True
    assert rbac.role_can("operator", "instance.manage") is True


def test_operator_denied_destructive_and_unknown():
    assert rbac.role_can("operator", "server.destroy") is False
    assert rbac.role_can("operator", "terraform.destroy") is False
    assert rbac.role_can("operator", "resource.delete") is False
    assert rbac.role_can("operator", "admin.panel") is False


def test_readonly_only_reads():
    assert rbac.role_can("readonly", "server.read") is True
    assert rbac.role_can("readonly", "server.start") is False
    assert rbac.role_can("readonly", "server.destroy") is False


def test_hierarchy_grants_lower_role_permissions():
    # Admin implicitly gets everything lower roles have.
    assert rbac.role_can("admin", "instance.manage") is True
    assert rbac.role_can("operator", "server.read") is True  # readonly perm


def test_unknown_role_normalized_then_checked():
    # Unknown normalizes to admin (top of hierarchy).
    assert rbac.role_can("bogus", "server.destroy") is True

# --------------------------------------------------------------------------- #
# resolve_role                                                                 #
# --------------------------------------------------------------------------- #
def test_resolve_role_uses_config_store(monkeypatch):
    fake = mock.Mock()
    fake.get_user_role.return_value = "operator"
    monkeypatch.setitem(sys.modules, "config_store", fake)
    assert rbac.resolve_role("alice") == "operator"


def test_resolve_role_degrades_to_default_on_error(monkeypatch):
    fake = mock.Mock()
    fake.get_user_role.side_effect = Exception("boom")
    monkeypatch.setitem(sys.modules, "config_store", fake)
    assert rbac.resolve_role("alice") == "admin"


def test_resolve_role_normalizes_invalid(monkeypatch):
    fake = mock.Mock()
    fake.get_user_role.return_value = "ghost"
    monkeypatch.setitem(sys.modules, "config_store", fake)
    assert rbac.resolve_role("alice") == "admin"


def test_current_roles():
    with mock.patch.object(rbac, "resolve_role", return_value="operator"):
        assert rbac.current_roles() == ("operator",)


# --------------------------------------------------------------------------- #
# require_role / require_permission decorators (Flask)                         #
# --------------------------------------------------------------------------- #
def _make_flask_app():
    from flask import Flask
    app = Flask(__name__)
    app.secret_key = "test-secret"
    return app


def test_require_role_allows_matching_role():
    app = _make_flask_app()
    with app.test_request_context("/admin"):
        with mock.patch.object(rbac, "_session_user", return_value="alice"):
            with mock.patch.object(rbac, "resolve_role", return_value="operator"):
                @rbac.require_role("operator", "admin")
                def view():
                    return "ok"
                assert view() == "ok"


def test_require_role_denies_wrong_role_with_403():
    app = _make_flask_app()
    with app.test_request_context("/admin"):
        with mock.patch.object(rbac, "_session_user", return_value="alice"):
            with mock.patch.object(rbac, "resolve_role", return_value="readonly"):
                @rbac.require_role("admin", "operator")
                def view():
                    return "ok"
                body, code = view()
                assert code == 403
                assert body.get_json()["code"] == "FORBIDDEN"


def test_require_role_unauthenticated_api_returns_401():
    app = _make_flask_app()
    with app.test_request_context("/api/thing"):
        with mock.patch.object(rbac, "_session_user", return_value=None):
            @rbac.require_role("admin")
            def view():
                return "ok"
            body, code = view()
            assert code == 401
            assert body.get_json()["code"] == "UNAUTHENTICATED"


def test_require_role_unauthenticated_ui_redirects_to_login():
    app = _make_flask_app()
    app.add_url_rule("/login", "auth.login", lambda: "login")
    with app.test_request_context("/page"):
        with mock.patch.object(rbac, "_session_user", return_value=None):
            @rbac.require_role("admin")
            def view():
                return "ok"
            resp = view()
            assert resp.status_code in (301, 302)


def test_require_permission_allows_granted():
    app = _make_flask_app()
    with app.test_request_context("/ops"):
        with mock.patch.object(rbac, "_session_user", return_value="alice"):
            with mock.patch.object(rbac, "resolve_role", return_value="operator"):
                @rbac.require_permission("server.start", "server.stop")
                def view():
                    return "ok"
                assert view() == "ok"


def test_require_permission_denies_ungranted():
    app = _make_flask_app()
    with app.test_request_context("/ops"):
        with mock.patch.object(rbac, "_session_user", return_value="alice"):
            with mock.patch.object(rbac, "resolve_role", return_value="readonly"):
                @rbac.require_permission("server.destroy")
                def view():
                    return "ok"
                body, code = view()
                assert code == 403
                assert body.get_json()["code"] == "FORBIDDEN"


def test_require_permission_admin_allowed_any():
    # Reserved sanity: admin holds "*" so any permission is granted.
    app = _make_flask_app()
    with app.test_request_context("/ops"):
        with mock.patch.object(rbac, "_session_user", return_value="alice"):
            with mock.patch.object(rbac, "resolve_role", return_value="admin"):
                @rbac.require_permission("server.destroy")
                def view():
                    return "ok"
                assert view() == "ok"
