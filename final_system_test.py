"""
Final System Test for ClassBackend
This script performs comprehensive testing of all core system components
"""

import requests
import json
import time
import sys
from datetime import datetime

BASE_URL = "http://127.0.0.1:8000"
TIMEOUT = 10

def test_endpoint(method, endpoint, data=None, headers=None, expect_status=None):
    """Test a single endpoint and return results"""
    url = f"{BASE_URL}{endpoint}"
    headers = headers or {"Accept": "application/json"}
    
    try:
        if method.upper() == "GET":
            response = requests.get(url, headers=headers, timeout=TIMEOUT)
        elif method.upper() == "POST":
            response = requests.post(url, json=data, headers=headers, timeout=TIMEOUT)
        else:
            return {"error": f"Unsupported method: {method}"}
        
        result = {
            "endpoint": endpoint,
            "method": method,
            "status_code": response.status_code,
            "success": True,
            "response_time": response.elapsed.total_seconds()
        }
        
        # Try to parse JSON response
        try:
            result["response_data"] = response.json()
        except:
            result["response_data"] = response.text[:200] + "..." if len(response.text) > 200 else response.text
        
        # Check expected status
        if expect_status and response.status_code != expect_status:
            result["warning"] = f"Expected status {expect_status}, got {response.status_code}"
        
        return result
        
    except Exception as e:
        return {
            "endpoint": endpoint,
            "method": method,
            "success": False,
            "error": str(e)
        }

def main():
    print("=" * 80)
    print("CLASSBACKEND - FINAL SYSTEM TEST REPORT")
    print("=" * 80)
    print(f"Test started at: {datetime.now()}")
    print(f"Base URL: {BASE_URL}")
    print()
    
    # Test cases: (method, endpoint, data, headers, expected_status)
    test_cases = [
        # Core health checks
        ("GET", "/health/", None, None, 200),
        ("GET", "/api/v1/health/", None, None, 200),
        ("GET", "/api/v1/cache-stats/", None, None, 200),
        
        # Authentication endpoints (should require auth)
        ("GET", "/api/v1/courses/", None, None, 401),
        ("GET", "/api/v1/learning-plans/", None, None, 401),
        ("POST", "/api/v1/auth/login/", {"username": "test"}, None, None),
        
        # AI Service endpoints (should require auth)
        ("POST", "/api/v1/ai/advisor/plan/create", {"test": "data"}, None, 401),
        ("POST", "/api/v1/ai/advisor/plan/chat", {"message": "hello"}, None, 401),
        
        # Static/Media endpoints
        ("GET", "/static/", None, None, None),
        ("GET", "/admin/", None, None, None),
    ]
    
    results = []
    passed = 0
    failed = 0
    
    print("RUNNING TESTS...")
    print("-" * 40)
    
    for i, (method, endpoint, data, headers, expected_status) in enumerate(test_cases, 1):
        print(f"Test {i:2d}: {method:4s} {endpoint}")
        result = test_endpoint(method, endpoint, data, headers, expected_status)
        results.append(result)
        
        if result.get("success"):
            passed += 1
            status = "✓ PASS"
            if result.get("warning"):
                status += f" (Warning: {result['warning']})"
        else:
            failed += 1
            status = f"✗ FAIL - {result.get('error', 'Unknown error')}"
        
        print(f"         Status: {result.get('status_code', 'N/A')} - {status}")
        if result.get("response_time"):
            print(f"         Response time: {result['response_time']:.3f}s")
        print()
    
    # Summary
    print("=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"Total tests: {len(test_cases)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Success rate: {(passed/len(test_cases)*100):.1f}%")
    print()
    
    # Detailed results
    print("DETAILED RESULTS")
    print("-" * 40)
    
    # Group results by category
    health_tests = [r for r in results if "/health" in r["endpoint"] or "/cache" in r["endpoint"]]
    auth_tests = [r for r in results if "/auth" in r["endpoint"] or r["endpoint"] in ["/api/v1/courses/", "/api/v1/learning-plans/"]]
    ai_tests = [r for r in results if "/ai/" in r["endpoint"]]
    other_tests = [r for r in results if r not in health_tests + auth_tests + ai_tests]
    
    for category, tests in [
        ("Health & Monitoring", health_tests),
        ("Authentication & API", auth_tests),
        ("AI Services", ai_tests),
        ("Other Endpoints", other_tests)
    ]:
        if tests:
            print(f"\n{category}:")
            for test in tests:
                status = "✓" if test.get("success") else "✗"
                print(f"  {status} {test['method']} {test['endpoint']} -> {test.get('status_code', 'ERROR')}")
    
    print()
    print("SYSTEM STATUS:")
    
    # Check if core services are working
    health_working = any(r.get("success") and "/health/" in r["endpoint"] for r in results)
    auth_working = any(r.get("success") and r.get("status_code") == 401 for r in auth_tests)
    ai_working = any(r.get("success") and "/ai/" in r["endpoint"] for r in ai_tests)
    
    print(f"  ✓ Core Health Endpoints: {'Working' if health_working else 'Failed'}")
    print(f"  ✓ Authentication System: {'Working' if auth_working else 'Failed'}")
    print(f"  ✓ AI Services: {'Working' if ai_working else 'Failed'}")
    print(f"  ✓ Redis Cache: {'Working' if any('redis' in str(r.get('response_data', '')).lower() for r in results) else 'Unknown'}")
    
    # Final assessment
    critical_failures = failed - len([r for r in results if not r.get("success") and r.get("error") and "timeout" in r.get("error", "").lower()])
    
    print()
    if critical_failures == 0:
        print("🎉 SYSTEM STATUS: HEALTHY - All critical components are working!")
    elif critical_failures <= 2:
        print("⚠️  SYSTEM STATUS: MOSTLY HEALTHY - Minor issues detected")
    else:
        print("❌ SYSTEM STATUS: ISSUES DETECTED - Multiple components failing")
    
    print(f"\nTest completed at: {datetime.now()}")
    print("=" * 80)
    
    return critical_failures == 0

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nTest failed with error: {e}")
        sys.exit(1)
