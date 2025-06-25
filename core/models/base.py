"""
基础模型类
"""
from django.db import models
from django.contrib.auth.models import User
import uuid


class BaseModel(models.Model):
    """基础模型类，包含通用字段"""
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="唯一标识符"
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="创建时间"
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="更新时间"
    )
    
    is_active = models.BooleanField(
        default=True,
        help_text="是否激活"
    )
    
    class Meta:
        abstract = True
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.__class__.__name__}: {self.id}"


class UserOwnedModel(BaseModel):
    """用户拥有的模型基类"""
    
    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='%(class)s_set',
        help_text="拥有者"
    )
    
    class Meta:
        abstract = True
    
    def __str__(self):
        return f"{self.__class__.__name__}: {self.id} (Owner: {self.owner.username})"


class NamedModel(BaseModel):
    """有名称的模型基类"""
    
    name = models.CharField(
        max_length=255,
        help_text="名称"
    )
    
    description = models.TextField(
        blank=True,
        null=True,
        help_text="描述"
    )
    
    class Meta:
        abstract = True
    
    def __str__(self):
        return self.name


class SlugModel(NamedModel):
    """带 slug 的模型基类"""
    
    slug = models.SlugField(
        max_length=255,
        unique=True,
        help_text="URL 友好的标识符"
    )
    
    class Meta:
        abstract = True
    
    def save(self, *args, **kwargs):
        if not self.slug:
            from django.utils.text import slugify
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
