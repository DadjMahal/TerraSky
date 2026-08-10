"""Policy engine (§67-68) + production-environment protection (§107-108).

Policies are **data**: plain dicts that can live in code, a JSON file, or a
future OPA/Conftest bundle. The evaluator is intentionally a small, pure,
compile-verified skeleton so it can be unit-tested without any external
binary::

    evaluate(action, resource, policies) -> list[verdict]
    allowed(action, resource, policies)   -> bool

Environment protection (§107) is layered on top as :func:`prod_shield` —
destructive actions against prod-tagged resources are **denied unless an
explicit approval flag is supplied** (the real approval workflow §66 and
MFA-for-destructive §68 are BLOCKED; see ``docs/security-governance-iter8.md``).

OPA / Conftest engine — **BLOCKED** (external ``opa``/``conftest`` binary is
not installed in this environment). ``evaluate()`` is designed so its
verdict list is the same shape an external engine would produce, allowing a
drop-in swap later.
"""
from __future__ import annotations

import fnmatch
from typing import Any

# --- Constants ---------------------------------------------------------------
# Actions considered destructive / environment-affecting under §107.
DESTRUCTIVE_ACTIONS: frozenset[str] = frozenset(
    {
        "server.destroy",
        "server.terminate",
        "server.delete",
        "server.stop",
        "server.reboot",
        "resource.delete",
        "terraform.destroy",
        "deployment.delete",
        "deployment.rollback",
    }
)

PROD_TAG_KEYS = ("env", "environment", "tier")
PROD_TAG_VALUES = {"prod", "production"}

IMPLICIT_ALLOW_ID = "__implicit_allow__"

# --- Policies as data ---------------------------------------------------------
# Example policies shipped with the skeleton. Each policy:
#   id       stable identifier (shown in verdicts + audit detail)
#   action   exact action id or fnmatch-style pattern ("server.*")
#   effect   "allow" | "deny"
#   priority higher wins; ties resolved deny-over-allow
#   when     optional conditions applied to the resource:
#              tags:      dict of tag key -> value the resource must have
#              resource:  fnmatch pattern matched against resource["id"]/"slug"
#   reason   human-readable justification (surfaced to the caller)
DEFAULT_POLICIES: list[dict[str, Any]] = [
    {
        "id": "default-allow-read",
        "action": "server.read",
        "effect": "allow",
        "priority": 10,
        "reason": "Read of any resource is permitted for authenticated users.",
    },
    {
        "id": "deny-destroy-prod",
        "action": "server.destroy",
        "effect": "deny",
        "priority": 100,
        "when": {"tags": {"env": "prod"}},
        "reason": "Destroying a production resource requires an admin-approved "
        "change ticket and MFA (66, 68).",
    },
    {
        "id": "deny-stop-prod",
        "action": "server.stop",
        "effect": "deny",
        "priority": 100,
        "when": {"tags": {"env": "prod"}},
        "reason": "Stopping a production resource requires approval (107).",
    },
]
# --- Matching -----------------------------------------------------------------
def _norm(value: Any) -> str:
    return str(value or "").strip().lower()


def _match_tags(policy_when: dict, resource: dict) -> bool:
    required = (policy_when or {}).get("tags") or {}
    tags = resource.get("tags") or {}
    for key, want in required.items():
        actual = _norm(tags.get(key))
        if actual != _norm(want) and actual not in PROD_TAG_VALUES:
            return False
    return True


def policy_matches(policy: dict, action: str, resource: dict) -> bool:
    """True when the policy applies to (action, resource)."""
    pat = policy.get("action")
    if pat:
        if not (pat == action or fnmatch.fnmatchcase(action, pat)):
            return False
    when = policy.get("when") or {}
    if "tags" in when and not _match_tags(when, resource):
        return False
    if "resource" in when:
        res_id = resource.get("id") or resource.get("slug") or resource.get("name") or ""
        if not fnmatch.fnmatchcase(_norm(res_id), _norm(when["resource"])):
            return False
    if "provider" in when:
        if _norm(resource.get("provider")) != _norm(when["provider"]):
            return False
    return True


# --- Evaluation ---------------------------------------------------------------
def evaluate(
    action: str, resource: dict, policies: list[dict] | None = None
) -> list[dict]:
    """Evaluate ``action`` against ``resource`` under ``policies``.

    Returns verdicts for every matched policy, highest priority first (ties:
    deny before allow). If nothing matches, a single ``__implicit_allow__``
    verdict is returned so callers always have a decision:
    ``[{"policy_id", "effect", "priority", "matched", "reason"}]``.
    """
    policies = list(policies if policies is not None else DEFAULT_POLICIES)
    matched = [
        {
            "policy_id": p.get("id", "?"),
            "effect": p.get("effect", "allow"),
            "priority": int(p.get("priority", 0)),
            "matched": True,
            "reason": p.get("reason", ""),
        }
        for p in policies
        if policy_matches(p, action, resource)
    ]
    matched.sort(
        key=lambda v: (v["priority"], 0 if v["effect"] == "deny" else 1),
        reverse=True,
    )
    if not matched:
        matched = [
            {
                "policy_id": IMPLICIT_ALLOW_ID,
                "effect": "allow",
                "priority": 0,
                "matched": False,
                "reason": "No policy matched; implicit allow for further checks.",
            }
        ]
    return matched


def allowed(
    action: str, resource: dict, policies: list[dict] | None = None
) -> bool:
    """True when the top-priority matched verdict is ``allow``.

    Tie-break is deny-over-allow at equal priority (fail-closed).
    """
    verdicts = evaluate(action, resource, policies)
    return verdicts[0]["effect"] == "allow"


# --- Environment protection (§107) --------------------------------------------
def is_prod_resource(resource: dict) -> bool:
    """True when the resource is tagged/env-flagged as production.

    Accepts resource dicts from ``models.Instance.to_dict()`` (tags keyed
    ``env``/``environment``/``tier``) and future domain-model resources that
    expose a top-level ``environment``/``tier`` field.
    """
    tags = resource.get("tags") or {}
    for key in PROD_TAG_KEYS:
        for source in (tags, resource):
            value = _norm(source.get(key))
            if value in PROD_TAG_VALUES:
                return True
    return False


def prod_shield(
    resource: dict,
    action: str,
    approved: bool = False,
    approval_ref: str | None = None,
    policies: list[dict] | None = None,
) -> dict:
    """Guard destructive actions on prod-tagged resources (§107).

    Returns a decision dict::

        {"allowed": bool, "code": "PROD_SHIELD"|"...", "reason": str,
         "prod": bool, "destructive": bool, "approved": bool,
         "verdicts": [...]}

    * Non-destructive action  -> always allowed (still evaluated).
    * Destructive + non-prod  -> allowed.
    * Destructive + prod      -> requires ``approved=True`` (+ ``approval_ref``
      for audit); otherwise **denied** with code ``PROD_SHIELD``.
    """
    is_destructive = action in DESTRUCTIVE_ACTIONS
    is_prod = is_prod_resource(resource)
    verdicts = evaluate(action, resource, policies)
    res_name = resource.get("slug") or resource.get("id") or "?"

    if not is_destructive or not is_prod:
        return {
            "allowed": True,
            "code": "OK",
            "reason": "Not a destructive action on a production resource.",
            "prod": is_prod,
            "destructive": is_destructive,
            "approved": bool(approved),
            "verdicts": verdicts,
        }
    if approved:
        return {
            "allowed": True,
            "code": "APPROVED",
            "reason": (
                f"Destructive action '{action}' on production resource "
                f"{res_name} approved (ref={approval_ref or 'n/a'})."
            ),
            "prod": True,
            "destructive": True,
            "approved": True,
            "verdicts": verdicts,
        }
    return {
        "allowed": False,
        "code": "PROD_SHIELD",
        "reason": (
            f"PROD_SHIELD: '{action}' on production resource {res_name} is "
            f"denied without approval. Re-submit with an approval token; MFA "
            f"and the formal approval workflow are required for production "
            f"(§66, §68, §107)."
        ),
        "prod": True,
        "destructive": True,
        "approved": False,
        "verdicts": verdicts,
    }