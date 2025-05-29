//This is my Arduino Sketch code for the ESP32 S3 - IMU data collection.
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <Wire.h>
#include <Adafruit_LSM6DSOX.h>
#include <Adafruit_LIS3MDL.h>
#include <Adafruit_Sensor.h>

// WiFi credentials for hotspot
const char* ssid = "Kamsi";          
const char* password = "nopassword"; 

// API endpoint - update this with your deployed API URL
const char* apiEndpoint = "https://your-api-endpoint.com/api/imu-data";

// Sensor objects
Adafruit_LSM6DSOX lsm6ds;
Adafruit_LIS3MDL lis3mdl;
bool magnetometer_available = false;  // Track if magnetometer is working

// Data collection timing
unsigned long lastSensorRead = 0;
const unsigned long sensorInterval = 100;  // Read sensors every 100ms (10Hz)

unsigned long lastDataSend = 0;
const unsigned long sendInterval = 1000;  // Send data every 1000ms (1Hz)

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

  Serial.println("ESP32 S3 IMU Data Collection Starting...");

  // Initialize I2C
  Wire.begin();

  // Initialize sensors
  if (!initializeSensors()) {
    Serial.println("Failed to initialize sensors!");
    while (1) delay(100);
  }

  // Connect to WiFi
  connectToWiFi();

  Serial.println("Setup complete! Starting data collection...");
}

void loop() {
  unsigned long currentTime = millis();

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
      Serial.println("WiFi disconnected, attempting reconnection...");
      connectToWiFi();
    }
    lastDataSend = currentTime;
  }

  // Small delay to prevent overwhelming the system
  delay(10);
}

bool initializeSensors() {
  Serial.println("Initializing LSM6DSOX...");
  if (!lsm6ds.begin_I2C(0x6A)) {  // Explicitly specify I2C address
    Serial.println("Failed to find LSM6DSOX chip");
    return false;
  }
  Serial.println("LSM6DSOX initialized successfully!");

  // Add delay between sensor initializations
  delay(100);

  Serial.println("Initializing LIS3MDL...");
  // Try multiple initialization approaches
  bool lis3mdl_success = false;

  // Method 1: Try with explicit address
  Serial.println("  Trying with address 0x1E...");
  if (lis3mdl.begin_I2C(0x1E)) {
    lis3mdl_success = true;
    Serial.println("  Success with 0x1E!");
  }

  // Method 2: Try without specifying address (auto-detect)
  if (!lis3mdl_success) {
    Serial.println("  Trying auto-detect...");
    if (lis3mdl.begin_I2C()) {
      lis3mdl_success = true;
      Serial.println("  Success with auto-detect!");
    }
  }

  // Method 3: Try alternative address
  if (!lis3mdl_success) {
    Serial.println("  Trying with address 0x1C...");
    if (lis3mdl.begin_I2C(0x1C)) {
      lis3mdl_success = true;
      Serial.println("  Success with 0x1C!");
    }
  }

  if (!lis3mdl_success) {
    Serial.println("Failed to find LIS3MDL chip with all methods");
    Serial.println("Continuing with LSM6DSOX only (6-DOF instead of 9-DOF)");
    // Don't return false - continue with just the accelerometer/gyroscope
  } else {
    Serial.println("LIS3MDL initialized successfully!");
  }

  // Configure LSM6DSOX
  Serial.println("Configuring LSM6DSOX...");
  lsm6ds.setAccelRange(LSM6DS_ACCEL_RANGE_4_G);
  lsm6ds.setGyroRange(LSM6DS_GYRO_RANGE_500_DPS);
  lsm6ds.setAccelDataRate(LSM6DS_RATE_104_HZ);
  lsm6ds.setGyroDataRate(LSM6DS_RATE_104_HZ);
  Serial.println("LSM6DSOX configured!");

  // Configure LIS3MDL only if it was successfully initialized
  if (lis3mdl_success) {
    Serial.println("Configuring LIS3MDL...");
    lis3mdl.setDataRate(LIS3MDL_DATARATE_155_HZ);
    lis3mdl.setRange(LIS3MDL_RANGE_4_GAUSS);
    lis3mdl.setPerformanceMode(LIS3MDL_MEDIUMMODE);
    lis3mdl.setOperationMode(LIS3MDL_CONTINUOUSMODE);
    Serial.println("LIS3MDL configured!");
    magnetometer_available = true;
  }

  if (magnetometer_available) {
    Serial.println("All sensors initialized and configured successfully! (9-DOF)");
  } else {
    Serial.println("Accelerometer and Gyroscope ready! (6-DOF, no magnetometer)");
  }
  return true;
}

void connectToWiFi() {
  WiFi.begin(ssid, password);
  Serial.print("Connecting to WiFi");

  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 20) {
    delay(500);
    Serial.print(".");
    attempts++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println();
    Serial.println("WiFi connected!");
    Serial.print("IP address: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println();
    Serial.println("WiFi connection failed!");
  }
}

void readSensorData() {
  // Read LSM6DSOX (accelerometer and gyroscope)
  sensors_event_t accel, gyro, temp;
  lsm6ds.getEvent(&accel, &gyro, &temp);

  currentData.accel_x = accel.acceleration.x;
  currentData.accel_y = accel.acceleration.y;
  currentData.accel_z = accel.acceleration.z;

  currentData.gyro_x = gyro.gyro.x;
  currentData.gyro_y = gyro.gyro.y;
  currentData.gyro_z = gyro.gyro.z;

  currentData.temperature = temp.temperature;

  // Read LIS3MDL (magnetometer) only if available
  if (magnetometer_available) {
    lis3mdl.read();
    currentData.mag_x = lis3mdl.x;
    currentData.mag_y = lis3mdl.y;
    currentData.mag_z = lis3mdl.z;
  } else {
    // Set magnetometer values to 0 if not available
    currentData.mag_x = 0.0;
    currentData.mag_y = 0.0;
    currentData.mag_z = 0.0;
  }

  currentData.timestamp = millis();

  // Print data to Serial for debugging
  if (magnetometer_available) {
    Serial.printf("Accel: %.2f, %.2f, %.2f | Gyro: %.2f, %.2f, %.2f | Mag: %.2f, %.2f, %.2f | Temp: %.2f°C\n",
                  currentData.accel_x, currentData.accel_y, currentData.accel_z,
                  currentData.gyro_x, currentData.gyro_y, currentData.gyro_z,
                  currentData.mag_x, currentData.mag_y, currentData.mag_z,
                  currentData.temperature);
  } else {
    Serial.printf("Accel: %.2f, %.2f, %.2f | Gyro: %.2f, %.2f, %.2f | Temp: %.2f°C (no magnetometer)\n",
                  currentData.accel_x, currentData.accel_y, currentData.accel_z,
                  currentData.gyro_x, currentData.gyro_y, currentData.gyro_z,
                  currentData.temperature);
  }
}

void sendDataToAPI() {
  HTTPClient http;
  http.begin(apiEndpoint);
  http.addHeader("Content-Type", "application/json");

  // Create JSON payload
  DynamicJsonDocument doc(1024);
  doc["device_id"] = WiFi.macAddress();
  doc["timestamp"] = currentData.timestamp;
  doc["magnetometer_available"] = magnetometer_available;

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

  doc["temperature"] = currentData.temperature;

  String jsonString;
  serializeJson(doc, jsonString);

  // Send HTTP POST request
  int httpResponseCode = http.POST(jsonString);

  if (httpResponseCode > 0) {
    String response = http.getString();
    Serial.printf("HTTP Response: %d - %s\n", httpResponseCode, response.c_str());
  } else {
    Serial.printf("HTTP Error: %d\n", httpResponseCode);
  }

  http.end();
}

// Optional: Function to get calibrated sensor readings
void printSensorDetails() {
  Serial.println("LSM6DSOX Configuration:");
  Serial.printf("Accelerometer range: ±%d G\n", lsm6ds.getAccelRange());
  Serial.printf("Gyroscope range: ±%d DPS\n", lsm6ds.getGyroRange());

  Serial.println("LIS3MDL Configuration:");
  Serial.printf("Magnetometer range: ±%d Gauss\n", lis3mdl.getRange());
}