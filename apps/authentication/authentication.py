"""
自定义认证类
"""
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django.utils.translation import gettext_lazy as _

from .services import AuthenticationService


class TokenAuthentication(BaseAuthentication):
    """
    自定义Token认证
    客户端应该在Authorization头中包含token：
    Authorization: Bearer 9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b
    """
    
    keyword = 'Bearer'
    model = None
    
    def authenticate(self, request):
        """认证用户"""
        auth = self.get_authorization_header(request).split()
        
        if not auth or auth[0].lower() != self.keyword.lower().encode():
            return None
        
        if len(auth) == 1:
            msg = _('Invalid token header. No credentials provided.')
            raise AuthenticationFailed(msg)
        elif len(auth) > 2:
            msg = _('Invalid token header. Token string should not contain spaces.')
            raise AuthenticationFailed(msg)
        
        try:
            token = auth[1].decode()
        except UnicodeError:
            msg = _('Invalid token header. Token string should not contain invalid characters.')
            raise AuthenticationFailed(msg)
        
        return self.authenticate_credentials(token, request)
    
    def authenticate_credentials(self, token, request):
        """验证token凭据"""
        user = AuthenticationService.get_user_from_token(token)
        
        if not user:
            raise AuthenticationFailed(_('Invalid token.'))
        
        if not user.is_active:
            raise AuthenticationFailed(_('User inactive or deleted.'))
        
        # 将token信息存储到request中，用于logout时使用
        from .models import UserSession
        try:
            session = UserSession.objects.get(token=token, is_active=True)
            request.session_id = session.session_id
        except UserSession.DoesNotExist:
            pass
        
        return (user, token)
    
    def get_authorization_header(self, request):
        """获取认证头"""
        auth = request.META.get('HTTP_AUTHORIZATION', b'')
        if isinstance(auth, str):
            # Work around django test client oddness
            auth = auth.encode('iso-8859-1')
        return auth
    
    def authenticate_header(self, request):
        """返回认证头格式"""
        return self.keyword
