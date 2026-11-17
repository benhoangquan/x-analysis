"""Provider-neutral Judge interface and the Jev implementation."""

from __future__ import annotations

import base64
import json
import os
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from typing import Any, Protocol

from src.enrichment import rubric
from src.schema import PostLabels

JEV_URL = "https://api.typesafe.ai/v1/systemone"
DEFAULT_MODEL = "jev-latest"
Transport = Callable[[dict[str, Any], dict[str, str]], dict[str, Any]]


class Judge(Protocol):
    version: str

    def label(
        self, post_id: str, text: str, media_kind: str | None, image: bytes | None
    ) -> PostLabels: ...


class JevError(RuntimeError):
    def __init__(self, status: int, detail: str):
        super().__init__(f"HTTP {status}: {detail}")
        self.status = status


def _http(body: dict[str, Any], headers: dict[str, str]) -> dict[str, Any]:
    req = urllib.request.Request(
        JEV_URL, data=json.dumps(body).encode(), headers=headers, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:  # noqa: S310
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        raise JevError(e.code, e.read().decode()[:300]) from e


class JevJudge:
    def __init__(
        self, token: str | None = None, model: str = DEFAULT_MODEL, transport: Transport = _http
    ):
        self.token = token or os.environ.get("JEV_TOKEN") or os.environ.get("TYPESAFE_API_KEY")
        if not self.token:
            raise RuntimeError("JEV_TOKEN is not set")
        self.model = model
        self.version = rubric.label_version(model)
        self.transport = transport
        self.input_tokens = 0  # running total, for cost reporting

    def _call(self, body: dict[str, Any], with_image: bool) -> dict[str, Any]:
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {self.token}"}
        if with_image:
            headers["TypeSafe-Danger-Zone-Images"] = "true"
        for attempt in range(4):
            try:
                out = self.transport(body, headers)
                self.input_tokens += out.get("usage", {}).get("input_tokens", 0)
                return out
            except JevError as e:
                if e.status == 429 and attempt < 3:
                    time.sleep(2**attempt)
                    continue
                raise
        raise AssertionError("unreachable")

    def ask(self, body: dict[str, Any]) -> dict[str, Any]:
        """Send a text-only request built elsewhere (for example roster admission)."""
        return self._call(body, with_image=False)

    def label(
        self, post_id: str, text: str, media_kind: str | None, image: bytes | None
    ) -> PostLabels:
        ref = f"img-{post_id}" if image else None
        b64 = base64.b64encode(image).decode() if image else None
        fmt = "png" if image and image[:4] == b"\x89PNG" else "jpg"
        body = rubric.build_request(text, self.model, ref, b64, fmt)
        used = image is not None
        try:
            out = self._call(body, with_image=used)
        except JevError as e:
            if not used or e.status not in (400, 422):
                raise
            # The image was rejected (size or format). Label the text without it.
            body = rubric.build_request(text, self.model)
            out, used = self._call(body, with_image=False), False
        return rubric.parse_answers(post_id, self.version, out["answers"], media_kind, used)
