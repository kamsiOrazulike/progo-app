#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <Wire.h>
#include <Adafruit_LSM6DSOX.h>
#include <Adafruit_LIS3MDL.h>
#include <Adafruit_Sensor.h>
#include <WebSocketsClient.h>

const char* ssid = "Kamsi";
const char* password = "nopassword";

const char* apiEndpoint = "http://render-progo.onrender.com/api/v1/sensor-data/";
const char* apiEndpointHTTPS = "https://render-progo.onrender.com/api/v1/sensor-data/";
const char* formAnalysisEndpoint = "https://render-progo.onrender.com/api/v1/sensor-data/analyze-form";
bool useHTTPS = false;

// 🆕 WebSocket Configuration
const char* wsHost = "render-progo.onrender.com";
const int wsPort = 443;
const char* wsPath = "/ws";
WebSocketsClient webSocket;
bool wsConnected = false;
unsigned long lastWSReconnect = 0;
const unsigned long wsReconnectInterval = 5000;

String deviceId = "";
String deviceInfo = "";

// Exercise type for training data collection
String currentExercise = "resting";

// 🆕 Form Analysis Configuration
const int FORM_BUFFER_SIZE = 150;  // 15 seconds at 10Hz
const unsigned long FORM_COLLECTION_DURATION = 15000;  // 15 seconds in milliseconds

struct SensorData {
  float accel_x, accel_y, accel_z;
  float gyro_x, gyro_y, gyro_z;
  float mag_x, mag_y, mag_z;
  float temperature;
  String timestamp;
};

// 🆕 Form Analysis Buffer
struct FormAnalysisBuffer {
  SensorData readings[FORM_BUFFER_SIZE];
  int currentIndex;
  bool isCollecting;
  unsigned long startTime;
  int totalReadings;
};

FormAnalysisBuffer formBuffer = {.currentIndex = 0, .isCollecting = false, .startTime = 0, .totalReadings = 0};

// Sensors
Adafruit_LSM6DSOX lsm6ds;
Adafruit_LIS3MDL lis3mdl;
bool magnetometer_available = false;
bool magnetometer_enabled = true;

// Data collection timing
unsigned long lastSensorRead = 0;
const unsigned long sensorInterval = 100;  // Read sensors every 100ms (10Hz)

unsigned long lastDataSend = 0;
const unsigned long sendInterval = 1000;  // Send data every 1000ms (1Hz)

unsigned long lastMagRead = 0;
const unsigned long magInterval = 500;

// 🆕 WebSocket heartbeat
unsigned long lastHeartbeat = 0;
const unsigned long heartbeatInterval = 30000;

SensorData currentData;

void setup() {
  Serial.begin(115200);
  while (!Serial) delay(10);

  Serial.println("🎉 ESP32 S3 IMU Data Collection - WITH FORM ANALYSIS!");
  Serial.println("============================================================");

  // Initialize I2C with custom settings
  Wire.begin();
  Wire.setClock(100000);

  // Initialize sensors
  if (!initializeSensors()) {
    Serial.println("❌ Failed to initialize sensors!");
    while (1) delay(100);
  }

  // Connect to WiFi
  connectToWiFi();

  // Extract and display device ID
  extractDeviceId();

  // Initialize WebSocket
  initializeWebSocket();

  Serial.println("============================================================");
  Serial.println("✅ Setup complete! Starting data collection...");
  Serial.println("🏋️‍♂️ Commands via Serial OR WebSocket:");
  Serial.println("  Type 'bicep' - Start bicep curl data collection");
  Serial.println("  Type 'squat' - Start squat data collection");
  Serial.println("  Type 'rest' - Stop exercise data collection");
  Serial.println("  Type 'start_form' - Begin form analysis (15sec buffer)");
  Serial.println("  Type 'stop_form' - Stop form analysis and send data");
  Serial.println("  Type 'test' - Test API connection");
  Serial.println("  Type 'info' - Show device information");
  Serial.println("  Type 'mag_off' - Disable magnetometer");
  Serial.println("  Type 'mag_on' - Enable magnetometer");
  Serial.println("============================================================");

  // Test API connection on startup
  testAPIConnection();
}

void loop() {
  unsigned long currentTime = millis();

  // Handle WebSocket events
  webSocket.loop();

  // Auto-reconnect WebSocket if disconnected
  handleWebSocketReconnect();

  // Send heartbeat to keep connection alive
  if (wsConnected && currentTime - lastHeartbeat >= heartbeatInterval) {
    sendHeartbeat();
    lastHeartbeat = currentTime;
  }

  // Check for commands via Serial
  checkSerialCommands();

  // Read sensor data at specified interval
  if (currentTime - lastSensorRead >= sensorInterval) {
    readSensorData();
    
    // 🆕 Add reading to form analysis buffer if collecting
    if (formBuffer.isCollecting) {
      addReadingToBuffer(currentData);
      
      // Check if collection time is complete
      if (currentTime - formBuffer.startTime >= FORM_COLLECTION_DURATION) {
        stopFormAnalysis();
      }
    }
    
    lastSensorRead = currentTime;
  }

  // Send data to API at specified interval
  if (currentTime - lastDataSend >= sendInterval) {
    if (WiFi.status() == WL_CONNECTED) {
      sendDataToAPI();
    } else {
      Serial.println("📶 WiFi disconnected, attempting reconnection...");
      connectToWiFi();
      initializeWebSocket();
    }
    lastDataSend = currentTime;
  }

  delay(10);
}

// 🆕 FORM ANALYSIS FUNCTIONS

void startFormAnalysis() {
  if (formBuffer.isCollecting) {
    Serial.println("⚠️ Form analysis already in progress!");
    return;
  }
  
  // Reset buffer
  formBuffer.currentIndex = 0;
  formBuffer.totalReadings = 0;
  formBuffer.isCollecting = true;
  formBuffer.startTime = millis();
  
  Serial.println("🏋️‍♂️ FORM ANALYSIS STARTED!");
  Serial.println("📊 Collecting 15 seconds of movement data...");
  Serial.println("💡 Perform your bicep curls with proper form!");
  
  // Notify backend via WebSocket
  if (wsConnected) {
    DynamicJsonDocument doc(256);
    doc["type"] = "form_analysis_started";
    doc["device_id"] = deviceId;
    doc["timestamp"] = millis();
    doc["collection_duration"] = FORM_COLLECTION_DURATION;
    
    String message;
    serializeJson(doc, message);
    webSocket.sendTXT(message);
  }
}

void stopFormAnalysis() {
  if (!formBuffer.isCollecting) {
    Serial.println("⚠️ Form analysis not in progress!");
    return;
  }
  
  formBuffer.isCollecting = false;
  
  Serial.printf("📊 Form analysis complete! Collected %d readings\n", formBuffer.totalReadings);
  Serial.println("🔄 Sending data for analysis...");
  
  // Send buffer for analysis
  sendBufferForAnalysis();
}

void addReadingToBuffer(SensorData data) {
  if (!formBuffer.isCollecting || formBuffer.currentIndex >= FORM_BUFFER_SIZE) {
    return;
  }
  
  formBuffer.readings[formBuffer.currentIndex] = data;
  formBuffer.currentIndex++;
  formBuffer.totalReadings++;
  
  // Show progress every 3 seconds (30 readings at 10Hz)
  if (formBuffer.totalReadings % 30 == 0) {
    int secondsElapsed = formBuffer.totalReadings / 10;
    Serial.printf("📊 Form analysis progress: %d seconds collected...\n", secondsElapsed);
  }
}

void sendBufferForAnalysis() {
  if (formBuffer.totalReadings < 5) {
    Serial.println("❌ Not enough readings for analysis (minimum 5 required)");
    return;
  }
  
  HTTPClient http;
  
  if (!http.begin(formAnalysisEndpoint)) {
    Serial.println("❌ Failed to begin HTTP connection for form analysis");
    return;
  }
  
  http.addHeader("Content-Type", "application/json");
  http.setTimeout(30000);  // Longer timeout for analysis
  
  // Create JSON payload with readings
  DynamicJsonDocument doc(8192);  // Larger buffer for many readings
  JsonArray readings = doc.createNestedArray("readings");
  
  for (int i = 0; i < formBuffer.totalReadings && i < FORM_BUFFER_SIZE; i++) {
    JsonObject reading = readings.createNestedObject();
    reading["accel_x"] = formBuffer.readings[i].accel_x;
    reading["accel_y"] = formBuffer.readings[i].accel_y;
    reading["accel_z"] = formBuffer.readings[i].accel_z;
    reading["gyro_x"] = formBuffer.readings[i].gyro_x;
    reading["gyro_y"] = formBuffer.readings[i].gyro_y;
    reading["gyro_z"] = formBuffer.readings[i].gyro_z;
    reading["temperature"] = formBuffer.readings[i].temperature;
    reading["timestamp"] = formBuffer.readings[i].timestamp;
  }
  
  String payload;
  serializeJson(doc, payload);
  
  Serial.printf("📤 Sending %d readings for form analysis...\n", formBuffer.totalReadings);
  
  int httpResponseCode = http.POST(payload);
  
  if (httpResponseCode > 0) {
    String response = http.getString();
    
    if (httpResponseCode == 200) {
      Serial.println("✅ Form analysis completed!");
      handleFormAnalysisResponse(response);
    } else {
      Serial.printf("❌ Form analysis failed with code: %d\n", httpResponseCode);
      Serial.println("Response: " + response);
    }
  } else {
    Serial.printf("❌ Form analysis request failed: %d\n", httpResponseCode);
  }
  
  http.end();
}

void handleFormAnalysisResponse(String response) {
  DynamicJsonDocument doc(1024);
  DeserializationError error = deserializeJson(doc, response);
  
  if (error) {
    Serial.println("❌ Failed to parse form analysis response");
    return;
  }
  
  if (doc["success"]) {
    JsonObject data = doc["data"];
    int formScore = data["form_score"];
    String feedback = data["feedback"];
    
    JsonObject analysis = data["analysis"];
    int rangeScore = analysis["range_score"];
    int smoothnessScore = analysis["smoothness_score"];
    int consistencyScore = analysis["consistency_score"];
    
    // Display beautiful form analysis results
    Serial.println("🏋️‍♂️ ====== FORM ANALYSIS RESULTS ======");
    Serial.printf("   Overall Score: %d/100 %s\n", formScore, getScoreEmoji(formScore));
    Serial.println("   ────────────────────────────────────");
    Serial.printf("   Range Score:       %d/100 %s\n", rangeScore, getScoreEmoji(rangeScore));
    Serial.printf("   Smoothness Score:  %d/100 %s\n", smoothnessScore, getScoreEmoji(smoothnessScore));
    Serial.printf("   Consistency Score: %d/100 %s\n", consistencyScore, getScoreEmoji(consistencyScore));
    Serial.println("   ────────────────────────────────────");
    Serial.printf("   💬 Feedback: %s\n", feedback.c_str());
    Serial.println("======================================");
    
    // Send results via WebSocket to frontend
    if (wsConnected) {
      DynamicJsonDocument wsDoc(1024);
      wsDoc["type"] = "form_analysis_result";
      wsDoc["device_id"] = deviceId;
      wsDoc["form_score"] = formScore;
      wsDoc["feedback"] = feedback;
      wsDoc["range_score"] = rangeScore;
      wsDoc["smoothness_score"] = smoothnessScore;
      wsDoc["consistency_score"] = consistencyScore;
      wsDoc["timestamp"] = millis();
      
      String wsMessage;
      serializeJson(wsDoc, wsMessage);
      webSocket.sendTXT(wsMessage);
    }
    
  } else {
    Serial.println("❌ Form analysis failed: " + String(doc["message"] | "Unknown error"));
  }
}

String getScoreEmoji(int score) {
  if (score >= 90) return "⭐⭐⭐⭐⭐";
  else if (score >= 80) return "⭐⭐⭐⭐";
  else if (score >= 70) return "⭐⭐⭐";
  else if (score >= 60) return "⭐⭐";
  else if (score >= 50) return "⭐";
  else return "💪 (Keep practicing!)";
}

// 🆕 WebSocket Initialization
void initializeWebSocket() {
  Serial.println("🔌 Initializing WebSocket connection...");

  webSocket.begin(wsHost, wsPort, wsPath, "wss");
  webSocket.onEvent(webSocketEvent);
  webSocket.setReconnectInterval(5000);
  webSocket.enableHeartbeat(15000, 3000, 2);

  Serial.printf("🔗 Connecting to WebSocket: wss://%s:%d%s\n", wsHost, wsPort, wsPath);
}

// 🆕 WebSocket Event Handler
void webSocketEvent(WStype_t type, uint8_t* payload, size_t length) {
  switch (type) {
    case WStype_DISCONNECTED:
      Serial.println("🔌 WebSocket Disconnected");
      wsConnected = false;
      break;

    case WStype_CONNECTED:
      Serial.printf("🔌 WebSocket Connected to: %s\n", payload);
      wsConnected = true;
      sendDeviceIdentification();
      break;

    case WStype_TEXT:
      Serial.printf("📨 WebSocket Message Received: %s\n", payload);
      handleWebSocketCommand((char*)payload);
      break;

    case WStype_BIN:
      Serial.printf("📨 WebSocket Binary Received: %u bytes\n", length);
      break;

    case WStype_ERROR:
      Serial.printf("❌ WebSocket Error: %s\n", payload);
      break;

    case WStype_FRAGMENT_TEXT_START:
    case WStype_FRAGMENT_BIN_START:
    case WStype_FRAGMENT:
    case WStype_FRAGMENT_FIN:
      break;
  }
}

// Send Device Identification to Backend
void sendDeviceIdentification() {
  DynamicJsonDocument doc(512);
  doc["type"] = "device_connect";
  doc["device_id"] = deviceId;
  doc["device_info"] = deviceInfo;
  doc["capabilities"] = "imu_9dof_form_analysis";
  doc["firmware_version"] = "1.1.0";
  doc["timestamp"] = millis();

  String message;
  serializeJson(doc, message);

  webSocket.sendTXT(message);
  Serial.println("🆔 Sent device identification to backend");
}

// Handle WebSocket Commands from Backend
void handleWebSocketCommand(String message) {
  DynamicJsonDocument doc(1024);
  DeserializationError error = deserializeJson(doc, message);

  if (error) {
    Serial.println("❌ Failed to parse WebSocket message");
    return;
  }

  if (doc["type"] == "device_command") {
    String command = doc["command"];
    String timestamp = doc["timestamp"] | "";

    Serial.printf("🎮 Received command from backend: %s\n", command.c_str());

    bool success = processCommand(command);
    sendCommandAcknowledgment(command, success, timestamp);
  }
}

// Process Command (updated with form analysis commands)
bool processCommand(String command) {
  command.trim();
  command.toLowerCase();

  if (command == "bicep") {
    currentExercise = "bicep_curl";
    Serial.println("🏋️‍♂️ Now collecting BICEP CURL data for device: " + deviceId);
    return true;
  } else if (command == "squat") {
    currentExercise = "squat";
    Serial.println("🦵 Now collecting SQUAT data for device: " + deviceId);
    return true;
  } else if (command == "rest") {
    currentExercise = "resting";
    Serial.println("😴 Now collecting RESTING data for device: " + deviceId);
    return true;
  } else if (command == "start_form" || command == "start_form_analysis") {
    startFormAnalysis();
    return true;
  } else if (command == "stop_form" || command == "stop_form_analysis") {
    stopFormAnalysis();
    return true;
  } else if (command == "test") {
    Serial.println("🧪 Testing API connection...");
    testAPIConnection();
    return true;
  } else if (command == "info") {
    showDeviceInfo();
    return true;
  } else if (command == "mag_off") {
    magnetometer_enabled = false;
    Serial.println("📴 Magnetometer disabled - using 6-DOF only");
    return true;
  } else if (command == "mag_on") {
    magnetometer_enabled = true;
    Serial.println("📡 Magnetometer enabled");
    return true;
  } else if (command == "train_complete") {
    Serial.println("🎓 Training completed signal received");
    return true;
  } else {
    Serial.println("❌ Unknown command: " + command);
    return false;
  }
}

// Send Command Acknowledgment to Backend
void sendCommandAcknowledgment(String command, bool success, String originalTimestamp) {
  if (!wsConnected) return;

  DynamicJsonDocument doc(512);
  doc["type"] = "command_ack";
  doc["device_id"] = deviceId;
  doc["command"] = command;
  doc["status"] = success ? "executed" : "failed";
  doc["timestamp"] = millis();
  doc["original_timestamp"] = originalTimestamp;
  doc["current_exercise"] = currentExercise;
  doc["form_analysis_active"] = formBuffer.isCollecting;

  String message;
  serializeJson(doc, message);

  webSocket.sendTXT(message);
  Serial.printf("📤 Sent command acknowledgment: %s -> %s\n", command.c_str(), success ? "executed" : "failed");
}

// Handle WebSocket Reconnection
void handleWebSocketReconnect() {
  if (!wsConnected && WiFi.status() == WL_CONNECTED) {
    unsigned long currentTime = millis();
    if (currentTime - lastWSReconnect >= wsReconnectInterval) {
      Serial.println("🔄 Attempting WebSocket reconnection...");
      webSocket.disconnect();
      delay(100);
      initializeWebSocket();
      lastWSReconnect = currentTime;
    }
  }
}

// Send Heartbeat to Keep Connection Alive
void sendHeartbeat() {
  if (!wsConnected) return;

  DynamicJsonDocument doc(256);
  doc["type"] = "heartbeat";
  doc["device_id"] = deviceId;
  doc["timestamp"] = millis();
  doc["uptime"] = millis() / 1000;
  doc["free_heap"] = ESP.getFreeHeap();
  doc["current_exercise"] = currentExercise;
  doc["form_analysis_active"] = formBuffer.isCollecting;

  String message;
  serializeJson(doc, message);

  webSocket.sendTXT(message);
  Serial.println("💓 Sent heartbeat");
}

void extractDeviceId() {
  deviceId = WiFi.macAddress();
  deviceInfo = "ESP32-S3 | MAC: " + deviceId + " | Chip: " + String(ESP.getChipModel());

  Serial.println("🆔 DEVICE IDENTIFICATION:");
  Serial.println("   Device ID: " + deviceId);
  Serial.println("   Chip Model: " + String(ESP.getChipModel()));
  Serial.println("   Chip Revision: " + String(ESP.getChipRevision()));
  Serial.println("   SDK Version: " + String(ESP.getSdkVersion()));
  Serial.println("   Free Heap: " + String(ESP.getFreeHeap()) + " bytes");

  Serial.println("📋 FOR FRONTEND CONFIGURATION:");
  Serial.println("   const DEVICE_ID = \"" + deviceId + "\";");
}

void checkSerialCommands() {
  if (Serial.available()) {
    String command = Serial.readStringUntil('\n');
    bool success = processCommand(command);

    if (!success) {
      Serial.println("❌ Unknown command. Use: bicep, squat, rest, start_form, stop_form, test, info, mag_off, mag_on");
    }
  }
}

void showDeviceInfo() {
  Serial.println("📱 DEVICE INFORMATION:");
  Serial.println("   Device ID: " + deviceId);
  Serial.println("   Current Exercise: " + currentExercise);
  Serial.println("   Form Analysis: " + String(formBuffer.isCollecting ? "ACTIVE" : "INACTIVE"));
  Serial.println("   WiFi Status: " + String(WiFi.status() == WL_CONNECTED ? "Connected" : "Disconnected"));
  Serial.println("   IP Address: " + WiFi.localIP().toString());
  Serial.println("   Signal Strength: " + String(WiFi.RSSI()) + " dBm");
  Serial.println("   WebSocket Status: " + String(wsConnected ? "Connected" : "Disconnected"));
  Serial.println("   Magnetometer Available: " + String(magnetometer_available ? "Yes" : "No"));
  Serial.println("   Magnetometer Enabled: " + String(magnetometer_enabled ? "Yes" : "No"));
  Serial.println("   Using: " + String(useHTTPS ? "HTTPS" : "HTTP"));
  Serial.println("   Free Memory: " + String(ESP.getFreeHeap()) + " bytes");
  Serial.println("   Uptime: " + String(millis() / 1000) + " seconds");
  if (formBuffer.isCollecting) {
    Serial.println("   Form Buffer: " + String(formBuffer.totalReadings) + "/" + String(FORM_BUFFER_SIZE) + " readings");
  }
}

bool initializeSensors() {
  Serial.println("🔧 Initializing LSM6DSOX...");
  if (!lsm6ds.begin_I2C(0x6A)) {
    Serial.println("❌ Failed to find LSM6DSOX chip");
    return false;
  }
  Serial.println("✅ LSM6DSOX initialized successfully!");

  delay(100);

  Serial.println("🔧 Initializing LIS3MDL (magnetometer)...");
  bool lis3mdl_success = false;

  if (!lis3mdl_success) {
    if (lis3mdl.begin_I2C(0x1E)) {
      lis3mdl_success = true;
      Serial.println("✅ LIS3MDL Success with 0x1E!");
    }
  }

  if (!lis3mdl_success) {
    if (lis3mdl.begin_I2C()) {
      lis3mdl_success = true;
      Serial.println("✅ LIS3MDL Success with auto-detect!");
    }
  }

  if (!lis3mdl_success) {
    if (lis3mdl.begin_I2C(0x1C)) {
      lis3mdl_success = true;
      Serial.println("✅ LIS3MDL Success with 0x1C!");
    }
  }

  if (!lis3mdl_success) {
    Serial.println("⚠️ Failed to find LIS3MDL chip");
    Serial.println("💡 Continuing with 6-DOF only (Accel + Gyro)");
    Serial.println("💡 This is fine - ML will work great with 6-DOF!");
    magnetometer_available = false;
    magnetometer_enabled = false;
  } else {
    magnetometer_available = true;
    magnetometer_enabled = true;

    lis3mdl.setDataRate(LIS3MDL_DATARATE_80_HZ);
    lis3mdl.setRange(LIS3MDL_RANGE_4_GAUSS);
    lis3mdl.setPerformanceMode(LIS3MDL_LOWPOWERMODE);
    lis3mdl.setOperationMode(LIS3MDL_CONTINUOUSMODE);
  }

  lsm6ds.setAccelRange(LSM6DS_ACCEL_RANGE_4_G);
  lsm6ds.setGyroRange(LSM6DS_GYRO_RANGE_500_DPS);
  lsm6ds.setAccelDataRate(LSM6DS_RATE_104_HZ);
  lsm6ds.setGyroDataRate(LSM6DS_RATE_104_HZ);

  return true;
}

void connectToWiFi() {
  WiFi.begin(ssid, password);
  Serial.print("📶 Connecting to WiFi");

  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 20) {
    delay(500);
    Serial.print(".");
    attempts++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println();
    Serial.println("✅ WiFi connected!");
    Serial.print("   IP address: ");
    Serial.println(WiFi.localIP());
    Serial.print("   MAC address: ");
    Serial.println(WiFi.macAddress());
  } else {
    Serial.println();
    Serial.println("❌ WiFi connection failed!");
  }
}

void readSensorData() {
  sensors_event_t accel, gyro, temp;
  lsm6ds.getEvent(&accel, &gyro, &temp);

  currentData.accel_x = accel.acceleration.x;
  currentData.accel_y = accel.acceleration.y;
  currentData.accel_z = accel.acceleration.z;

  currentData.gyro_x = gyro.gyro.x;
  currentData.gyro_y = gyro.gyro.y;
  currentData.gyro_z = gyro.gyro.z;

  currentData.temperature = temp.temperature;

  // Create timestamp string
  currentData.timestamp = String(millis());

  unsigned long currentTime = millis();
  if (magnetometer_available && magnetometer_enabled && (currentTime - lastMagRead >= magInterval)) {
    bool mag_read_success = false;

    try {
      lis3mdl.read();
      currentData.mag_x = lis3mdl.x;
      currentData.mag_y = lis3mdl.y;
      currentData.mag_z = lis3mdl.z;
      mag_read_success = true;
      lastMagRead = currentTime;
    } catch (...) {
      Serial.println("⚠️ Magnetometer read failed, using previous values");
    }

    if (!mag_read_success) {
      if (currentData.mag_x == 0 && currentData.mag_y == 0 && currentData.mag_z == 0) {
        currentData.mag_x = 0.0;
        currentData.mag_y = 0.0;
        currentData.mag_z = 0.0;
      }
    }
  } else if (!magnetometer_available || !magnetometer_enabled) {
    currentData.mag_x = 0.0;
    currentData.mag_y = 0.0;
    currentData.mag_z = 0.0;
  }

  // Print data with form analysis status
  String formStatus = formBuffer.isCollecting ? "FORM" : "NORM";
  
  Serial.printf("[%s | %s | %s | WS:%s] A:%.2f,%.2f,%.2f G:%.2f,%.2f,%.2f T:%.1f°C",
                deviceId.c_str(),
                currentExercise.c_str(),
                formStatus.c_str(),
                wsConnected ? "✓" : "✗",
                currentData.accel_x, currentData.accel_y, currentData.accel_z,
                currentData.gyro_x, currentData.gyro_y, currentData.gyro_z,
                currentData.temperature);

  if (magnetometer_available && magnetometer_enabled) {
    Serial.printf(" M:%.0f,%.0f,%.0f", currentData.mag_x, currentData.mag_y, currentData.mag_z);
  }
  Serial.println();
}

void testAPIConnection() {
  Serial.println("🔍 Testing API connection with real device ID...");

  HTTPClient http;
  const char* testEndpoint = useHTTPS ? apiEndpointHTTPS : apiEndpoint;

  Serial.printf("📡 Testing endpoint: %s\n", testEndpoint);
  Serial.printf("🆔 Using device ID: %s\n", deviceId.c_str());

  if (!http.begin(testEndpoint)) {
    Serial.println("❌ Failed to begin HTTP connection");
    return;
  }

  http.addHeader("Content-Type", "application/json");
  http.setTimeout(15000);
  http.setFollowRedirects(HTTPC_FORCE_FOLLOW_REDIRECTS);

  DynamicJsonDocument testDoc(1024);
  testDoc["device_id"] = deviceId;
  testDoc["accel_x"] = 1.0;
  testDoc["accel_y"] = 2.0;
  testDoc["accel_z"] = 3.0;
  testDoc["gyro_x"] = 0.1;
  testDoc["gyro_y"] = 0.2;
  testDoc["gyro_z"] = 0.3;
  testDoc["mag_x"] = magnetometer_available ? 100.0 : 0.0;
  testDoc["mag_y"] = magnetometer_available ? 200.0 : 0.0;
  testDoc["mag_z"] = magnetometer_available ? 300.0 : 0.0;
  testDoc["magnetometer_available"] = magnetometer_available;
  testDoc["temperature"] = 25.0;

  JsonObject accelerometer = testDoc.createNestedObject("accelerometer");
  accelerometer["x"] = 1.0;
  accelerometer["y"] = 2.0;
  accelerometer["z"] = 3.0;

  JsonObject gyroscope = testDoc.createNestedObject("gyroscope");
  gyroscope["x"] = 0.1;
  gyroscope["y"] = 0.2;
  gyroscope["z"] = 0.3;

  JsonObject magnetometer = testDoc.createNestedObject("magnetometer");
  magnetometer["x"] = magnetometer_available ? 100.0 : 0.0;
  magnetometer["y"] = magnetometer_available ? 200.0 : 0.0;
  magnetometer["z"] = magnetometer_available ? 300.0 : 0.0;

  String testPayload;
  serializeJson(testDoc, testPayload);

  Serial.println("📤 Sending test payload with real device ID...");

  int httpResponseCode = http.POST(testPayload);

  if (httpResponseCode > 0) {
    String response = http.getString();
    Serial.printf("📊 Response code: %d\n", httpResponseCode);

    if (httpResponseCode == 200 || httpResponseCode == 201) {
      Serial.println("🎉 TEST PASSED! API connection successful!");
      Serial.println("✅ Device ID " + deviceId + " is ready for data streaming!");
    } else if (httpResponseCode == 307) {
      Serial.println("🔄 307 Redirect - trying HTTPS...");
      useHTTPS = true;
    } else {
      Serial.printf("⚠️ Unexpected response: %d\n", httpResponseCode);
      Serial.println("Response: " + response);
    }
  } else {
    Serial.printf("❌ Connection failed with error: %d\n", httpResponseCode);
  }

  http.end();
}

void sendDataToAPI() {
  HTTPClient http;
  const char* currentEndpoint = useHTTPS ? apiEndpointHTTPS : apiEndpoint;

  http.setTimeout(15000);
  http.setFollowRedirects(HTTPC_FORCE_FOLLOW_REDIRECTS);

  if (!http.begin(currentEndpoint)) {
    Serial.println("❌ HTTP client begin failed!");
    return;
  }

  http.addHeader("Content-Type", "application/json");

  DynamicJsonDocument doc(1536);

  doc["device_id"] = deviceId;

  doc["accel_x"] = currentData.accel_x;
  doc["accel_y"] = currentData.accel_y;
  doc["accel_z"] = currentData.accel_z;
  doc["gyro_x"] = currentData.gyro_x;
  doc["gyro_y"] = currentData.gyro_y;
  doc["gyro_z"] = currentData.gyro_z;
  doc["mag_x"] = currentData.mag_x;
  doc["mag_y"] = currentData.mag_y;
  doc["mag_z"] = currentData.mag_z;
  doc["magnetometer_available"] = magnetometer_available && magnetometer_enabled;
  doc["temperature"] = currentData.temperature;
  doc["exercise_type"] = currentExercise;

  JsonObject accelerometer = doc.createNestedObject("accelerometer");
  accelerometer["x"] = currentData.accel_x;
  accelerometer["y"] = currentData.accel_y;
  accelerometer["z"] = currentData.accel_z;

  JsonObject gyroscope = doc.createNestedObject("gyroscope");
  gyroscope["x"] = currentData.gyro_x;
  gyroscope["y"] = currentData.gyro_y;
  gyroscope["z"] = currentData.gyro_z;

  JsonObject magnetometer = doc.createNestedObject("magnetometer");
  magnetometer["x"] = currentData.mag_x;
  magnetometer["y"] = currentData.mag_y;
  magnetometer["z"] = currentData.mag_z;

  doc["session_id"] = String("session_") + deviceId + "_" + String(millis() / 60000);

  String jsonString;
  serializeJson(doc, jsonString);

  int httpResponseCode = http.POST(jsonString);

  if (httpResponseCode > 0) {
    String response = http.getString();

    if (httpResponseCode == 200 || httpResponseCode == 201) {
      Serial.printf("✅ [%s] Data sent successfully!\n", deviceId.c_str());
    } else if (httpResponseCode == 307) {
      if (!useHTTPS) {
        Serial.println("🔄 Got 307 redirect, switching to HTTPS...");
        useHTTPS = true;
      }
    } else if (httpResponseCode == 422) {
      Serial.println("❌ Data validation error (422)");
      Serial.println("Response: " + response);
    } else {
      Serial.printf("⚠️ Response code: %d\n", httpResponseCode);
    }
  } else {
    Serial.printf("❌ HTTP Error Code: %d\n", httpResponseCode);

    switch (httpResponseCode) {
      case -1:
        Serial.println("💡 Connection failed - check WiFi or wake up Render service");
        break;
      case -3:
        Serial.println("💡 Connection lost during request");
        break;
      case -11:
        Serial.println("💡 Request timeout");
        break;
      default:
        Serial.println("💡 Check WiFi and API endpoint");
    }
  }

  http.end();
}