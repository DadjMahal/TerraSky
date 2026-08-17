"""Tests for auth — login/logout routes, password verification, login_required.

Exercises the pure decision helpers (login_required, get_current_user) as well
as the HTTP routes via a Flask test client (GET/POST /login, /logout).
"""
from __future__ import annotations

import os
import sys
from unittest import mock

import pytest

pytest.importorskip("flask")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config_store
import auth

# --------------------------------------------------------------------------- #
# Fixtures                                                                     #
# --------------------------------------------------------------------------- #
@pytest.fixture
def app():
    """A minimal Flask app with the auth blueprint wired up (no index route)."""
    import flask

    test_app = flask.Flask(
        __name__,
        template_folder=os.path.join(
            os.path.dirname(os.path.abspath(auth.__file__)), "templates"
        ),
    )
    test_app.secret_key = "test-secret"
    test_app.config["TESTING"] = True
    test_app.config["WTF_CSRF_ENABLED"] = False

    @test_app.route("/")
    def index():
        return "index"
    test_app.add_url_rule("/", "index", index)

    auth.init_auth(test_app)
    return test_app


@pytest.fixture
def client(app):
    return app.test_client()


# --------------------------------------------------------------------------- #
# login_required                                                               #
# --------------------------------------------------------------------------- #
def test_login_required_allows_authenticated_view():
    @auth.login_required
    def protected(**kwargs):
        return "secret"

    with mock.patch.object(auth, "session", {"skydash_user": "admin"}):
        assert protected() == "secret"


def test_login_required_redirects_unauthenticated_to_login(app):
    @auth.login_required
    def protected(**kwargs):
        return "secret"

    with app.test_request_context("/dashboard"):
        with mock.patch.object(auth, "session", {}):
            resp = protected()
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


# --------------------------------------------------------------------------- #
# get_current_user                                                             #
# --------------------------------------------------------------------------- #
def test_get_current_user_returns_username():
    with mock.patch.object(auth, "session", {auth.SESSION_KEY: "alice"}):
        assert auth.get_current_user() == "alice"
    with mock.patch.object(auth, "session", {}):
        assert auth.get_current_user() is None


# --------------------------------------------------------------------------- #
# /login route                                                                 #
# --------------------------------------------------------------------------- #
def test_login_get_renders_login_page(client):
    with mock.patch.object(auth, "render_template", return_value="login-page-html") as rt:
        resp = client.get("/login")
    assert resp.status_code == 200
    assert resp.data == b"login-page-html"
    assert rt.call_args.args[0] == "login.html"


def test_login_redirects_when_already_logged_in(client):
    with client.session_transaction() as sess:
        sess[auth.SESSION_KEY] = "admin"
    resp = client.get("/login")
    assert resp.status_code == 302
    assert "/" in resp.headers["Location"]


def test_login_missing_credentials_shows_error(client):
    with mock.patch.object(
        auth, "render_template", return_value="login-page-html"
    ) as rt:
        resp = client.post("/login", data={"username": "", "password": ""})
    assert resp.status_code == 200
    kwargs = rt.call_args.kwargs
    assert kwargs.get("error") == "Username and password are required."


def test_login_invalid_password_shows_error(client):
    with mock.patch.object(config_store, "verify_password", return_value=False):
        with mock.patch.object(
            auth, "render_template", return_value="login-page-html"
        ) as rt:
            resp = client.post(
                "/login", data={"username": "admin", "password": "wrong"}
            )
    assert resp.status_code == 200
    kwargs = rt.call_args.kwargs
    assert kwargs.get("error") == "Invalid username or password."


def test_login_success_sets_session_and_redirects_index(client):
    with mock.patch.object(config_store, "verify_password", return_value=True):
        resp = client.post(
            "/login", data={"username": "admin", "password": "correct"}
        )
    assert resp.status_code == 302
    assert resp.headers["Location"].rstrip("/") in ("", "/")
    with client.session_transaction() as sess:
        assert sess.get(auth.SESSION_KEY) == "admin"
        assert sess.get("_permanent")


def test_login_success_respects_next_param(client):
    with mock.patch.object(config_store, "verify_password", return_value=True):
        resp = client.post(
            "/login?next=/dashboard",
            data={"username": "admin", "password": "correct"},
        )
    assert resp.status_code == 302
    assert "/dashboard" in resp.headers["Location"]


# --------------------------------------------------------------------------- #
# /logout route                                                                #
# --------------------------------------------------------------------------- #
def test_logout_clears_session(client):
    with client.session_transaction() as sess:
        sess[auth.SESSION_KEY] = "admin"
    resp = client.get("/logout")
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]
    with client.session_transaction() as sess:
        assert auth.SESSION_KEY not in sess
