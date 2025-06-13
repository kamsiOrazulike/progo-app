#!/usr/bin/env python3
"""
Test script for the ESP32 command system implementation.
"""

import requests
import json
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:8000"
TEST_DEVICE_ID = "AA:BB:CC:DD:EE:FF"  # Test MAC address

def test_command_endpoint():
    """Test the new command endpoint"""
    print("🧪 Testing ESP32 Command System")
    print("=" * 50)
    
    # Test valid command
    print("\n1. Testing valid command...")
    command_data = {
        "command": "bicep",
        "timestamp": datetime.now().isoformat()
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/sensor-data/devices/{TEST_DEVICE_ID}/command",
            json=command_data,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"Response Status: {response.status_code}")
        print(f"Response Body: {response.json()}")
        
        if response.status_code == 200:
            print("✅ Valid command test PASSED")
        else:
            print("❌ Valid command test FAILED")
            
    except Exception as e:
        print(f"❌ Error testing valid command: {e}")
    
    # Test invalid device ID
    print("\n2. Testing invalid device ID...")
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/sensor-data/devices/invalid-device-id/command",
            json=command_data,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"Response Status: {response.status_code}")
        print(f"Response Body: {response.json()}")
        
        if response.status_code == 400:
            print("✅ Invalid device ID test PASSED")
        else:
            print("❌ Invalid device ID test FAILED")
            
    except Exception as e:
        print(f"❌ Error testing invalid device ID: {e}")
    
    # Test invalid command
    print("\n3. Testing invalid command...")
    invalid_command_data = {
        "command": "invalid_command",
        "timestamp": datetime.now().isoformat()
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/sensor-data/devices/{TEST_DEVICE_ID}/command",
            json=invalid_command_data,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"Response Status: {response.status_code}")
        print(f"Response Body: {response.json()}")
        
        if response.status_code == 400:
            print("✅ Invalid command test PASSED")
        else:
            print("❌ Invalid command test FAILED")
            
    except Exception as e:
        print(f"❌ Error testing invalid command: {e}")
    
    # Test all valid commands
    print("\n4. Testing all valid commands...")
    valid_commands = ["bicep", "squat", "rest", "train_complete", "test", "info", "mag_off", "mag_on"]
    
    for command in valid_commands:
        try:
            command_data = {"command": command}
            response = requests.post(
                f"{BASE_URL}/api/v1/sensor-data/devices/{TEST_DEVICE_ID}/command",
                json=command_data,
                headers={"Content-Type": "application/json"}
            )
            
            print(f"  Command '{command}': {response.status_code}")
            
        except Exception as e:
            print(f"  Command '{command}': ERROR - {e}")

def test_api_documentation():
    """Test if the new endpoint appears in API documentation"""
    print("\n5. Testing API documentation...")
    try:
        response = requests.get(f"{BASE_URL}/openapi.json")
        if response.status_code == 200:
            openapi_spec = response.json()
            command_endpoint = "/api/v1/sensor-data/devices/{device_id}/command"
            
            if "paths" in openapi_spec and command_endpoint in openapi_spec["paths"]:
                print("✅ Command endpoint found in API documentation")
            else:
                print("❌ Command endpoint NOT found in API documentation")
        else:
            print(f"❌ Could not fetch API documentation: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error testing API documentation: {e}")

def test_websocket_status():
    """Test WebSocket status endpoint"""
    print("\n6. Testing WebSocket status endpoint...")
    try:
        response = requests.get(
            f"{BASE_URL}/api/v1/sensor-data/devices/{TEST_DEVICE_ID}/websocket-status"
        )
        
        print(f"Response Status: {response.status_code}")
        print(f"Response Body: {response.json()}")
        
        if response.status_code == 200:
            print("✅ WebSocket status endpoint test PASSED")
        else:
            print("❌ WebSocket status endpoint test FAILED")
            
    except Exception as e:
        print(f"❌ Error testing WebSocket status: {e}")

if __name__ == "__main__":
    print("Starting ESP32 Command System Test")
    print("Make sure the backend server is running on localhost:8000")
    print()
    
    try:
        # Test if server is running
        health_response = requests.get(f"{BASE_URL}/health", timeout=5)
        if health_response.status_code == 200:
            print("✅ Backend server is running")
            test_command_endpoint()
            test_api_documentation()
            test_websocket_status()
        else:
            print("❌ Backend server is not responding properly")
            
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to backend server. Is it running on localhost:8000?")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
    
    print("\n" + "=" * 50)
    print("Test completed!")
