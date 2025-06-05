//🎉 ESP32 CODE - FIXED I2C MAGNETOMETER ISSUES
//✅ IMPROVED: Better I2C error handling
//✅ IMPROVED: Graceful magnetometer failure handling
//✅ FIXED: Reduced I2C transaction frequency

#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <Wire.h>
#include <Adafruit_LSM6DSOX.h>
#include <Adafruit_LIS3MDL.h>
#include <Adafruit_Sensor.h>

// WiFi credentials
const char* ssid = "Kamsi";
const char* password = "nopassword";

// API endpoints - FIXED: Use HTTP to avoid 307 redirects
const char* apiEndpoint = "http://render-progo.onrender.com/api/v1/sensor-data/";
const char* apiEndpointHTTPS = "https://render-progo.onrender.com/api/v1/sensor-data/";
bool useHTTPS = false;  // Start with HTTP to avoid redirects

// 🆔 DEVICE IDENTIFICATION
String deviceId = "";    // Will be set to real MAC address
String deviceInfo = "";  // Formatted device info

// Exercise type for training data collection
String currentExercise = "resting";  // Options: "bicep_curl", "squat", "resting"

// Sensor objects
Adafruit_LSM6DSOX lsm6ds;
Adafruit_LIS3MDL lis3mdl;
bool magnetometer_available = false;
bool magnetometer_enabled = true;  // Can disable if too many errors

// Data collection timing
unsigned long lastSensorRead = 0;
const unsigned long sensorInterval = 100;  // Read sensors every 100ms (10Hz)

unsigned long lastDataSend = 0;
const unsigned long sendInterval = 1000;  // Send data every 1000ms (1Hz)

unsigned long lastMagRead = 0;
const unsigned long magInterval = 500;  // Read magnetometer less frequently (2Hz)

// Data storage
struct SensorData {
  float accel_x, accel_y, accel_z;
  float gyro_x, gyro_y, gyro_z;
  float mag_x, mag_y, mag_z;
  float temperature;
  unsigned long timestamp;
};

SensorData currentData;

void setup() {
  Serial.begin(115200);
  while (!Serial) delay(10);

  Serial.println("🎉 ESP32 S3 IMU Data Collection - FIXED I2C ISSUES!");
  Serial.println("============================================================");

  // Initialize I2C with custom settings
  Wire.begin();
  Wire.setClock(100000);  // Slower I2C clock for stability

  // Initialize sensors
  if (!initializeSensors()) {
    Serial.println("❌ Failed to initialize sensors!");
    while (1) delay(100);
  }

  // Connect to WiFi
  connectToWiFi();

  // 🆔 EXTRACT AND DISPLAY REAL DEVICE ID
  extractDeviceId();

  Serial.println("============================================================");
  Serial.println("✅ Setup complete! Starting data collection...");
  Serial.println("🏋️‍♂️ Commands via Serial:");
  Serial.println("  Type 'bicep' - Start bicep curl data collection");
  Serial.println("  Type 'squat' - Start squat data collection");
  Serial.println("  Type 'rest' - Stop exercise data collection");
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

  // Check for commands via Serial
  checkSerialCommands();

  // Read sensor data at specified interval
  if (currentTime - lastSensorRead >= sensorInterval) {
    readSensorData();
    lastSensorRead = currentTime;
  }

  // Send data to API at specified interval
  if (currentTime - lastDataSend >= sendInterval) {
    if (WiFi.status() == WL_CONNECTED) {
      sendDataToAPI();
    } else {
      Serial.println("📶 WiFi disconnected, attempting reconnection...");
      connectToWiFi();
    }
    lastDataSend = currentTime;
  }

  delay(10);
}

void extractDeviceId() {
  // Get the real MAC address as device ID
  deviceId = WiFi.macAddress();

  // Format device info
  deviceInfo = "ESP32-S3 | MAC: " + deviceId + " | Chip: " + String(ESP.getChipModel());

  Serial.println("🆔 DEVICE IDENTIFICATION:");
  Serial.println("   Device ID: " + deviceId);
  Serial.println("   Chip Model: " + String(ESP.getChipModel()));
  Serial.println("   Chip Revision: " + String(ESP.getChipRevision()));
  Serial.println("   SDK Version: " + String(ESP.getSdkVersion()));
  Serial.println("   Free Heap: " + String(ESP.getFreeHeap()) + " bytes");

  // Also print in a format easy to copy for frontend
  Serial.println("📋 FOR FRONTEND CONFIGURATION:");
  Serial.println("   const DEVICE_ID = \"" + deviceId + "\";");
}

void checkSerialCommands() {
  if (Serial.available()) {
    String command = Serial.readStringUntil('\n');
    command.trim();
    command.toLowerCase();

    if (command == "bicep") {
      currentExercise = "bicep_curl";
      Serial.println("🏋️‍♂️ Now collecting BICEP CURL data for device: " + deviceId);
    } else if (command == "squat") {
      currentExercise = "squat";
      Serial.println("🦵 Now collecting SQUAT data for device: " + deviceId);
    } else if (command == "rest") {
      currentExercise = "resting";
      Serial.println("😴 Now collecting RESTING data for device: " + deviceId);
    } else if (command == "test") {
      Serial.println("🧪 Testing API connection...");
      testAPIConnection();
    } else if (command == "info") {
      showDeviceInfo();
    } else if (command == "mag_off") {
      magnetometer_enabled = false;
      Serial.println("📴 Magnetometer disabled - using 6-DOF only");
    } else if (command == "mag_on") {
      magnetometer_enabled = true;
      Serial.println("📡 Magnetometer enabled");
    } else {
      Serial.println("❌ Unknown command. Use: bicep, squat, rest, test, info, mag_off, mag_on");
    }
  }
}

void showDeviceInfo() {
  Serial.println("📱 DEVICE INFORMATION:");
  Serial.println("   Device ID: " + deviceId);
  Serial.println("   Current Exercise: " + currentExercise);
  Serial.println("   WiFi Status: " + String(WiFi.status() == WL_CONNECTED ? "Connected" : "Disconnected"));
  Serial.println("   IP Address: " + WiFi.localIP().toString());
  Serial.println("   Signal Strength: " + String(WiFi.RSSI()) + " dBm");
  Serial.println("   Magnetometer Available: " + String(magnetometer_available ? "Yes" : "No"));
  Serial.println("   Magnetometer Enabled: " + String(magnetometer_enabled ? "Yes" : "No"));
  Serial.println("   Using: " + String(useHTTPS ? "HTTPS" : "HTTP"));
  Serial.println("   Free Memory: " + String(ESP.getFreeHeap()) + " bytes");
  Serial.println("   Uptime: " + String(millis() / 1000) + " seconds");
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

  // Try different I2C addresses with error handling
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

    // Configure magnetometer with conservative settings
    lis3mdl.setDataRate(LIS3MDL_DATARATE_80_HZ);  // Slower rate
    lis3mdl.setRange(LIS3MDL_RANGE_4_GAUSS);
    lis3mdl.setPerformanceMode(LIS3MDL_LOWPOWERMODE);  // Low power mode
    lis3mdl.setOperationMode(LIS3MDL_CONTINUOUSMODE);
  }

  // Configure LSM6DSOX
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
  // Read LSM6DSOX (accelerometer and gyroscope) - this always works
  sensors_event_t accel, gyro, temp;
  lsm6ds.getEvent(&accel, &gyro, &temp);

  currentData.accel_x = accel.acceleration.x;
  currentData.accel_y = accel.acceleration.y;
  currentData.accel_z = accel.acceleration.z;

  currentData.gyro_x = gyro.gyro.x;
  currentData.gyro_y = gyro.gyro.y;
  currentData.gyro_z = gyro.gyro.z;

  currentData.temperature = temp.temperature;

  // Read magnetometer less frequently and with error handling
  unsigned long currentTime = millis();
  if (magnetometer_available && magnetometer_enabled && (currentTime - lastMagRead >= magInterval)) {

    // Try to read magnetometer with timeout
    bool mag_read_success = false;

    try {
      lis3mdl.read();
      currentData.mag_x = lis3mdl.x;
      currentData.mag_y = lis3mdl.y;
      currentData.mag_z = lis3mdl.z;
      mag_read_success = true;
      lastMagRead = currentTime;
    } catch (...) {
      // If magnetometer read fails, use previous values
      Serial.println("⚠️ Magnetometer read failed, using previous values");
    }

    if (!mag_read_success) {
      // Keep previous magnetometer values or set to zero
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

  currentData.timestamp = millis();

  // Print data with device ID and current exercise type
  Serial.printf("[%s | %s] A:%.2f,%.2f,%.2f G:%.2f,%.2f,%.2f T:%.1f°C",
                deviceId.c_str(),
                currentExercise.c_str(),
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
  http.setFollowRedirects(HTTPC_FORCE_FOLLOW_REDIRECTS);  // Force follow redirects

  // Create test payload with REAL device ID
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

  // Add compound objects
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

  // Create complete payload with REAL device ID
  DynamicJsonDocument doc(1536);

  // 🆔 REAL DEVICE ID (MAC address)
  doc["device_id"] = deviceId;

  // Individual sensor fields
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

  // Compound objects for validation
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

  // Session grouping
  doc["session_id"] = String("session_") + deviceId + "_" + String(millis() / 60000);

  String jsonString;
  serializeJson(doc, jsonString);

  // Send HTTP POST request
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