# 🚀 Render Deployment Guide for Progo Backend

This guide will help you deploy your FastAPI + ML backend to Render in production.

## 📋 Prerequisites

1. ✅ **GitHub Account** - Your code needs to be in a GitHub repository
2. ✅ **Render Account** - Sign up at [render.com](https://render.com) (free)
3. ✅ **Code Ready** - All files updated and committed to GitHub

## 🗂️ Files Created for Deployment

```
Progo-BE/
├── render.yaml              # ✅ Render service configuration
├── .env.render             # ✅ Environment variables template
├── app/config.py           # ✅ Updated with Render auto-detection
├── app/main.py             # ✅ Enhanced health check & CORS
└── requirements.txt        # ✅ Already includes PostgreSQL drivers
```

## 🚀 Step-by-Step Deployment

### Step 1: Push Code to GitHub

```bash
# Navigate to your project
cd /Users/kams/Documents/workspace/progo-app

# Initialize git (if not already done)
git init
git add .
git commit -m "Initial commit - Render deployment ready"

# Push to GitHub
git remote add origin https://github.com/YOUR_USERNAME/progo-app.git
git branch -M main
git push -u origin main
```

### Step 2: Create Render Services

1. **Login to Render**: Go to [render.com](https://render.com) and sign in

2. **Create PostgreSQL Database**:
   - Click "New +" → "PostgreSQL"
   - Name: `progo-database`
   - Database: `progo_db`
   - User: `progo_user`
   - Region: `US East (Ohio)` (or closest to you)
   - Plan: `Free`
   - Click "Create Database"
   - **Save the DATABASE_URL** - you'll need it

3. **Create Web Service**:
   - Click "New +" → "Web Service"
   - Connect your GitHub repository
   - Select the `progo-app` repository
   - Configure the service:

```yaml
Name: progo-backend
Branch: main
Root Directory: Progo-BE
Runtime: Python 3
Build Command: pip install -r requirements.txt
Start Command: uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

### Step 3: Configure Environment Variables

In your Render web service dashboard, add these environment variables:

```bash
# Required
SECRET_KEY=your-super-secret-key-change-this-in-production
ENVIRONMENT=production
DEBUG=false

# Database (Render provides this automatically when you connect the database)
DATABASE_URL=postgresql://[WILL_BE_AUTO_FILLED]

# Optional (with good defaults)
LOG_LEVEL=INFO
API_V1_STR=/api/v1
PROJECT_NAME=Progo ML Backend
FEATURE_WINDOW_SIZE=200
WINDOW_OVERLAP=0.5
MIN_TRAINING_SAMPLES=100
```

### Step 4: Connect Database to Web Service

1. In your web service dashboard
2. Go to "Environment" tab
3. Click "Add from Service"
4. Select your PostgreSQL database (`progo-database`)
5. This automatically adds `DATABASE_URL`

### Step 5: Deploy

1. Click "Create Web Service"
2. Render will automatically:
   - Clone your repo
   - Install dependencies
   - Start your FastAPI server
   - Provide you with a live URL!

## 🎯 Expected Results

### ✅ Live URLs
- **Backend**: `https://progo-backend.onrender.com`
- **Health Check**: `https://progo-backend.onrender.com/health`
- **API Docs**: `https://progo-backend.onrender.com/docs`
- **Sensor Data**: `https://progo-backend.onrender.com/api/v1/sensor-data/`

### ✅ Database
- PostgreSQL database with auto-created tables
- Connection tested via health check

### ✅ ML Pipeline
- All ML endpoints live and functional
- Model training/prediction ready

## 🧪 Testing Your Deployment

### 1. Health Check
```bash
curl https://your-app-name.onrender.com/health
```

Expected response:
```json
{
  "status": "healthy",
  "environment": "production",
  "version": "1.0.0",
  "checks": {
    "database": "healthy",
    "ml_model": "not_loaded",
    "logs_dir": "exists",
    "models_dir": "exists",
    "render_env": "detected"
  },
  "platform": "render"
}
```

### 2. Test Sensor Data Endpoint
```bash
curl -X POST https://your-app-name.onrender.com/api/v1/sensor-data/ \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "ESP32_TEST_001",
    "timestamp": 1640995200000,
    "magnetometer_available": true,
    "accelerometer": {"x": 0.23, "y": -0.01, "z": 9.85},
    "gyroscope": {"x": 0.01, "y": 0.01, "z": -0.00},
    "magnetometer": {"x": 1617.00, "y": 1119.00, "z": -14421.00},
    "temperature": 26.82
  }'
```

### 3. Test API Documentation
Visit: `https://your-app-name.onrender.com/docs`

## 🔧 Update ESP32 Code

Once deployed, update your Arduino code:

```cpp
// Replace this line in your ESP32 code:
const char* apiEndpoint = "https://your-api-endpoint.com/api/imu-data";

// With your actual Render URL:
const char* apiEndpoint = "https://your-app-name.onrender.com/api/v1/sensor-data/";
```

## 🎉 Production Ready!

Your backend is now:
- ✅ **Live on the internet** with HTTPS
- ✅ **PostgreSQL database** for scalable data storage
- ✅ **Auto-deployments** from GitHub main branch
- ✅ **Health monitoring** with detailed status checks
- ✅ **ML pipeline ready** for real exercise data
- ✅ **ESP32 integration ready** - just update the endpoint!

## ⚠️ Important Notes

### Cold Starts (Free Tier)
- Services spin down after 15 minutes of inactivity
- Takes ~30 seconds to wake up
- **Your case**: ESP32 sends data every second, so always warm! ✅

### Usage Limits
- **750 hours/month** (covers 24/7 usage)
- **1GB PostgreSQL database**
- **Perfect for your IoT project** ✅

### Next Steps
1. Test all endpoints work correctly
2. Update ESP32 with production URL
3. Start collecting real sensor data
4. Train ML models with actual exercise data
5. Monitor via Render dashboard

## 🆘 Troubleshooting

### Build Fails
- Check `requirements.txt` is in `Progo-BE/` folder
- Verify Python version compatibility

### Database Connection Issues
- Ensure DATABASE_URL is set from connected PostgreSQL service
- Check health endpoint for database status

### 503 Service Unavailable
- Check build logs in Render dashboard
- Verify start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

### ESP32 Can't Connect
- Verify CORS is allowing your requests
- Check the exact endpoint URL format
- Test with curl first to verify backend works

---

**🎯 Total Deployment Time: ~50 minutes to production-ready IoT + ML system!** 🚀
