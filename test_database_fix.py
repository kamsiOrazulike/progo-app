#!/usr/bin/env python3
"""
Quick test to verify exercise_type is being stored in database correctly.
"""

import sqlite3
import json
import requests
import time
from datetime import datetime

BACKEND_URL = "http://localhost:8000"
DEVICE_ID = "TEST:EXERCISE:TYPE"
DB_PATH = "/Users/kams/Documents/workspace/progo-app/Progo-BE/progo_dev.db"

def check_database_schema():
    """Verify exercise_type column exists"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check if exercise_type column exists
    cursor.execute("PRAGMA table_info(sensor_readings)")
    columns = [row[1] for row in cursor.fetchall()]
    
    if 'exercise_type' in columns:
        print("✅ exercise_type column exists in database")
        return True
    else:
        print("❌ exercise_type column missing from database")
        return False

def check_current_data():
    """Check current exercise type distribution"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            COALESCE(exercise_type, 'NULL') as exercise_type,
            COUNT(*) as count 
        FROM sensor_readings 
        GROUP BY exercise_type 
        ORDER BY exercise_type
    """)
    
    results = cursor.fetchall()
    print("\n📊 Current exercise type distribution:")
    for exercise_type, count in results:
        print(f"   {exercise_type}: {count} readings")
    
    conn.close()
    return results

def test_backend_running():
    """Test if backend is accessible"""
    try:
        response = requests.get(f"{BACKEND_URL}/docs", timeout=5)
        if response.status_code == 200:
            print("✅ Backend is running and accessible")
            return True
        else:
            print(f"⚠️ Backend responded with status: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Backend is not accessible: {e}")
        print(f"Please start backend: cd Progo-BE && source venv/bin/activate && python -m uvicorn app.main:app --port 8000 --reload")
        return False

def send_test_data():
    """Send test data with exercise_type"""
    if not test_backend_running():
        return False
    
    # Test data with different exercise types
    test_readings = [
        {
            "device_id": DEVICE_ID,
            "timestamp": int(time.time() * 1000),
            "accelerometer": {"x": 0.1, "y": -0.9, "z": 9.8},
            "gyroscope": {"x": 0.01, "y": 0.01, "z": 0.01},
            "magnetometer": {"x": 100, "y": 200, "z": -300},
            "magnetometer_available": True,
            "temperature": 25.5,
            "exercise_type": "resting"
        },
        {
            "device_id": DEVICE_ID,
            "timestamp": int(time.time() * 1000) + 1000,
            "accelerometer": {"x": 2.5, "y": -3.1, "z": 8.2},
            "gyroscope": {"x": 0.5, "y": -0.3, "z": 0.1},
            "magnetometer": {"x": 150, "y": 180, "z": -250},
            "magnetometer_available": True,
            "temperature": 26.0,
            "exercise_type": "bicep_curl"
        },
        {
            "device_id": DEVICE_ID,
            "timestamp": int(time.time() * 1000) + 2000,
            "accelerometer": {"x": 1.5, "y": 2.1, "z": 7.8},
            "gyroscope": {"x": -0.3, "y": 0.4, "z": -0.2},
            "magnetometer": {"x": 120, "y": 160, "z": -280},
            "magnetometer_available": True,
            "temperature": 25.8,
            "exercise_type": "squat"
        }
    ]
    
    print("\n📤 Sending test sensor data...")
    for i, data in enumerate(test_readings):
        try:
            response = requests.post(f"{BACKEND_URL}/api/v1/sensor-data/", 
                                   json=data, timeout=10)
            if response.status_code == 200:
                print(f"✅ Sent {data['exercise_type']} data successfully")
            else:
                print(f"❌ Failed to send {data['exercise_type']} data: {response.status_code}")
                print(f"Response: {response.text}")
                return False
        except Exception as e:
            print(f"❌ Error sending {data['exercise_type']} data: {e}")
            return False
    
    return True

def verify_data_stored():
    """Verify the data was stored with exercise_type"""
    time.sleep(1)  # Give database time to update
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check for our test data
    cursor.execute("""
        SELECT exercise_type, COUNT(*) 
        FROM sensor_readings 
        WHERE device_id = ? 
        GROUP BY exercise_type 
        ORDER BY exercise_type
    """, (DEVICE_ID,))
    
    results = cursor.fetchall()
    
    if results:
        print("\n✅ Test data stored successfully with exercise_type:")
        for exercise_type, count in results:
            print(f"   {exercise_type}: {count} reading(s)")
        
        # Check if all expected types are present
        expected_types = {'resting', 'bicep_curl', 'squat'}
        stored_types = {row[0] for row in results}
        
        if expected_types.issubset(stored_types):
            print("✅ All exercise types stored correctly")
            conn.close()
            return True
        else:
            missing = expected_types - stored_types
            print(f"⚠️ Missing exercise types: {missing}")
    else:
        print("❌ No test data found in database")
    
    conn.close()
    return False

if __name__ == "__main__":
    print("🧪 Exercise Type Database Verification")
    print("=" * 40)
    
    # Check database schema
    if not check_database_schema():
        exit(1)
    
    # Check current data
    check_current_data()
    
    # Test sending new data
    if send_test_data():
        # Verify data was stored correctly
        if verify_data_stored():
            print("\n🎉 SUCCESS: Exercise type data flow is working correctly!")
            print("✅ exercise_type column exists in database")
            print("✅ Backend accepts exercise_type in API")
            print("✅ Data is stored with exercise_type labels")
            print("✅ Ready for ML training with labeled data")
        else:
            print("\n❌ FAILED: Data storage verification failed")
            exit(1)
    else:
        print("\n❌ FAILED: Could not send test data")
        exit(1)
