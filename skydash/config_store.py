"""Config store for SkyDash site settings and admin profile.

Stores config in a JSON file (skydash_config.json) that persists across restarts.
Handles: site name/description/favicon/logo, admin profile (username/email/
password), hidden instances, and instance display overrides.
"""
from __future__ import annotations

import json
import os
import time

from werkzeug.security import check_password_hash, generate_password_hash

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "skydash_config.json")

DEFAULT_CONFIG: dict = {
    "site_name": "SkyDash",
    "site_description": "Multi-Cloud Infrastructure Management Panel",
    "favicon_url": "",
    "logo_url": "",
    "admin_username": "admin",
    "admin_email": "",
    "admin_password_hash": "",  # empty = use SKYDASH_ADMIN_PASSWORD env var
    "role": "admin",            # RBAC role of the built-in profile (§33; rbac.py)
    "hidden_instances": [],     # slugs to hide from dashboard
    "instance_overrides": {},   # slug -> {display_name, description, tags}
    "custom_instances": [],     # manually added instances
}


def load_config() -> dict:
    """Load config from file, creating defaults if not exists."""
    if not os.path.exists(CONFIG_FILE):
        save_config(DEFAULT_CONFIG.copy())
        return DEFAULT_CONFIG.copy()
    try:
        with open(CONFIG_FILE, "r") as f:
            config = json.load(f)
        result = DEFAULT_CONFIG.copy()
        result.update(config)
        return result
    except Exception:
        return DEFAULT_CONFIG.copy()


def save_config(config: dict):
    """Save config to file."""
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


def get_site_settings() -> dict:
    """Get site settings for templates."""
    config = load_config()
    return {
        "site_name": config.get("site_name", "SkyDash"),
        "site_description": config.get("site_description", ""),
        "favicon_url": config.get("favicon_url", ""),
        "logo_url": config.get("logo_url", ""),
    }


def get_admin_profile() -> dict:
    """Get admin profile info."""
    config = load_config()
    return {
        "username": config.get("admin_username", "admin"),
        "email": config.get("admin_email", ""),
    }


def verify_password(password: str) -> bool:
    """Verify admin password against config hash or env var."""
    config = load_config()
    stored_hash = config.get("admin_password_hash", "")
    if stored_hash:
        return check_password_hash(stored_hash, password)
    env_password = os.environ.get("SKYDASH_ADMIN_PASSWORD", "admin")
    return password == env_password


def set_password(password: str):
    """Set admin password hash in config (overrides env var)."""
    config = load_config()
    config["admin_password_hash"] = generate_password_hash(password)
    save_config(config)


def update_profile(username: str | None = None, email: str | None = None):
    """Update admin profile."""
    config = load_config()
    if username is not None:
        config["admin_username"] = username
    if email is not None:
        config["admin_email"] = email
    save_config(config)


def get_user_role(username: str | None = None) -> str:
    """Resolve the RBAC role for a username (single-profile model today).

    All users resolve to the one profile's ``role`` field (default ``admin``)
    until the multi-user/team model lands (rbac.resolve_role, Iter 9/10).
    """
    return str(load_config().get("role", "admin"))


def set_user_role(role: str) -> str:
    """Persist the profile role (validated against rbac.VALID_ROLES).

    Additive and opt-in: the default remains ``admin``, so existing
    deployments keep exactly their current behavior.
    """
    from rbac import VALID_ROLES

    role = role if role in VALID_ROLES else "admin"
    config = load_config()
    config["role"] = role
    save_config(config)
    return role


def update_site_settings(site_name: str | None = None, site_description: str | None = None,
                          favicon_url: str | None = None, logo_url: str | None = None):
    """Update site settings."""
    config = load_config()
    if site_name is not None:
        config["site_name"] = site_name
    if site_description is not None:
        config["site_description"] = site_description
    if favicon_url is not None:
        config["favicon_url"] = favicon_url
    if logo_url is not None:
        config["logo_url"] = logo_url
    save_config(config)


def hide_instance(slug: str):
    """Add instance slug to hidden list."""
    config = load_config()
    if slug not in config["hidden_instances"]:
        config["hidden_instances"].append(slug)
        save_config(config)


def unhide_instance(slug: str):
    """Remove instance slug from hidden list."""
    config = load_config()
    if slug in config["hidden_instances"]:
        config["hidden_instances"].remove(slug)
        save_config(config)


def get_hidden_instances() -> list:
    """Get list of hidden instance slugs."""
    return load_config().get("hidden_instances", [])


def set_instance_override(slug: str, display_name: str | None = None,
                           description: str | None = None, tags: dict | None = None):
    """Set override metadata for an instance."""
    config = load_config()
    if "instance_overrides" not in config:
        config["instance_overrides"] = {}
    override = config["instance_overrides"].get(slug, {})
    if display_name is not None:
        override["display_name"] = display_name
    if description is not None:
        override["description"] = description
    if tags is not None:
        override["tags"] = tags
    config["instance_overrides"][slug] = override
    save_config(config)


def delete_instance_override(slug: str):
    """Delete override metadata for an instance."""
    config = load_config()
    if "instance_overrides" in config and slug in config["instance_overrides"]:
        del config["instance_overrides"][slug]
        save_config(config)


def get_instance_overrides() -> dict:
    """Get all instance overrides."""
    return load_config().get("instance_overrides", {})


def get_instance_override(slug: str) -> dict:
    """Get override for a specific instance."""
    return get_instance_overrides().get(slug, {})


def add_custom_instance(provider: str, instance_id: str, name: str,
                         region: str = "", instance_type: str = "",
                         description: str = "", readonly: bool = False) -> dict:
    """Add a custom (manually entered) instance."""
    config = load_config()
    if "custom_instances" not in config:
        config["custom_instances"] = []
    inst = {
        "provider": provider,
        "instance_id": instance_id,
        "name": name,
        "region": region,
        "instance_type": instance_type,
        "description": description,
        "readonly": readonly,  # §106 read-only import marker
        "slug": f"{provider}-{name.lower().replace(' ', '-')}",
    }
    existing = [i for i in config["custom_instances"] if i["instance_id"] == instance_id]
    if not existing:
        config["custom_instances"].append(inst)
        save_config(config)
    return inst


def remove_custom_instance(instance_id: str):
    """Remove a custom instance by instance_id."""
    config = load_config()
    config["custom_instances"] = [
        i for i in config.get("custom_instances", []) if i["instance_id"] != instance_id
    ]
    save_config(config)


def get_custom_instances() -> list:
    """Get all custom instances."""
    return load_config().get("custom_instances", [])


# --- Custom domain mapping (#19) ------------------------------------------
def get_domain_mappings() -> list:
    """Return all custom domain→instance mappings [{domain, slug, created}]."""
    return load_config().get("domain_mappings", [])


def add_domain_mapping(domain: str, slug: str) -> dict:
    """Map a custom domain to an instance slug."""
    domain = (domain or "").strip().lower()
    if not domain or not slug:
        return {}
    config = load_config()
    mappings = config.get("domain_mappings", [])
    mappings = [m for m in mappings if m.get("domain") != domain]
    entry = {"domain": domain, "slug": slug, "created": time.time()}
    mappings.append(entry)
    config["domain_mappings"] = mappings
    save_config(config)
    return entry


def remove_domain_mapping(domain: str) -> None:
    """Remove a custom domain mapping."""
    domain = (domain or "").strip().lower()
    config = load_config()
    config["domain_mappings"] = [
        m for m in config.get("domain_mappings", []) if m.get("domain") != domain
    ]
    save_config(config)