import pytest
from django.urls import reverse
from rest_framework.test import APIClient


@pytest.fixture
def openapi_schema():
    client = APIClient()

    response = client.get(
        reverse("schema"),
        HTTP_ACCEPT="application/vnd.oai.openapi+json",
    )

    assert response.status_code == 200
    return response.json()


def resolve_schema(schema, reference):
    """Resolve a local OpenAPI component reference."""
    assert reference.startswith("#/components/schemas/")

    name = reference.split("/")[-1]
    return schema["components"]["schemas"][name]


def test_route_optimize_is_documented(openapi_schema):
    paths = openapi_schema["paths"]

    assert "/api/v1/routes/optimize/" in paths
    assert "post" in paths["/api/v1/routes/optimize/"]


def test_route_optimize_has_request_body(openapi_schema):
    endpoint = openapi_schema["paths"]["/api/v1/routes/optimize/"]["post"]

    request_body = endpoint["requestBody"]

    assert request_body["required"] is True

    content = request_body["content"]
    assert "application/json" in content

    request_schema = content["application/json"]["schema"]

    if "$ref" in request_schema:
        request_schema = resolve_schema(
            openapi_schema,
            request_schema["$ref"],
        )

    assert "start" in request_schema["properties"]
    assert "finish" in request_schema["properties"]

    assert {"start", "finish"}.issubset(set(request_schema["required"]))


def test_route_optimize_has_success_response(openapi_schema):
    endpoint = openapi_schema["paths"]["/api/v1/routes/optimize/"]["post"]

    responses = endpoint["responses"]

    assert "200" in responses

    response_schema = responses["200"]["content"]["application/json"]["schema"]

    if "$ref" in response_schema:
        response_schema = resolve_schema(
            openapi_schema,
            response_schema["$ref"],
        )

    expected_fields = {
        "start",
        "finish",
        "distance_miles",
        "duration_minutes",
        "geometry",
        "fuel",
    }

    assert expected_fields.issubset(set(response_schema["properties"]))


def test_route_optimize_documents_errors(openapi_schema):
    endpoint = openapi_schema["paths"]["/api/v1/routes/optimize/"]["post"]

    responses = endpoint["responses"]

    assert "400" in responses
    assert "422" in responses
    assert "502" in responses
