from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.orm import Session
from typing import Dict, Any
import json
import logging

from ..database import get_db
from ..websocket.manager import websocket_manager
from ..models.database import WorkoutSession
from ..ml.workout_manager import WorkoutManager

router = APIRouter()
logger = logging.getLogger(__name__)

# Global instances
workout_manager = WorkoutManager()


@router.websocket("/ws/{device_id}")
async def websocket_endpoint(websocket: WebSocket, device_id: str):
    """WebSocket endpoint for real-time communication with fitness devices"""
    # Extract client type from query params if available
    client_info = {
        "user_agent": websocket.headers.get("user-agent", "unknown"),
        "origin": websocket.headers.get("origin", "unknown"),
        "client_type": "esp32" if "ESP32" in websocket.headers.get("user-agent", "") else "frontend"
    }
    
    await websocket_manager.connect(websocket, device_id, client_info)
    logger.info(f"WebSocket connected for device: {device_id} (client: {client_info['client_type']})")
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Handle different message types
            await handle_websocket_message(device_id, message)
            
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket)
        logger.info(f"WebSocket disconnected for device: {device_id}")
    except Exception as e:
        logger.error(f"WebSocket error for device {device_id}: {str(e)}")
        websocket_manager.disconnect(websocket)


async def handle_websocket_message(device_id: str, message: Dict[str, Any]):
    """Handle incoming WebSocket messages"""
    message_type = message.get("type")
    
    try:
        if message_type == "ping":
            # Respond to ping with pong
            await websocket_manager.send_to_device(
                device_id,
                {"type": "pong", "timestamp": message.get("timestamp")}
            )
            
        elif message_type == "start_detection":
            # Start rep detection for the device
            exercise_type = message.get("exercise_type", "unknown")
            await workout_manager.start_detection(device_id, exercise_type)
            
            await websocket_manager.send_to_device(
                device_id,
                {
                    "type": "detection_started",
                    "exercise_type": exercise_type,
                    "message": "Rep detection started"
                }
            )
            
        elif message_type == "stop_detection":
            # Stop rep detection for the device
            await workout_manager.stop_detection(device_id)
            
            await websocket_manager.send_to_device(
                device_id,
                {
                    "type": "detection_stopped",
                    "message": "Rep detection stopped"
                }
            )
            
        elif message_type == "get_status":
            # Send current workout status
            status = await get_device_status(device_id)
            await websocket_manager.send_to_device(device_id, status)
            
        elif message_type == "calibrate":
            # Calibrate rep detection
            await workout_manager.calibrate_detection(device_id)
            
            await websocket_manager.send_to_device(
                device_id,
                {
                    "type": "calibration_complete",
                    "message": "Rep detection calibrated"
                }
            )
            
        else:
            logger.warning(f"Unknown message type: {message_type} from device: {device_id}")
            
    except Exception as e:
        logger.error(f"Error handling message type {message_type} for device {device_id}: {str(e)}")
        await websocket_manager.send_to_device(
            device_id,
            {
                "type": "error",
                "message": f"Error processing {message_type}: {str(e)}"
            }
        )


async def get_device_status(device_id: str) -> Dict[str, Any]:
    """Get current status for a device"""
    # This would typically use a database session, but for WebSocket context
    # we'll keep it simple and use the workout manager
    try:
        is_detecting = workout_manager.is_detection_active(device_id)
        latest_detection = await workout_manager.get_latest_detection(device_id)
        
        return {
            "type": "status_update",
            "device_id": device_id,
            "detection_active": is_detecting,
            "latest_detection": latest_detection,
            "connected_devices": len(websocket_manager.active_connections),
            "timestamp": "utcnow"
        }
    except Exception as e:
        logger.error(f"Error getting status for device {device_id}: {str(e)}")
        return {
            "type": "status_error",
            "device_id": device_id,
            "error": str(e)
        }


# Utility functions for broadcasting workout events
async def broadcast_rep_completed(device_id: str, rep_data: Dict[str, Any]):
    """Broadcast rep completion event"""
    message = {
        "type": "rep_completed",
        "device_id": device_id,
        "data": rep_data,
        "timestamp": "utcnow"
    }
    await websocket_manager.broadcast_to_device(device_id, message)


async def broadcast_set_completed(device_id: str, set_data: Dict[str, Any]):
    """Broadcast set completion event"""
    message = {
        "type": "set_completed",
        "device_id": device_id,
        "data": set_data,
        "timestamp": "utcnow"
    }
    await websocket_manager.broadcast_to_device(device_id, message)


async def broadcast_workout_completed(device_id: str, workout_data: Dict[str, Any]):
    """Broadcast workout completion event"""
    message = {
        "type": "workout_completed",
        "device_id": device_id,
        "data": workout_data,
        "timestamp": "utcnow"
    }
    await websocket_manager.broadcast_to_device(device_id, message)


async def broadcast_form_warning(device_id: str, warning_data: Dict[str, Any]):
    """Broadcast form warning event"""
    message = {
        "type": "form_warning",
        "device_id": device_id,
        "data": warning_data,
        "timestamp": "utcnow"
    }
    await websocket_manager.broadcast_to_device(device_id, message)


# Export broadcast functions for use in other modules
__all__ = [
    "router",
    "broadcast_rep_completed",
    "broadcast_set_completed", 
    "broadcast_workout_completed",
    "broadcast_form_warning"
]
