"""
OpenAPI预处理钩子 - 移除敏感字段
"""


def remove_sensitive_fields(result, generator, request, public):
    """
    移除API文档中的敏感字段信息
    """
    sensitive_fields = [
        'password', 
        'secret_key', 
        'api_key', 
        'token',
        'csrf_token',
        'session_id'
    ]
    
    def clean_schema(schema):
        if isinstance(schema, dict):
            # 移除敏感属性
            for field in sensitive_fields:
                if field in schema.get('properties', {}):
                    del schema['properties'][field]
            
            # 递归清理嵌套结构
            for key, value in schema.items():
                if isinstance(value, (dict, list)):
                    clean_schema(value)
        elif isinstance(schema, list):
            for item in schema:
                clean_schema(item)
    
    # 清理整个API文档
    clean_schema(result)
    return result