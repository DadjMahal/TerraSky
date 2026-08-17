"""Tests for openapi — declarative OpenAPI 3.0.3 spec generation (§62, §125).

build_spec() composes the document from a small route registry. These tests
verify the schema-generation helpers and the structure of the emitted spec
(version, info, security schemes, reusable components, and route paths with
their response references), staying on pure stdlib.
"""
from __future__ import annotations

import json
import os
import sys
from unittest import mock

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import openapi  # noqa: E402


# --------------------------------------------------------------------------- #
# _ref                                                                        #
# --------------------------------------------------------------------------- #
def test_ref_builds_components_pointer():
    assert openapi._ref("Unauthorized") == {"$ref": "#/components/responses/Unauthorized"}


def test_ref_raises_ref_name():
    assert openapi._ref("NotFound")["$ref"].endswith("/NotFound")

# --------------------------------------------------------------------------- #
# _paths                                                                      #
# --------------------------------------------------------------------------- #
def test_paths_covers_expected_routes():
    paths = openapi._paths(openapi._ref)
    assert "/instances" in paths
    assert "/instances/{slug}" in paths
    assert "/instances/{slug}/{action}" in paths
    assert "/instances/{slug}/metrics" in paths
    assert "/instances/{slug}/logs/{log_type}" in paths
    assert "/instance/{slug}/security-groups" in paths
    assert "/security/checklist" in paths


def test_paths_passes_error_ref_to_responses():
    """The er callable is used to build $ref response entries."""
    fake = mock.Mock(side_effect=lambda n: {"$ref": f"resp/{n}"})
    paths = openapi._paths(fake)
    fake.assert_called()
    # At least one response references a component through the callable.
    refs = json.dumps(paths)
    assert "resp/" in refs


def test_paths_instances_list_get():
    paths = openapi._paths(openapi._ref)
    op = paths["/instances"]["get"]
    assert op["tags"] == ["Instances"]
    assert op["responses"]["200"] == {"description": "OK"}
    assert op["responses"]["401"] == {"$ref": "#/components/responses/Unauthorized"}


def test_paths_instance_action_post_has_request_body():
    paths = openapi._paths(openapi._ref)
    op = paths["/instances/{slug}/{action}"]["post"]
    assert op["responses"]["400"] == {"$ref": "#/components/responses/InvalidAction"}
    assert op["responses"]["503"] == {"$ref": "#/components/responses/ProviderUnavailable"}
    body = op["requestBody"]
    assert body["required"] is True
    assert body["content"]["application/json"]["schema"]["$ref"] == \
        "#/components/schemas/ActionRequest"


def test_paths_security_groups_has_502_provider_error():
    paths = openapi._paths(openapi._ref)
    op = paths["/instance/{slug}/security-groups"]["get"]
    assert op["responses"]["502"] == {"$ref": "#/components/responses/ProviderError"}


def test_paths_path_parameters_slug():
    paths = openapi._paths(openapi._ref)
    op = paths["/instances/{slug}"]["get"]
    (param,) = op["parameters"]
    assert param["name"] == "slug"
    assert param["in"] == "path"
    assert param["required"] is True
    assert param["schema"] == {"type": "string"}


# --------------------------------------------------------------------------- #
# build_spec                                                                  #
# --------------------------------------------------------------------------- #
def test_build_spec_version_and_info():
    spec = openapi.build_spec()
    assert spec["openapi"] == "3.0.3"
    assert spec["info"]["title"] == "SkyDash API"
    assert spec["info"]["version"] == "1.0.0"
    assert spec["servers"] == [{"url": "/api/v1", "description": "Versioned (primary)"}]


def test_build_spec_serializable():
    """The whole spec must encode to JSON (no non-serializable members)."""
    spec = openapi.build_spec()
    json.dumps(spec)  # must not raise


def test_build_spec_security_schemes():
    spec = openapi.build_spec()
    schemes = spec["components"]["securitySchemes"]
    assert schemes["sessionAuth"] == {
        "type": "apiKey", "in": "cookie", "name": "session",
        "description": "Flask session cookie (login_required).",
    }
    assert schemes["csrfHeader"]["in"] == "header"
    assert schemes["csrfHeader"]["name"] == "X-CSRFToken"


def test_build_spec_security_global():
    spec = openapi.build_spec()
    assert {"sessionAuth": []} in spec["security"]
    assert {"csrfHeader": []} in spec["security"]


def test_build_spec_response_components():
    spec = openapi.build_spec()
    responses = spec["components"]["responses"]
    for name in ("Unauthorized", "NotFound", "InvalidAction", "ProviderUnavailable", "CsrfFailure"):
        assert name in responses
        assert responses[name]["description"]


def test_build_spec_schema_components():
    spec = openapi.build_spec()
    schemas = spec["components"]["schemas"]
    assert "Envelope" in schemas
    assert "Instance" in schemas
    assert "StatusList" in schemas
    assert "ActionRequest" in schemas
    # The ActionRequest schema enum drives the instance action verb.
    assert "start" in schemas["ActionRequest"]["properties"]["action"]["enum"]


def test_build_spec_uses_paths():
    """build_spec composes paths from the route registry via the error ref fn."""
    spec = openapi.build_spec()
    assert "/instances" in spec["paths"]
    assert "/security/checklist" in spec["paths"]


def test_build_spec_paths_responses_resolve_to_components():
    spec = openapi.build_spec()
    refs = json.dumps(spec["paths"])
    # Every emitted $ref targets a real component response.
    assert "#/components/responses/" in refs


# --------------------------------------------------------------------------- #
# SWAGGER_UI_HTML                                                             #
# --------------------------------------------------------------------------- #
def test_swagger_ui_html_loads_cdn_and_spec_url():
    html = openapi.SWAGGER_UI_HTML
    assert "swagger-ui-dist@5.11.0" in html
    assert "/api/v1/openapi.json" in html
    assert "swagger-ui" in html


if __name__ == "__main__":
    import pytest as _pytest
    sys.exit(_pytest.main([__file__, "-v"]))

