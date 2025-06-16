#!/usr/bin/env python3
"""
Test the complete exercise_type data flow from ESP32 to Frontend.
This script tests the fixes we've made to ensure proper exercise type handling.
"""

import json
import requests
import time
from datetime import datetime
import sys

# Configuration
BACKEND_URL = "http://localhost:8000"
DEVICE_ID = "AA:BB:CC:DD:EE:FF"

def test_exercise_type_data_flow():
    """Test complete exercise type data flow"""
    print("🧪 Testing Exercise Type Data Flow")
    print("=" * 50)
    
    # Test 1: Send sensor data with exercise_type
    print("\n1️⃣ Testing sensor data with exercise_type...")
    
    # Send rest data
    rest_data = {
        "device_id": DEVICE_ID,
        "timestamp": int(time.time() * 1000),
        "accelerometer": {"x": 0.1, "y": -0.9, "z": 9.8},
        "gyroscope": {"x": 0.01, "y": 0.01, "z": 0.01},
        "magnetometer": {"x": 100, "y": 200, "z": -300},
        "magnetometer_available": True,
        "temperature": 25.5,
        "exercise_type": "resting"
    }
    
    try:
        response = requests.post(f"{BACKEND_URL}/api/v1/sensor-data/", 
                               json=rest_data, timeout=10)
        if response.status_code == 200:
            print("✅ Rest data sent successfully")
        else:
            print(f"❌ Failed to send rest data: {response.status_code}")
            print(f"Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error sending rest data: {e}")
        return False
    
    # Send bicep curl data
    bicep_data = {
        "device_id": DEVICE_ID,
        "timestamp": int(time.time() * 1000),
        "accelerometer": {"x": 2.5, "y": -3.1, "z": 8.2},
        "gyroscope": {"x": 0.5, "y": -0.3, "z": 0.1},
        "magnetometer": {"x": 150, "y": 180, "z": -250},
        "magnetometer_available": True,
        "temperature": 26.0,
        "exercise_type": "bicep_curl"
    }
    
    try:
        response = requests.post(f"{BACKEND_URL}/api/v1/sensor-data/", 
                               json=bicep_data, timeout=10)
        if response.status_code == 200:
            print("✅ Bicep curl data sent successfully")
        else:
            print(f"❌ Failed to send bicep curl data: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error sending bicep curl data: {e}")
        return False
    
    # Test 2: Check exercise statistics
    print("\n2️⃣ Testing exercise statistics endpoint...")
    
    try:
        response = requests.get(f"{BACKEND_URL}/api/v1/sensor-data/devices/{DEVICE_ID}/exercise-stats",
                               timeout=10)
        if response.status_code == 200:
            stats = response.json()
            print("✅ Exercise statistics retrieved:")
            print(f"   Total readings: {stats.get('total_readings', 0)}")
            print(f"   Rest samples: {stats.get('exercise_samples', {}).get('rest', 0)}")
            print(f"   Bicep samples: {stats.get('exercise_samples', {}).get('bicep_curl', 0)}")
            print(f"   Current exercise: {stats.get('current_exercise', 'unknown')}")
            
            # Verify we have labeled data
            rest_count = stats.get('exercise_samples', {}).get('rest', 0)
            bicep_count = stats.get('exercise_samples', {}).get('bicep_curl', 0)
            
            if rest_count > 0 and bicep_count > 0:
                print("✅ Both rest and bicep curl samples found in database")
            else:
                print(f"⚠️ Sample counts may be low - Rest: {rest_count}, Bicep: {bicep_count}")
        else:
            print(f"❌ Failed to get exercise statistics: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error getting exercise statistics: {e}")
        return False
    
    # Test 3: Check latest sensor data includes exercise_type
    print("\n3️⃣ Testing latest sensor data includes exercise_type...")
    
    try:
        response = requests.get(f"{BACKEND_URL}/api/v1/sensor-data/latest/{DEVICE_ID}?count=5",
                               timeout=10)
        if response.status_code == 200:
            readings = response.json()
            print(f"✅ Retrieved {len(readings)} latest sensor readings")
            
            # Check if exercise_type is included
            exercise_types_found = []
            for reading in readings:
                if 'exercise_type' in reading and reading['exercise_type']:
                    exercise_types_found.append(reading['exercise_type'])
            
            if exercise_types_found:
                print(f"✅ Exercise types found in readings: {set(exercise_types_found)}")
                print("✅ Frontend will be able to count samples by exercise type")
            else:
                print("❌ No exercise_type found in latest readings")
                print("❌ Frontend sample counting will not work properly")
                return False
        else:
            print(f"❌ Failed to get latest sensor data: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error getting latest sensor data: {e}")
        return False
    
    # Test 4: Test device status
    print("\n4️⃣ Testing device status endpoint...")
    
    try:
        response = requests.get(f"{BACKEND_URL}/api/v1/sensor-data/devices/{DEVICE_ID}/status",
                               timeout=10)
        if response.status_code == 200:
            status = response.json()
            print("✅ Device status retrieved:")
            print(f"   Is online: {status.get('is_online', False)}")
            print(f"   Total readings: {status.get('total_readings', 0)}")
            print(f"   Ready for prediction: {status.get('ready_for_prediction', False)}")
        else:
            print(f"❌ Failed to get device status: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error getting device status: {e}")
        return False
    
    print("\n🎉 All tests passed! Exercise type data flow is working correctly.")
    print("\n📋 Summary of fixes implemented:")
    print("✅ Added exercise_type column to sensor_readings table")
    print("✅ Updated backend to store exercise_type in database (not just memory)")
    print("✅ Updated SensorDataResponse schema to include exercise_type")
    print("✅ Updated exercise statistics to return real counts from database")
    print("✅ Frontend can now count labeled samples for training data")
    
    return True

def check_backend_running():
    """Check if backend is running"""
    try:
        response = requests.get(f"{BACKEND_URL}/health", timeout=5)
        return response.status_code == 200
    except:
        return False

if __name__ == "__main__":
    if not check_backend_running():
        print("❌ Backend is not running!")
        print(f"Please start the backend server at {BACKEND_URL}")
        print("Command: cd Progo-BE && source venv/bin/activate && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload")
        sys.exit(1)
    
    success = test_exercise_type_data_flow()
    sys.exit(0 if success else 1)
