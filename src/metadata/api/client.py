"""HTTP client for the ODE REST interface with retry and backoff."""

from __future__ import annotations

import random
import time
from typing import Any

import httpx

from metadata import configs
from metadata.models.errors import ODEError


class ODEClient:
    """A thin, retrying wrapper over the ODE REST GET interface."""

    def __init__(
        self,
        *,
        timeout: float = configs.REQUEST_TIMEOUT,
        max_retries: int = configs.MAX_RETRIES,
        backoff_base: float = configs.BACKOFF_BASE,
        client: httpx.Client | None = None,
    ) -> None:
        """Create a client.

        Args:
            timeout: Per request timeout in seconds.
            max_retries: Number of retries after the first attempt.
            backoff_base: Base delay in seconds for exponential backoff.
            client: An optional shared httpx client to reuse connections.

        Returns:
            None.
        """
        self._max_retries = max_retries
        self._backoff_base = backoff_base
        self._client = client or httpx.Client(timeout=timeout)

    def query(self, params: dict[str, str]) -> dict[str, Any]:
        """Run one ODE query and return its parsed ODEResults payload.

        Args:
            params: Query parameters excluding the output format.

        Returns:
            The ODEResults object from the response body.

        Raises:
            ODEError: If ODE errors, refuses the request, or every attempt fails.
        """
        merged = {**params, "output": "JSON"}
        last_error: Exception | None = None
        for attempt in range(self._max_retries + 1):
            try:
                response = self._client.get(configs.ODE_BASE_URL, params=merged)
            except httpx.HTTPError as exc:
                last_error = exc
                self._maybe_sleep(attempt)
                continue
            if response.status_code in configs.RETRYABLE_STATUS:
                last_error = ODEError(f"HTTP {response.status_code}")
                self._maybe_sleep(attempt)
                continue
            if response.status_code >= 400:
                raise ODEError(f"ODE refused the request: HTTP {response.status_code}")
            try:
                payload = response.json()
            except ValueError as exc:
                last_error = exc
                self._maybe_sleep(attempt)
                continue
            results = payload.get("ODEResults") if isinstance(payload, dict) else None
            if not isinstance(results, dict):
                last_error = ODEError("malformed ODE response")
                self._maybe_sleep(attempt)
                continue
            if str(results.get("Status", "")).upper() == "ERROR":
                raise ODEError(str(results.get("Error", "unknown ODE error")))
            return results
        raise ODEError(f"query failed after {self._max_retries} retries: {last_error}")

    def _maybe_sleep(self, attempt: int) -> None:
        """Sleep with capped exponential backoff and jitter before the next try.

        Args:
            attempt: The zero based attempt index that just failed.

        Returns:
            None.
        """
        if attempt >= self._max_retries:
            return
        delay = min(self._backoff_base * (2**attempt), configs.BACKOFF_MAX)
        time.sleep(delay + random.uniform(0.0, self._backoff_base))

    def close(self) -> None:
        """Close the underlying httpx client.

        Returns:
            None.
        """
        self._client.close()

    def __enter__(self) -> ODEClient:
        """Enter a context manager.

        Returns:
            This client.
        """
        return self

    def __exit__(self, *exc: object) -> None:
        """Close the client on context manager exit.

        Args:
            exc: Unused exception information.

        Returns:
            None.
        """
        self.close()
