#!/usr/bin/env python
"""
Test script for the standardized API error handling system
测试标准化API错误处理系统的脚本
"""

import os
import sys
import django
from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status

# Setup Django environment
sys.path.append('/Users/sampan/Documents/GitHub/Classroom/ClassBackend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.testing')

try:
    django.setup()
except Exception as e:
    print(f"Failed to setup Django: {e}")
    sys.exit(1)

# Now we can import Django models and our modules
from core.utils.api_response import (
    StandardResponse, 
    ApiErrorHandler, 
    api_error_handler,
    user_operation_handler
)
from apps.authentication.models import User, UserSettings
from rest_framework.response import Response
from rest_framework.serializers import ValidationError as DRFValidationError
from django.core.exceptions import ValidationError, ObjectDoesNotExist


def test_standard_response():
    """Test StandardResponse class methods"""
    print("=== Testing StandardResponse ===")
    
    # Test success response
    success_response = StandardResponse.success(
        data={"user_id": 123},
        message="测试成功"
    )
    print(f"Success Response: {success_response.data}")
    assert success_response.status_code == 200
    assert success_response.data['success'] is True
    
    # Test error response
    error_response = StandardResponse.error(
        message="测试错误",
        error_details="详细错误信息"
    )
    print(f"Error Response: {error_response.data}")
    assert error_response.status_code == 400
    assert error_response.data['success'] is False
    
    # Test validation error
    validation_response = StandardResponse.validation_error(
        errors={"field": ["This field is required"]}
    )
    print(f"Validation Response: {validation_response.data}")
    assert 'errors' in validation_response.data
    
    print("✅ StandardResponse tests passed!\n")


def test_api_error_handler():
    """Test ApiErrorHandler exception handling"""
    print("=== Testing ApiErrorHandler ===")
    
    # Test DRF validation error
    drf_error = DRFValidationError({"email": ["This field is required"]})
    response = ApiErrorHandler.handle_exception(drf_error, "用户注册")
    print(f"DRF Validation Error: {response.data}")
    assert response.status_code == 400
    assert 'errors' in response.data
    
    # Test ObjectDoesNotExist error
    not_found_error = ObjectDoesNotExist("User matching query does not exist")
    response = ApiErrorHandler.handle_exception(not_found_error, "用户查询")
    print(f"Not Found Error: {response.data}")
    assert response.status_code == 404
    
    # Test generic exception
    generic_error = Exception("Something went wrong")
    response = ApiErrorHandler.handle_exception(generic_error, "未知操作")
    print(f"Generic Error: {response.data}")
    assert response.status_code == 500
    
    print("✅ ApiErrorHandler tests passed!\n")


def test_decorator():
    """Test the api_error_handler decorator"""
    print("=== Testing @api_error_handler decorator ===")
    
    @api_error_handler("测试操作")
    def successful_operation():
        return {"result": "success"}
    
    @api_error_handler("失败操作")
    def failing_operation():
        raise DRFValidationError({"field": ["Invalid value"]})
    
    @api_error_handler("异常操作")
    def exception_operation():
        raise Exception("Unexpected error")
    
    # Test successful operation
    success_response = successful_operation()
    print(f"Successful operation: {success_response.data}")
    assert isinstance(success_response, Response)
    assert success_response.data['success'] is True
    
    # Test validation error
    validation_response = failing_operation()
    print(f"Validation error: {validation_response.data}")
    assert validation_response.status_code == 400
    assert validation_response.data['success'] is False
    
    # Test generic exception
    exception_response = exception_operation()
    print(f"Exception handling: {exception_response.data}")
    assert exception_response.status_code == 500
    assert exception_response.data['success'] is False
    
    print("✅ Decorator tests passed!\n")


def test_specialized_decorators():
    """Test specialized decorators"""
    print("=== Testing specialized decorators ===")
    
    @user_operation_handler("注册")
    def user_registration():
        return {"user_id": 123, "email": "test@example.com"}
    
    response = user_registration()
    print(f"User operation: {response.data}")
    assert response.data['success'] is True
    assert response.data['message'] == "操作成功"
    
    print("✅ Specialized decorator tests passed!\n")


def run_all_tests():
    """Run all tests"""
    print("🚀 Starting API Error Handling System Tests")
    print("=" * 50)
    
    try:
        test_standard_response()
        test_api_error_handler()
        test_decorator()
        test_specialized_decorators()
        
        print("🎉 All tests passed successfully!")
        print("✅ Standardized error handling system is working correctly")
        
    except AssertionError as e:
        print(f"❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error during testing: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    run_all_tests()