from __future__ import annotations

from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities import ParameterOption
from dify_plugin.entities.tool import ToolInvokeMessage

from tools._client import ApiError, as_list, file_url, parse_extra
from tools._common import client_for, deliver, model_options

MAX_REFERENCES = 16
WAIT_SECONDS = 300


class GenerateImageTool(Tool):
    def _fetch_parameter_options(self, parameter: str) -> list[ParameterOption]:
        return model_options("image") if parameter == "model" else []

    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        try:
            prompt = (tool_parameters.get("prompt") or "").strip()
            model = (tool_parameters.get("model") or "").strip()
            if not prompt:
                raise ApiError("A prompt is required.")
            if not model:
                raise ApiError("Pick an image model.")
            client = client_for(self)
            body: dict[str, Any] = {**parse_extra(tool_parameters.get("extra")), "model": model, "prompt": prompt}
            for key in ("aspect_ratio", "resolution", "quality"):
                value = tool_parameters.get(key)
                if value and value != "auto":
                    body[key] = value

            references = as_list(tool_parameters.get("images"))
            links = [u.strip() for u in str(tool_parameters.get("image_urls") or "").split(",") if u.strip()]
            if len(references) + len(links) > MAX_REFERENCES:
                raise ApiError(f"At most {MAX_REFERENCES} reference images.")
            urls = [file_url(client, f, f"reference-{i + 1}.png") for i, f in enumerate(references)] + links
            if urls:
                body["image_urls"] = urls

            task = client.submit("images", body)
            result = client.wait("images", task, WAIT_SECONDS)
            yield from deliver(self, "images", model, result)
        except ApiError as exc:
            raise ValueError(str(exc)) from None
