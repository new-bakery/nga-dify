
import json
import redis
import numpy as np
import networkx as nx
from typing import Any
from redis.commands.search.query import Query
from networkx.readwrite import json_graph

from core.tools.tool.builtin_tool import BuiltinTool
from core.tools.entities.tool_entities import ToolInvokeMessage


from core.tools.provider.builtin.newbakery.config_keys import *
from core.tools.provider.builtin.newbakery.tools.newbakery_tool import *

class GetSOPs(BuiltinTool):
    
    def embedding_text(self, text: str, user_id:str) -> list[float]:
        from core.tools.provider.builtin.newbakery.tools.text_embedding import EmbeddingTextTool
        result = EmbeddingTextTool().fork_tool_runtime(
                runtime={
                    "credentials": self.runtime.credentials,
                }
            ).invoke(
                user_id=user_id,
                tool_parameters={
                    "text": text,
                },
            )
        result = json.loads(result[0].model_dump_json())
        return result['message'][EMBEDDING] 
    
    def _search_sops(self, redis_client: redis.StrictRedis, vector_buffer: bytes, P: int, similarity_threshold: float):
        redis_index_name = self.runtime.credentials[REDIS_SOP_INDEX_NAME]
        filter = f"@{IS_DISABLED}:{{{str(False).lower()}}}"
        query = (
            Query(f"({filter})=>[KNN {P} @embedding_sop $query_embedding AS vector_score]")
            .return_fields("sop_doc_id", "category", "metadata", "vector_score")
            .dialect(2)
        )
        result = redis_client.ft(redis_index_name).search(
            query, query_params={"query_embedding": vector_buffer}
        )
        # TODO: Need to add a threshold to detect non-related results
        # TODO：Use similarity_threshold here
        return result
    
    def get_related_sops(self, vector: list[float], similarity_threshold: float = 0.3, K : int = 1):
        redis_connection_string = self.runtime.credentials[REDIS_CONNECTION_STRING]
        
        redis_client = redis.Redis.from_url(redis_connection_string)
        vector_buffer = np.array(vector, dtype=np.float32).tobytes()
        sop_results = self._search_sops(redis_client, vector_buffer, K, similarity_threshold)
        sop_doc_ids = [doc["sop_doc_id"] for doc in sop_results.docs]

        return list(set(sop_doc_ids))
    
    def _invoke(self, user_id: str, tool_parameters: dict[str, Any]) -> ToolInvokeMessage:
        
        user_query = tool_parameters.get("user_query", "")
        similarity_threshold = tool_parameters.get("similarity_threshold", 0.3)
        
        vector = self.embedding_text(user_query, user_id)
        sop_doc_ids = self.get_related_sops(vector, similarity_threshold)

        sops = NewBakeryTool.get_sops(self, sop_doc_ids)
        
        res = {}
        if sops and len(sops) > 0:
            res[SOPS] = [copy_without_control_keys(sop) for sop in sops]
        else:
            res[SOPS] = []
        message = self.create_json_message(res)
        return message
    
    