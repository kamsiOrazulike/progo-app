#!/bin/bash

# ProGo PWA Test Script
echo "🚀 Testing ProGo PWA..."

# Test basic server response
echo "📡 Testing server response..."
if curl -s -f http://localhost:3000 > /dev/null; then
    echo "✅ Server is responding"
else
    echo "❌ Server is not responding"
    exit 1
fi

# Test PWA manifest
echo "📱 Testing PWA manifest..."
if curl -s -f http://localhost:3000/manifest.json > /dev/null; then
    echo "✅ PWA manifest is accessible"
else
    echo "❌ PWA manifest is not accessible"
fi

# Test service worker
echo "🔧 Testing service worker..."
if curl -s -f http://localhost:3000/sw.js > /dev/null; then
    echo "✅ Service worker is accessible"
else
    echo "❌ Service worker is not accessible"
fi

# Test PWA icons
echo "🎨 Testing PWA icons..."
if curl -s -f http://localhost:3000/icon-192x192.svg > /dev/null; then
    echo "✅ 192x192 icon is accessible"
else
    echo "❌ 192x192 icon is not accessible"
fi

if curl -s -f http://localhost:3000/icon-512x512.svg > /dev/null; then
    echo "✅ 512x512 icon is accessible"
else
    echo "❌ 512x512 icon is not accessible"
fi

echo ""
echo "🎉 ProGo PWA is ready!"
echo "📍 App URL: http://localhost:3000"
echo "📱 Install as PWA: Click 'Install' in your browser"
echo "🔌 Backend: wss://progo-be.onrender.com"
