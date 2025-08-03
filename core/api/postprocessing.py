"""
OpenAPI后处理钩子 - 添加安全头
"""


def add_security_headers(result, generator, request, public):
    """
    为API文档添加安全配置信息
    """
    if 'info' not in result:
        result['info'] = {}
    
    # 添加安全策略信息
    result['info']['x-security-policy'] = {
        'authentication_required': True,
        'rate_limiting': True,
        'cors_enabled': True,
        'https_only': not public  # 生产环境强制HTTPS
    }
    
    # 添加安全定义
    if 'components' not in result:
        result['components'] = {}
    
    if 'securitySchemes' not in result['components']:
        result['components']['securitySchemes'] = {}
    
    result['components']['securitySchemes'].update({
        'TokenAuthentication': {
            'type': 'apiKey',
            'in': 'header',
            'name': 'Authorization',
            'description': 'Token-based authentication. Format: Token <your-token>'
        },
        'SessionAuthentication': {
            'type': 'apiKey',
            'in': 'cookie',
            'name': 'sessionid',
            'description': 'Session-based authentication for web clients'
        }
    })
    
    # 为所有路径添加安全要求
    if 'paths' in result:
        for path_item in result['paths'].values():
            for operation in path_item.values():
                if isinstance(operation, dict) and 'operationId' in operation:
                    if 'security' not in operation:
                        operation['security'] = [
                            {'TokenAuthentication': []},
                            {'SessionAuthentication': []}
                        ]
    
    return result