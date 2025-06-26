"""
用户认证序列化器
"""
from rest_framework import serializers
from django.contrib.auth import authenticate
from django.core.validators import EmailValidator
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone
from datetime import timedelta
import re
import secrets

from .models import User, UserSettings


class UserRegistrationSerializer(serializers.ModelSerializer):
    """用户注册序列化器"""
    
    password = serializers.CharField(
        write_only=True,
        min_length=8,
        style={'input_type': 'password'},
        help_text='密码至少8位，包含字母和数字'
    )
    password_confirm = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'},
        help_text='确认密码'
    )
    
    class Meta:
        model = User
        fields = ['email', 'username', 'password', 'password_confirm']
        extra_kwargs = {
            'email': {'help_text': '有效的邮箱地址'},
            'username': {'help_text': '用户名，3-100位字符'},
        }
    
    def validate_email(self, value):
        """验证邮箱"""
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("该邮箱已被注册")
        return value
    
    def validate_username(self, value):
        """验证用户名"""
        if len(value) < 3:
            raise serializers.ValidationError("用户名至少3位字符")
        if len(value) > 100:
            raise serializers.ValidationError("用户名不能超过100位字符")
        return value
    
    def validate_password(self, value):
        """验证密码强度"""
        if len(value) < 8:
            raise serializers.ValidationError("密码至少8位字符")
        if not re.search(r'[A-Za-z]', value):
            raise serializers.ValidationError("密码必须包含字母")
        if not re.search(r'\d', value):
            raise serializers.ValidationError("密码必须包含数字")
        return value
    
    def validate(self, attrs):
        """验证密码确认"""
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({"password_confirm": "两次输入的密码不一致"})
        return attrs
    
    def create(self, validated_data):
        """创建用户"""
        validated_data.pop('password_confirm')
        user = User.objects.create_user(**validated_data)
        return user


class UserLoginSerializer(serializers.Serializer):
    """用户登录序列化器"""
    
    email = serializers.EmailField(help_text='邮箱地址')
    password = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'},
        help_text='密码'
    )
    
    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')
        
        if not email or not password:
            raise serializers.ValidationError("邮箱和密码都是必需的")
        
        try:
            user = User.objects.get(email=email)
            if not user.check_password(password):
                raise serializers.ValidationError("邮箱或密码错误")
            if not user.is_active:
                raise serializers.ValidationError("账户已被禁用")
        except User.DoesNotExist:
            raise serializers.ValidationError("邮箱或密码错误")
        
        attrs['user'] = user
        return attrs


class UserSerializer(serializers.ModelSerializer):
    """用户信息序列化器"""
    
    class Meta:
        model = User
        fields = ['uuid', 'email', 'username', 'last_login', 'created_at']
        read_only_fields = ['uuid', 'last_login', 'created_at']


class UserUpdateSerializer(serializers.ModelSerializer):
    """用户信息更新序列化器"""
    
    class Meta:
        model = User
        fields = ['username', 'email']
    
    def validate_email(self, value):
        """验证邮箱是否已被其他用户使用"""
        user = self.instance
        if User.objects.filter(email=value).exclude(uuid=user.uuid).exists():
            raise serializers.ValidationError("该邮箱已被其他用户使用")
        return value
    
    def validate_username(self, value):
        """验证用户名"""
        if len(value) < 3:
            raise serializers.ValidationError("用户名至少3位字符")
        if len(value) > 100:
            raise serializers.ValidationError("用户名不能超过100位字符")
        return value


class PasswordChangeSerializer(serializers.Serializer):
    """密码修改序列化器"""
    
    old_password = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'},
        help_text='当前密码'
    )
    new_password = serializers.CharField(
        write_only=True,
        min_length=8,
        style={'input_type': 'password'},
        help_text='新密码'
    )
    new_password_confirm = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'},
        help_text='确认新密码'
    )
    
    def validate_old_password(self, value):
        """验证旧密码"""
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("当前密码错误")
        return value
    
    def validate_new_password(self, value):
        """验证新密码强度"""
        if len(value) < 8:
            raise serializers.ValidationError("密码至少8位字符")
        if not re.search(r'[A-Za-z]', value):
            raise serializers.ValidationError("密码必须包含字母")
        if not re.search(r'\d', value):
            raise serializers.ValidationError("密码必须包含数字")
        return value
    
    def validate(self, attrs):
        """验证新密码确认"""
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({"new_password_confirm": "两次输入的新密码不一致"})
        return attrs
    
    def save(self):
        """保存新密码"""
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save()
        return user



class LoginResponseSerializer(serializers.Serializer):
    """登录响应序列化器"""
    
    user = UserSerializer(read_only=True)


class UserSettingsSerializer(serializers.ModelSerializer):
    """用户设置序列化器"""
    
    class Meta:
        model = UserSettings
        fields = [
            'user_uuid', 'preferred_pace', 'preferred_style', 'tone',
            'feedback_frequency', 'major', 'education_level', 'notes',
            'skills', 'created_at', 'updated_at'
        ]
        read_only_fields = ['user_uuid', 'created_at', 'updated_at']
    
    def validate_skills(self, value):
        """验证技能列表"""
        if not isinstance(value, list):
            raise serializers.ValidationError("技能必须是一个列表")
        
        # 确保技能列表中都是字符串
        for skill in value:
            if not isinstance(skill, str):
                raise serializers.ValidationError("技能项必须是字符串")
            if len(skill.strip()) == 0:
                raise serializers.ValidationError("技能项不能为空")
        
        # 去重并去除空白
        cleaned_skills = list(set(skill.strip() for skill in value if skill.strip()))
        
        # 限制技能数量
        if len(cleaned_skills) > 20:
            raise serializers.ValidationError("技能数量不能超过20个")
        
        return cleaned_skills
    
    def validate_major(self, value):
        """验证专业字段"""
        if value and len(value.strip()) > 100:
            raise serializers.ValidationError("专业名称不能超过100个字符")
        return value.strip() if value else value
    
    def validate_notes(self, value):
        """验证备注字段"""
        if value and len(value.strip()) > 1000:
            raise serializers.ValidationError("备注不能超过1000个字符")
        return value.strip() if value else value


class UserSettingsCreateSerializer(UserSettingsSerializer):
    """用户设置创建序列化器 - 用于注册后创建用户设置"""
    
    def create(self, validated_data):
        """创建用户设置"""
        user = self.context['request'].user
        validated_data['user_uuid'] = user
        return super().create(validated_data)


class UserSettingsUpdateSerializer(UserSettingsSerializer):
    """用户设置更新序列化器"""
    
    class Meta(UserSettingsSerializer.Meta):
        # 更新时所有字段都是可选的
        extra_kwargs = {
            'preferred_pace': {'required': False},
            'preferred_style': {'required': False},
            'tone': {'required': False},
            'feedback_frequency': {'required': False},
        }
