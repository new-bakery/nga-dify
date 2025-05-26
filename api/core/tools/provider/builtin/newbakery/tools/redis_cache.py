
from typing import Any
import redis

from core.tools.entities.tool_entities import ToolInvokeMessage
from core.tools.tool.builtin_tool import BuiltinTool

from core.tools.provider.builtin.newbakery.config_keys import *
from core.tools.provider.builtin.newbakery.tools.newbakery_tool import *


class RedisCacheTool(BuiltinTool):
    def _invoke(self, user_id: str, tool_parameters: dict[str, Any]) -> ToolInvokeMessage:
        
        redis_connection_string = self.runtime.credentials[REDIS_CONNECTION_STRING]

        workflow_runid = tool_parameters.get("dify_workflow_runid", None)
        key = tool_parameters.get("key", None)
        value = tool_parameters.get("value", None)
        action = tool_parameters.get("action", None)
        expire = tool_parameters.get("expire", 300)

        action = action.strip().lower()
        res = ''
        redis_client = redis.Redis.from_url(redis_connection_string)
        if action == 'get':
            if not redis_client.exists(f'{workflow_runid}-{key}'):
                res = value
            else:
                result = redis_client.get(f'{workflow_runid}-{key}')
                if result:
                    result = result.decode('utf-8')
                res = result
        elif action == 'set':
            redis_client.setex(f'{workflow_runid}-{key}', expire, value)
            res = ''
        else:
            raise ValueError(f'Invalid action {action}. Only accept "get" or "set"')
        message = self.create_text_message(res)
        return message

