"""SkyDash - lightweight multi-cloud infrastructure management panel.

The Flask layer is intentionally thin: it renders the dashboard and detail pages
and exposes JSON endpoints for live status and instance actions. All
cloud-specific logic lives in the provider implementations under `providers/`,
reached through the provider registry, so business logic stays
provider-independent (see SPEC.md "Architecture Goals").
"""
from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from flask import Flask, abort, jsonify, redirect, render_template, request, url_for

from models import STATUS_UNKNOWN
from providers.registry import get_provider
from state_reader import get_instance_by_slug, get_instances
from auth import auth_bp, init_auth, login_required, get_current_user
import hermes_agent
import config_store


def _apply_overrides(inst_dict: dict) -> dict:
    """Apply instance display overrides (display_name, description, tags) from config_store."""
    overrides = config_store.get_instance_override(inst_dict.get("slug", ""))
    if overrides:
        if "display_name" in overrides and overrides["display_name"]:
            inst_dict["name"] = overrides["display_name"]
            inst_dict["display_name"] = overrides["display_name"]
        if "description" in overrides and overrides["description"]:
            inst_dict["description"] = overrides["description"]
        if "tags" in overrides and overrides["tags"]:
            inst_dict["tags"] = overrides["tags"]
    return inst_dict

logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = "skydash-dev-secret-change-me"
init_auth(app)

# Inject site settings and current_user into ALL templates automatically
@app.context_processor
def inject_settings():
    settings = config_store.get_site_settings()
    return {
        "site_name": settings["site_name"],
        "site_description": settings["site_description"],
        "favicon_url": settings["favicon_url"],
        "logo_url": settings["logo_url"],
        "current_user": get_current_user(),
    }

# In-process TTL cache for live statuses, to avoid hammering cloud APIs on every
# dashboard load. A short TTL keeps the dashboard responsive but bounded.
_STATUS_TTL = 60  # seconds — longer TTL so auto-refresh (30s) always hits cache
_status_cache: dict[str, tuple[float, dict]] = {}
import threading
_cache_lock = threading.Lock()


def _cache_get(slug: str):
    with _cache_lock:
        entry = _status_cache.get(slug)
    if entry and (time.time() - entry[0]) < _STATUS_TTL:
        return entry[1]
    return None


def _cache_put(slug: str, data: dict):
    with _cache_lock:
        _status_cache[slug] = (time.time(), data)


def _live_status(instance) -> dict:
    """Return a status dict for one instance, using the cache when fresh."""
    cached = _cache_get(instance.slug)
    if cached is not None:
        return cached
    provider = get_provider(instance.provider)
    data = {"slug": instance.slug, "status": STATUS_UNKNOWN, "can_manage": False, "error": "", "public_ip": instance.public_ip, "private_ip": instance.private_ip}
    if provider and provider.available():
        status, err, pub_ip, priv_ip = provider.get_status(instance)
        data["status"] = status
        data["can_manage"] = True
        data["error"] = err
        data["public_ip"] = pub_ip or instance.public_ip
        data["private_ip"] = priv_ip or instance.private_ip
    else:
        data["error"] = "Provider SDK/credentials not available"
    _cache_put(instance.slug, data)
    return data


@app.route("/")
@login_required
def index():
    # Statuses are intentionally left as "loading" server-side; the browser
    # fetches them live via /api/statuses so the page never blocks on cloud APIs.
    # We do NOT call provider.get_instance_details() here to keep page load instant.
    instances = [_apply_overrides(i.to_dict()) for i in get_instances()]
    return render_template("index.html", instances=instances, current_user=get_current_user())


@app.route("/api/statuses")
@login_required
def api_statuses():
    """Live status for every instance (used for dashboard auto-refresh).

    Fetches all statuses in PARALLEL using a thread pool so the total time is
    the max of any single provider call, not the sum of all of them.
    """
    instances = get_instances()
    # Check which ones are already cached (fast path — no cloud API call needed)
    results: dict[str, dict] = {}
    uncached = []
    for inst in instances:
        cached = _cache_get(inst.slug)
        if cached is not None:
            results[inst.slug] = cached
        else:
            uncached.append(inst)
    # Fetch uncached statuses in parallel (max 7 threads — one per instance)
    if uncached:
        with ThreadPoolExecutor(max_workers=7) as pool:
            future_map = {pool.submit(_live_status, inst): inst.slug for inst in uncached}
            for future in as_completed(future_map):
                slug = future_map[future]
                try:
                    results[slug] = future.result()
                except Exception as e:
                    logger.error(f"Failed to get status for {slug}: {e}")
                    results[slug] = {"slug": slug, "status": "error", "can_manage": False, "error": str(e), "public_ip": "", "private_ip": ""}
    # Return in the same order as the instance list
    return jsonify([results.get(inst.slug, {"slug": inst.slug, "status": "unknown", "can_manage": False, "error": "", "public_ip": "", "private_ip": ""}) for inst in instances])


def _parse_size(value: str) -> float:
    """Parse a spec string like '2 vCPU' / '16 GB' into a plain number."""
    import re
    m = re.search(r"(\d+(?:\.\d+)?)", str(value))
    return float(m.group(1)) if m else 0.0


@app.route("/api/load")
@login_required
def api_load():
    """Per-instance CPU/RAM data for the dashboard resource bars (#7).

    Returns each instance's configured vCPU count and RAM (GB) as parsed from the
    Terraform inventory, plus fleet max values so the front-end can render
    relative progress bars. Live utilization requires the SSH agent (Hermes,
    Cat 3) — this endpoint intentionally exposes only real inventory specs.
    """
    instances = get_instances()
    cpus = [_parse_size(i.cpu) for i in instances]
    rams = [_parse_size(i.ram) for i in instances]
    fleet_max_cpu = max(cpus) if cpus else 1
    fleet_max_ram = max(rams) if rams else 1
    data = []
    for i, (cpu, ram) in zip(instances, zip(cpus, rams)):
        data.append({
            "slug": i.slug,
            "cpu_vcpus": cpu,
            "ram_gb": ram,
            "cpu_pct": round((cpu / fleet_max_cpu) * 100) if fleet_max_cpu else 0,
            "ram_pct": round((ram / fleet_max_ram) * 100) if fleet_max_ram else 0,
            "fleet_max_cpu": fleet_max_cpu,
            "fleet_max_ram": fleet_max_ram,
        })
    return jsonify(data)


@app.route("/logs/<instance_slug>", methods=["GET"])
@login_required
def get_instance_logs(instance_slug: str):
    """Fetch logs for a specific instance.
    Query params: type (all, info, warning, error)
    """
    log_type = request.args.get("type", "all")
    inst = get_instance_by_slug(instance_slug)
    if not inst:
        return jsonify({"messages": [], "status": "error", "message": "Instance not found"}), 404
    try:
        provider = get_provider(inst.provider)
        if not provider:
            return jsonify({"messages": [], "status": "error", "message": "Provider not available"}), 500
        logs = provider.get_logs(inst, log_type)
        return jsonify({"messages": logs, "status": "ok"})
    except Exception as e:
        logger.error(f"Failed to fetch logs for {instance_slug}: {e}")
        return jsonify({"messages": [], "status": "error", "message": str(e)}), 500


@app.route("/logs/<instance_slug>/scan", methods=["GET"])
@login_required
def scan_instance_logs(instance_slug: str):
    """Scan logs for an instance and return categorized results.

    Returns errors, warnings, and info lines separately, plus a summary with
    counts. Used by the "Scan for Errors" / "Scan for Warnings" buttons on the
    detail page.
    """
    inst = get_instance_by_slug(instance_slug)
    if not inst:
        return jsonify({"errors": [], "warnings": [], "info": [], "summary": {}, "status": "error", "message": "Instance not found"}), 404
    try:
        provider = get_provider(inst.provider)
        if not provider:
            return jsonify({"errors": [], "warnings": [], "info": [], "summary": {}, "status": "error", "message": "Provider not available"}), 500
        # Fetch all log types and categorize them
        all_logs = provider.get_logs(inst, "all")
        error_logs = provider.get_logs(inst, "error")
        warning_logs = provider.get_logs(inst, "warning")
        info_logs = provider.get_logs(inst, "info")
        summary = {
            "total": len(all_logs),
            "errors": len(error_logs),
            "warnings": len(warning_logs),
            "info": len(info_logs),
            "instance": inst.name,
            "provider": inst.provider_label,
            "status": inst.status,
        }
        return jsonify({
            "errors": error_logs,
            "warnings": warning_logs,
            "info": info_logs,
            "all": all_logs,
            "summary": summary,
            "status": "ok",
        })
    except Exception as e:
        logger.error(f"Failed to scan logs for {instance_slug}: {e}")
        return jsonify({"errors": [], "warnings": [], "info": [], "summary": {}, "status": "error", "message": str(e)}), 500



@app.route("/api/status/<slug>")
@login_required
def api_status(slug: str):
    inst = get_instance_by_slug(slug)
    if not inst:
        return jsonify({"error": "not found"}), 404
    _status_cache.pop(slug, None)  # force a fresh live read for single-status poll
    return jsonify(_live_status(inst))


@app.route("/instance/<slug>")
@login_required
def instance_detail(slug: str):
    inst = get_instance_by_slug(slug)
    if not inst:
        abort(404)
    # Apply display overrides from config
    override = config_store.get_instance_override(slug)
    if override and override.get("display_name"):
        inst.display_name = override["display_name"]
    provider = get_provider(inst.provider)
    if provider:
        provider.get_instance_details(inst)  # enrich with live status
    return render_template("detail.html", inst=inst.to_dict())


@app.route("/instance/<slug>/<action>", methods=["POST"])
@login_required
def instance_action(slug: str, action: str):
    inst = get_instance_by_slug(slug)
    if not inst:
        return jsonify({"ok": False, "message": "Instance not found"}), 404
    if action not in ("start", "stop"):
        return jsonify({"ok": False, "message": "Invalid action"}), 400
    provider = get_provider(inst.provider)
    if not provider or not provider.available():
        return jsonify({"ok": False, "message": "Provider not available"})
    ok, msg = provider.start_instance(inst) if action == "start" else provider.stop_instance(inst)
    _status_cache.pop(slug, None)  # invalidate so the next poll reflects the change
    # Optimistic transitional status for immediate UI feedback.
    transitional = "starting" if action == "start" else "stopping"
    return jsonify({"ok": ok, "message": msg, "status": transitional if ok else "error"})




@app.route("/hermes/<slug>/logs/<log_type>")
@login_required
def hermes_logs(slug: str, log_type: str):
    """Fetch Hermes Agent logs from the Hermes server via SSH.
    
    log_type can be: gateway, signal, commands, all
    """
    inst = get_instance_by_slug(slug)
    if not inst:
        return jsonify({"ok": False, "error": "Instance not found"}), 404
    if inst.provider != "aws" or "hermes" not in inst.name.lower():
        return jsonify({"ok": False, "error": "Hermes Agent is only available on the Hermes server"}), 400
    
    # Use the live IP from the API (not the stale TF state IP)
    provider = get_provider(inst.provider)
    if provider:
        provider.get_instance_details(inst)
    host = inst.public_ip
    if not host:
        return jsonify({"ok": False, "error": "Hermes server has no public IP"}), 400
    
    lines = request.args.get("lines", 100, type=int)
    
    log_functions = {
        "gateway": hermes_agent.fetch_gateway_logs,
        "signal": hermes_agent.fetch_signal_logs,
        "commands": hermes_agent.fetch_command_logs,
        "all": hermes_agent.fetch_all_logs,
    }
    
    func = log_functions.get(log_type)
    if not func:
        return jsonify({"ok": False, "error": f"Unknown log type: {log_type}. Use: gateway, signal, commands, all"}), 400
    
    try:
        result = func(host, lines)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Hermes Agent error for {slug}: {e}")
        return jsonify({"ok": False, "error": f"Hermes Agent error: {e}"}), 500


@app.route("/hermes/<slug>/disk")
@login_required
def hermes_disk_status(slug: str):
    """Fetch disk usage information from the Hermes server via SSH."""
    inst = get_instance_by_slug(slug)
    if not inst:
        return jsonify({"ok": False, "error": "Instance not found"}), 404
    if inst.provider != "aws" or "hermes" not in inst.name.lower():
        return jsonify({"ok": False, "error": "Disk status is only available on the Hermes server"}), 400
    
    # Use the live IP from the API (not the stale TF state IP)
    provider = get_provider(inst.provider)
    if provider:
        provider.get_instance_details(inst)
    host = inst.public_ip
    if not host:
        return jsonify({"ok": False, "error": "Hermes server has no public IP"}), 400
    
    try:
        result = hermes_agent.fetch_disk_status(host)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Hermes disk status error for {slug}: {e}")
        return jsonify({"ok": False, "error": f"Disk status error: {e}"}), 500


@app.route("/hermes/<slug>/test")
@login_required
def hermes_test_connection(slug: str):
    """Test SSH connection to the Hermes server and return diagnostics."""
    inst = get_instance_by_slug(slug)
    if not inst:
        return jsonify({"ok": False, "error": "Instance not found"}), 404
    if inst.provider != "aws" or "hermes" not in inst.name.lower():
        return jsonify({"ok": False, "error": "Only available on the Hermes server"}), 400
    
    # Use the live IP from the API (not the stale TF state IP)
    provider = get_provider(inst.provider)
    if provider:
        provider.get_instance_details(inst)
    host = inst.public_ip
    if not host:
        return jsonify({"ok": False, "error": "Hermes server has no public IP"}), 400
    
    try:
        result = hermes_agent.test_connection(host)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Hermes test connection error for {slug}: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500



# --- Admin routes ---

@app.route("/admin")
@login_required
def admin_panel():
    """Admin panel with site settings, profile, and instance management."""
    instances = [_apply_overrides(i.to_dict()) for i in get_instances()]
    return render_template("admin.html",
        site_settings=config_store.get_site_settings(),
        profile=config_store.get_admin_profile(),
        all_instances=instances,
        hidden_instances=config_store.get_hidden_instances(),
        custom_instances=config_store.get_custom_instances(),
        instance_overrides=config_store.get_instance_overrides(),
        edit_slug=None,
        edit_instance=None,
        edit_override={},
    )


@app.route("/admin/settings", methods=["POST"])
@login_required
def admin_save_settings():
    """Save site settings (name, description, favicon, logo)."""
    config_store.update_site_settings(
        site_name=request.form.get("site_name", "SkyDash"),
        site_description=request.form.get("site_description", ""),
        favicon_url=request.form.get("favicon_url", ""),
        logo_url=request.form.get("logo_url", ""),
    )
    flash("Site settings saved successfully!", "success")
    return redirect(url_for("admin_panel"))


@app.route("/admin/profile", methods=["POST"])
@login_required
def admin_save_profile():
    """Save admin profile (username, email)."""
    config_store.update_profile(
        username=request.form.get("username", "admin"),
        email=request.form.get("email", ""),
    )
    flash("Profile updated successfully!", "success")
    return redirect(url_for("admin_panel"))


@app.route("/admin/password", methods=["POST"])
@login_required
def admin_change_password():
    """Change admin password."""
    current_pw = request.form.get("current_password", "")
    new_pw = request.form.get("new_password", "")
    confirm_pw = request.form.get("confirm_password", "")

    if not config_store.verify_password(current_pw):
        flash("Current password is incorrect.", "danger")
        return redirect(url_for("admin_panel"))
    if new_pw != confirm_pw:
        flash("New passwords do not match.", "danger")
        return redirect(url_for("admin_panel"))
    if len(new_pw) < 6:
        flash("Password must be at least 6 characters.", "danger")
        return redirect(url_for("admin_panel"))

    config_store.set_password(new_pw)
    flash("Password changed successfully!", "success")
    return redirect(url_for("admin_panel"))


@app.route("/admin/instance/<slug>/hide")
@login_required
def admin_hide_instance(slug: str):
    """Hide an instance from the dashboard."""
    config_store.hide_instance(slug)
    flash(f"Instance {slug} hidden from dashboard.", "warning")
    return redirect(url_for("admin_panel"))


@app.route("/admin/instance/<slug>/unhide")
@login_required
def admin_unhide_instance(slug: str):
    """Unhide an instance from the dashboard."""
    config_store.unhide_instance(slug)
    flash(f"Instance {slug} is now visible.", "success")
    return redirect(url_for("admin_panel"))


@app.route("/admin/instance/add", methods=["POST"])
@login_required
def admin_add_instance():
    """Add a custom instance manually."""
    config_store.add_custom_instance(
        provider=request.form.get("provider", "aws"),
        instance_id=request.form.get("instance_id", ""),
        name=request.form.get("name", ""),
        region=request.form.get("region", ""),
        instance_type=request.form.get("instance_type", ""),
    )
    flash("Custom instance added!", "success")
    return redirect(url_for("admin_panel"))


@app.route("/admin/instance/<instance_id>/remove")
@login_required
def admin_remove_instance(instance_id: str):
    """Remove a custom instance."""
    config_store.remove_custom_instance(instance_id)
    flash("Custom instance removed.", "warning")
    return redirect(url_for("admin_panel"))

@app.route("/admin/instance/<slug>/edit", methods=["POST"])
@login_required
def admin_edit_instance(slug: str):
    """Edit instance display name, description, and tags."""
    display_name = request.form.get("display_name", "").strip()
    description = request.form.get("description", "").strip()
    tags_raw = request.form.get("tags", "").strip()
    tags = [t.strip() for t in tags_raw.split(",") if t.strip()] if tags_raw else []
    config_store.set_instance_override(slug, display_name=display_name or None, description=description or None, tags=tags or None)
    flash(f"Instance {slug} updated successfully!", "success")
    return redirect(url_for("admin_panel"))


@app.route("/admin/instance/<slug>/edit")
@login_required
def admin_edit_instance_form(slug: str):
    """Show edit form for an instance."""
    instances = [_apply_overrides(i.to_dict()) for i in get_instances()]
    inst = get_instance_by_slug(slug)
    if not inst:
        flash(f"Instance {slug} not found.", "danger")
        return redirect(url_for("admin_panel"))
    override = config_store.get_instance_override(slug)
    return render_template("admin.html",
        site_settings=config_store.get_site_settings(),
        profile=config_store.get_admin_profile(),
        all_instances=instances,
        hidden_instances=config_store.get_hidden_instances(),
        custom_instances=config_store.get_custom_instances(),
        instance_overrides=config_store.get_instance_overrides(),
        edit_slug=slug,
        edit_instance=inst.to_dict(),
        edit_override=override,
    )

# --- Error handlers ---

@app.errorhandler(404)
def not_found_error(e):
    return render_template("404.html"), 404


@app.errorhandler(500)
def internal_error(e):
    return render_template("503.html"), 503


@app.route("/refresh")
@login_required
def refresh():
    _status_cache.clear()
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=False)
