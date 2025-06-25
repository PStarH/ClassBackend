"""
模型混入类
"""
from django.db import models
from django.contrib.auth.models import User


class TimestampMixin(models.Model):
    """时间戳混入"""
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        abstract = True


class SoftDeleteMixin(models.Model):
    """软删除混入"""
    
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        abstract = True
    
    def soft_delete(self):
        from django.utils import timezone
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save()
    
    def restore(self):
        self.is_deleted = False
        self.deleted_at = None
        self.save()


class AuditMixin(models.Model):
    """审计混入"""
    
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(class)s_created_set'
    )
    
    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(class)s_updated_set'
    )
    
    class Meta:
        abstract = True


class PublishMixin(models.Model):
    """发布状态混入"""
    
    class PublishStatus(models.TextChoices):
        DRAFT = 'draft', '草稿'
        PUBLISHED = 'published', '已发布'
        ARCHIVED = 'archived', '已归档'
    
    status = models.CharField(
        max_length=20,
        choices=PublishStatus.choices,
        default=PublishStatus.DRAFT
    )
    
    published_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        abstract = True
    
    def publish(self):
        from django.utils import timezone
        self.status = self.PublishStatus.PUBLISHED
        self.published_at = timezone.now()
        self.save()
    
    def unpublish(self):
        self.status = self.PublishStatus.DRAFT
        self.published_at = None
        self.save()


class VersionMixin(models.Model):
    """版本控制混入"""
    
    version = models.PositiveIntegerField(default=1)
    
    class Meta:
        abstract = True
    
    def save(self, *args, **kwargs):
        if self.pk:
            self.version += 1
        super().save(*args, **kwargs)
