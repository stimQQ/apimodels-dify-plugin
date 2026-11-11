from typing import Any

from dify_plugin import ToolProvider
from dify_plugin.errors.tool import ToolProviderCredentialValidationError

from tools._client import ApiError, Client


class ApimodelsProvider(ToolProvider):
    def _validate_credentials(self, credentials: dict[str, Any]) -> None:
        try:
            Client(credentials.get("api_key") or "", timeout=20).balance()
        except ApiError as exc:
            raise ToolProviderCredentialValidationError(str(exc)) from None
