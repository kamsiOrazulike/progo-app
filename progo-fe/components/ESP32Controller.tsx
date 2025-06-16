/* eslint-disable @typescript-eslint/no-explicit-any */
// components/ESP32Controller.tsx
"use client";

import { useState, useEffect, useCallback } from "react";

// Replace with your ESP32 MAC address
const DEVICE_ID = "CC:BA:97:01:3D:18";
const API_BASE_URL = "https://render-progo.onrender.com/api/v1";

interface WebSocketStatus {
  device_id: string;
  is_connected: boolean;
  connection_count: number;
  queued_messages: number;
}

interface DeviceStatus {
  device_id: string;
  is_online: boolean;
  recent_readings_5min: number;
  total_readings: number;
  ready_for_prediction: boolean;
}

interface CommandResponse {
  success: boolean;
  message: string;
  command: string;
}

interface WorkoutSession {
  id: number;
  device_id: string;
  exercise_type: string;
  status: string;
  current_set: number;
  current_reps: number;
  target_sets: number;
  target_reps_per_set: number;
  started_at: string;
}

interface TrainingStatus {
  is_training: boolean;
  message: string;
  accuracy?: number;
  training_samples?: number;
}

export default function ESP32Controller() {
  const [wsStatus, setWsStatus] = useState<WebSocketStatus | null>(null);
  const [deviceStatus, setDeviceStatus] = useState<DeviceStatus | null>(null);
  const [isTraining, setIsTraining] = useState(false);
  const [trainingProgress, setTrainingProgress] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [trainingTimeLeft, setTrainingTimeLeft] = useState(0);
  const [currentWorkout, setCurrentWorkout] = useState<WorkoutSession | null>(null);
  const [trainingStatus, setTrainingStatus] = useState<TrainingStatus>({
    is_training: false,
    message: "Ready to collect data"
  });
  const [dataCollectionPhase, setDataCollectionPhase] = useState<"rest" | "bicep" | "complete">("rest");
  const [collectedSamples, setCollectedSamples] = useState({
    rest: 0,
    bicep_curl: 0
  });

  const isConnected = (wsStatus?.is_connected || deviceStatus?.is_online || (deviceStatus?.total_readings && deviceStatus.total_readings > 0)) ?? false;

  const fetchStatus = useCallback(async () => {
    try {
      // Try WebSocket status endpoint (may not be available on live server)
      let wsData = null;
      try {
        const wsResponse = await fetch(`${API_BASE_URL}/sensor-data/devices/${DEVICE_ID}/websocket-status`);
        if (wsResponse.ok) {
          wsData = await wsResponse.json();
        }
      } catch {
        console.log("WebSocket status endpoint not available");
      }
      setWsStatus(wsData);

      // Device status endpoint
      let deviceData = null;
      try {
        const deviceResponse = await fetch(`${API_BASE_URL}/sensor-data/devices/${DEVICE_ID}/status`);
        if (deviceResponse.ok) {
          deviceData = await deviceResponse.json();
        }
      } catch {
        console.log("Device status endpoint may not be available");
      }
      setDeviceStatus(deviceData);

      // Workout endpoint (may not be available)
      let workoutData = null;
      try {
        const workoutResponse = await fetch(`${API_BASE_URL}/workouts/current/${DEVICE_ID}`);
        if (workoutResponse.ok) {
          workoutData = await workoutResponse.json();
        }
      } catch {
        console.log("Workout endpoint not available");
      }
      setCurrentWorkout(workoutData);

      // Fetch collected samples count using the new exercise statistics endpoint
      try {
        const exerciseStatsResponse = await fetch(`${API_BASE_URL}/sensor-data/devices/${DEVICE_ID}/exercise-stats`);
        if (exerciseStatsResponse.ok) {
          const exerciseStats = await exerciseStatsResponse.json();
          console.log('Exercise statistics:', exerciseStats);
          
          // Use the exercise samples from the statistics endpoint
          setCollectedSamples({
            rest: exerciseStats.exercise_samples?.rest || exerciseStats.exercise_samples?.resting || 0,
            bicep_curl: exerciseStats.exercise_samples?.bicep_curl || exerciseStats.exercise_samples?.bicep || 0
          });
          
          // Update device status with real data
          if (!deviceData && exerciseStats.total_readings > 0) {
            deviceData = {
              device_id: DEVICE_ID,
              is_online: exerciseStats.total_readings > 0,
              recent_readings_5min: exerciseStats.recent_readings_1h || 0,
              total_readings: exerciseStats.total_readings,
              ready_for_prediction: exerciseStats.total_readings > 0
            };
            setDeviceStatus(deviceData);
          }
        } else {
          console.log("Exercise statistics endpoint not available, falling back to sample counting");
          
          // Fallback: Fetch collected samples count from latest readings
          const samplesResponse = await fetch(`${API_BASE_URL}/sensor-data/latest/${DEVICE_ID}?count=1000`);
          if (samplesResponse.ok) {
            const samplesData = await samplesResponse.json();
            console.log(`Fetched ${samplesData.length} sensor readings for sample counting`);
            
            // Count samples by exercise_type (with fallback for old data)
            const restCount = samplesData.filter((s: any) => 
              s.exercise_type === "resting" || s.exercise_type === "rest"
            ).length;
            const bicepCount = samplesData.filter((s: any) => 
              s.exercise_type === "bicep_curl" || s.exercise_type === "bicep"
            ).length;
            
            console.log(`Sample counts - Rest: ${restCount}, Bicep: ${bicepCount}`);
            setCollectedSamples({ rest: restCount, bicep_curl: bicepCount });
            
            // Update device status to reflect we have data
            if (!deviceData) {
              deviceData = {
                device_id: DEVICE_ID,
                is_online: samplesData.length > 0,
                recent_readings_5min: samplesData.length,
                total_readings: samplesData.length,
                ready_for_prediction: samplesData.length > 0
              };
            } else {
              deviceData.total_readings = samplesData.length;
              deviceData.recent_readings_5min = samplesData.length;
              deviceData.is_online = samplesData.length > 0;
            }
            setDeviceStatus(deviceData);
          }
        }
      } catch (error) {
        console.error("Failed to fetch exercise statistics:", error);
      }
    } catch (error) {
      console.error("Failed to fetch status:", error);
      setWsStatus(null);
      setDeviceStatus(null);
      setCurrentWorkout(null);
    }
  }, []);

  const sendCommand = async (command: string) => {
    if (isLoading) return;

    setIsLoading(true);
    try {
      const response = await fetch(
        `${API_BASE_URL}/sensor-data/devices/${DEVICE_ID}/command`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ command }),
        }
      );

      if (response.ok) {
        const result: CommandResponse = await response.json();
        console.log("Command sent successfully:", result);
        
        // Update data collection phase based on command
        if (command === "rest") {
          setDataCollectionPhase("rest");
        } else if (command === "bicep") {
          setDataCollectionPhase("bicep");
        }
        
        // Refresh status after command
        setTimeout(fetchStatus, 1000);
      } else {
        console.error("Failed to send command - endpoint may not be available");
        // Simulate command for demo purposes when endpoint is not available
        console.log(`Simulating command: ${command}`);
        
        if (command === "rest") {
          setDataCollectionPhase("rest");
        } else if (command === "bicep") {
          setDataCollectionPhase("bicep");
        }
      }
    } catch (error) {
      console.error("Error sending command:", error);
      console.log(`Command endpoint not available, simulating: ${command}`);
      
      // Simulate command for demo purposes
      if (command === "rest") {
        setDataCollectionPhase("rest");
      } else if (command === "bicep") {
        setDataCollectionPhase("bicep");
      }
    } finally {
      setIsLoading(false);
    }
  };

  const startBicepTraining = async () => {
    if (!isConnected || isTraining) return;

    setIsTraining(true);
    setTrainingProgress(0);
    setTrainingTimeLeft(8);

    // Send bicep command
    await sendCommand("bicep");

    // 8-second countdown with progress bar
    const interval = setInterval(() => {
      setTrainingProgress((prev) => {
        const newProgress = prev + 12.5; // 12.5% per second for 8 seconds
        return newProgress >= 100 ? 100 : newProgress;
      });

      setTrainingTimeLeft((prev) => {
        const newTime = prev - 1;
        if (newTime <= 0) {
          clearInterval(interval);
          // Send rest command after training
          sendCommand("rest");
          setTimeout(() => {
            setIsTraining(false);
            setTrainingProgress(0);
            setTrainingTimeLeft(0);
          }, 1000);
          return 0;
        }
        return newTime;
      });
    }, 1000);
  };

  const startDataCollection = async (duration: number, exerciseType: "rest" | "bicep") => {
    if (!isConnected) return;

    setIsLoading(true);
    setDataCollectionPhase(exerciseType);
    
    try {
      // Send command to ESP32
      const command = exerciseType === "rest" ? "rest" : "bicep";
      await sendCommand(command);
      
      // Wait for specified duration
      await new Promise(resolve => setTimeout(resolve, duration * 1000));
      
      // Send rest command at the end
      await sendCommand("rest");
      
      // Refresh status to update sample counts
      setTimeout(fetchStatus, 2000);
      
    } finally {
      setIsLoading(false);
      setDataCollectionPhase("rest");
    }
  };

  const trainBicepModel = async () => {
    if (!isConnected) return;

    setTrainingStatus({ is_training: true, message: "Starting model training..." });
    
    try {
      const response = await fetch(`${API_BASE_URL}/ml/train`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          model_name: "bicep_curl_classifier",
          model_type: "random_forest",
          device_id: DEVICE_ID,
        }),
      });

      if (response.ok) {
        const result = await response.json();
        setTrainingStatus({
          is_training: false,
          message: "Model training completed successfully!",
          accuracy: result.data?.validation_accuracy,
          training_samples: result.data?.training_samples
        });
      } else {
        const error = await response.json();
        setTrainingStatus({
          is_training: false,
          message: `Training failed: ${error.detail || "Unknown error"}`
        });
      }
    } catch (error) {
      setTrainingStatus({
        is_training: false,
        message: `Training error: ${error instanceof Error ? error.message : "Unknown error"}`
      });
    }
  };

  const startWorkoutSession = async () => {
    if (!isConnected) return;

    try {
      const response = await fetch(`${API_BASE_URL}/workouts/start`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          device_id: DEVICE_ID,
          exercise_type: "bicep_curl",
          target_sets: 3,
          target_reps: 8,
        }),
      });

      if (response.ok) {
        const workout = await response.json();
        setCurrentWorkout(workout);
        await sendCommand("bicep"); // Start bicep curl detection
      }
    } catch (error) {
      console.error("Failed to start workout:", error);
    }
  };

  const stopWorkout = async () => {
    if (!currentWorkout) return;

    try {
      await fetch(`${API_BASE_URL}/workouts/${currentWorkout.id}/complete`, {
        method: "POST",
      });
      
      await sendCommand("rest");
      setCurrentWorkout(null);
      setTimeout(fetchStatus, 1000);
    } catch (error) {
      console.error("Failed to stop workout:", error);
    }
  };

  // Poll status every 5 seconds
  useEffect(() => {
    fetchStatus(); // Initial fetch
    const interval = setInterval(fetchStatus, 5000);
    return () => clearInterval(interval);
  }, [fetchStatus]);

  const formatDeviceId = (id: string) => {
    return id.length > 6 ? id.slice(-6) : id;
  };

  return (
    <div className="space-y-8">
      {/* Header Status */}
      <div className="text-center">
        <h2 className="text-2xl font-bold text-white mb-2">🏋️‍♂️ Bicep Curl Training System</h2>
        <p className="text-gray-400">
          Collect data, train models, and track your bicep curl workouts in real-time
        </p>
      </div>

      {/* Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
        {/* Device Status Card */}
        <div className="bg-white/5 backdrop-blur-sm border border-white/10 rounded-lg p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-white">Device Status</h3>
            <div
              className={`w-3 h-3 rounded-full ${
                isConnected ? "bg-green-500 animate-pulse" : "bg-red-500"
              }`}
            ></div>
          </div>
          <div className="space-y-3">
            <div className="flex justify-between">
              <span className="text-gray-400 text-sm">Connection</span>
              <span className={`text-sm font-medium ${isConnected ? "text-green-500" : "text-red-500"}`}>
                {isConnected ? "Online" : "Offline"}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400 text-sm">Device ID</span>
              <span className="text-white text-sm font-mono">
                {formatDeviceId(DEVICE_ID)}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400 text-sm">Recent Data</span>
              <span className="text-white text-sm">
                {deviceStatus?.recent_readings_5min || 0} points
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400 text-sm">Current Mode</span>
              <span className={`px-2 py-1 rounded text-xs font-medium ${
                dataCollectionPhase === "bicep" ? "bg-orange-500/20 text-orange-400" :
                dataCollectionPhase === "rest" ? "bg-green-500/20 text-green-400" :
                "bg-gray-500/20 text-gray-400"
              }`}>
                {dataCollectionPhase === "bicep" ? "Bicep Curls" : 
                 dataCollectionPhase === "rest" ? "Resting" : "Standby"}
              </span>
            </div>
          </div>
        </div>

        {/* Data Collection Card */}
        <div className="bg-white/5 backdrop-blur-sm border border-white/10 rounded-lg p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-white">Data Collection</h3>
            <div className="w-3 h-3 bg-blue-500 rounded-full"></div>
          </div>
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4 text-center">
              <div className="bg-green-500/10 rounded-lg p-3">
                <div className="text-green-400 font-bold text-lg">{collectedSamples.rest}</div>
                <div className="text-green-400 text-xs">Rest Samples</div>
              </div>
              <div className="bg-orange-500/10 rounded-lg p-3">
                <div className="text-orange-400 font-bold text-lg">{collectedSamples.bicep_curl}</div>
                <div className="text-orange-400 text-xs">Bicep Samples</div>
              </div>
            </div>
            
            <div className="space-y-2">
              <button
                onClick={() => startDataCollection(10, "rest")}
                disabled={!isConnected || isLoading}
                className={`w-full py-2 px-3 rounded text-sm font-medium transition-colors ${
                  !isConnected || isLoading
                    ? "bg-gray-800 text-gray-500 cursor-not-allowed"
                    : "bg-green-600 hover:bg-green-700 text-white"
                }`}
              >
                Collect Rest Data (10s)
              </button>
              <button
                onClick={() => startDataCollection(10, "bicep")}
                disabled={!isConnected || isLoading}
                className={`w-full py-2 px-3 rounded text-sm font-medium transition-colors ${
                  !isConnected || isLoading
                    ? "bg-gray-800 text-gray-500 cursor-not-allowed"
                    : "bg-orange-600 hover:bg-orange-700 text-white"
                }`}
              >
                Collect Bicep Data (10s)
              </button>
            </div>
          </div>
        </div>

        {/* Model Training Card */}
        <div className="bg-white/5 backdrop-blur-sm border border-white/10 rounded-lg p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-white">Model Training</h3>
            <div
              className={`w-3 h-3 rounded-full ${
                trainingStatus.is_training ? "bg-yellow-500 animate-pulse" : "bg-purple-500"
              }`}
            ></div>
          </div>
          <div className="space-y-4">
            <div className="text-center">
              <div className="text-xs text-gray-400 mb-2">Training Status</div>
              <div className={`text-sm font-medium px-3 py-2 rounded ${
                trainingStatus.is_training ? "bg-yellow-500/20 text-yellow-400" :
                trainingStatus.message.includes("success") ? "bg-green-500/20 text-green-400" :
                trainingStatus.message.includes("fail") ? "bg-red-500/20 text-red-400" :
                "bg-gray-500/20 text-gray-400"
              }`}>
                {trainingStatus.message}
              </div>
            </div>
            
            {trainingStatus.accuracy && (
              <div className="text-center">
                <div className="text-2xl font-bold text-white">{(trainingStatus.accuracy * 100).toFixed(1)}%</div>
                <div className="text-xs text-gray-400">Model Accuracy</div>
              </div>
            )}
            
            <button
              onClick={trainBicepModel}
              disabled={!isConnected || trainingStatus.is_training || collectedSamples.rest < 50 || collectedSamples.bicep_curl < 50}
              className={`w-full py-2 px-3 rounded text-sm font-medium transition-colors ${
                !isConnected || trainingStatus.is_training || collectedSamples.rest < 50 || collectedSamples.bicep_curl < 50
                  ? "bg-gray-800 text-gray-500 cursor-not-allowed"
                  : "bg-purple-600 hover:bg-purple-700 text-white"
              }`}
            >
              {trainingStatus.is_training ? "Training..." : "Train Bicep Model"}
            </button>
            
            {(collectedSamples.rest < 50 || collectedSamples.bicep_curl < 50) && (
              <div className="text-xs text-yellow-400 text-center">
                Need 50+ samples each (rest & bicep)
              </div>
            )}
          </div>
        </div>

        {/* Workout Session Card */}
        <div className="bg-white/5 backdrop-blur-sm border border-white/10 rounded-lg p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-white">Live Workout</h3>
            <div
              className={`w-3 h-3 rounded-full ${
                currentWorkout ? "bg-green-500 animate-pulse" : "bg-gray-500"
              }`}
            ></div>
          </div>
          
          {currentWorkout ? (
            <div className="space-y-4">
              <div className="text-center">
                <div className="text-2xl font-bold text-white">
                  Set {currentWorkout.current_set}/{currentWorkout.target_sets}
                </div>
                <div className="text-sm text-gray-400">
                  {currentWorkout.current_reps}/{currentWorkout.target_reps_per_set} reps
                </div>
              </div>
              
              <div className="w-full bg-gray-700 rounded-full h-2">
                <div
                  className="bg-green-500 h-2 rounded-full transition-all duration-300"
                  style={{
                    width: `${(currentWorkout.current_reps / currentWorkout.target_reps_per_set) * 100}%`
                  }}
                />
              </div>
              
              <button
                onClick={stopWorkout}
                className="w-full py-2 px-3 rounded text-sm font-medium bg-red-600 hover:bg-red-700 text-white transition-colors"
              >
                Stop Workout
              </button>
            </div>
          ) : (
            <div className="space-y-4">
              <div className="text-center text-gray-400 text-sm">
                No active workout session
              </div>
              <button
                onClick={startWorkoutSession}
                disabled={!isConnected || !trainingStatus.accuracy}
                className={`w-full py-2 px-3 rounded text-sm font-medium transition-colors ${
                  !isConnected || !trainingStatus.accuracy
                    ? "bg-gray-800 text-gray-500 cursor-not-allowed"
                    : "bg-green-600 hover:bg-green-700 text-white"
                }`}
              >
                Start Bicep Workout
              </button>
              {!trainingStatus.accuracy && (
                <div className="text-xs text-yellow-400 text-center">
                  Train a model first
                </div>
              )}
            </div>
          )}
        </div>

        {/* Quick Training Session Card */}
        <div className="bg-white/5 backdrop-blur-sm border border-white/10 rounded-lg p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-white">Quick Session</h3>
            <div
              className={`w-3 h-3 rounded-full ${
                isTraining ? "bg-green-500 animate-pulse" : "bg-gray-500"
              }`}
            ></div>
          </div>
          <p className="text-gray-400 text-sm mb-4">
            8-second bicep curl data collection for quick training samples.
          </p>
          <div className="space-y-4">
            <button
              onClick={startBicepTraining}
              disabled={!isConnected || isTraining}
              className={`w-full py-3 px-4 rounded transition-colors text-sm font-medium ${
                !isConnected || isTraining
                  ? "bg-gray-800 text-gray-500 cursor-not-allowed"
                  : "bg-white text-black hover:bg-gray-200"
              }`}
            >
              {isTraining ? "Recording..." : "Start Quick Session"}
            </button>

            {isTraining && (
              <div className="space-y-3">
                <div className="w-full bg-gray-800 rounded-full h-2">
                  <div
                    className="bg-green-500 h-2 rounded-full transition-all duration-1000"
                    style={{ width: `${trainingProgress}%` }}
                  />
                </div>
                <p className="text-center text-gray-400 text-xs">
                  {trainingTimeLeft > 0
                    ? `${trainingTimeLeft}s remaining`
                    : "Complete!"}
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Manual Commands Card */}
        <div className="bg-white/5 backdrop-blur-sm border border-white/10 rounded-lg p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-white">Manual Control</h3>
            <div className="w-3 h-3 bg-blue-500 rounded-full"></div>
          </div>
          <p className="text-gray-400 text-sm mb-4">
            Send individual commands directly to your ESP32 device.
          </p>
          <div className="grid grid-cols-3 gap-2">
            <button
              onClick={() => sendCommand("bicep")}
              disabled={!isConnected || isLoading}
              className={`py-2 px-3 rounded transition-colors text-xs font-medium ${
                !isConnected || isLoading
                  ? "bg-gray-800 text-gray-500 cursor-not-allowed"
                  : "bg-orange-600 hover:bg-orange-700 text-white"
              }`}
            >
              Bicep
            </button>
            <button
              onClick={() => sendCommand("squat")}
              disabled={!isConnected || isLoading}
              className={`py-2 px-3 rounded transition-colors text-xs font-medium ${
                !isConnected || isLoading
                  ? "bg-gray-800 text-gray-500 cursor-not-allowed"
                  : "bg-blue-600 hover:bg-blue-700 text-white"
              }`}
            >
              Squat
            </button>
            <button
              onClick={() => sendCommand("rest")}
              disabled={!isConnected || isLoading}
              className={`py-2 px-3 rounded transition-colors text-xs font-medium ${
                !isConnected || isLoading
                  ? "bg-gray-800 text-gray-500 cursor-not-allowed"
                  : "bg-green-600 hover:bg-green-700 text-white"
              }`}
            >
              Rest
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
