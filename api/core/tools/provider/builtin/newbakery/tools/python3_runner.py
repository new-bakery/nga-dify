
import json
import redis
import numpy as np
import networkx as nx
from typing import Any
from redis.commands.search.query import Query
from networkx.readwrite import json_graph
from textwrap import dedent
import json
from base64 import b64decode, b64encode
import re
import pickle
import base64
from io import BytesIO
import zlib


from core.tools.tool.builtin_tool import BuiltinTool
from core.tools.entities.tool_entities import ToolInvokeMessage
from core.helper.code_executor.code_executor import CodeExecutor, CodeLanguage

class Python3RunnerTool(BuiltinTool):
    
    def get_python_code(self, text):
        match = re.search(r'```python(.*?)```', text, re.DOTALL)
        if match:
            code = match.group(1).strip()
            return code
        else:
            return text
    
    def _invoke(self, user_id: str, tool_parameters: dict[str, Any]) -> ToolInvokeMessage:
        
        data = tool_parameters.get("data", "")
        code = tool_parameters.get("code")
        result_type = tool_parameters.get("result_type") # dataframe, str, json, 
        
        if result_type.strip().lower() not in ['dataframe', 'str', 'json']:
            raise ValueError(f"Only dataframe, str, json are supported, got {result_type}")
        
        code = self.get_python_code(code)
        
        data = b64encode(data.encode('utf-8')).decode("utf-8")

        runner_script = dedent("""
            import json
            import pickle
            from base64 import b64decode, b64encode
            from io import BytesIO
            
            # declare main function
            {code}
            
            data = json.loads(b64decode('{data}'.encode('utf-8')).decode('utf-8'))
            
            # execute main function
            output_obj = main(data)
            
            pickle_bytes = BytesIO()
            pickle.dump(output_obj, pickle_bytes)
            pickle_bytes.seek(0)
            encoded_pickle = b64encode(pickle_bytes.read()).decode('utf-8')
            
            result = f'''<<RESULT>>{{encoded_pickle}}<<RESULT>>'''
            print(result)
            """)

        runner_script = runner_script.format(code=code, data=data)

        try:
            result = CodeExecutor.execute_code(CodeLanguage.PYTHON3, "", runner_script)
        except Exception as e:
            return self.create_json_message({"is_error":True, "error": str(e)})

        result = re.search(rf"<<RESULT>>(.*)<<RESULT>>", result, re.DOTALL)
        if not result:
            raise ValueError("Failed to parse result")
        result = result.group(1)
        
        pickle_bytes = BytesIO(base64.b64decode(result))
        restored = pickle.load(pickle_bytes)
        
        res = {"is_error": False}

        if result_type.strip().lower() == 'dataframe':
            res["result"] = restored.to_dict(orient='records')
        elif result_type.strip().lower() == 'json':
            res["result"] = restored
        elif result_type.strip().lower() == 'str':
            input_bytes = restored.encode('utf-8')
            compressed_data = zlib.compress(input_bytes)
            base64_encoded = base64.b64encode(compressed_data).decode('utf-8')
            res["result"] = base64_encoded
            
        message = self.create_json_message(res)
        return message
    
    
    