import json
import uuid
import datetime
import redis
import struct
from typing import Any
from redis.commands.search.field import TagField, TextField, VectorField, NumericField


from core.tools.entities.tool_entities import ToolInvokeMessage
from core.tools.tool.builtin_tool import BuiltinTool

from core.tools.provider.builtin.newbakery.config_keys import *
from core.tools.provider.builtin.newbakery.tools.newbakery_tool import *


FLAT = "FLAT" # 线性搜索
HNSW = "HNSW" # Hierarchical Navigable Small World

IP = "IP" #内积。
COSINE = "COSINE" # 余弦相似度。
L2 = "L2" # L2 欧几里得距离

# 定义构建索引时的搜索宽度。
# 默认值为 200，增加此值可以提升索引构建精度，但会显著增加索引构建时间和内存占用。
EF_CONSTRUCTION = 200 

# 定义每个节点的连接数（即图的稀疏程度）。
# 默认值为 16，增大此值可以提高搜索精度，但会增加内存使用。
M = 16


ID = 'id'


class AddtoConversationTool(BuiltinTool):

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

    def create_redis_index(self, redis_client, index_name: str, vector_dim: int, index_type: str = HNSW, similarity_type: str = COSINE):
        try:
            redis_client.ft(index_name).info()
        except redis.exceptions.ResponseError:
            options = {
                "TYPE": "FLOAT32",
                "DIM": vector_dim,
                "DISTANCE_METRIC": similarity_type,
            }
            if index_type == HNSW:
                options.update({
                    "EF_CONSTRUCTION": EF_CONSTRUCTION,
                    "M": M
                })
            if index_type == FLAT:
                options.update({
                    "BLOCK_SIZE" : 1024
                })
            redis_client.ft(index_name).create_index([
                TagField(ID),
                TagField(CONVERSATION_ID),
                TagField(MESSAGE_ID),
                TagField(ROLE),
                TagField(IS_ERROR),
                TextField(MESSAGE),
                VectorField(
                    name=EMBEDDING,
                    algorithm=index_type,
                    attributes=options
                ),
                NumericField(TOKENS_COUNT),
            ])
    def add_to_redis(self, conversation_id, message):
        message_id = message[MESSAGE_ID]
        role = message[ROLE]
        is_error = message[IS_ERROR]
        embedding = message[EMBEDDING]
        binary_vector = struct.pack(f"{len(embedding)}f", *embedding)
        key = f"{conversation_id}-{message_id}"

        redis_connection_string = self.runtime.credentials[REDIS_CONNECTION_STRING]
        redis_index_name = self.runtime.credentials[REDIS_CONVERSATION_INDEX_NAME]

        redis_client = redis.StrictRedis.from_url(redis_connection_string)
        self.create_redis_index(redis_client, redis_index_name, len(embedding))

        if redis_client.exists(key):
            redis_client.delete(key)
        
        redis_client.hset(
            key,
            mapping={
                ID: key,
                CONVERSATION_ID: conversation_id,
                MESSAGE_ID: message_id,
                ROLE: role,
                IS_ERROR: str(is_error).lower(),
                EMBEDDING: binary_vector,
                MESSAGE: json.dumps(message),
                TOKENS_COUNT: 0, # TODO: calculate tokens count
            }
        )

    def add_to_mongodb(self, conversation_id, message):
        
        collection = NewBakeryTool.get_conversation_collection(self)
        conversation = NewBakeryTool.get_conversation(self, conversation_id)
        if not conversation:
            untitled_topic = f"Untitled_{datetime.datetime.now().strftime('%Y_%m_%d_%H_%M_%S')}"
            topic = untitled_topic
            if MARKDOWNS in message:
                markdowns = message.get(MARKDOWNS, [])
                if len(markdowns) > 0:
                    topic = markdowns[0]
                    if len(str.strip(topic)) == 0:
                        topic = untitled_topic
            if len(topic) == 0:
                topic = untitled_topic
            payload = {
                "_id": ObjectId(conversation_id),
                TOPIC: topic, 
                MESSAGES:[
                    message,
                ],
            }
            collection.insert_one(payload)
        else:
            collection.update_one({"_id": ObjectId(conversation_id)}, {"$push": {"messages": message}})


    def _invoke(self, user_id: str, tool_parameters: dict[str, Any]) -> ToolInvokeMessage:

        conversation_id = tool_parameters.get("conversation_id")
        message = tool_parameters.get("message", "{}")

        message = json.loads(message)
        
        if ROLE not in message:
            raise Exception(f"Message must contain {ROLE} field")
        
        if MESSAGE_ID not in message:
            message[MESSAGE_ID] = str(uuid.uuid4())
        if TIMESTAMP not in message:
            message[TIMESTAMP] = datetime.datetime.now().isoformat(timespec='milliseconds')
        if IS_ERROR not in message:
            message[IS_ERROR] = False
        elif isinstance(message[IS_ERROR], str):
            message[IS_ERROR] = message[IS_ERROR] == "true"
        if MARKDOWNS not in message:
            message[MARKDOWNS] = []
        if EMBEDDING not in message and not message[IS_ERROR]: # Embedding is for seaching the related messages. Error Messages should not be searchable
            embedding_markdown = NewBakeryTool.build_message_markdown(message)
            if embedding_markdown and len(embedding_markdown) > 0:
                # TODO: Embedding is not working properly. Sometimes, the embedding_markdown is too long, which cause the error !
                # message[EMBEDDING] = self.embedding_text(embedding_markdown, user_id)
                pass
        if ERROR_MESSAGE not in message:
            message[ERROR_MESSAGE] = ""
        if JSONS not in message:
            message[JSONS] = []
        if THOUGHT_PROCESS not in message:
            message[THOUGHT_PROCESS] = []
        
        message[CONVERSATION_ID] = conversation_id

        if EMBEDDING in message: # Only message has embedding can be searchable
            self.add_to_redis(conversation_id, message)

        self.add_to_mongodb(conversation_id, message)

        return self.create_json_message(message)
