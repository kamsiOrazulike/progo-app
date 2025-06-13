# ESP32 Command System Implementation

This document explains the ESP32 command system that has been added to the Progo ML backend.

## Overview

The command system allows the frontend to send commands to ESP32 devices via WebSocket relay. Commands are sent through HTTP API endpoints and relayed to ESP32 devices through WebSocket connections.

## Architecture

```
Frontend → HTTP POST → Backend API → WebSocket Manager → ESP32 Device
```

## New API Endpoints

### 1. Send Command to Device
```http
POST /api/v1/sensor-data/devices/{device_id}/command
```

**Request Body:**
```json
{
    "command": "bicep",
    "timestamp": "2024-01-01T12:00:00Z"
}
```

**Response:**
```json
{
    "success": true,
    "message": "Command 'bicep' sent to device AA:BB:CC:DD:EE:FF",
    "device_id": "AA:BB:CC:DD:EE:FF",
    "command": "bicep",
    "timestamp": "2024-01-01T12:00:00Z"
}
```

### 2. Check WebSocket Status
```http
GET /api/v1/sensor-data/devices/{device_id}/websocket-status
```

**Response:**
```json
{
    "device_id": "AA:BB:CC:DD:EE:FF",
    "is_connected": true,
    "connection_count": 1,
    "queued_messages": 0,
    "global_stats": {
        "total_connections": 2,
        "connected_devices": 1,
        "device_connections": {
            "AA:BB:CC:DD:EE:FF": 1
        }
    },
    "timestamp": "2024-01-01T12:00:00Z"
}
```

## Valid Commands

The system supports these ESP32 commands:
- `bicep` - Start bicep curl data collection
- `squat` - Start squat data collection  
- `rest` - Stop exercise data collection
- `train_complete` - Signal training completion
- `test` - Test API connection
- `info` - Show device information
- `mag_off` - Disable magnetometer
- `mag_on` - Enable magnetometer

## WebSocket Message Format

Commands sent to ESP32 devices use this JSON structure:
```json
{
    "type": "device_command",
    "command": "bicep",
    "timestamp": "2024-01-01T12:00:00Z"
}
```

## Implementation Details

### 1. Pydantic Models (`app/models/schemas.py`)

```python
class CommandRequest(BaseModel):
    command: str = Field(..., description="Command to send to ESP32 device")
    timestamp: Optional[datetime] = None

class CommandResponse(BaseModel):
    success: bool
    message: str
    device_id: str
    command: str
    timestamp: datetime
```

### 2. WebSocket Manager Enhancement (`app/websocket/manager.py`)

```python
async def send_command_to_device(self, device_id: str, command_data: dict) -> bool:
    """Send command to specific ESP32 device if connected via WebSocket."""
    # Prepare command message in the required format
    command_message = {
        "type": "device_command",
        "command": command_data.get("command"),
        "timestamp": command_data.get("timestamp", datetime.now().isoformat())
    }
    
    # Send to device or queue if offline
    if device_id in self.active_connections:
        await self.send_to_device(device_id, command_message)
        return True
    else:
        self.message_queue[device_id].append(command_message)
        return False
```

### 3. API Endpoint (`app/routers/sensor_data.py`)

```python
@router.post("/devices/{device_id}/command", response_model=CommandResponse)
async def send_device_command(device_id: str, command: CommandRequest):
    """Send command to ESP32 device via WebSocket."""
    # Validate MAC address format
    # Validate command
    # Send via WebSocket manager
    # Return response
```

## Usage Examples

### Frontend JavaScript Example
```javascript
// Send bicep curl command
const response = await fetch('/api/v1/sensor-data/devices/AA:BB:CC:DD:EE:FF/command', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        command: 'bicep',
        timestamp: new Date().toISOString()
    })
});

const result = await response.json();
console.log('Command sent:', result);
```

### ESP32 WebSocket Client Example
```cpp
// ESP32 would connect to WebSocket endpoint
// ws://your-backend.com/ws/AA:BB:CC:DD:EE:FF

// Listen for incoming commands
void onWebSocketMessage(String message) {
    JsonDocument doc;
    deserializeJson(doc, message);
    
    if (doc["type"] == "device_command") {
        String command = doc["command"];
        
        if (command == "bicep") {
            currentExercise = "bicep_curl";
            Serial.println("Command received: Start bicep curl mode");
        }
        // Handle other commands...
    }
}
```

## Error Handling

### Invalid Device ID
```json
{
    "detail": "Invalid device_id format. Expected MAC address format, got: invalid-id"
}
```

### Invalid Command
```json
{
    "detail": "Invalid command. Valid commands are: bicep, squat, rest, train_complete, test, info, mag_off, mag_on"
}
```

### Device Offline
```json
{
    "success": false,
    "message": "Command 'bicep' queued for device AA:BB:CC:DD:EE:FF",
    "device_id": "AA:BB:CC:DD:EE:FF",
    "command": "bicep",
    "timestamp": "2024-01-01T12:00:00Z"
}
```

## Testing

Use the provided test script:
```bash
cd /Users/kams/Documents/workspace/progo-app/Progo-BE
python3 test_command_system.py
```

This will test:
- Valid command sending
- Invalid device ID handling
- Invalid command handling
- All supported commands
- API documentation integration

## Security Considerations

- Device ID validation (MAC address format)
- Command validation (whitelist approach)
- WebSocket connection management
- Message queuing for offline devices
- Proper error handling and logging

## Future Enhancements

1. **Authentication**: Add device authentication for WebSocket connections
2. **Command History**: Store command history in database
3. **Command Acknowledgments**: ESP32 confirms command receipt
4. **Batch Commands**: Send multiple commands at once
5. **Scheduled Commands**: Queue commands for future execution
