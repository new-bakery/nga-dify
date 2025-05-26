
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

class GetQuerySchemaTool(BuiltinTool):

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

    def _search_redis(self, redis_client: redis.StrictRedis, vector_buffer: bytes, source_doc_id: str, category: str, index_name: str, P: int, similarity_threshold: float):
        filter = f"@{SOURCE_DOC_ID}:{{{source_doc_id}}} @{CATEGORY}:{{{category}}} @{IS_DISABLED}:{{{str(False).lower()}}}"
        query = (
            Query(f"({filter})=>[KNN {P} @embedding_schema $query_embedding AS vector_score]")
            .return_fields(TABLE_NAME, "metadata", "vector_score")
            .dialect(2)
        )
        result = redis_client.ft(index_name).search(
            query, query_params={"query_embedding": vector_buffer}
        )
        # TODO: Need to add a threshold to detect non-related results
        # TODO：Use similarity_threshold here
        return result

    def get_related_tables(self, vector: list[float], source_doc_id: str, similarity_threshold: float = 0.3, N : int = 3, K : int = 5):
        redis_connection_string = self.runtime.credentials[REDIS_CONNECTION_STRING]
        redis_index_name = self.runtime.credentials[REDIS_SCHEMA_INDEX_NAME]

        redis_client = redis.Redis.from_url(redis_connection_string)
        vector_buffer = np.array(vector, dtype=np.float32).tobytes()

        column_results = self._search_redis(redis_client, vector_buffer, source_doc_id, COLUMNS, redis_index_name, K, similarity_threshold)
        column_tables = [doc[TABLE_NAME] for doc in column_results.docs]
        table_results = self._search_redis(redis_client, vector_buffer, source_doc_id, TABLES, redis_index_name, N, similarity_threshold)
        table_tables = [doc[TABLE_NAME] for doc in table_results.docs]

        return list(set(column_tables + table_tables))
    
    def get_connected_sub_graph(self, table_names: list[str], G: nx.Graph):
        subgraph_nodes = set(table_names)
        for i in range(len(table_names)):
            for j in range(len(table_names)):
                if j <= i:
                    continue
                try:
                    path = nx.shortest_path(G, source=table_names[i], target=table_names[j])
                    subgraph_nodes.update(path)
                except nx.NetworkXNoPath:
                    # If no path exists, ignore it
                    pass

        subgraph = G.subgraph(subgraph_nodes).copy()
        return subgraph

    def _invoke(self, user_id: str, tool_parameters: dict[str, Any]) -> ToolInvokeMessage:
        
        user_query = tool_parameters.get("user_query", "")
        source_doc_id = tool_parameters.get("source_doc_id", "")
        schema_tokens_threshold = tool_parameters.get("schema_tokens_threshold", 8000)
        similarity_threshold = tool_parameters.get("similarity_threshold", 0.3)
        
        res = {}

        source_schema = NewBakeryTool.get_source_schema(self, source_doc_id)

        source_name = source_schema[SOURCE_NAME]
        dialect = source_schema[DIALECT]
        res[DIALECT] = dialect
        res[CONNECTION_STRING] = source_schema[CONNECTION_STRING]
        
        # if a database total token count smaller or equal to the threshold, we will directly use it without any searching
        if STATISTICS in source_schema and TOKENS_COUNT in source_schema[STATISTICS]:
            token_count = source_schema[STATISTICS][TOKENS_COUNT]
            if token_count <= schema_tokens_threshold:
                table_schemas =  source_schema[TABLES]
                res[QUERY_SCHEMA] = [copy_without_control_keys(table_schema) for table_schema in table_schemas]
                message = self.create_json_message(res)
                return message

        # if the schema is too large, we will use the embedding to represent the schema
        # First check the GRAPH existence, if not, throw error

        if GRAPH not in source_schema:
            raise Exception('_graph is required to get_query_schema')

        # if the schema is too large, we will use the embedding to represent the schema
        vector = self.embedding_text(user_query, user_id)
        # res[EMBEDDING] = vector
        
        G = json_graph.node_link_graph(source_schema[GRAPH], edges="edges")
        
        table_list = self.get_related_tables(vector, source_doc_id, similarity_threshold, N = 3, K = 5)
        
       
        if table_list and len(table_list) > 0:
            subgraph = self.get_connected_sub_graph(table_list, G)
            nodes = set(subgraph.nodes)
            res[QUERY_SCHEMA] = [copy_without_control_keys(table_schema) for table_schema in source_schema[TABLES] if table_schema[TABLE_NAME] in nodes]
            message = self.create_json_message(res)
            return message
        else:
            raise Exception('No related tables found')

