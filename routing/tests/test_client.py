from unittest.mock import patch

import httpx
import pytest
from django.test import override_settings

from routing.services.client import (
    OpenRouteServiceClient,
    RoutingProviderError,
)


@override_settings(
    ROUTING_API_KEY="test-api-key",
    ROUTING_API_URL="https://api.openrouteservice.org",
)
def test_client_initialization():
    client = OpenRouteServiceClient()

    assert client.api_key == "test-api-key"
    assert client.base_url == "https://api.openrouteservice.org"


@override_settings(ROUTING_API_KEY="")
def test_client_requires_api_key():
    with pytest.raises(
        RoutingProviderError,
        match="ROUTING_API_KEY is not configured",
    ):
        OpenRouteServiceClient()


@override_settings(
    ROUTING_API_KEY="test-api-key",
    ROUTING_API_URL="https://api.openrouteservice.org",
)
def test_client_successful_request():
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            json={"features": []},
        )
    )

    with patch(
        "routing.services.client.httpx.Client",
        wraps=httpx.Client,
    ) as mock_client:
        mock_client.return_value = httpx.Client(
            transport=transport,
            base_url="https://api.openrouteservice.org",
        )

        client = OpenRouteServiceClient()
        result = client.request("GET", "/geocode/search")

    assert result == {"features": []}


@override_settings(
    ROUTING_API_KEY="test-api-key",
    ROUTING_API_URL="https://api.openrouteservice.org",
)
def test_client_handles_http_error():
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            429,
            json={"error": "Rate limit exceeded"},
        )
    )

    with patch(
        "routing.services.client.httpx.Client",
        return_value=httpx.Client(
            transport=transport,
            base_url="https://api.openrouteservice.org",
        ),
    ):
        client = OpenRouteServiceClient()

        with pytest.raises(
            RoutingProviderError,
            match="HTTP 429",
        ):
            client.request("GET", "/geocode/search")


@override_settings(
    ROUTING_API_KEY="test-api-key",
    ROUTING_API_URL="https://api.openrouteservice.org",
)
def test_client_rejects_invalid_json():
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            content=b"not valid json",
        )
    )

    with patch(
        "routing.services.client.httpx.Client",
        return_value=httpx.Client(
            transport=transport,
            base_url="https://api.openrouteservice.org",
        ),
    ):
        client = OpenRouteServiceClient()

        with pytest.raises(
            RoutingProviderError,
            match="invalid JSON",
        ):
            client.request("GET", "/geocode/search")


@override_settings(
    ROUTING_API_KEY="test-api-key",
    ROUTING_API_URL="https://api.openrouteservice.org",
)
def test_client_uses_geojson_accept_header():
    captured_requests = []

    def handler(request):
        captured_requests.append(request)
        return httpx.Response(
            200,
            json={"features": []},
        )

    transport = httpx.MockTransport(handler)

    # Save the real constructor before patching it.
    original_client = httpx.Client

    def client_factory(*args, **kwargs):
        kwargs["transport"] = transport
        return original_client(*args, **kwargs)

    with patch(
        "routing.services.client.httpx.Client",
        side_effect=client_factory,
    ):
        client = OpenRouteServiceClient()

        client.request(
            "POST",
            "/v2/directions/driving-car/geojson",
            json={
                "coordinates": [
                    [-74.0, 40.7],
                    [-75.1, 39.9],
                ],
            },
        )

    assert len(captured_requests) == 1

    request = captured_requests[0]

    assert request.headers["Accept"] == "application/geo+json"
    assert request.headers["Authorization"] == "test-api-key"
    assert request.headers["Content-Type"] == "application/json"
