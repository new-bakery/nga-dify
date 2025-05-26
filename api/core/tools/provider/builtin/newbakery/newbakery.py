from typing import Any

from core.tools.errors import ToolProviderCredentialValidationError
from core.tools.provider.builtin.time.tools.current_time import CurrentTimeTool
from core.tools.provider.builtin_tool_provider import BuiltinToolProviderController
from services.account_service import AccountService
from .config_keys import DIFY_ACCOUNT_USER_EMAIL, DIFY_ACCOUNT_USER_PASSWORD

class NewBakeryProvider(BuiltinToolProviderController):
    def _validate_credentials(self, credentials: dict[str, Any]) -> None:
        try:
            email = credentials[DIFY_ACCOUNT_USER_EMAIL]
            password = credentials[DIFY_ACCOUNT_USER_PASSWORD]
            account = AccountService.authenticate(email, password)

            # TODO: validate all parameters

        except Exception as e:
            raise ToolProviderCredentialValidationError(str(e))