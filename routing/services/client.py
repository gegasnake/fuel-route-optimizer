from typing import Any

import httpx
from django.conf import settings


class RoutingProviderError(Exception):
    """An error occurred while communicating with the routing provider."""


class OpenRouteServiceClient:
    def __init__(self) -> None:
        self.base_url = settings.ROUTING_API_URL.rstrip("/")
        self.api_key = settings.ROUTING_API_KEY

        if not self.api_key:
            raise RoutingProviderError("ROUTING_API_KEY is not configured.")

    def request(
        self,
        method: str,
        endpoint: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        headers = {
            "Authorization": self.api_key,
            "Accept": (
                "application/geo+json"
                if endpoint.endswith("/geojson")
                else "application/json"
            ),
        }

        try:
            with httpx.Client(
                base_url=self.base_url,
                timeout=httpx.Timeout(20.0, connect=5.0),
                headers=headers,
            ) as client:
                response = client.request(
                    method,
                    endpoint,
                    params=params,
                    json=json,
                )
                response.raise_for_status()
                data = response.json()

        except httpx.HTTPStatusError as exc:
            raise RoutingProviderError(
                f"Routing provider returned HTTP {exc.response.status_code}."
            ) from exc

        except httpx.RequestError as exc:
            raise RoutingProviderError("Routing provider request failed.") from exc

        except ValueError as exc:
            raise RoutingProviderError(
                "Routing provider returned invalid JSON."
            ) from exc

        if not isinstance(data, dict):
            raise RoutingProviderError("Unexpected routing provider response.")

        return data
