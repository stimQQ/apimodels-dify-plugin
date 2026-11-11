from __future__ import annotations

from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities import ParameterOption
from dify_plugin.entities.tool import ToolInvokeMessage

from tools._client import FIRST_FRAME_AS_IMAGE, FIRST_FRAME_AS_IMAGES, ApiError, as_list, file_url, parse_extra
from tools._common import client_for, deliver, model_options

MAX_REFERENCES = 9
# Dify allows a tool call up to 600 s here (see main.py); most clips finish well inside this.
WAIT_SECONDS = 540


class GenerateVideoTool(Tool):
    def _fetch_parameter_options(self, parameter: str) -> list[ParameterOption]:
        return model_options("video") if parameter == "model" else []

    @staticmethod
    def _one(client: Any, upload: Any, link: Any, name: str) -> str | None:
        if upload:
            return file_url(client, upload, name)
        link = str(link or "").strip()
        return link or None

    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        try:
            prompt = (tool_parameters.get("prompt") or "").strip()
            model = (tool_parameters.get("model") or "").strip()
            if not model:
                raise ApiError("Pick a video model.")
            client = client_for(self)
            body: dict[str, Any] = {**parse_extra(tool_parameters.get("extra")), "model": model}
            if prompt:
                body["prompt"] = prompt
            aspect = tool_parameters.get("aspect_ratio")
            if aspect and aspect != "auto":
                body["aspect_ratio"] = aspect
            resolution = str(tool_parameters.get("resolution") or "").strip()
            if resolution:
                body["resolution"] = resolution
            duration = tool_parameters.get("duration")
            if duration not in (None, "", 0):
                body["duration"] = int(duration)

            first = self._one(client, tool_parameters.get("first_frame"), tool_parameters.get("first_frame_url"), "first-frame.png")
            last = self._one(client, tool_parameters.get("last_frame"), tool_parameters.get("last_frame_url"), "last-frame.png")
            if last and not first:
                raise ApiError("A last frame needs a first frame.")
            if first:
                # first_frame_url is the platform's documented field (Seedance, Wan, MiniMax H3, Kling 4.0,
                # Vidu, Muse, Gemini Omni). A few model families read the first frame from another field.
                lowered = model.lower()
                body["first_frame_url"] = first
                if lowered in FIRST_FRAME_AS_IMAGE:
                    body["image"] = first
                elif lowered in FIRST_FRAME_AS_IMAGES:
                    body["images"] = [first]
            if last:
                # Most models read last_frame_url; older Kling models read image_tail.
                body["last_frame_url"] = last
                if model.lower() in FIRST_FRAME_AS_IMAGE:
                    body["image_tail"] = last

            references = as_list(tool_parameters.get("reference_images"))
            if len(references) > MAX_REFERENCES:
                raise ApiError(f"At most {MAX_REFERENCES} reference images.")
            if references:
                if first:
                    raise ApiError("Use either a first/last frame or reference images, not both.")
                body["reference_image_urls"] = [
                    file_url(client, f, f"reference-{i + 1}.png") for i, f in enumerate(references)
                ]

            task = client.submit("video", body)
            result = client.wait("video", task, WAIT_SECONDS)
            yield from deliver(self, "video", model, result)
        except ApiError as exc:
            raise ValueError(str(exc)) from None
