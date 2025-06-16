# 🏋️‍♂️ ESP32 Fitness Tracker Website

A simple, responsive Next.js website for controlling your ESP32 fitness tracker device.

## 🚀 Quick Start

1. **Install dependencies**:
   ```bash
   npm install
   ```

2. **Update your ESP32 device ID**:
   - Open `components/ESP32Controller.tsx`
   - Replace `AA:BB:CC:DD:EE:FF` with your ESP32's MAC address on line 7

3. **Start the development server**:
   ```bash
   npm run dev
   ```

4. **Open your browser** to `http://localhost:3000`

## 📱 Features

- ✅ **Real-time ESP32 connection status** - Updates every 5 seconds
- ✅ **8-second training timer** with progress bar and countdown
- ✅ **Manual command buttons** (Bicep, Squat, Rest)
- ✅ **Responsive design** - Works great on mobile and desktop
- ✅ **Dark theme** with gradient background
- ✅ **Clean, minimal interface** - Focus on functionality
- ✅ **Touch-friendly buttons** - Easy to use on mobile devices

## 🔧 Configuration

### ESP32 Device ID
```typescript
// In components/ESP32Controller.tsx
const DEVICE_ID = "YOUR_ESP32_MAC_ADDRESS_HERE"; // Replace this!
```

### API Endpoints
The app connects to these endpoints:
- WebSocket Status: `GET /devices/{device_id}/websocket-status`
- Device Status: `GET /devices/{device_id}/status`
- Send Command: `POST /devices/{device_id}/command`

## 🎯 Usage

### Training Mode
1. Ensure your ESP32 is connected (green "Connected" badge)
2. Tap "Start 8-Second Training"
3. Watch the progress bar and "X seconds remaining" countdown
4. After 8 seconds, the app automatically sends a "rest" command

### Manual Commands
- **Bicep**: Send bicep curl command to ESP32
- **Squat**: Send squat command to ESP32  
- **Rest**: Send rest/stop command to ESP32

### Status Monitoring
- **Device ID**: Shows last 6 characters of your ESP32's MAC address
- **WebSocket**: Number of active connections
- **Recent (5min)**: Sensor readings in last 5 minutes
- **Total Readings**: All-time sensor data count

## 📱 Responsive Design

### Mobile (default)
- Vertical stack layout
- Touch-friendly button sizes (minimum 48px)
- Full-width buttons
- 2-column status grid

### Desktop (md breakpoints and up)
- Centered content with max-width
- 4-column status grid
- Horizontal button layout
- Optimized spacing

## 🛠️ Development

Built with:
- **Next.js 14** with App Router
- **TypeScript** for type safety
- **Tailwind CSS** for styling
- **React Hooks** for state management

## 🎨 Design System

### Color Palette
- **Background**: Dark gradient (slate-900 to slate-800)
- **Cards**: Semi-transparent white with backdrop blur
- **Primary**: Blue-600 for interactive elements
- **Success**: Green-600 for connected status
- **Error**: Red-600 for offline status
- **Text**: White for headers, slate-300 for body text

### Typography
- **Headers**: Bold, larger text with proper hierarchy
- **Body**: Easy-to-read slate-300 color
- **Device ID**: Monospace font for technical data

## 📦 Build for Production

```bash
npm run build
npm start
```

## 🌐 Deploy

The website is ready to deploy to Vercel, Netlify, or any static hosting service.

```bash
npm run build
```

## 📖 API Integration

The app polls your ESP32 device every 5 seconds via the backend API. Make sure your ESP32 is connected to the backend WebSocket server.

**Backend API**: `https://render-progo.onrender.com/api/v1/sensor-data`

## 🎨 Customization

### Colors
Edit the color scheme in `components/ESP32Controller.tsx`:
- Connection status: `bg-green-600` (connected) / `bg-red-600` (offline)
- Buttons: `bg-blue-600 hover:bg-blue-700`
- Background: `from-slate-900 to-slate-800`

### Layout
- Mobile-first responsive design
- Breakpoints: `md:` (768px+) for desktop layouts
- Container: Centered with max-width and padding

### Timing
- Status polling: Every 5 seconds
- Training duration: 8 seconds (configurable)
- Progress updates: Every 1 second

## 🔍 File Structure

```
app/
├── page.tsx                 // Main page with layout
├── layout.tsx              // Basic layout (no PWA)
└── globals.css             // Tailwind + dark theme

components/
└── ESP32Controller.tsx     // Main controller component

tailwind.config.ts          // Tailwind configuration
```

## 🆚 Differences from PWA Version

This is a **regular responsive website**, not a PWA:
- ❌ No app installation capabilities
- ❌ No offline functionality
- ❌ No service worker
- ❌ No app manifest
- ✅ Works in any modern browser
- ✅ Responsive design for all devices
- ✅ Clean, fast loading

---

**Made with ❤️ using ESP32 + Next.js**
