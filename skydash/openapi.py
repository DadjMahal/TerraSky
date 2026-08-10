"""OpenAPI 3.0 spec for SkyDash (§62, §125).

Composed from a small declarative registry that mirrors the real routes in
`app.py`, so the spec stays in sync with the code. Consumed by:
  GET /api/v1/openapi.json  -> machine-readable spec
  GET /api/v1/docs          -> Swagger UI (CDN bundle, no build step)
"""
from __future__ import annotations

from typing import Any

_SWAGGER_UI_CDN = "https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.11.0"

SWAGGER_UI_HTML = (
    "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
    "<title>SkyDash API — Swagger UI</title>"
    "<link rel=\"stylesheet\" href=\"" + _SWAGGER_UI_CDN + "/swagger-ui.css\">"
    "</head><body><div id=\"swagger-ui\"></div>"
    "<script src=\"" + _SWAGGER_UI_CDN + "/swagger-ui-bundle.js\"></script>"
    "<script>window.addEventListener('load',function(){\n"
    "window.ui=SwaggerUIBundle({url:'/api/v1/openapi.json',dom_id:'#swagger-ui',"
    "presets:[SwaggerUIBundle.presets.apis]});\n"
    "});</script></body></html>"
)


def _ref(name: str) -> str:
    """Reference a reusable OpenAPI response component."""
    return {"$ref": "#/components/responses/" + name}


def build_spec() -> dict[str, Any]:
    """Build the OpenAPI 3.0.3 document reflecting the real v1 routes."""
    error_ref = lambda n: _ref(n)  # noqa: E731
    return {
        "openapi": "3.0.3",
        "info": {
            "title": "SkyDash API",
            "version": "1.0.0",
            "description": "Versioned REST API for the SkyDash multi-cloud console.",
        },
        "servers": [{"url": "/api/v1", "description": "Versioned (primary)"}],
        "components": {
            "securitySchemes": {
                "sessionAuth": {
                    "type": "apiKey", "in": "cookie", "name": "session",
                    "description": "Flask session cookie (login_required).",
                },
                "csrfHeader": {
                    "type": "apiKey", "in": "header", "name": "X-CSRFToken",
                    "description": "Required for POST/PUT/PATCH/DELETE (§77).",
                },
            },
            "responses": {
                "Unauthorized": {"description": "Authentication required.", "content": {"application/json": {"schema": {"type": "object"}}}},
                "NotFound": {"description": "Resource not found.", "content": {"application/json": {"schema": {"type": "object"}}}},
                "InvalidAction": {"description": "Invalid action.", "content": {"application/json": {"schema": {"type": "object"}}}},
                "ProviderUnavailable": {"description": "Provider unavailable.", "content": {"application/json": {"schema": {"type": "object"}}}},
                "CsrfFailure": {"description": "CSRF token missing/invalid.", "content": {"application/json": {"schema": {"type": "object"}}}},
            },
            "schemas": {
                "Envelope": {
                    "type": "object",
                    "properties": {
                        "status": {"type": "string", "enum": ["ok", "error"]},
                        "data": {},
                        "error": {"type": "string"},
                    },
                    "required": ["status"],
                },
                "Instance": {"type": "object", "description": "Instance resource (see models.Instance)."},
                "StatusList": {"type": "object", "description": "Instance statuses (see /api/statuses)."},
                "ActionRequest": {"type": "object", "properties": {"action": {"type": "string", "enum": ["start", "stop"]}}, "required": ["action"]},
            },
        },
        "security": [{"sessionAuth": []}, {"csrfHeader": []}],
        "paths": _paths(error_ref),
    }


def _paths(er: Any) -> dict[str, Any]:
    """Route registry mirroring the v1 routes actually defined in app.py."""
    ok = {"description": "OK"}
    slug = {"name": "slug", "in": "path", "required": True, "schema": {"type": "string"}}
    return {
        "/instances": {
            "get": {
                "tags": ["Instances"], "summary": "List all instance statuses",
                "responses": {"200": ok, "401": er("Unauthorized")},
            }
        },
        "/instances/{slug}": {
            "get": {
                "tags": ["Instances"], "summary": "Instance detail (live refresh)",
                "parameters": [slug],
                "responses": {"200": ok, "401": er("Unauthorized"), "404": er("NotFound")},
            }
        },
        "/instances/{slug}/{action}": {
            "post": {
                "tags": ["Instances"], "summary": "Start/stop an instance",
                "parameters": [slug],
                "requestBody": {
                    "required": True,
                    "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ActionRequest"}}},
                },
                "responses": {
                    "200": ok, "400": er("InvalidAction"), "401": er("Unauthorized"),
                    "404": er("NotFound"), "503": er("ProviderUnavailable"),
                },
            }
        },
        "/instances/{slug}/metrics": {
            "get": {
                "tags": ["Instances"], "summary": "CPU/RAM/disk metrics",
                "parameters": [slug],
                "responses": {"200": ok, "401": er("Unauthorized"), "404": er("NotFound")},
            }
        },
        "/instances/{slug}/logs/{log_type}": {
            "get": {
                "tags": ["Instances"], "summary": "Instance logs (dmesg/journal/etc)",
                "parameters": [
                    slug,
                    {"name": "log_type", "in": "path", "required": True, "schema": {"type": "string"}},
                ],
                "responses": {"200": ok, "401": er("Unauthorized"), "404": er("NotFound"), "503": er("ProviderUnavailable")},
            }
        },
    }
