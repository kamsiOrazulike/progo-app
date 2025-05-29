#!/usr/bin/env python3
"""
Render Deployment Test Script
Tests the deployed Progo Backend API on Render
"""

import requests
import json
import time
from typing import Dict, Any

# Replace with your actual Render URL
BASE_URL = "https://your-app-name.onrender.com"
API_BASE = f"{BASE_URL}/api/v1"

def test_endpoint(method: str, url: str, data: Dict[Any, Any] = None, expected_status: int = 200) -> bool:
    """Test an API endpoint"""
    try:
        print(f"\n🧪 Testing {method} {url}")
        
        if method == "GET":
            response = requests.get(url, timeout=30)
        elif method == "POST":
            response = requests.post(url, json=data, timeout=30)
        
        print(f"   Status: {response.status_code}")
        
        if response.status_code == expected_status:
            print(f"   ✅ PASS")
            if response.headers.get('content-type', '').startswith('application/json'):
                result = response.json()
                print(f"   Response: {json.dumps(result, indent=2)}")
            return True
        else:
            print(f"   ❌ FAIL - Expected {expected_status}, got {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"   ❌ FAIL - Request error: {e}")
        return False

def main():
    """Run all deployment tests"""
    print("🚀 Testing Progo Backend Deployment on Render")
    print(f"🌐 Base URL: {BASE_URL}")
    print("=" * 60)
    
    # Update this with your actual Render URL before running
    if "your-app-name" in BASE_URL:
        print("❌ Please update BASE_URL with your actual Render URL first!")
        print("   Find it in your Render dashboard after deployment")
        return
    
    tests_passed = 0
    total_tests = 0
    
    # Test 1: Health Check
    total_tests += 1
    if test_endpoint("GET", f"{BASE_URL}/health"):
        tests_passed += 1
    
    # Test 2: Root endpoint
    total_tests += 1
    if test_endpoint("GET", BASE_URL):
        tests_passed += 1
    
    # Test 3: API Info
    total_tests += 1
    if test_endpoint("GET", f"{API_BASE}/info"):
        tests_passed += 1
    
    # Test 4: Submit Sensor Data
    total_tests += 1
    sensor_data = {
        "device_id": "ESP32_RENDER_TEST",
        "timestamp": int(time.time() * 1000),
        "magnetometer_available": True,
        "accelerometer": {"x": 0.23, "y": -0.01, "z": 9.85},
        "gyroscope": {"x": 0.01, "y": 0.01, "z": -0.00},
        "magnetometer": {"x": 1617.00, "y": 1119.00, "z": -14421.00},
        "temperature": 26.82
    }
    if test_endpoint("POST", f"{API_BASE}/sensor-data/", sensor_data, 201):
        tests_passed += 1
    
    # Test 5: Get Sensor Data
    total_tests += 1
    if test_endpoint("GET", f"{API_BASE}/sensor-data/?limit=5"):
        tests_passed += 1
    
    # Test 6: ML Status
    total_tests += 1
    if test_endpoint("GET", f"{API_BASE}/ml/status"):
        tests_passed += 1
    
    # Test 7: Create Session
    total_tests += 1
    session_data = {
        "device_id": "ESP32_RENDER_TEST",
        "exercise_type": "squat",
        "description": "Render deployment test session"
    }
    if test_endpoint("POST", f"{API_BASE}/sessions/", session_data, 201):
        tests_passed += 1
    
    # Test 8: Get Sessions
    total_tests += 1
    if test_endpoint("GET", f"{API_BASE}/sessions/?limit=5"):
        tests_passed += 1
    
    # Summary
    print("\n" + "=" * 60)
    print(f"🎯 Test Results: {tests_passed}/{total_tests} tests passed")
    
    if tests_passed == total_tests:
        print("🎉 All tests passed! Your Render deployment is working perfectly!")
        print("\n✅ Ready for ESP32 integration:")
        print(f"   Update your Arduino code endpoint to: {API_BASE}/sensor-data/")
    else:
        print(f"❌ {total_tests - tests_passed} tests failed. Check Render logs for issues.")
        print("\n🔧 Troubleshooting:")
        print("   1. Check Render service status in dashboard")
        print("   2. Verify DATABASE_URL environment variable is set")
        print("   3. Check build and deploy logs")
        print("   4. Ensure all environment variables are configured")

if __name__ == "__main__":
    main()
