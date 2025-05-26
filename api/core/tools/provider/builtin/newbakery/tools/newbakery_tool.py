import json
import copy
import pymongo
from core.tools.provider.builtin.newbakery.config_keys import *
from bson import ObjectId

def copy_without_control_keys(json_data, is_control_key=lambda key: key.startswith('_')):
    def _remove_control_keys(data):
        if isinstance(data, dict):
            keys_to_remove = [key for key in data if is_control_key(key)]
            for key in keys_to_remove:
                del data[key]
            for key, value in data.items():
                if isinstance(value, (dict, list)):
                    _remove_control_keys(value)
        elif isinstance(data, list):
            for item in data:
                if isinstance(item, (dict, list)):
                    _remove_control_keys(item)
        return data

    json_data_copy = copy.deepcopy(json_data)
    return _remove_control_keys(json_data_copy)



class NewBakeryTool():

    @staticmethod
    def get_mongodb_collection(tool, collection_name):
        mongodb_connection_string = tool.runtime.credentials[MONGODB_CONNECTION_STRING]
        mongodb_database_name = tool.runtime.credentials[MONGODB_DATABASE_NAME]

        client = pymongo.MongoClient(mongodb_connection_string)
        db = client[mongodb_database_name]
        collection = db[collection_name]
        
        return collection

    @staticmethod
    def get_conversation_collection(tool):
        conversation_collection_name = tool.runtime.credentials[CONVERSATION_COLLECTION_NAME]
        collection = NewBakeryTool.get_mongodb_collection(tool, conversation_collection_name)
        return collection

    @staticmethod
    def get_sop_collection(tool):
        sop_collection_name = tool.runtime.credentials[SOP_COLLECTION_NAME]
        collection = NewBakeryTool.get_mongodb_collection(tool, sop_collection_name)
        return collection

    @staticmethod
    def get_sops(tool, sop_doc_ids, projection = None):
        sop_collection = NewBakeryTool.get_sop_collection(tool)
        sops = []
        if projection:
            projection = {k: 1 for k in projection}
            if not '_id' in projection:
                projection['_id'] = 0
                
        for sop_doc_id in sop_doc_ids:
            sop = sop_collection.find_one({"_id": ObjectId(sop_doc_id)}, projection)
            if '_id' in sop:
                sop['_id'] = str(sop['_id'])
            sops.append(sop)
            
        return sops

    @staticmethod
    def get_source_schema(tool, source_doc_id, projection = None):
        schema_collection_name = tool.runtime.credentials[SCHEMA_COLLECTION_NAME]
        collection = NewBakeryTool.get_mongodb_collection(tool, schema_collection_name)

        if projection:
            projection = {k: 1 for k in projection}
            if not '_id' in projection:
                projection['_id'] = 0

        source_schema = collection.find_one({'_id': ObjectId(source_doc_id)}, projection)
        if not source_schema:
            raise Exception(f"Schema database {source_doc_id} not found")
        
        if '_id' in source_schema:
            source_schema['_id'] = str(source_schema['_id'])

        return source_schema
    
    @staticmethod
    def get_conversation(tool, conversation_id):
        collection = NewBakeryTool.get_conversation_collection(tool)
        conversation = collection.find_one({'_id': ObjectId(conversation_id)}, projection={'_id': 0} )
        return conversation

    @staticmethod
    def build_message_markdown(message):
        # NOTICE: This is not for DISPLAY for end users. Its for reference for LLMs or for Embedding
        content = []
        role = message[ROLE]
        mardkwon_content = '\n'.join(message.get(MARKDOWNS, []))
        json_content = '\n'.join([f"```json \n {json.dumps(j)} \n ```" for j in message.get(JSONS, [])])
        content.append(f"**{role}:**")
        content.append(mardkwon_content)
        content.append(json_content)
        content.append("\n---\n")
        return '\n'.join(content)

    @staticmethod
    def build_conversation_markdown(conversation):
        # NOTICE: This is not for DISPLAY for end users. Its for reference for LLMs or for Embedding
        history = []
        if conversation and MESSAGES in conversation:
            for message in conversation[MESSAGES]:
                history.append(NewBakeryTool.build_message_markdown(message))
        return '\n'.join(history)
    
    