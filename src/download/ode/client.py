"""HTTP client for the ODE REST interface with retry and backoff."""

from __future__ import annotations

import random
import time
from typing import Any

import httpx

from download import configs


class ODEError(RuntimeError):
    """Raised when ODE reports an error or a query keeps failing."""


def as_list(value: Any) -> list[Any]:
    """Normalise an ODE field that may be missing, a single object, or a list.

    ODE returns a bare object rather than a one element list when a result set
    has a single member.

    Args:
        value: The raw field value from a parsed response.

    Returns:
        A list, empty when the value is missing.
    """
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


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
        self._timeout = timeout
        self._max_retries = max_retries
        self._backoff_base = backoff_base
        self._client = client or httpx.Client(timeout=timeout)

    def query(self, params: dict[str, str]) -> dict[str, Any]:
        """Run one ODE query and return its parsed ODEResults payload.

        Output is always requested as JSON. Transient transport failures,
        retryable HTTP statuses, and malformed bodies are retried with
        exponential backoff and jitter. An ODE body reporting Status ERROR is
        deterministic and is raised without retrying.

        Args:
            params: Query parameters excluding the output format.

        Returns:
            The ODEResults object from the response body.

        Raises:
            ODEError: If ODE reports an error or all attempts fail.
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
            response.raise_for_status()
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
        """Sleep with exponential backoff and jitter before the next attempt.

        Args:
            attempt: The zero based attempt index that just failed.

        Returns:
            None.
        """
        if attempt >= self._max_retries:
            return
        delay = self._backoff_base * (2**attempt)
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
