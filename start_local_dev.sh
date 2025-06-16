#!/usr/bin/env bash
# Frontend-Backend Local Testing Setup

echo "🚀 Setting up local development environment..."

# Start backend
echo "📡 Starting backend server..."
cd /Users/kams/Documents/workspace/progo-app/Progo-BE

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Creating one..."
    python3 -m venv venv
fi

# Activate virtual environment and install dependencies
source venv/bin/activate
echo "📦 Installing backend dependencies..."
pip install -q -r requirements.txt

# Start backend in background
echo "🖥️ Starting backend server on port 8000..."
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

# Wait for backend to start
echo "⏳ Waiting for backend to initialize..."
sleep 5

# Test backend health
echo "🔍 Testing backend health..."
if curl -s http://localhost:8000/health > /dev/null; then
    echo "✅ Backend is running successfully"
else
    echo "❌ Backend failed to start"
    kill $BACKEND_PID 2>/dev/null
    exit 1
fi

# Start frontend
echo "🎨 Starting frontend..."
cd /Users/kams/Documents/workspace/progo-app/progo-fe

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "📦 Installing frontend dependencies..."
    npm install
fi

echo "🖥️ Starting frontend development server..."
echo ""
echo "🎯 SETUP COMPLETE!"
echo "=================================="
echo "✅ Backend running at: http://localhost:8000"
echo "✅ Frontend will run at: http://localhost:3000"
echo ""
echo "⚠️  IMPORTANT: Update your frontend to use local backend!"
echo "   Change API_BASE_URL to: http://localhost:8000/api/v1"
echo ""
echo "🔧 To test exercise type collection:"
echo "   1. Send 'rest' command from frontend"
echo "   2. Send 'bicep' command from frontend"  
echo "   3. Check sample counts update"
echo ""
echo "🛑 To stop servers:"
echo "   - Press Ctrl+C to stop frontend"
echo "   - Run: kill $BACKEND_PID"
echo ""

# Start frontend (this will block)
npm run dev
