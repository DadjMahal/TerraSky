"""Kubernetes management contract (§24)."""
from __future__ import annotations

FEATURE_STATUS = "scaffold"
SPEC_SECTIONS = ["§16", "§24"]

COMMANDS = {
    "pods": "kubectl get pods --all-namespaces -o wide",
    "deployments": "kubectl get deployments -A",
    "scale": "kubectl scale deployment <name> --replicas=<n> -n <ns>",
    "restart": "kubectl rollout restart deployment <name> -n <ns>",
    "describe": "kubectl describe pod <name> -n <ns>",
    "logs": "kubectl logs --tail 200 <pod> -n <ns>",
}


def describe() -> dict:
    return {"feature": "kubernetes", "status": FEATURE_STATUS, "spec": SPEC_SECTIONS,
            "commands": COMMANDS,
            "blocked": "requires kubectl + cluster access on target host + deployed agent"}
