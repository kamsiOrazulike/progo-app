// Enhanced ESP32Controller with debug capabilities
// This version can switch between local and production backends for testing

// Add this at the top of your ESP32Controller.tsx file, right after the imports:

// Configuration - change this to switch between environments
const ENVIRONMENT = "local"; // Change to "production" for live testing

const CONFIG = {
  local: {
    API_BASE_URL: "http://localhost:8000/api/v1",
    DEVICE_ID: "CC:BA:97:01:3D:18",
    description: "Local Development"
  },
  production: {
    API_BASE_URL: "https://render-progo.onrender.com/api/v1", 
    DEVICE_ID: "CC:BA:97:01:3D:18",
    description: "Production (Render)"
  }
};

const { API_BASE_URL, DEVICE_ID } = CONFIG[ENVIRONMENT];

// Add this helper function to your component:
const debugLog = (message: string, data?: any) => {
  console.log(`[${CONFIG[ENVIRONMENT].description}] ${message}`, data || '');
};

// Enhanced status fetching with debug info:
const fetchStatus = useCallback(async () => {
  debugLog("🔍 Fetching status...");
  
  try {
    // ... existing code ...
    
    // Enhanced exercise statistics with debug
    try {
      debugLog("📊 Fetching exercise statistics...");
      const exerciseStatsResponse = await fetch(`${API_BASE_URL}/sensor-data/devices/${DEVICE_ID}/exercise-stats`);
      
      if (exerciseStatsResponse.ok) {
        const exerciseStats = await exerciseStatsResponse.json();
        debugLog("✅ Exercise statistics received:", exerciseStats);
        
        // Check if we have the new exercise_type support
        const hasExerciseTypes = exerciseStats.exercise_samples && 
          typeof exerciseStats.exercise_samples.rest === 'number';
        
        if (hasExerciseTypes) {
          debugLog("✅ Backend has exercise type support");
        } else {
          debugLog("⚠️ Backend may not have exercise type support");
        }
        
        setCollectedSamples({
          rest: exerciseStats.exercise_samples?.rest || exerciseStats.exercise_samples?.resting || 0,
          bicep_curl: exerciseStats.exercise_samples?.bicep_curl || exerciseStats.exercise_samples?.bicep || 0
        });
        
        // ... rest of existing code ...
      } else {
        debugLog(`⚠️ Exercise statistics failed: ${exerciseStatsResponse.status}`);
        
        // Enhanced fallback with debug
        debugLog("🔄 Falling back to sample counting...");
        const samplesResponse = await fetch(`${API_BASE_URL}/sensor-data/latest/${DEVICE_ID}?count=1000`);
        
        if (samplesResponse.ok) {
          const samplesData = await samplesResponse.json();
          debugLog(`📥 Fetched ${samplesData.length} sensor readings`);
          
          // Check if any readings have exercise_type
          const labeledReadings = samplesData.filter((s: any) => s.exercise_type);
          debugLog(`🏷️ Found ${labeledReadings.length} labeled readings`);
          
          if (labeledReadings.length > 0) {
            const uniqueTypes = new Set(labeledReadings.map((s: any) => s.exercise_type));
            debugLog("✅ Exercise types found:", Array.from(uniqueTypes));
          } else {
            debugLog("⚠️ No exercise_type labels found in sensor data");
          }
          
          // ... rest of existing fallback code ...
        }
      }
    } catch (error) {
      debugLog("❌ Exercise statistics error:", error);
    }
  } catch (error) {
    debugLog("❌ Status fetch error:", error);
  }
}, []);

// Enhanced command sending with debug:
const sendCommand = async (command: string) => {
  if (isLoading) return;

  debugLog(`📤 Sending command: ${command}`);
  setIsLoading(true);
  
  try {
    const response = await fetch(
      `${API_BASE_URL}/sensor-data/devices/${DEVICE_ID}/command`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ command }),
      }
    );

    if (response.ok) {
      const result = await response.json();
      debugLog("✅ Command sent successfully:", result);
      
      // Update data collection phase
      if (command === "rest") {
        setDataCollectionPhase("rest");
      } else if (command === "bicep") {
        setDataCollectionPhase("bicep");
      }
      
      // Refresh status after command
      setTimeout(fetchStatus, 1000);
    } else {
      debugLog(`⚠️ Command failed: ${response.status}`);
      // ... existing fallback code ...
    }
  } catch (error) {
    debugLog("❌ Command error:", error);
    // ... existing error handling ...
  } finally {
    setIsLoading(false);
  }
};

/* 
DEBUGGING CHECKLIST:
===================

1. ENVIRONMENT SETUP:
   ✅ Change ENVIRONMENT to "local" for testing
   ✅ Start local backend: ./start_local_dev.sh
   ✅ Check browser console for debug messages

2. BACKEND VERIFICATION:
   ✅ Visit http://localhost:8000/docs (API documentation)
   ✅ Test exercise stats: http://localhost:8000/api/v1/sensor-data/devices/CC:BA:97:01:3D:18/exercise-stats
   ✅ Check database: sqlite3 Progo-BE/progo_dev.db "SELECT exercise_type, COUNT(*) FROM sensor_readings GROUP BY exercise_type;"

3. FRONTEND TESTING:
   ✅ Send 'rest' and 'bicep' commands
   ✅ Check if sample counts update
   ✅ Verify exercise_type appears in debug logs
   ✅ Test exercise statistics endpoint

4. DATA FLOW VERIFICATION:
   ✅ ESP32 sends exercise_type ➜ Backend stores in DB ➜ Frontend displays counts
   ✅ Check browser Network tab for API calls
   ✅ Verify exercise_type in API responses

5. PRODUCTION TESTING:
   ✅ Change ENVIRONMENT to "production"
   ✅ Deploy backend changes to Render
   ✅ Test with live ESP32 device
*/
