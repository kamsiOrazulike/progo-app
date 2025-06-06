import json
import logging
from typing import Dict, List, Set, Optional, Any
from fastapi import WebSocket, WebSocketDisconnect
from datetime import datetime
import asyncio
from collections import defaultdict

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    WebSocket connection manager for real-time workout communication.
    Manages multiple connections per device and broadcasts workout updates.
    """
    
    def __init__(self):
        # Device ID -> Set of WebSocket connections
        self.active_connections: Dict[str, Set[WebSocket]] = defaultdict(set)
        # Track connection metadata
        self.connection_metadata: Dict[WebSocket, Dict[str, Any]] = {}
        # Message queue for offline devices
        self.message_queue: Dict[str, List[Dict]] = defaultdict(list)
        
    async def connect(self, websocket: WebSocket, device_id: str, client_info: Optional[Dict] = None):
        """Connect a WebSocket for a specific device."""
        await websocket.accept()
        
        self.active_connections[device_id].add(websocket)
        self.connection_metadata[websocket] = {
            "device_id": device_id,
            "connected_at": datetime.now(),
            "client_info": client_info or {}
        }
        
        logger.info(f"WebSocket connected for device {device_id}. Total connections: {len(self.active_connections[device_id])}")
        
        # Send any queued messages
        if device_id in self.message_queue:
            for message in self.message_queue[device_id]:
                await self.send_to_device(device_id, message, websocket)
            del self.message_queue[device_id]
    
    def disconnect(self, device_id_or_websocket):
        """Disconnect a WebSocket or all connections for a device."""
        if isinstance(device_id_or_websocket, str):
            # Disconnect all connections for a device
            device_id = device_id_or_websocket
            if device_id in self.active_connections:
                connections_to_close = list(self.active_connections[device_id])
                for websocket in connections_to_close:
                    try:
                        # Remove from metadata
                        if websocket in self.connection_metadata:
                            del self.connection_metadata[websocket]
                    except Exception as e:
                        logger.error(f"Error cleaning up websocket metadata: {e}")
                
                # Clear all connections for device
                del self.active_connections[device_id]
                logger.info(f"Disconnected all connections for device {device_id}")
        else:
            # Original method for disconnecting specific WebSocket
            websocket = device_id_or_websocket
            if websocket in self.connection_metadata:
                device_id = self.connection_metadata[websocket]["device_id"]
                
                # Remove from active connections
                self.active_connections[device_id].discard(websocket)
                
                # Clean up empty device entries
                if not self.active_connections[device_id]:
                    del self.active_connections[device_id]
                
                # Clean up metadata
                del self.connection_metadata[websocket]
                logger.info(f"WebSocket disconnected for device {device_id}")

    
    async def send_to_device(self, device_id: str, message: Dict, specific_websocket: Optional[WebSocket] = None):
        """Send message to all connections for a device or a specific connection."""
        message_text = json.dumps(message)
        
        if specific_websocket:
            # Send to specific WebSocket
            try:
                await specific_websocket.send_text(message_text)
            except Exception as e:
                logger.error(f"Error sending to specific WebSocket: {e}")
                await self.disconnect(specific_websocket)
        else:
            # Send to all connections for device
            if device_id in self.active_connections:
                disconnected_websockets = []
                
                for websocket in self.active_connections[device_id].copy():
                    try:
                        await websocket.send_text(message_text)
                    except Exception as e:
                        logger.error(f"Error sending to WebSocket: {e}")
                        disconnected_websockets.append(websocket)
                
                # Clean up disconnected WebSockets
                for websocket in disconnected_websockets:
                    await self.disconnect(websocket)
            else:
                # Queue message for when device connects
                self.message_queue[device_id].append(message)
                # Keep only last 50 messages to prevent memory issues
                if len(self.message_queue[device_id]) > 50:
                    self.message_queue[device_id] = self.message_queue[device_id][-50:]
    
    async def broadcast_rep_completed(self, device_id: str, rep_data: Dict):
        """Broadcast rep completion event."""
        message = {
            "type": "rep_completed",
            "data": {
                **rep_data,
                "timestamp": datetime.now().isoformat()
            }
        }
        await self.send_to_device(device_id, message)
        logger.debug(f"Broadcasted rep completion for device {device_id}: rep {rep_data.get('rep_number')}")
    
    async def broadcast_set_completed(self, device_id: str, set_data: Dict):
        """Broadcast set completion event."""
        message = {
            "type": "set_completed",
            "data": {
                **set_data,
                "timestamp": datetime.now().isoformat()
            }
        }
        await self.send_to_device(device_id, message)
        logger.info(f"Broadcasted set completion for device {device_id}: set {set_data.get('set_number')}")
    
    async def broadcast_workout_completed(self, device_id: str, workout_data: Dict):
        """Broadcast workout completion event."""
        message = {
            "type": "workout_completed",
            "data": {
                **workout_data,
                "timestamp": datetime.now().isoformat()
            }
        }
        await self.send_to_device(device_id, message)
        logger.info(f"Broadcasted workout completion for device {device_id}")
    
    async def broadcast_form_warning(self, device_id: str, warning_data: Dict):
        """Broadcast form quality warning."""
        message = {
            "type": "form_warning",
            "data": {
                **warning_data,
                "timestamp": datetime.now().isoformat()
            }
        }
        await self.send_to_device(device_id, message)
        logger.debug(f"Broadcasted form warning for device {device_id}")
    
    async def broadcast_workout_status(self, device_id: str, status_data: Dict):
        """Broadcast general workout status update."""
        message = {
            "type": "workout_status",
            "data": {
                **status_data,
                "timestamp": datetime.now().isoformat()
            }
        }
        await self.send_to_device(device_id, message)
    
    async def broadcast_to_device(self, device_id: str, message: Dict):
        """Broadcast message to all connections for a device (alias for send_to_device)."""
        await self.send_to_device(device_id, message)
    
    async def send_personal_message(self, device_id: str, message: Dict):
        """Send personal message to a device (alias for send_to_device)."""
        await self.send_to_device(device_id, message)
    
    def get_connection_count(self, device_id: str) -> int:
        """Get number of active connections for a device."""
        return len(self.active_connections.get(device_id, set()))
    
    def get_all_connected_devices(self) -> List[str]:
        """Get list of all devices with active connections."""
        return list(self.active_connections.keys())
    
    def get_connection_stats(self) -> Dict:
        """Get connection statistics."""
        total_connections = sum(len(connections) for connections in self.active_connections.values())
        return {
            "total_connections": total_connections,
            "connected_devices": len(self.active_connections),
            "device_connections": {
                device_id: len(connections) 
                for device_id, connections in self.active_connections.items()
            },
            "queued_messages": {
                device_id: len(messages)
                for device_id, messages in self.message_queue.items()
            }
        }


# Global WebSocket manager instance
websocket_manager = ConnectionManager()