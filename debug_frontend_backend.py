#!/usr/bin/env python3
"""
Frontend-Backend Debug Helper
This script helps debug the connection between frontend and backend for exercise type handling.
"""

import requests
import json
import time
from datetime import datetime
import sys

# Configuration
BACKEND_URL_LOCAL = "http://localhost:8000"
BACKEND_URL_RENDER = "https://render-progo.onrender.com"
DEVICE_ID = "CC:BA:97:01:3D:18"

def test_backend(base_url):
    """Test backend health and endpoints"""
    print(f"\n🔍 Testing backend at: {base_url}")
    print("=" * 50)
    
    # Test 1: Health check
    try:
        response = requests.get(f"{base_url}/health", timeout=10)
        if response.status_code == 200:
            print("✅ Health check: OK")
        else:
            print(f"⚠️ Health check: {response.status_code}")
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False
    
    # Test 2: Device status
    try:
        response = requests.get(f"{base_url}/api/v1/sensor-data/devices/{DEVICE_ID}/status", timeout=10)
        if response.status_code == 200:
            status = response.json()
            print(f"✅ Device status: {status.get('total_readings', 0)} readings")
        else:
            print(f"⚠️ Device status: {response.status_code}")
    except Exception as e:
        print(f"❌ Device status failed: {e}")
    
    # Test 3: Exercise statistics (our new endpoint)
    try:
        response = requests.get(f"{base_url}/api/v1/sensor-data/devices/{DEVICE_ID}/exercise-stats", timeout=10)
        if response.status_code == 200:
            stats = response.json()
            print(f"✅ Exercise stats: Rest={stats.get('exercise_samples', {}).get('rest', 0)}, Bicep={stats.get('exercise_samples', {}).get('bicep_curl', 0)}")
            return True
        else:
            print(f"⚠️ Exercise stats: {response.status_code}")
            if response.status_code == 404:
                print("   This means our new exercise statistics endpoint is not deployed")
    except Exception as e:
        print(f"❌ Exercise stats failed: {e}")
    
    # Test 4: Latest sensor data (check if exercise_type is included)
    try:
        response = requests.get(f"{base_url}/api/v1/sensor-data/latest/{DEVICE_ID}?count=5", timeout=10)
        if response.status_code == 200:
            readings = response.json()
            exercise_types = [r.get('exercise_type') for r in readings if r.get('exercise_type')]
            if exercise_types:
                print(f"✅ Latest data includes exercise types: {set(exercise_types)}")
            else:
                print("⚠️ Latest data: No exercise_type found in readings")
        else:
            print(f"⚠️ Latest data: {response.status_code}")
    except Exception as e:
        print(f"❌ Latest data failed: {e}")
    
    return False

def check_frontend_config():
    """Check frontend configuration"""
    print("\n🎛️ Frontend Configuration Check")
    print("=" * 40)
    
    frontend_file = "/Users/kams/Documents/workspace/progo-app/progo-fe/components/ESP32Controller.tsx"
    
    try:
        with open(frontend_file, 'r') as f:
            content = f.read()
        
        # Check API base URL
        if "https://render-progo.onrender.com" in content:
            print("⚠️ Frontend is configured for PRODUCTION (Render)")
            print("   This means you're testing against the live server")
            print("   Your local backend changes won't be visible")
        elif "localhost:8000" in content:
            print("✅ Frontend is configured for LOCAL development")
        else:
            print("❌ Could not determine frontend API configuration")
        
        # Check device ID
        if "CC:BA:97:01:3D:18" in content:
            print(f"✅ Device ID configured: CC:BA:97:01:3D:18")
        else:
            print("⚠️ Device ID not found or different")
        
        # Check if exercise type handling is present
        if "exercise_type" in content:
            print("✅ Exercise type handling code found")
        else:
            print("❌ Exercise type handling code missing")
            
    except Exception as e:
        print(f"❌ Could not read frontend file: {e}")

def send_test_data(base_url):
    """Send test data with exercise_type to verify the flow"""
    print(f"\n📤 Sending test data to: {base_url}")
    print("=" * 40)
    
    test_data = {
        "device_id": DEVICE_ID,
        "timestamp": int(time.time() * 1000),
        "accelerometer": {"x": 0.1, "y": -0.9, "z": 9.8},
        "gyroscope": {"x": 0.01, "y": 0.01, "z": 0.01},
        "magnetometer": {"x": 100, "y": 200, "z": -300},
        "magnetometer_available": True,
        "temperature": 25.5,
        "exercise_type": "test_debug"
    }
    
    try:
        response = requests.post(f"{base_url}/api/v1/sensor-data/", 
                               json=test_data, timeout=10)
        if response.status_code == 200:
            print("✅ Test data sent successfully")
            
            # Wait a moment then check if it appears in exercise stats
            time.sleep(2)
            stats_response = requests.get(f"{base_url}/api/v1/sensor-data/devices/{DEVICE_ID}/exercise-stats", timeout=10)
            if stats_response.status_code == 200:
                stats = stats_response.json()
                print(f"✅ Exercise stats updated: {stats.get('exercise_samples', {})}")
            else:
                print("⚠️ Could not verify exercise stats update")
                
        else:
            print(f"❌ Failed to send test data: {response.status_code}")
            print(f"Response: {response.text}")
    except Exception as e:
        print(f"❌ Error sending test data: {e}")

def main():
    print("🔧 Frontend-Backend Debug Helper")
    print("This script will help identify issues with your setup")
    
    # Check frontend configuration
    check_frontend_config()
    
    # Test local backend (if running)
    print("\n" + "="*60)
    local_working = test_backend(BACKEND_URL_LOCAL)
    
    # Test production backend
    print("\n" + "="*60)
    production_working = test_backend(BACKEND_URL_RENDER)
    
    # Recommendations
    print("\n🎯 RECOMMENDATIONS")
    print("=" * 20)
    
    if local_working:
        print("✅ Your local backend is working with exercise type support")
        print("💡 To test your changes:")
        print("   1. Update frontend API_BASE_URL to 'http://localhost:8000/api/v1'")
        print("   2. Start frontend: npm run dev")
        print("   3. Test exercise type collection")
        
        # Send test data to local backend
        send_test_data(BACKEND_URL_LOCAL)
        
    elif production_working:
        print("⚠️ Only production backend is available")
        print("💡 Your local changes are not deployed yet")
        print("   - Production may not have exercise_type support")
        print("   - You need to deploy your changes to see them work")
        
    else:
        print("❌ Neither backend is responding properly")
        print("💡 To fix this:")
        print("   1. Start local backend: cd Progo-BE && source venv/bin/activate && python -m uvicorn app.main:app --port 8000 --reload")
        print("   2. Check backend logs for errors")
        print("   3. Verify database has exercise_type column")

if __name__ == "__main__":
    main()
