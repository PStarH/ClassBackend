"""
用户认证序列化器
"""
from rest_framework import serializers
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from django.core.validators import EmailValidator
from django.core.exceptions import ValidationError as DjangoValidationError
from .models import UserProfile, EmailVerification
import re


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
    email = serializers.EmailField(
        validators=[EmailValidator()],
        help_text='有效的邮箱地址'
    )
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'password_confirm', 'first_name', 'last_name']
        extra_kwargs = {
            'username': {'help_text': '用户名，3-30位字符'},
            'first_name': {'required': False, 'help_text': '姓'},
            'last_name': {'required': False, 'help_text': '名'},
        }
    
    def validate_username(self, value):
        """验证用户名"""
        if len(value) < 3:
            raise serializers.ValidationError("用户名至少3位字符")
        if len(value) > 30:
            raise serializers.ValidationError("用户名不能超过30位字符")
        if not re.match(r'^[a-zA-Z0-9_]+$', value):
            raise serializers.ValidationError("用户名只能包含字母、数字和下划线")
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("该用户名已被注册")
        return value
    
    def validate_email(self, value):
        """验证邮箱"""
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("该邮箱已被注册")
        return value
    
    def validate_password(self, value):
        """验证密码强度"""
        if len(value) < 8:
            raise serializers.ValidationError("密码至少8位字符")
        
        # 检查是否包含字母
        if not re.search(r'[a-zA-Z]', value):
            raise serializers.ValidationError("密码必须包含字母")
        
        # 检查是否包含数字
        if not re.search(r'\d', value):
            raise serializers.ValidationError("密码必须包含数字")
        
        return value
    
    def validate(self, data):
        """验证密码确认"""
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError("两次输入的密码不一致")
        return data
    
    def create(self, validated_data):
        """创建用户"""
        # 移除确认密码字段
        validated_data.pop('password_confirm', None)
        
        # 创建用户
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            is_active=True  # 先设为激活，后续可以改为需要邮箱验证
        )
        
        # 创建用户资料
        UserProfile.objects.create(user=user)
        
        return user


class UserLoginSerializer(serializers.Serializer):
    """用户登录序列化器"""
    
    username = serializers.CharField(
        help_text='用户名或邮箱'
    )
    password = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'},
        help_text='密码'
    )
    
    def validate(self, data):
        """验证登录凭据"""
        username = data.get('username')
        password = data.get('password')
        
        if username and password:
            # 支持用户名或邮箱登录
            if '@' in username:
                # 使用邮箱登录
                try:
                    user_obj = User.objects.get(email=username)
                    username = user_obj.username
                except User.DoesNotExist:
                    raise serializers.ValidationError("邮箱或密码错误")
            
            user = authenticate(username=username, password=password)
            
            if not user:
                raise serializers.ValidationError("用户名/邮箱或密码错误")
            
            if not user.is_active:
                raise serializers.ValidationError("账户已被禁用")
            
            data['user'] = user
        else:
            raise serializers.ValidationError("必须提供用户名和密码")
        
        return data


class UserSerializer(serializers.ModelSerializer):
    """用户信息序列化器"""
    
    profile = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 
                 'date_joined', 'last_login', 'is_active', 'profile']
        read_only_fields = ['id', 'date_joined', 'last_login', 'is_active']
    
    def get_profile(self, obj):
        """获取用户资料"""
        try:
            profile = obj.profile
            return {
                'phone': profile.phone,
                'bio': profile.bio,
                'learning_style': profile.learning_style,
                'timezone': profile.timezone,
                'email_notifications': profile.email_notifications,
                'is_profile_public': profile.is_profile_public,
            }
        except UserProfile.DoesNotExist:
            return None


class UserProfileSerializer(serializers.ModelSerializer):
    """用户资料序列化器"""
    
    class Meta:
        model = UserProfile
        fields = ['phone', 'bio', 'birth_date', 'learning_style', 
                 'timezone', 'email_notifications', 'is_profile_public']


class EmailVerificationSerializer(serializers.ModelSerializer):
    """邮箱验证序列化器"""
    
    class Meta:
        model = EmailVerification
        fields = ['email', 'verification_code']
        read_only_fields = ['email']


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
    
    def validate_new_password(self, value):
        """验证新密码强度"""
        if len(value) < 8:
            raise serializers.ValidationError("密码至少8位字符")
        
        if not re.search(r'[a-zA-Z]', value):
            raise serializers.ValidationError("密码必须包含字母")
        
        if not re.search(r'\d', value):
            raise serializers.ValidationError("密码必须包含数字")
        
        return value
    
    def validate(self, data):
        """验证密码"""
        if data['new_password'] != data['new_password_confirm']:
            raise serializers.ValidationError("两次输入的新密码不一致")
        return data
