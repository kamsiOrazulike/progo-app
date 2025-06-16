#!/usr/bin/env python3
"""
Complete Bicep Curl Training Workflow Test
Test the full pipeline from data collection to model training to live workouts
"""

import requests
import json
import time
from datetime import datetime

# Configuration
BACKEND_URL = "https://render-progo.onrender.com"  # Live deployment
DEVICE_ID = "CC:BA:97:01:3D:18"  # ESP32 MAC address from frontend

def test_backend_health():
    """Test if backend is accessible"""
    print("🔍 Testing Backend Health...")
    try:
        response = requests.get(f"{BACKEND_URL}/health", timeout=10)
        if response.status_code == 200:
            health = response.json()
            print(f"✅ Backend is healthy: {health['status']}")
            print(f"   Database: {health['checks'].get('database', 'unknown')}")
            print(f"   ML Model: {health['checks'].get('ml_model', 'unknown')}")
            return True
        else:
            print(f"❌ Backend health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Backend health check error: {e}")
        return False

def test_device_status():
    """Test device status endpoint"""
    print(f"\n🔍 Testing Device Status for {DEVICE_ID}...")
    try:
        response = requests.get(f"{BACKEND_URL}/api/v1/sensor-data/devices/{DEVICE_ID}/status", timeout=10)
        if response.status_code == 200:
            status = response.json()
            print(f"✅ Device Status Retrieved:")
            print(f"   Online: {status.get('is_online', False)}")
            print(f"   Recent Readings: {status.get('recent_readings_5min', 0)}")
            print(f"   Total Readings: {status.get('total_readings', 0)}")
            return status
        else:
            print(f"❌ Device status failed: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Device status error: {e}")
        return None

def test_websocket_status():
    """Test WebSocket status endpoint"""
    print(f"\n🔍 Testing WebSocket Status for {DEVICE_ID}...")
    try:
        response = requests.get(f"{BACKEND_URL}/api/v1/sensor-data/devices/{DEVICE_ID}/websocket-status", timeout=10)
        if response.status_code == 200:
            ws_status = response.json()
            print(f"✅ WebSocket Status Retrieved:")
            print(f"   Connected: {ws_status.get('is_connected', False)}")
            print(f"   Connection Count: {ws_status.get('connection_count', 0)}")
            print(f"   Queued Messages: {ws_status.get('queued_messages', 0)}")
            return ws_status
        else:
            print(f"❌ WebSocket status failed: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ WebSocket status error: {e}")
        return None

def test_esp32_command():
    """Test ESP32 command system"""
    print(f"\n🔍 Testing ESP32 Command System...")
    
    # Test with 'test' command first
    test_command = {
        "command": "test",
        "timestamp": datetime.now().isoformat()
    }
    
    try:
        response = requests.post(
            f"{BACKEND_URL}/api/v1/sensor-data/devices/{DEVICE_ID}/command",
            json=test_command,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        print(f"   Response Status: {response.status_code}")
        print(f"   Response Body: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Command System Working:")
            print(f"   Success: {result.get('success', False)}")
            print(f"   Message: {result.get('message', 'No message')}")
            return True
        else:
            print(f"❌ Command system failed: {response.status_code}")
            print(f"   Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Command system error: {e}")
        return False

def test_ml_training():
    """Test ML model training endpoint"""
    print(f"\n🔍 Testing ML Training System...")
    
    training_request = {
        "model_name": "bicep_curl_classifier",
        "model_type": "random_forest",
        "device_id": DEVICE_ID
    }
    
    try:
        response = requests.post(
            f"{BACKEND_URL}/api/v1/ml/train",
            json=training_request,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        print(f"   Response Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ ML Training System Available:")
            print(f"   Status: {result.get('status', 'unknown')}")
            return True
        else:
            print(f"⚠️ ML Training response: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ ML Training error: {e}")
        return False

def test_workout_system():
    """Test workout session management"""
    print(f"\n🔍 Testing Workout Session System...")
    
    try:
        # Test current workout status
        response = requests.get(f"{BACKEND_URL}/api/v1/workouts/current/{DEVICE_ID}", timeout=10)
        print(f"   Current Workout Status: {response.status_code}")
        
        if response.status_code == 200:
            workout = response.json()
            print(f"✅ Active Workout Found:")
            print(f"   Exercise: {workout.get('exercise_type', 'unknown')}")
            print(f"   Status: {workout.get('status', 'unknown')}")
        elif response.status_code == 404:
            print(f"✅ No Active Workout (Expected)")
        
        return True
        
    except Exception as e:
        print(f"❌ Workout system error: {e}")
        return False

def run_complete_test():
    """Run complete bicep curl training workflow test"""
    print("🏋️‍♂️ BICEP CURL TRAINING WORKFLOW TEST")
    print("=" * 60)
    
    results = {
        "backend_health": test_backend_health(),
        "device_status": test_device_status() is not None,
        "websocket_status": test_websocket_status() is not None,
        "esp32_commands": test_esp32_command(),
        "ml_training": test_ml_training(),
        "workout_system": test_workout_system()
    }
    
    print("\n" + "=" * 60)
    print("📊 TEST RESULTS SUMMARY:")
    
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"   {test_name.replace('_', ' ').title()}: {status}")
    
    total_tests = len(results)
    passed_tests = sum(results.values())
    
    print(f"\n🎯 Overall: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print("🎉 ALL SYSTEMS READY FOR BICEP CURL TRAINING!")
    else:
        print("⚠️ Some systems need attention before full workflow can work")
    
    return results

if __name__ == "__main__":
    run_complete_test()
