"""
数据库行级安全策略
"""
from django.db import models
from django.core.exceptions import PermissionDenied
from django.contrib.auth import get_user_model

User = get_user_model()


class RowLevelSecurityMixin:
    """行级安全混入类"""
    
    def check_access_permission(self, user, action='read'):
        """检查访问权限"""
        if not user.is_authenticated:
            raise PermissionDenied("用户未认证")
        
        # 检查是否为数据拥有者
        if hasattr(self, 'user') and self.user != user:
            if not user.is_staff:
                raise PermissionDenied("无权限访问其他用户的数据")
        
        # 检查是否为用户自己的数据
        if hasattr(self, 'user_uuid') and self.user_uuid != user:
            if not user.is_staff:
                raise PermissionDenied("无权限访问其他用户的数据")
        
        return True
    
    def save(self, *args, **kwargs):
        """重写保存方法，添加安全检查"""
        user = kwargs.pop('user', None)
        if user:
            self.check_access_permission(user, 'write')
        super().save(*args, **kwargs)


class SecureQuerySet(models.QuerySet):
    """安全查询集"""
    
    def for_user(self, user):
        """只返回用户有权限访问的数据"""
        if not user.is_authenticated:
            return self.none()
        
        if user.is_staff:
            return self
        
        # 根据模型类型过滤数据
        if hasattr(self.model, 'user'):
            return self.filter(user=user)
        elif hasattr(self.model, 'user_uuid'):
            return self.filter(user_uuid=user)
        
        return self
    
    def active_only(self):
        """只返回激活的数据"""
        if hasattr(self.model, 'is_active'):
            return self.filter(is_active=True)
        return self


class SecureManager(models.Manager):
    """安全管理器"""
    
    def get_queryset(self):
        return SecureQuerySet(self.model, using=self._db)
    
    def for_user(self, user):
        return self.get_queryset().for_user(user)
    
    def active_only(self):
        return self.get_queryset().active_only()


class DataMaskingMixin:
    """数据脱敏混入类"""
    
    SENSITIVE_FIELDS = ['phone', 'email', 'id_card']
    
    def mask_sensitive_data(self, user=None):
        """脱敏敏感数据"""
        if user and (user.is_staff or self._is_data_owner(user)):
            return self  # 管理员和数据拥有者可以看到原始数据
        
        masked_instance = self.__class__()
        for field in self._meta.fields:
            field_name = field.name
            value = getattr(self, field_name)
            
            if field_name in self.SENSITIVE_FIELDS and value:
                if field_name == 'phone':
                    masked_value = f"{value[:3]}****{value[-4:]}" if len(value) >= 7 else '****'
                elif field_name == 'email':
                    parts = value.split('@')
                    if len(parts) == 2:
                        username = parts[0]
                        domain = parts[1]
                        masked_username = f"{username[:2]}****{username[-1:]}" if len(username) > 3 else '****'
                        masked_value = f"{masked_username}@{domain}"
                    else:
                        masked_value = '****'
                elif field_name == 'id_card':
                    masked_value = f"{value[:6]}****{value[-4:]}" if len(value) >= 10 else '****'
                else:
                    masked_value = '****'
                
                setattr(masked_instance, field_name, masked_value)
            else:
                setattr(masked_instance, field_name, value)
        
        return masked_instance
    
    def _is_data_owner(self, user):
        """检查是否为数据拥有者"""
        if hasattr(self, 'user') and self.user == user:
            return True
        if hasattr(self, 'user_uuid') and self.user_uuid == user:
            return True
        return False


class AuditMixin(models.Model):
    """审计混入类"""
    
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(class)s_created_set',
        verbose_name='创建者'
    )
    
    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(class)s_updated_set',
        verbose_name='最后修改者'
    )
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    # 审计字段
    audit_log = models.JSONField(default=dict, blank=True, verbose_name='审计日志')
    
    class Meta:
        abstract = True
    
    def save(self, *args, **kwargs):
        """重写保存方法，记录审计信息"""
        user = kwargs.pop('user', None)
        
        # 记录修改历史
        if self.pk:  # 更新操作
            if user:
                self.updated_by = user
            
            # 记录字段变更
            if hasattr(self, '_state') and self._state.adding is False:
                old_instance = self.__class__.objects.get(pk=self.pk)
                changes = {}
                
                for field in self._meta.fields:
                    field_name = field.name
                    old_value = getattr(old_instance, field_name)
                    new_value = getattr(self, field_name)
                    
                    if old_value != new_value:
                        changes[field_name] = {
                            'old': str(old_value),
                            'new': str(new_value)
                        }
                
                if changes:
                    if 'changes' not in self.audit_log:
                        self.audit_log['changes'] = []
                    
                    self.audit_log['changes'].append({
                        'timestamp': str(models.functions.Now()),
                        'user': str(user.uuid) if user else 'system',
                        'changes': changes
                    })
        else:  # 创建操作
            if user:
                self.created_by = user
        
        super().save(*args, **kwargs)


class SoftDeleteMixin(models.Model):
    """软删除混入类"""
    
    is_deleted = models.BooleanField(default=False, verbose_name='是否删除')
    deleted_at = models.DateTimeField(null=True, blank=True, verbose_name='删除时间')
    deleted_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(class)s_deleted_set',
        verbose_name='删除者'
    )
    
    class Meta:
        abstract = True
    
    def delete(self, *args, **kwargs):
        """软删除"""
        user = kwargs.pop('user', None)
        self.is_deleted = True
        self.deleted_at = models.functions.Now()
        if user:
            self.deleted_by = user
        self.save()
    
    def hard_delete(self, *args, **kwargs):
        """硬删除"""
        super().delete(*args, **kwargs)
    
    def restore(self, user=None):
        """恢复删除"""
        self.is_deleted = False
        self.deleted_at = None
        self.deleted_by = None
        self.save()


class EncryptedFieldMixin:
    """加密字段混入类"""
    
    def encrypt_field(self, field_name, value):
        """加密字段值"""
        if not value:
            return value
        
        # 这里可以集成更复杂的加密逻辑
        # 简单示例使用base64编码（生产环境应使用更强的加密）
        import base64
        return base64.b64encode(str(value).encode()).decode()
    
    def decrypt_field(self, field_name, value):
        """解密字段值"""
        if not value:
            return value
        
        try:
            import base64
            return base64.b64decode(value.encode()).decode()
        except:
            return value  # 解密失败返回原值
