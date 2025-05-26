from typing import Any
import time

from flask_login import current_user

from core.tools.entities.tool_entities import ToolInvokeMessage
from core.tools.tool.builtin_tool import BuiltinTool
from core.model_manager import ModelManager,ModelType
from core.entities.embedding_type import EmbeddingInputType
from services.account_service import AccountService

from core.tools.provider.builtin.newbakery.config_keys import *


class EmbeddingTextTool(BuiltinTool):
    def _invoke(self, user_id: str, tool_parameters: dict[str, Any]) -> ToolInvokeMessage:

        try:
            # if you use this tool direct in dify, you can get the tenant id easily.
            tenant_id = current_user.current_tenant_id
        except:
            # if you call it from api, you cannot get the tenant id. We need try to sign in.
            email = self.runtime.credentials[DIFY_ACCOUNT_USER_EMAIL]
            password = self.runtime.credentials[DIFY_ACCOUNT_USER_PASSWORD]
            account = AccountService.authenticate(email, password)
            account = AccountService.load_user(account.id)
            tenant_id = account.current_tenant_id

        text = tool_parameters.get("text", "").strip()
        model_manager = ModelManager()
        model = model_manager.get_default_model_instance(tenant_id=tenant_id, model_type=ModelType.TEXT_EMBEDDING)

        max_retry = 3
        retry_interval = 2
        retried = 0
        while retried < max_retry:
            try:
                texts = model.invoke_text_embedding(texts=[text], user=user_id, input_type=EmbeddingInputType.QUERY)
                break
            except Exception as e:
                retried += 1
                if retried == max_retry:
                    raise e
                else:
                    time.sleep(retry_interval)

        res = {"text" : text , 'model': model.model, EMBEDDING : texts.embeddings[0], DIMENSION : len(texts.embeddings[0])}
        message = self.create_json_message(res)
        message.meta['usage'] = texts.usage
        return message
