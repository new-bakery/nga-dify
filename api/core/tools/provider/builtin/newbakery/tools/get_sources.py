import json
from typing import Any

from core.tools.entities.tool_entities import ToolInvokeMessage
from core.tools.tool.builtin_tool import BuiltinTool
from core.model_manager import ModelManager,ModelType
from core.entities.embedding_type import EmbeddingInputType
from core.model_runtime.utils.encoders import jsonable_encoder
from flask_login import current_user

from pymongo import MongoClient
from bson import ObjectId
import copy

from core.tools.provider.builtin.newbakery.config_keys import *
from core.tools.provider.builtin.newbakery.tools.newbakery_tool import *


class GetSourcesTool(BuiltinTool):
    def _invoke(self, user_id: str, tool_parameters: dict[str, Any]) -> ToolInvokeMessage:

        source_doc_ids = tool_parameters.get("source_doc_ids")
        source_doc_ids = [str.strip(s) for s in source_doc_ids.split(',')]

        res = {}
        for source_doc_id in source_doc_ids:
            res[source_doc_id] = NewBakeryTool.get_source_schema(self, source_doc_id, [SOURCE_NAME, DESCRIPTION, ADDITIONAL_DETAILS])
        
        return self.create_json_message(res)
    