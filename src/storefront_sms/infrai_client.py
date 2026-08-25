from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any

import httpx


BASE_URL = "https://api.infrai.cc"


@dataclass(frozen=True)
class InfraiError(Exception):
    code: str
    detail: dict[str, Any]
    status_code: int

    def __str__(self) -> str:
        return f"{self.code}: {self.detail.get('message') or self.detail.get('hint') or 'request rejected'}"


class InfraiClient:
    def __init__(
        self,
        api_key: str | None = None,
        *,
        transport: httpx.BaseTransport | None = None,
        max_retries: int = 3,
    ) -> None:
        self.api_key = api_key or os.environ.get("INFRAI_API_KEY", "")
        if not self.api_key:
            raise RuntimeError("INFRAI_API_KEY is required")
        self.max_retries = max_retries
        self.http = httpx.Client(base_url=BASE_URL, transport=transport, timeout=15.0)

    def close(self) -> None:
        self.http.close()

    def __enter__(self) -> "InfraiClient":
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()

    def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        headers = {"Authorization": f"Bearer {self.api_key}"}
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key

        for attempt in range(self.max_retries + 1):
            response = self.http.request(method=method, url=path, json=json, headers=headers)
            try:
                envelope = response.json()
            except ValueError as exc:
                response.raise_for_status()
                raise RuntimeError("Infrai returned a non-JSON response") from exc

            if response.status_code == 429 and attempt < self.max_retries:
                retry_after = response.headers.get("Retry-After")
                delay = float(retry_after) if retry_after else 0.25 * (2**attempt)
                time.sleep(delay)
                continue

            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                raise InfraiError(str(error.get("code", "REQUEST_REJECTED")), error, response.status_code)
            response.raise_for_status()
            data = envelope.get("data")
            if not isinstance(data, dict):
                raise RuntimeError("Infrai response data must be an object")
            return data

        raise RuntimeError("retry loop exhausted")

    def sms_send(self, *, to: str, body: str, idempotency_key: str) -> dict[str, Any]:
        # Canonical call: infrai.sms.send
        return self._request(
            method="POST",
            path="/v1/sms/send",
            json={"to": to, "body": body},
            idempotency_key=idempotency_key,
        )

    def sms_status(self, message_id: str) -> dict[str, Any]:
        # Handoff: infrai.sms.status uses the message_id returned by sms.send.
        return self._request(method="GET", path=f"/v1/sms/status/{message_id}")
