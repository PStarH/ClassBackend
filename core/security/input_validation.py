"""
输入验证和过滤中间件
防止XSS、SQL注入、CSRF等安全威胁
基于建议的最佳实践实现
"""
import re
import html
import logging
from typing import Dict, Any, List, Optional
from urllib.parse import unquote

from django.http import JsonResponse, HttpResponseBadRequest
from django.conf import settings
from django.core.exceptions import SuspiciousOperation
from django.utils.deprecation import MiddlewareMixin
from rest_framework import status

logger = logging.getLogger('security')

# 危险模式列表
DANGEROUS_PATTERNS = [
    # SQL注入模式
    r'(?i)(union\s+select|drop\s+table|delete\s+from|insert\s+into)',
    r'(?i)(select\s+.*\s+from\s+.*\s+where)',
    r'(?i)(exec\s*\(|execute\s*\()',
    r'(?i)(sp_executesql|xp_cmdshell)',
    r'(?i)(\'\s*;\s*drop|\'\s*;\s*delete|\'\s*;\s*insert)',
    
    # XSS模式
    r'(?i)(<script[^>]*>.*?</script>)',
    r'(?i)(javascript\s*:)',
    r'(?i)(on\w+\s*=)',
    r'(?i)(<iframe[^>]*>)',
    r'(?i)(<object[^>]*>)',
    r'(?i)(<embed[^>]*>)',
    r'(?i)(<link[^>]*>)',
    r'(?i)(<meta[^>]*>)',
    
    # 命令注入模式
    r'(?i)(;\s*rm\s+-rf|;\s*cat\s+/etc/passwd)',
    r'(?i)(wget\s+|curl\s+|nc\s+)',
    r'(?i)(\|\s*sh|\|\s*bash)',
    r'(?i)(eval\s*\(|exec\s*\()',
    
    # 路径遍历模式
    r'(?i)(\.\.\/|\.\.\\ )',
    r'(?i)(%2e%2e%2f|%2e%2e%5c)',
    r'(?i)(/etc/passwd|/etc/shadow)',
    r'(?i)(\/proc\/|\/sys\/)',
    
    # LDAP注入模式
    r'(?i)(\*\)\(|\)\(.*\*)',
    r'(?i)(\(\|\()',
    
    # NoSQL注入模式
    r'(?i)(\$where|\$ne|\$gt|\$lt)',
    r'(?i)(\{.*\$.*\})',
    
    # 文件包含漏洞
    r'(?i)(php://|file://|data://)',
    r'(?i)(include\s*\(|require\s*\()',
]

# 编译正则表达式模式
COMPILED_PATTERNS = [re.compile(pattern) for pattern in DANGEROUS_PATTERNS]

# 允许的HTML标签和属性
ALLOWED_HTML_TAGS = {
    'p', 'br', 'strong', 'em', 'u', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    'ul', 'ol', 'li', 'blockquote', 'code', 'pre'
}

ALLOWED_HTML_ATTRIBUTES = {
    'class', 'id'
}

# 最大字段长度限制
MAX_FIELD_LENGTHS = {
    'default': 1000,
    'text': 10000,
    'description': 5000,
    'title': 200,
    'name': 100,
    'email': 254,
    'url': 2048,
    'phone': 20,
    'username': 50,
}


class SecurityValidationError(Exception):
    """安全验证错误"""
    def __init__(self, message: str, attack_type: str = 'unknown'):
        self.message = message
        self.attack_type = attack_type
        super().__init__(message)


class InputSanitizer:
    """输入清理器"""
    
    @staticmethod
    def sanitize_string(value: str, max_length: Optional[int] = None) -> str:
        """清理字符串输入"""
        if not isinstance(value, str):
            return str(value)
        
        # URL解码
        try:
            value = unquote(value)
        except Exception:
            pass
        
        # 限制长度
        if max_length:
            value = value[:max_length]
        
        # HTML实体编码
        value = html.escape(value)
        
        # 移除控制字符
        value = ''.join(char for char in value if ord(char) >= 32 or char in '\n\r\t')
        
        return value.strip()
    
    @staticmethod
    def sanitize_html(value: str, allowed_tags: set = None, allowed_attrs: set = None) -> str:
        """清理HTML输入"""
        if not isinstance(value, str):
            return str(value)
        
        allowed_tags = allowed_tags or ALLOWED_HTML_TAGS
        allowed_attrs = allowed_attrs or ALLOWED_HTML_ATTRIBUTES
        
        # 简单的HTML清理实现
        # 在生产环境中建议使用专业的HTML清理库如bleach
        import re
        
        # 移除危险标签
        dangerous_tags = ['script', 'iframe', 'object', 'embed', 'link', 'meta', 'style']
        for tag in dangerous_tags:
            pattern = f'<{tag}[^>]*>.*?</{tag}>'
            value = re.sub(pattern, '', value, flags=re.IGNORECASE | re.DOTALL)
            pattern = f'<{tag}[^>]*/?>'
            value = re.sub(pattern, '', value, flags=re.IGNORECASE)
        
        # 移除事件处理器
        value = re.sub(r'on\w+\s*=\s*["\'][^"\']*["\']', '', value, flags=re.IGNORECASE)
        
        # 移除javascript:协议
        value = re.sub(r'javascript\s*:', '', value, flags=re.IGNORECASE)
        
        return value
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """清理文件名"""
        if not isinstance(filename, str):
            return str(filename)
        
        # 移除路径分隔符
        filename = filename.replace('/', '').replace('\\', '')
        
        # 移除危险字符
        filename = re.sub(r'[<>:"|?*]', '', filename)
        
        # 限制长度
        filename = filename[:255]
        
        # 防止保留文件名
        reserved_names = ['CON', 'PRN', 'AUX', 'NUL'] + [f'COM{i}' for i in range(1, 10)] + [f'LPT{i}' for i in range(1, 10)]
        if filename.upper() in reserved_names:
            filename = f'file_{filename}'
        
        return filename.strip()


class SecurityValidator:
    """安全验证器"""
    
    @staticmethod
    def detect_injection_attack(value: str) -> Optional[str]:
        """检测注入攻击"""
        if not isinstance(value, str):
            return None
        
        # 检查危险模式
        for pattern in COMPILED_PATTERNS:
            if pattern.search(value):
                return pattern.pattern
        
        return None
    
    @staticmethod
    def validate_field_length(value: str, field_name: str) -> bool:
        """验证字段长度"""
        max_length = MAX_FIELD_LENGTHS.get(field_name, MAX_FIELD_LENGTHS['default'])
        return len(value) <= max_length
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """验证邮箱格式"""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    @staticmethod
    def validate_url(url: str) -> bool:
        """验证URL格式"""
        from urllib.parse import urlparse
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception:
            return False
    
    @staticmethod
    def validate_json_structure(data: Dict[str, Any], max_depth: int = 10) -> bool:
        """验证JSON结构深度"""
        def get_depth(obj, current_depth=0):
            if current_depth > max_depth:
                return current_depth
            
            if isinstance(obj, dict):
                return max(get_depth(v, current_depth + 1) for v in obj.values()) if obj else current_depth
            elif isinstance(obj, list):
                return max(get_depth(item, current_depth + 1) for item in obj) if obj else current_depth
            else:
                return current_depth
        
        return get_depth(data) <= max_depth


class InputValidationMiddleware(MiddlewareMixin):
    """输入验证中间件"""
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.sanitizer = InputSanitizer()
        self.validator = SecurityValidator()
        
        # 跳过验证的路径
        self.skip_paths = getattr(settings, 'SECURITY_SKIP_PATHS', [
            '/health/',
            '/metrics/',
            '/static/',
            '/media/',
        ])
        
        # 严格验证的路径
        self.strict_paths = getattr(settings, 'SECURITY_STRICT_PATHS', [
            '/api/auth/',
            '/api/ai/',
            '/admin/',
        ])
    
    def __call__(self, request):
        # 检查是否跳过验证
        if self.should_skip_validation(request):
            return self.get_response(request)
        
        try:
            # 验证和清理输入
            self.validate_and_sanitize_request(request)
            
            # 处理请求
            response = self.get_response(request)
            
            # 添加安全头
            self.add_security_headers(response)
            
            return response
            
        except SecurityValidationError as e:
            # 记录安全事件
            self.log_security_event(request, e)
            
            # 返回错误响应
            return self.create_security_error_response(e)
    
    def should_skip_validation(self, request) -> bool:
        """检查是否应该跳过验证"""
        path = request.path
        return any(path.startswith(skip_path) for skip_path in self.skip_paths)
    
    def is_strict_path(self, request) -> bool:
        """检查是否是严格验证路径"""
        path = request.path
        return any(path.startswith(strict_path) for strict_path in self.strict_paths)
    
    def validate_and_sanitize_request(self, request):
        """验证和清理请求"""
        # 验证请求头
        self.validate_headers(request)
        
        # 验证查询参数
        self.validate_query_params(request)
        
        # 验证请求体
        if hasattr(request, 'body') and request.body:
            self.validate_request_body(request)
        
        # 验证文件上传
        if request.FILES:
            self.validate_uploaded_files(request)
    
    def validate_headers(self, request):
        """验证请求头"""
        dangerous_headers = ['X-Forwarded-Host', 'X-Originating-IP']
        
        for header_name, header_value in request.META.items():
            if not header_name.startswith('HTTP_'):
                continue
            
            # 检查危险头
            if header_name in dangerous_headers:
                logger.warning(f"Suspicious header detected: {header_name}")
            
            # 检查注入攻击
            if isinstance(header_value, str):
                attack_pattern = self.validator.detect_injection_attack(header_value)
                if attack_pattern:
                    raise SecurityValidationError(
                        f"Injection attack detected in header {header_name}",
                        'header_injection'
                    )
    
    def validate_query_params(self, request):
        """验证查询参数"""
        for param_name, param_values in request.GET.lists():
            for param_value in param_values:
                # 检查注入攻击
                attack_pattern = self.validator.detect_injection_attack(param_value)
                if attack_pattern:
                    raise SecurityValidationError(
                        f"Injection attack detected in parameter {param_name}",
                        'query_injection'
                    )
                
                # 验证字段长度
                if not self.validator.validate_field_length(param_value, param_name):
                    raise SecurityValidationError(
                        f"Parameter {param_name} exceeds maximum length",
                        'length_exceeded'
                    )
                
                # 清理参数值
                request.GET._mutable = True
                request.GET[param_name] = self.sanitizer.sanitize_string(param_value)
                request.GET._mutable = False
    
    def validate_request_body(self, request):
        """验证请求体"""
        content_type = request.content_type
        
        if content_type == 'application/json':
            self.validate_json_body(request)
        elif content_type.startswith('text/'):
            self.validate_text_body(request)
    
    def validate_json_body(self, request):
        """验证JSON请求体"""
        try:
            import json
            data = json.loads(request.body.decode('utf-8'))
            
            # 验证JSON结构深度
            if not self.validator.validate_json_structure(data):
                raise SecurityValidationError(
                    "JSON structure too deep",
                    'json_depth'
                )
            
            # 递归验证所有字符串字段
            self.validate_json_data(data)
            
        except json.JSONDecodeError:
            # JSON格式错误
            raise SecurityValidationError(
                "Invalid JSON format",
                'json_format'
            )
        except UnicodeDecodeError:
            # 编码错误
            raise SecurityValidationError(
                "Invalid encoding",
                'encoding_error'
            )
    
    def validate_json_data(self, data, path=""):
        """递归验证JSON数据"""
        if isinstance(data, dict):
            for key, value in data.items():
                current_path = f"{path}.{key}" if path else key
                
                if isinstance(value, str):
                    # 检查注入攻击
                    attack_pattern = self.validator.detect_injection_attack(value)
                    if attack_pattern:
                        raise SecurityValidationError(
                            f"Injection attack detected in field {current_path}",
                            'json_injection'
                        )
                    
                    # 验证字段长度
                    if not self.validator.validate_field_length(value, key):
                        raise SecurityValidationError(
                            f"Field {current_path} exceeds maximum length",
                            'json_length'
                        )
                
                elif isinstance(value, (dict, list)):
                    self.validate_json_data(value, current_path)
        
        elif isinstance(data, list):
            for i, item in enumerate(data):
                current_path = f"{path}[{i}]" if path else f"[{i}]"
                if isinstance(item, (dict, list, str)):
                    self.validate_json_data(item, current_path)
    
    def validate_text_body(self, request):
        """验证文本请求体"""
        try:
            text = request.body.decode('utf-8')
            
            # 检查注入攻击
            attack_pattern = self.validator.detect_injection_attack(text)
            if attack_pattern:
                raise SecurityValidationError(
                    "Injection attack detected in request body",
                    'body_injection'
                )
        
        except UnicodeDecodeError:
            raise SecurityValidationError(
                "Invalid text encoding",
                'encoding_error'
            )
    
    def validate_uploaded_files(self, request):
        """验证上传的文件"""
        for field_name, uploaded_file in request.FILES.items():
            # 验证文件名
            safe_filename = self.sanitizer.sanitize_filename(uploaded_file.name)
            uploaded_file.name = safe_filename
            
            # 验证文件大小
            max_size = getattr(settings, 'MAX_UPLOAD_SIZE', 100 * 1024 * 1024)  # 100MB
            if uploaded_file.size > max_size:
                raise SecurityValidationError(
                    f"File {field_name} exceeds maximum size",
                    'file_size'
                )
            
            # 验证文件类型
            allowed_types = getattr(settings, 'ALLOWED_FILE_TYPES', [
                'image/jpeg', 'image/png', 'image/gif', 'text/plain', 
                'application/pdf', 'application/json'
            ])
            
            if uploaded_file.content_type not in allowed_types:
                raise SecurityValidationError(
                    f"File type {uploaded_file.content_type} not allowed",
                    'file_type'
                )
    
    def add_security_headers(self, response):
        """添加安全头"""
        # 基础安全头
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        # 内容安全策略
        if not response.has_header('Content-Security-Policy'):
            csp = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
                "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
                "font-src 'self' https://fonts.gstatic.com; "
                "img-src 'self' data: https:; "
                "connect-src 'self' https://api.deepseek.com; "
                "frame-ancestors 'none';"
            )
            response['Content-Security-Policy'] = csp
        
        # HSTS (仅HTTPS)
        if getattr(settings, 'SECURE_SSL_REDIRECT', False):
            response['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains; preload'
        
        return response
    
    def log_security_event(self, request, error: SecurityValidationError):
        """记录安全事件"""
        client_ip = self.get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', 'Unknown')
        
        logger.warning(
            f"Security violation detected: {error.message} | "
            f"Attack type: {error.attack_type} | "
            f"IP: {client_ip} | "
            f"Path: {request.path} | "
            f"Method: {request.method} | "
            f"User-Agent: {user_agent}"
        )
        
        # 记录到安全事件表（如果配置了）
        if getattr(settings, 'SECURITY_LOG_TO_DB', False):
            self.log_to_database(request, error, client_ip, user_agent)
    
    def get_client_ip(self, request):
        """获取客户端IP"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', 'Unknown')
        return ip
    
    def log_to_database(self, request, error, client_ip, user_agent):
        """记录到数据库"""
        # 这里可以实现具体的数据库记录逻辑
        pass
    
    def create_security_error_response(self, error: SecurityValidationError):
        """创建安全错误响应"""
        response_data = {
            'error': 'Security validation failed',
            'message': 'Your request contains potentially harmful content',
            'code': 'SECURITY_VIOLATION'
        }
        
        response = JsonResponse(response_data, status=status.HTTP_400_BAD_REQUEST)
        self.add_security_headers(response)
        
        return response


# 导出主要组件
__all__ = [
    'InputValidationMiddleware',
    'SecurityValidator',
    'InputSanitizer',
    'SecurityValidationError',
]