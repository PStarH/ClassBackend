#!/usr/bin/env python3
"""
Backend API Testing Script
"""
import requests
import json
import time
import subprocess
import signal
import os
from concurrent.futures import ThreadPoolExecutor
import threading

BASE_URL = 'http://127.0.0.1:8000'

def test_endpoint(endpoint, method='GET', data=None, auth=None):
    """Test a single endpoint"""
    url = f"{BASE_URL}{endpoint}"
    try:
        headers = {'Content-Type': 'application/json'}
        if auth:
            headers['Authorization'] = f'Bearer {auth}'
            
        if method == 'GET':
            response = requests.get(url, headers=headers, timeout=5)
        elif method == 'POST':
            response = requests.post(url, json=data, headers=headers, timeout=5)
        elif method == 'PUT':
            response = requests.put(url, json=data, headers=headers, timeout=5)
            
        return {
            'endpoint': endpoint,
            'status_code': response.status_code,
            'success': response.status_code < 500,
            'response_size': len(response.content),
            'content_type': response.headers.get('content-type', 'unknown')
        }
    except requests.exceptions.ConnectionError:
        return {
            'endpoint': endpoint,
            'status_code': 'CONNECTION_ERROR',
            'success': False,
            'error': 'Could not connect to server'
        }
    except Exception as e:
        return {
            'endpoint': endpoint, 
            'status_code': 'ERROR',
            'success': False,
            'error': str(e)
        }

def main():
    """Test backend endpoints"""
    print("🔍 Testing Backend API Endpoints...")
    
    # Test endpoints
    endpoints_to_test = [
        '/health/',
        '/api/v1/health/',
        '/api/v1/auth/register/',
        '/api/v1/auth/login/',
        '/api/v1/courses/',
        '/api/v1/learning-plans/',
        '/api/v1/ai/',
        '/admin/',
    ]
    
    results = []
    
    print(f"Testing {len(endpoints_to_test)} endpoints...")
    
    for endpoint in endpoints_to_test:
        print(f"  Testing {endpoint}...", end=" ")
        result = test_endpoint(endpoint)
        results.append(result)
        
        if result['success']:
            print(f"✅ {result['status_code']}")
        else:
            print(f"❌ {result.get('status_code', 'ERROR')}")
    
    print("\n📊 Test Results Summary:")
    print("=" * 50)
    
    success_count = sum(1 for r in results if r['success'])
    total_count = len(results)
    
    for result in results:
        status = "✅" if result['success'] else "❌"
        print(f"{status} {result['endpoint']} - {result.get('status_code', 'ERROR')}")
    
    print("=" * 50)
    print(f"Success Rate: {success_count}/{total_count} ({success_count/total_count*100:.1f}%)")
    
    if success_count == total_count:
        print("🎉 All endpoints are accessible!")
        return True
    else:
        print("⚠️ Some endpoints have issues.")
        return False

if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)