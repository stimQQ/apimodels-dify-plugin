from __future__ import annotations

from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

from tools._client import ApiError
from tools._common import client_for, deliver

WAIT_SECONDS = 240


class GetTaskTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        try:
            task_id = (tool_parameters.get("task_id") or "").strip()
            if not task_id:
                raise ApiError("A task ID is required.")
            kind = "video" if tool_parameters.get("kind") == "video" else "images"
            client = client_for(self)
            result = client.wait(kind, client.check(kind, task_id), WAIT_SECONDS)
            yield from deliver(self, kind, "", result)
        except ApiError as exc:
            raise ValueError(str(exc)) from None
