"""Authentication module for SkyDash.

Provides login/logout routes, password hashing, and a login_required decorator
to protect all dashboard routes. The admin password is verified via
config_store (which checks a stored hash first, then falls back to the
SKYDASH_ADMIN_PASSWORD env var).
"""
from __future__ import annotations

import functools
import os
from datetime import timedelta

from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Blueprint for auth routes
auth_bp = Blueprint("auth", __name__)

# Session key and timeout
SESSION_KEY = "skydash_user"
SESSION_TIMEOUT = 3600  # 1 hour in seconds

# Rate limiter — initialized in init_auth() via init_app()
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[],
    storage_uri="memory://",
)


def login_required(view):
    """Decorator that redirects unauthenticated users to the login page."""

    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if not session.get(SESSION_KEY):
            return redirect(url_for("auth.login", next=request.path))
        return view(**kwargs)

    return wrapped_view


@auth_bp.route("/login", methods=["GET", "POST"])
@limiter.limit("5 per minute")
def login():
    """Handle user login."""
    # If already logged in, redirect to dashboard
    if session.get(SESSION_KEY):
        return redirect(url_for("index"))

    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not username or not password:
            error = "Username and password are required."
        else:
            # Use config_store for password verification (supports both
            # stored hash from admin panel and env var fallback)
            import config_store
            if not config_store.verify_password(password):
                error = "Invalid username or password."
            else:
                # Login successful
                session.clear()
                session[SESSION_KEY] = username
                session.permanent = True
                # Set session timeout
                from datetime import timedelta
                session.permanent_session_lifetime = timedelta(seconds=SESSION_TIMEOUT)
                flash("Logged in successfully.", "success")
                next_page = request.args.get("next")
                if next_page:
                    return redirect(next_page)
                return redirect(url_for("index"))

    return render_template("login.html", error=error)


@auth_bp.route("/logout")
def logout():
    """Log the user out and clear the session."""
    session.clear()
    flash("Logged out successfully.", "success")
    return redirect(url_for("auth.login"))


def get_current_user() -> str | None:
    """Return the current logged-in username, or None."""
    return session.get(SESSION_KEY)


def init_auth(app):
    """Register the auth blueprint, configure session settings, and init limiter."""
    app.register_blueprint(auth_bp)
    app.config["SESSION_PERMANENT"] = True
    # Session timeout is set during login
    limiter.init_app(app)