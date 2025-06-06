#!/usr/bin/env python3
"""
Comprehensive test script for the enhanced fitness tracking API.
Tests all new endpoints and WebSocket functionality.
"""

import asyncio
import json
import time
import websockets
import requests
from datetime import datetime
from typing import Dict, List


BASE_URL = "http://localhost:8000"
WS_URL = "ws://localhost:8000"


def test_api_health():
    """Test that the API is running and accessible."""
    try:
        response = requests.get(f"{BASE_URL}/")
        print(f"✅ API is accessible - Status: {response.status_code}")
        return True
    except Exception as e:
        print(f"❌ API health check failed: {e}")
        return False


def test_workout_endpoints():
    """Test workout management endpoints."""
    print("\n🏋️ Testing Workout Endpoints")
    
    # Test create workout session
    workout_data = {
        "device_id": "test_device_001",
        "exercise_type": "squat",
        "target_reps": 20,
        "target_sets": 3
    }
    
    try:
        response = requests.post(f"{BASE_URL}/workouts/", json=workout_data)
        print(f"Create workout - Status: {response.status_code}")
        
        if response.status_code == 200:
            workout = response.json()
            workout_id = workout["id"]
            print(f"✅ Created workout session: {workout_id}")
            
            # Test get workout
            response = requests.get(f"{BASE_URL}/workouts/{workout_id}")
            if response.status_code == 200:
                print("✅ Retrieved workout session")
            
            # Test get active workouts
            response = requests.get(f"{BASE_URL}/workouts/?device_id=test_device_001")
            if response.status_code == 200:
                workouts = response.json()
                print(f"✅ Found {len(workouts)} active workouts")
            
            return workout_id
        else:
            print(f"❌ Failed to create workout: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Workout endpoint test failed: {e}")
        return None


def test_rep_detection_endpoints():
    """Test rep detection and pattern endpoints."""
    print("\n🎯 Testing Rep Detection Endpoints")
    
    try:
        # Test rep detection calibration
        calibration_data = {
            "device_id": "test_device_001",
            "exercise_type": "squat",
            "sensor_data": [
                {"timestamp": time.time(), "accel_x": 0.1, "accel_y": 0.2, "accel_z": 9.8},
                {"timestamp": time.time() + 0.1, "accel_x": 0.2, "accel_y": 0.3, "accel_z": 9.7}
            ]
        }
        
        response = requests.post(f"{BASE_URL}/reps/calibrate", json=calibration_data)
        print(f"Calibration - Status: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ Rep detection calibration successful")
        
        # Test real-time rep detection
        detection_data = {
            "device_id": "test_device_001",
            "exercise_type": "squat",
            "sensor_data": [
                {"timestamp": time.time(), "accel_x": 0.1, "accel_y": 0.2, "accel_z": 9.8},
                {"timestamp": time.time() + 0.1, "accel_x": 0.3, "accel_y": 0.4, "accel_z": 9.6},
                {"timestamp": time.time() + 0.2, "accel_x": 0.1, "accel_y": 0.2, "accel_z": 9.8}
            ]
        }
        
        response = requests.post(f"{BASE_URL}/reps/detect", json=detection_data)
        print(f"Rep detection - Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Rep detection result: {result}")
        
        # Test rep patterns
        response = requests.get(f"{BASE_URL}/reps/patterns/test_device_001")
        print(f"Get patterns - Status: {response.status_code}")
        
        if response.status_code == 200:
            patterns = response.json()
            print(f"✅ Found {len(patterns)} rep patterns")
        
        return True
        
    except Exception as e:
        print(f"❌ Rep detection endpoint test failed: {e}")
        return False


async def test_websocket_connection():
    """Test WebSocket connection and messaging."""
    print("\n🔌 Testing WebSocket Connection")
    
    try:
        uri = f"{WS_URL}/ws/test_device_001"
        
        async with websockets.connect(uri) as websocket:
            print("✅ WebSocket connection established")
            
            # Send a test message
            test_message = {
                "type": "test",
                "data": "Hello WebSocket!",
                "timestamp": datetime.now().isoformat()
            }
            
            await websocket.send(json.dumps(test_message))
            print("✅ Test message sent")
            
            # Wait for potential response (with timeout)
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                print(f"✅ Received response: {response}")
            except asyncio.TimeoutError:
                print("ℹ️ No immediate response (expected for test message)")
            
            return True
            
    except Exception as e:
        print(f"❌ WebSocket test failed: {e}")
        return False


def test_sensor_data_integration():
    """Test sensor data processing with rep detection."""
    print("\n📊 Testing Sensor Data Integration")
    
    try:
        # First create a workout session
        workout_data = {
            "device_id": "test_device_002",
            "exercise_type": "squat",
            "target_reps": 10,
            "target_sets": 2
        }
        
        workout_response = requests.post(f"{BASE_URL}/workouts/", json=workout_data)
        if workout_response.status_code != 200:
            print("❌ Failed to create workout for sensor data test")
            return False
        
        workout_id = workout_response.json()["id"]
        print(f"✅ Created workout {workout_id} for sensor data test")
        
        # Send sensor data
        sensor_data = {
            "device_id": "test_device_002",
            "timestamp": time.time(),
            "accel_x": 0.1,
            "accel_y": 0.2,
            "accel_z": 9.8,
            "gyro_x": 0.01,
            "gyro_y": 0.02,
            "gyro_z": 0.03
        }
        
        response = requests.post(f"{BASE_URL}/sensor-data/", json=sensor_data)
        print(f"Sensor data processing - Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Sensor data processed: {result}")
            return True
        else:
            print(f"❌ Sensor data processing failed: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Sensor data integration test failed: {e}")
        return False


def test_training_data_collection():
    """Test training data collection endpoints."""
    print("\n🎓 Testing Training Data Collection")
    
    try:
        training_data = {
            "device_id": "test_device_003",
            "exercise_type": "squat",
            "rep_data": [
                {
                    "rep_number": 1,
                    "duration": 2.5,
                    "quality_score": 0.85,
                    "sensor_sequence": [
                        {"timestamp": time.time(), "accel_x": 0.1, "accel_y": 0.2, "accel_z": 9.8},
                        {"timestamp": time.time() + 1, "accel_x": 0.3, "accel_y": 0.4, "accel_z": 9.6}
                    ]
                }
            ]
        }
        
        response = requests.post(f"{BASE_URL}/ml/training-data", json=training_data)
        print(f"Training data collection - Status: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ Training data collected successfully")
            return True
        else:
            print(f"❌ Training data collection failed: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Training data collection test failed: {e}")
        return False


async def run_all_tests():
    """Run all tests in sequence."""
    print("🚀 Starting Comprehensive API Testing")
    print("=" * 50)
    
    results = {}
    
    # Test API health
    results["api_health"] = test_api_health()
    
    # Test workout endpoints
    workout_id = test_workout_endpoints()
    results["workout_endpoints"] = workout_id is not None
    
    # Test rep detection endpoints
    results["rep_detection"] = test_rep_detection_endpoints()
    
    # Test WebSocket connection
    results["websocket"] = await test_websocket_connection()
    
    # Test sensor data integration
    results["sensor_integration"] = test_sensor_data_integration()
    
    # Test training data collection
    results["training_data"] = test_training_data_collection()
    
    # Print summary
    print("\n" + "=" * 50)
    print("📋 Test Results Summary")
    print("=" * 50)
    
    for test_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name.replace('_', ' ').title()}: {status}")
    
    total_tests = len(results)
    passed_tests = sum(results.values())
    
    print(f"\nOverall: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print("🎉 All tests passed! The enhanced fitness tracking API is working correctly.")
    else:
        print("⚠️ Some tests failed. Check the output above for details.")
    
    return results


if __name__ == "__main__":
    asyncio.run(run_all_tests())
