#!/usr/bin/env python3
"""
Simple test script to verify API endpoints are working.
"""

import requests
import json
from datetime import datetime
import random
import time

BASE_URL = "http://localhost:8000"

def test_health_check():
    """Test the health check endpoint."""
    print("🔍 Testing health check...")
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    return response.status_code == 200

def test_sensor_data_post():
    """Test posting sensor data."""
    print("\n🔍 Testing sensor data POST...")
    
    # Create sample sensor data with correct schema
    sensor_data = {
        "device_id": "ESP32_TEST_001",
        "timestamp": int(datetime.now().timestamp() * 1000),  # Unix timestamp in milliseconds
        "magnetometer_available": True,
        "accelerometer": {
            "x": round(random.uniform(-10, 10), 3),
            "y": round(random.uniform(-10, 10), 3),
            "z": round(random.uniform(-10, 10), 3)
        },
        "gyroscope": {
            "x": round(random.uniform(-500, 500), 3),
            "y": round(random.uniform(-500, 500), 3),
            "z": round(random.uniform(-500, 500), 3)
        },
        "magnetometer": {
            "x": round(random.uniform(-100, 100), 3),
            "y": round(random.uniform(-100, 100), 3),
            "z": round(random.uniform(-100, 100), 3)
        },
        "temperature": round(random.uniform(20, 30), 2)
    }
    
    response = requests.post(f"{BASE_URL}/api/v1/sensor-data/", json=sensor_data)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    return response.status_code == 200

def test_get_sensor_data():
    """Test getting sensor data."""
    print("\n🔍 Testing sensor data GET...")
    
    response = requests.get(f"{BASE_URL}/api/v1/sensor-data/?limit=5")
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Response: Found {len(data.get('items', []))} sensor readings")
    return response.status_code == 200

def test_create_session():
    """Test creating an exercise session."""
    print("\n🔍 Testing session creation...")
    
    session_data = {
        "device_id": "ESP32_TEST_001",
        "exercise_type": "squat",
        "session_name": "Test Squat Session",
        "notes": "API test session"
    }
    
    response = requests.post(f"{BASE_URL}/api/v1/sessions/", json=session_data)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    
    if response.status_code == 200:
        return response.json().get("id")
    return None

def test_get_sessions():
    """Test getting sessions."""
    print("\n🔍 Testing sessions GET...")
    
    response = requests.get(f"{BASE_URL}/api/v1/sessions/?limit=5")
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Response: Found {len(data)} sessions")
    return response.status_code == 200

def test_ml_status():
    """Test ML system status."""
    print("\n🔍 Testing ML status...")
    
    response = requests.get(f"{BASE_URL}/api/v1/ml/status")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    return response.status_code == 200

def test_get_models():
    """Test getting ML models."""
    print("\n🔍 Testing ML models GET...")
    
    response = requests.get(f"{BASE_URL}/api/v1/ml/models")
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Response: Found {len(data)} models")
    return response.status_code == 200

def test_ml_training():
    """Test ML model training."""
    print("\n🔍 Testing ML model training...")
    
    training_data = {
        "model_name": "test_classifier",
        "model_type": "random_forest",
        "device_id": "ESP32_TEST_001"
    }
    
    response = requests.post(f"{BASE_URL}/api/v1/ml/train", json=training_data)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    return response.status_code == 200

def test_ml_prediction():
    """Test ML prediction."""
    print("\n🔍 Testing ML prediction...")
    
    # Create prediction request with sensor data list
    prediction_data = {
        "sensor_data": [
            {
                "device_id": "ESP32_TEST_001",
                "timestamp": int(datetime.now().timestamp() * 1000),
                "magnetometer_available": True,
                "accelerometer": {
                    "x": 1.2,
                    "y": -0.5,
                    "z": 9.8
                },
                "gyroscope": {
                    "x": 10.5,
                    "y": -20.3,
                    "z": 5.1
                },
                "magnetometer": {
                    "x": 25.0,
                    "y": 15.5,
                    "z": -40.2
                }
            }
        ]
    }
    
    response = requests.post(f"{BASE_URL}/api/v1/ml/predict", json=prediction_data)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    return response.status_code in [200, 400, 503]  # 400/503 are OK if no model is trained yet

def main():
    """Run all tests."""
    print("🚀 Starting Progo-BE API Tests")
    print("=" * 50)
    
    tests = [
        ("Health Check", test_health_check),
        ("Sensor Data POST", test_sensor_data_post),
        ("Sensor Data GET", test_get_sensor_data),
        ("Session Creation", test_create_session),
        ("Sessions GET", test_get_sessions),
        ("ML Status", test_ml_status),
        ("ML Models GET", test_get_models),
        ("ML Training", test_ml_training),
        ("ML Prediction", test_ml_prediction),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            success = test_func()
            results.append((test_name, "✅ PASS" if success else "❌ FAIL"))
        except Exception as e:
            print(f"❌ ERROR: {e}")
            results.append((test_name, f"❌ ERROR: {str(e)}"))
        
        time.sleep(0.5)  # Small delay between tests
    
    print("\n" + "=" * 50)
    print("📊 Test Results Summary:")
    print("=" * 50)
    
    for test_name, result in results:
        print(f"{test_name:<20} {result}")
    
    passed = sum(1 for _, result in results if "✅" in result)
    total = len(results)
    
    print(f"\n🎯 Total: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! API is working correctly.")
    else:
        print("⚠️  Some tests failed. Check the output above for details.")

if __name__ == "__main__":
    main()
