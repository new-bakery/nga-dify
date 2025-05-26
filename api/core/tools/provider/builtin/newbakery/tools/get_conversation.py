import json
from typing import Any
from core.tools.entities.tool_entities import ToolInvokeMessage
from core.tools.tool.builtin_tool import BuiltinTool

from core.tools.provider.builtin.newbakery.config_keys import *
from core.tools.provider.builtin.newbakery.tools.newbakery_tool import *


class GetConversationTool(BuiltinTool):

    def _invoke(self, user_id: str, tool_parameters: dict[str, Any]) -> ToolInvokeMessage:
        conversation_id = tool_parameters.get(CONVERSATION_ID, '')
        conversation = NewBakeryTool.get_conversation(self, conversation_id)
        markdown_history = NewBakeryTool.build_conversation_markdown(conversation)
        return self.create_json_message({MARKDOWN_HISTORY: markdown_history, CONVERSATION: conversation})
        