"""Role-Based Access Control (§33) + resource-level authorization (§34).

In-process role layer for SkyDash. Multi-tenancy (§35-36 — org/project
scoping, row-level isolation, per-tenant role assignment) is **BLOCKED**: it
requires the domain-model database from Iterations 9/10 (see
``docs/domain-model.md``). Until then this module ships:

* role constants ``admin > operator > readonly``,
* a permission map and ``role_can()`` for role -> permission checks,
* ``resolve_role()`` — role resolution backed by the ``config_store`` profile
  (additive; defaults to ``admin`` for the single built-in user),
* ``require_role(*roles)`` / ``require_permission(*perms)`` Flask decorators
  that return the standardized **403 FORBIDDEN** JSON envelope.

Importing this module is dependency-light on purpose: Flask and
``config_store`` are imported lazily inside the decorators/callables so the
module can be unit-tested standalone (this sandbox has no Flask installed).
"""
from __future__ import annotations

import functools

# --- Role constants (§33) ---------------------------------------------------
ADMIN = "admin"          # full control incl. admin panel + destructive ops
OPERATOR = "operator"    # operates instances (start/stop/reboot) + reads
READONLY = "readonly"    # read-only visibility of inventory/status

VALID_ROLES = (ADMIN, OPERATOR, READONLY)
DEFAULT_ROLE = ADMIN

# Higher number = more privileged. Admin can do everything an operator can, etc.
ROLE_HIERARCHY: dict[str, int] = {
    ADMIN: 3,
    OPERATOR: 2,
    READONLY: 1,
}

# Role -> set of permissions. "*" = everything.
ROLE_PERMISSIONS: dict[str, set[str]] = {
    ADMIN: {"*"},
    OPERATOR: {
        "server.read",
        "server.start",
        "server.stop",
        "server.reboot",
        "server.exec",
        "instance.manage",
    },
    READONLY: {"server.read"},
}

DESTRUCTIVE_PERMISSIONS = {
    "server.destroy",
    "server.terminate",
    "server.stop",
    "server.reboot",
    "terraform.destroy",
    "resource.delete",
}


def _denied_json(required: str) -> tuple:
    """Build the standardized 403 FORBIDDEN JSON envelope (tuple for Flask)."""
    from flask import jsonify

    return (
        jsonify(
            {
                "status": "error",
                "error": f"Forbidden: requires {required}.",
                "code": "FORBIDDEN",
            }
        ),
        403,
    )


def normalize_role(role: str | None) -> str:
    """Coerce a role string into a valid role constant (default: admin)."""
    if role in VALID_ROLES:
        return role
    return DEFAULT_ROLE


def role_can(role: str | None, permission: str) -> bool:
    """True when ``role`` (role hierarchy aware) grants ``permission``."""
    role = normalize_role(role)
    if permission == "*":
        return role in ROLE_PERMISSIONS and "*" in ROLE_PERMISSIONS[role]
    perms = ROLE_PERMISSIONS.get(role, set())
    if "*" in perms or permission in perms:
        return True
    # Hierarchy: a more privileged role implicitly grants this role's perms.
    mine = ROLE_HIERARCHY.get(role, 0)
    return any(
        ROLE_HIERARCHY.get(r, 0) < mine and permission in r_perms
        for r, r_perms in ROLE_PERMISSIONS.items()
        if r != role
    )
def _session_user():
    """Current logged-in username from the Flask session (lazy import)."""
    try:
        from flask import session
        from auth import SESSION_KEY

        return session.get(SESSION_KEY)
    except Exception:  # noqa: BLE001 - no Flask here (offline unit tests)
        return None


def resolve_role(username: str | None = None) -> str:
    """Resolve a user's role from the ``config_store`` profile (additive).

    With the current single-user model there is exactly one profile; its
    ``role`` field (default ``admin``) is returned for any username. When the
    multi-user/team model lands (Iterations 9/10) this becomes a per-user
    lookup — the signature is already future-proof.
    """
    import config_store  # lazy: this sandbox has no werkzeug/flask installed

    if username is None:
        username = _session_user()
    try:
        return normalize_role(config_store.get_user_role(username))
    except Exception:  # noqa: BLE001 - degrade to default role, never crash authz
        return DEFAULT_ROLE


def current_roles() -> tuple[str, ...]:
    """Roles currently active for the session user (single-role today)."""
    return (resolve_role(),)
def require_role(*roles: str):
    """Decorator: allow only users holding at least one of ``roles``.

    Unauthenticated requests are redirected to login (UI) or get a 401 JSON
    envelope (``/api/*``). Authorized-but-wrong-role requests always return
    the standardized ``403 {"code": "FORBIDDEN"}`` JSON envelope. Stack below
    or above :func:`auth.login_required` — works either way.
    """

    def decorator(view):
        @functools.wraps(view)
        def wrapped(*args, **kwargs):
            from flask import request, redirect, url_for

            user = _session_user()
            if not user:
                if request.path.startswith("/api/"):
                    return (_json_unauthenticated(), 401)
                return redirect(url_for("auth.login", next=request.path))
            if resolve_role(user) not in roles:
                return _denied_json("role(s): " + ", ".join(roles))
            return view(*args, **kwargs)

        return wrapped

    return decorator


def require_permission(*permissions: str):
    """Decorator: allow only users whose role grants *any* permission listed.

    Returns the same 403 FORBIDDEN JSON envelope as :func:`require_role`.
    Resource-level checks (which permission *and* which org/project/instance)
    belong here once the domain-model DB lands (§34, Iter 9/10).
    """

    def decorator(view):
        @functools.wraps(view)
        def wrapped(*args, **kwargs):
            from flask import request, redirect, url_for

            user = _session_user()
            if not user:
                if request.path.startswith("/api/"):
                    return (_json_unauthenticated(), 401)
                return redirect(url_for("auth.login", next=request.path))
            granted = any(
                role_can(role, perm)
                for perm in permissions
                for role in current_roles()
            )
            if not granted:
                return _denied_json("permission(s): " + ", ".join(permissions))
            return view(*args, **kwargs)

        return wrapped

    return decorator


def _json_unauthenticated():
    from flask import jsonify

    return jsonify(
        {
            "status": "error",
            "error": "Authentication required.",
            "code": "UNAUTHENTICATED",
        }
    )