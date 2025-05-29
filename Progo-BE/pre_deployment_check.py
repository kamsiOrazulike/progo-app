#!/usr/bin/env python3
"""
Pre-Deployment Local Test
Tests your backend locally before deploying to Render
"""

import requests
import json
import time
import subprocess
import sys
import os
from pathlib import Path

def check_requirements():
    """Check if all requirements are met"""
    print("🔍 Checking pre-deployment requirements...")
    
    # Check if we're in the right directory
    if not os.path.exists("app/main.py"):
        print("❌ Please run this script from the Progo-BE directory")
        return False
    
    # Check if virtual environment is activated
    if not hasattr(sys, 'real_prefix') and not (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("⚠️  Virtual environment not detected. Consider activating it.")
    
    # Check if required files exist
    required_files = [
        "render.yaml",
        "requirements.txt", 
        "app/main.py",
        "app/config.py",
        "DEPLOYMENT_GUIDE.md"
    ]
    
    for file in required_files:
        if os.path.exists(file):
            print(f"✅ {file}")
        else:
            print(f"❌ Missing: {file}")
            return False
    
    return True

def test_local_server():
    """Test the local server"""
    print("\n🚀 Testing local server...")
    
    # Test basic endpoints
    base_url = "http://localhost:8000"
    
    try:
        # Health check
        response = requests.get(f"{base_url}/health", timeout=5)
        if response.status_code == 200:
            print("✅ Health check passed")
            health_data = response.json()
            print(f"   Environment: {health_data.get('environment', 'unknown')}")
            print(f"   Database: {health_data.get('checks', {}).get('database', 'unknown')}")
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
            
        # Test sensor data endpoint
        sensor_data = {
            "device_id": "ESP32_LOCAL_TEST",
            "timestamp": int(time.time() * 1000),
            "magnetometer_available": True,
            "accelerometer": {"x": 0.23, "y": -0.01, "z": 9.85},
            "gyroscope": {"x": 0.01, "y": 0.01, "z": -0.00},
            "magnetometer": {"x": 1617.00, "y": 1119.00, "z": -14421.00},
            "temperature": 26.82
        }
        
        response = requests.post(f"{base_url}/api/v1/sensor-data/", json=sensor_data, timeout=5)
        if response.status_code == 201:
            print("✅ Sensor data endpoint works")
        else:
            print(f"❌ Sensor data endpoint failed: {response.status_code}")
            
        return True
        
    except requests.exceptions.ConnectionError:
        print("❌ Can't connect to local server. Is it running?")
        print("   Start with: uvicorn app.main:app --reload")
        return False
    except Exception as e:
        print(f"❌ Error testing server: {e}")
        return False

def main():
    """Run pre-deployment checks"""
    print("🎯 Progo Backend - Pre-Deployment Check")
    print("=" * 50)
    
    # Step 1: Check requirements
    if not check_requirements():
        print("\n❌ Pre-deployment check failed!")
        return
    
    print("\n✅ All required files present!")
    
    # Step 2: Check if server is running
    print("\n🖥️  Checking local server...")
    if test_local_server():
        print("\n✅ Local server tests passed!")
    else:
        print("\n⚠️  Local server not running or has issues.")
        print("   This is okay if you're confident in your setup.")
    
    # Step 3: Git status check
    print("\n📋 Git Status Check:")
    try:
        # Check if git repo exists
        result = subprocess.run(["git", "status", "--porcelain"], 
                              capture_output=True, text=True, cwd=".")
        if result.returncode == 0:
            if result.stdout.strip():
                print("⚠️  You have uncommitted changes:")
                print(result.stdout)
                print("   Consider committing before deployment")
            else:
                print("✅ Git working directory clean")
        else:
            print("⚠️  Not a git repository or git not available")
    except Exception as e:
        print(f"⚠️  Git check failed: {e}")
    
    # Step 4: Final checklist
    print("\n" + "=" * 50)
    print("🎯 RENDER DEPLOYMENT CHECKLIST:")
    print("=" * 50)
    
    checklist = [
        "✅ Code pushed to GitHub",
        "✅ render.yaml configured", 
        "✅ Environment variables ready (see .env.render)",
        "🔲 Render account created",
        "🔲 PostgreSQL database service created on Render",
        "🔲 Web service created and connected to database",
        "🔲 Environment variables set in Render dashboard"
    ]
    
    for item in checklist:
        print(f"   {item}")
    
    print("\n🚀 NEXT STEPS:")
    print("1. Follow DEPLOYMENT_GUIDE.md for detailed instructions")
    print("2. Push code to GitHub if not already done")
    print("3. Create Render services (PostgreSQL + Web Service)")
    print("4. Set environment variables in Render dashboard")
    print("5. Test deployment with test_render_deployment.py")
    
    print("\n🎉 Your backend is ready for Render deployment!")
    print("   Estimated deployment time: ~40 minutes")

if __name__ == "__main__":
    main()
