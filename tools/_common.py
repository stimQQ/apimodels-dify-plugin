"""Helpers shared by the tools. Kept outside the tool modules because the Dify SDK expects
exactly one Tool subclass per tool source file."""

from __future__ import annotations

import re
from collections.abc import Generator
from typing import Any

from dify_plugin.entities import I18nObject, ParameterOption

from tools._client import ApiError, Client, TaskResult, extension_for

RECORDS_URL = "https://apimodels.app/console/records"


def client_for(tool: Any) -> Client:
    return Client(tool.runtime.credentials.get("api_key") or "")


def model_options(modality: str) -> list[ParameterOption]:
    return [ParameterOption(value=m, label=I18nObject(en_US=m)) for m in Client.models(modality)]


def safe_name(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", text).strip("-") or "result"


def deliver(tool: Any, kind: str, model: str, result: TaskResult) -> Generator[Any, None, None]:
    """Turn a task result into Dify messages: files for the results, JSON for the workflow, text for chat."""
    label = "image" if kind == "images" else "video"
    if result.state == "failed":
        raise ApiError(f"The {label} was not generated and nothing was charged. Reason: {result.message}")
    if result.state == "running":
        yield tool.create_json_message({"task_id": result.task_id, "status": "running"})
        yield tool.create_text_message(
            f"The {label} is still being generated. Task ID: {result.task_id}. "
            f"Run the Get Task tool with this ID in a minute or two, or see {RECORDS_URL}"
        )
        return
    summary = {"task_id": result.task_id, "status": "completed", "urls": result.urls, "credits": result.credits}
    if model:
        summary["model"] = model
    yield tool.create_json_message(summary)
    not_attached = []
    for index, url in enumerate(result.urls):
        fetched = tool_download(url)
        if fetched is None:
            not_attached.append(url)
            continue
        data, mime = fetched
        filename = f"{safe_name(model or result.task_id)}-{index + 1}.{extension_for(mime, url)}"
        yield tool.create_blob_message(blob=data, meta={"mime_type": mime, "filename": filename})
    lines = [f"Result {i + 1}: {u}" for i, u in enumerate(result.urls)]
    note = "Result links are kept for 30 days."
    if not_attached:
        note += " Some files could not be attached here (too large or not on apimodels.app storage); use the links."
    yield tool.create_text_message("\n".join(lines + [note]))


def tool_download(url: str):
    return Client.download(url)
