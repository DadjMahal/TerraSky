"""SkyDash CLI (§63 — currently NOT_IMPLEMENTED in the spec).

A small, in-process command-line client that drives the same provider layer
the web UI uses, so operators can start/stop machines and inspect state without
the dashboard. Intended to be invoked as:

    python3 -m skydash.cli list
    python3 -m skydash.cli status <slug>
    python3 -m skydash.cli start <slug>
    python3 -m skydash.cli stop  <slug>

It deliberately avoids HTTP so it can run on the host alongside the systemd
unit; a future token-based (§94) HTTP client can be layered on top.
"""
from __future__ import annotations

import argparse
import sys

import policy as policy_engine
from providers.registry import get_provider
from state_reader import get_instance_by_slug, get_instances


def _print_inst(i) -> None:
    print(f"{i.slug}\t{i.provider_label}\t{i.status}\t{i.name}")


def cmd_list(_args) -> int:
    print(f"{'SLUG':<28}{'PROVIDER':<14}{'STATUS':<12}NAME")
    for i in get_instances():
        print(f"{i.slug:<28}{i.provider_label:<14}{i.status:<12}{i.name}")
    return 0


def cmd_status(args) -> int:
    inst = get_instance_by_slug(args.slug)
    if not inst:
        print(f"error: instance not found: {args.slug}", file=sys.stderr)
        return 2
    provider = get_provider(inst.provider)
    if provider and provider.available():
        try:
            provider.get_instance_details(inst)
        except Exception as exc:  # noqa: BLE001
            print(f"warn: could not refresh live status: {exc}", file=sys.stderr)
    print(f"slug      : {inst.slug}")
    print(f"name      : {inst.name}")
    print(f"provider  : {inst.provider_label}")
    print(f"region    : {inst.region or '—'}")
    print(f"status    : {inst.status}")
    print(f"public_ip : {inst.public_ip or '—'}")
    print(f"private_ip: {inst.private_ip or '—'}")
    return 0


def _mutating(args, action: str) -> int:
    inst = get_instance_by_slug(args.slug)
    if not inst:
        print(f"error: instance not found: {args.slug}", file=sys.stderr)
        return 2
    # §107 environment protection: destructive actions on prod-tagged
    # resources need an explicit --approve (until §66 approval system).
    resource = inst.to_dict()
    if action in policy_engine.DESTRUCTIVE_ACTIONS and policy_engine.is_prod_resource(resource):
        if not getattr(args, "approve", False):
            print(
                f"PROD_SHIELD: '{action}' on production resource {getattr(args, 'slug', '')} "
                f"is denied without approval. Re-run with --approve "
                f"(and MFA once §68 lands).",
                file=sys.stderr,
            )
            return 3
    provider = get_provider(inst.provider)
    if not provider or not provider.available():
        print("error: provider not available (check credentials/env)", file=sys.stderr)
        return 3
    ok, msg = provider.start_instance(inst) if action == "start" else provider.stop_instance(inst)
    print(("ok: " if ok else "fail: ") + msg)
    return 0 if ok else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="skydash", description="SkyDash multi-cloud CLI (§63)")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("list", help="List all known instances")
    sp = sub.add_parser("status", help="Show an instance")
    sp.add_argument("slug")
    sp = sub.add_parser("start", help="Start an instance")
    sp.add_argument("slug")
    sp.add_argument("--approve", action="store_true",
                    help="Approve prod-shielded action (§107; convention until §66)")
    sp = sub.add_parser("stop", help="Stop an instance")
    sp.add_argument("slug")
    sp.add_argument("--approve", action="store_true",
                    help="Approve prod-shielded action (§107; convention until §66)")
    args = parser.parse_args(argv)

    cmd_map = {"list": cmd_list, "status": cmd_status, "start": lambda a: _mutating(a, "start"), "stop": lambda a: _mutating(a, "stop")}
    return cmd_map[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main())
