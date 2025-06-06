#!/usr/bin/env python3
"""
Test script for the enhanced Progo Backend API
Tests the new workout management and rep detection endpoints
"""
import requests
import json
import time
from datetime import datetime

BASE_URL = "http://localhost:8000"
API_V1 = f"{BASE_URL}/api/v1"

def test_health_check():
    """Test basic health check"""
    print("🔍 Testing health check...")
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            print("✅ Health check passed")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False

def test_workout_endpoints():
    """Test workout management endpoints"""
    print("\n🏋️‍♂️ Testing workout endpoints...")
    
    device_id = "test-device-123"
    
    # Start a workout
    workout_data = {
        "device_id": device_id,
        "exercise_type": "squat",
        "target_reps": 10,
        "target_sets": 3
    }
    
    try:
        print("📋 Starting workout...")
        response = requests.post(f"{API_V1}/workouts/start", json=workout_data)
        if response.status_code == 200:
            workout = response.json()
            print(f"✅ Workout started: ID {workout['id']}")
            
            # Get current workout
            print("📊 Getting current workout...")
            response = requests.get(f"{API_V1}/workouts/current/{device_id}")
            if response.status_code == 200:
                current = response.json()
                print(f"✅ Current workout: {current['exercise_type']} - {current['status']}")
                
                # Complete the workout
                print("🏁 Completing workout...")
                response = requests.post(f"{API_V1}/workouts/{workout['id']}/complete")
                if response.status_code == 200:
                    print("✅ Workout completed successfully")
                    return True
                else:
                    print(f"❌ Failed to complete workout: {response.status_code}")
            else:
                print(f"❌ Failed to get current workout: {response.status_code}")
        else:
            print(f"❌ Failed to start workout: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"❌ Workout test error: {e}")
    
    return False

def test_rep_endpoints():
    """Test rep detection endpoints"""
    print("\n🔄 Testing rep detection endpoints...")
    
    device_id = "test-device-123"
    
    try:
        # Get rep patterns
        print("📈 Getting rep patterns...")
        response = requests.get(f"{API_V1}/reps/{device_id}/patterns")
        if response.status_code == 200:
            patterns = response.json()
            print(f"✅ Found {len(patterns)} rep patterns")
        else:
            print(f"⚠️ No patterns found yet: {response.status_code}")
        
        # Test rep validation
        print("🔍 Testing rep validation...")
        validation_data = {
            "device_id": device_id,
            "expected_exercise": "squat",
            "rep_data": [
                {
                    "device_id": device_id,
                    "timestamp": int(time.time() * 1000),
                    "accelerometer": {"x": 0.1, "y": 0.2, "z": 9.8},
                    "gyroscope": {"x": 0.01, "y": 0.02, "z": 0.03},
                    "magnetometer_available": False
                }
            ]
        }
        
        response = requests.post(f"{API_V1}/reps/validate", json=validation_data)
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Rep validation: valid={result['is_valid_rep']}, confidence={result['confidence']:.2f}")
            return True
        else:
            print(f"❌ Rep validation failed: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"❌ Rep test error: {e}")
    
    return False

def test_sensor_data_integration():
    """Test sensor data with rep detection integration"""
    print("\n📡 Testing sensor data integration...")
    
    device_id = "test-device-123"
    
    try:
        # Send sensor data
        sensor_data = {
            "device_id": device_id,
            "timestamp": int(time.time() * 1000),
            "accelerometer": {"x": 0.1, "y": 0.2, "z": 9.8},
            "gyroscope": {"x": 0.01, "y": 0.02, "z": 0.03},
            "magnetometer_available": False
        }
        
        response = requests.post(f"{API_V1}/sensor-data/", json=sensor_data)
        if response.status_code == 200:
            result = response.json()
            print("✅ Sensor data sent successfully")
            return True
        else:
            print(f"❌ Sensor data failed: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"❌ Sensor data test error: {e}")
    
    return False

def main():
    """Run all tests"""
    print("🚀 Starting Progo Backend Enhanced API Tests")
    print("=" * 50)
    
    tests = [
        test_health_check,
        test_workout_endpoints,
        test_rep_endpoints,
        test_sensor_data_integration
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        time.sleep(1)  # Brief pause between tests
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Enhanced backend is working correctly.")
    else:
        print("⚠️ Some tests failed. Check the output above for details.")
    
    return passed == total

if __name__ == "__main__":
    main()
