
import os
import boto3
from typing import Any

from botocore.exceptions import NoCredentialsError

from core.tools.entities.tool_entities import ToolInvokeMessage
from core.tools.tool.builtin_tool import BuiltinTool

from core.tools.provider.builtin.newbakery.config_keys import *
from core.tools.provider.builtin.newbakery.tools.newbakery_tool import *

class UploadtoS3Tool(BuiltinTool):
    
    def _invoke(self, user_id: str, tool_parameters: dict[str, Any]) -> ToolInvokeMessage:
        
        endpoint = self.runtime.credentials[S3_ENDPOINT]
        access_key = self.runtime.credentials[S3_ACCESS_KEY]
        secret_key = self.runtime.credentials[S3_SECRET_KEY]
        bucket_name = self.runtime.credentials[S3_BUCKET_NAME]
        use_ssl = self.runtime.credentials[S3_USE_SSL]
        region_name =self.runtime.credentials[S3_REGION_NAME]
        verify = self.runtime.credentials[S3_VERIFY]

        object_name = tool_parameters.get("s3_object_name", "")
        file_path = tool_parameters.get("s3_file_path", "")
        
        res = ''
        file_path = os.path.abspath(file_path)
        if verify.strip().lower() in ['', 'false', 'no']:
            verify = False
        s3_client = boto3.client('s3',
                    endpoint_url = endpoint,
                    aws_access_key_id = access_key,
                    aws_secret_access_key = secret_key,
                    region_name = region_name,
                    use_ssl = use_ssl,
                    verify = verify) 
        s3_client.upload_file(file_path, bucket_name, object_name)
        message = self.create_text_message(res)
        return message

    
