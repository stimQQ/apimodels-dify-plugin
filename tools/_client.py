"""Small HTTP client for the apimodels.app generation API, shared by the tools.

Image and video generation is asynchronous on apimodels.app: a POST creates a task and
returns its id, and GET ?task_id= reports its state until it is "completed" (with result
URLs) or "failed". Billing happens only when a task completes, so a failed or abandoned
task costs nothing.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import Any

import requests

API_BASE = "https://api.apimodels.app/v1"
USER_AGENT = "apimodels-dify-plugin/0.1.0"
POLL_SECONDS = 5
# Larger results are not attached to the Dify message; the URL is returned instead.
MAX_ATTACH_BYTES = 50 * 1024 * 1024

# Ids in the public model list that are not text/image-to-image or text/image-to-video
# generation (downloaders, face detection, lip-sync helpers) or that are not suitable for
# a general-purpose marketplace tool.
_EXCLUDE = re.compile(r"spicy|^media-downloader$|^kling-identify-face$|^kling-lip-sync-")

# Video models that read the first frame from the scalar `image` field (as well as, or instead
# of, `first_frame_url`).
FIRST_FRAME_AS_IMAGE = {
    "kling-v2-6",
    "kling-video-o1",
    "kling-v3-omni",
    "kling-effects",
    "dreamactor-v2",
    "v3.1-fast-start-end",
    "wan-animate",
    "ltx-2.3",
    "grok-imagine-video-1.5",
    "grok-video-3",
    "grok-video-3-10s",
}
# Video models that read the first frame from `images[0]`.
FIRST_FRAME_AS_IMAGES = {"veo-3.1", "veo-3.1-fast-fhd", "veo-3.1-fast-hd"}


class ApiError(Exception):
    """An error message that is safe to show to the user (never contains the API key)."""


@dataclass
class TaskResult:
    task_id: str
    state: str  # "completed", "failed" or "running"
    urls: list[str] = field(default_factory=list)
    message: str = ""
    credits: Any = None


class Client:
    def __init__(self, api_key: str, timeout: int = 60):
        self.api_key = (api_key or "").strip()
        self.timeout = timeout

    # ---- plumbing ---------------------------------------------------------------

    def _headers(self, json_body: bool = True) -> dict[str, str]:
        if not self.api_key:
            raise ApiError("No apimodels.app API key is configured for this plugin.")
        headers = {"Authorization": f"Bearer {self.api_key}", "User-Agent": USER_AGENT}
        if json_body:
            headers["Content-Type"] = "application/json"
        return headers

    @staticmethod
    def _message(payload: Any, status: int) -> str:
        if isinstance(payload, dict):
            err = payload.get("error")
            if isinstance(err, dict) and err.get("message"):
                return str(err["message"])
            if isinstance(err, str) and err:
                return err
            for key in ("msg", "message"):
                if payload.get(key):
                    return str(payload[key])
        return f"HTTP {status}"

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        try:
            resp = requests.request(method, f"{API_BASE}{path}", timeout=self.timeout, **kwargs)
        except requests.RequestException as exc:
            raise ApiError(f"Could not reach apimodels.app: {type(exc).__name__}") from None
        try:
            payload = resp.json()
        except ValueError:
            payload = None
        if resp.status_code >= 400:
            if resp.status_code == 401:
                raise ApiError("The apimodels.app API key was rejected. Check it at https://apimodels.app/console/api-keys")
            if resp.status_code == 402:
                raise ApiError("The apimodels.app balance is too low for this request. Top up at https://apimodels.app/console/credits")
            raise ApiError(self._message(payload, resp.status_code))
        return payload

    # ---- endpoints -----------------------------------------------------------

    def balance(self) -> dict[str, Any]:
        payload = self._request("GET", "/balance", headers=self._headers())
        return (payload or {}).get("data") or {}

    @staticmethod
    def models(modality: str) -> list[str]:
        """Public model list (no key needed), filtered to one modality ("image" or "video")."""
        try:
            resp = requests.get(f"{API_BASE}/models", headers={"User-Agent": USER_AGENT}, timeout=20)
            data = resp.json().get("data") or []
        except (requests.RequestException, ValueError, AttributeError):
            return []
        ids = [m.get("id") for m in data if isinstance(m, dict) and m.get("modality") == modality]
        return sorted(i for i in ids if isinstance(i, str) and not _EXCLUDE.search(i))

    def upload(self, data: bytes, filename: str, mime: str) -> str:
        """Upload bytes (e.g. a Dify file) and return a public URL the generation API can read."""
        files = {"file": (filename, data, mime or "application/octet-stream")}
        payload = self._request("POST", "/files", headers=self._headers(json_body=False), files=files)
        url = ((payload or {}).get("data") or {}).get("publicUrl")
        if not url:
            raise ApiError(f"Upload of {filename} failed.")
        return url

    def submit(self, kind: str, body: dict[str, Any]) -> TaskResult:
        """kind is "images" or "video". Returns a running task, or a completed one for a synchronous answer."""
        if kind == "images":
            body = {**body, "async": True, "response_format": "url"}
        payload = self._request("POST", f"/{kind}/generations", headers=self._headers(), json=body) or {}
        data = payload.get("data")
        if isinstance(data, dict) and data.get("taskId"):
            return TaskResult(task_id=str(data["taskId"]), state="running")
        if isinstance(data, list):  # an older synchronous image answer: already finished
            urls = [d.get("url") for d in data if isinstance(d, dict) and isinstance(d.get("url"), str)]
            if urls:
                return TaskResult(task_id="(synchronous)", state="completed", urls=urls)
        raise ApiError(self._message(payload, 200) if payload else "The API returned no task id.")

    def check(self, kind: str, task_id: str) -> TaskResult:
        payload = self._request("GET", f"/{kind}/generations", headers=self._headers(), params={"task_id": task_id}) or {}
        d = payload.get("data") or {}
        state = d.get("state")
        if state == "completed":
            urls = d.get("resultUrls") or []
            if not urls:
                return TaskResult(task_id, "failed", message="The task finished without a result.")
            return TaskResult(task_id, "completed", urls=list(urls), credits=d.get("credits"))
        if state == "failed":
            return TaskResult(task_id, "failed", message=str(d.get("failMsg") or d.get("failCode") or "Generation failed."))
        return TaskResult(task_id, "running")

    def wait(self, kind: str, task: TaskResult, max_seconds: int) -> TaskResult:
        if task.state != "running":
            return task
        deadline = time.monotonic() + max_seconds
        while True:
            time.sleep(POLL_SECONDS)
            result = self.check(kind, task.task_id)
            if result.state != "running" or time.monotonic() >= deadline:
                return result

    @staticmethod
    def download(url: str) -> tuple[bytes, str] | None:
        """Fetch a result file to attach it in Dify. Returns None when it is too large or unreachable."""
        try:
            with requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=120, stream=True) as resp:
                if resp.status_code != 200:
                    return None
                size = int(resp.headers.get("Content-Length") or 0)
                if size > MAX_ATTACH_BYTES:
                    return None
                chunks, total = [], 0
                for chunk in resp.iter_content(1024 * 256):
                    total += len(chunk)
                    if total > MAX_ATTACH_BYTES:
                        return None
                    chunks.append(chunk)
                mime = (resp.headers.get("Content-Type") or "application/octet-stream").split(";")[0].strip()
                return b"".join(chunks), mime
        except requests.RequestException:
            return None


def parse_extra(raw: Any) -> dict[str, Any]:
    """The optional "extra" parameter: a JSON object of model-specific fields, passed through as-is."""
    import json

    if raw in (None, ""):
        return {}
    if isinstance(raw, dict):
        return raw
    try:
        value = json.loads(str(raw))
    except ValueError:
        raise ApiError('"Extra parameters" must be a JSON object, for example {"seed": 42}.') from None
    if not isinstance(value, dict):
        raise ApiError('"Extra parameters" must be a JSON object, for example {"seed": 42}.')
    return value


def as_list(value: Any) -> list[Any]:
    if not value:
        return []
    return value if isinstance(value, list) else [value]


def file_url(client: Client, upload: Any, fallback_name: str) -> str:
    """Turn a Dify file parameter into a public URL by uploading its bytes to apimodels.app."""
    name = getattr(upload, "filename", None) or fallback_name
    mime = getattr(upload, "mime_type", None) or "application/octet-stream"
    return client.upload(upload.blob, name, mime)


def extension_for(mime: str, url: str) -> str:
    known = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp", "image/gif": "gif",
             "image/svg+xml": "svg", "video/mp4": "mp4", "video/webm": "webm", "video/quicktime": "mov"}
    if mime in known:
        return known[mime]
    tail = url.split("?")[0].rsplit(".", 1)
    return tail[1].lower() if len(tail) == 2 and len(tail[1]) <= 4 else "bin"
