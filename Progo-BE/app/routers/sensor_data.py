from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, func
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import re

from app.database import get_sync_db
from app.models.schemas import (
    SensorDataInput, SensorDataResponse, SensorDataQuery, 
    APIResponse, PaginatedResponse, CommandRequest, CommandResponse
)
from app.models.database import SensorReading, ExerciseSession, DeviceInfo, WorkoutSession
from app.ml.inference import inference_engine
from app.ml.workout_manager import WorkoutManager
from app.websocket.manager import websocket_manager
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sensor-data", tags=["Sensor Data"])

# Global workout manager instance
workout_manager = WorkoutManager()


@router.post("/", response_model=APIResponse)
async def receive_sensor_data(
    sensor_data: SensorDataInput,
    session_id: Optional[int] = None,
    db: Session = Depends(get_sync_db)
):
    """
    Receive sensor data from ESP32 device.
    Optionally associate with an exercise session.
    """
    try:
        # Convert timestamp if provided
        timestamp = None
        if sensor_data.timestamp:
            timestamp = datetime.fromtimestamp(sensor_data.timestamp / 1000)
        
        # Create sensor reading record
        db_reading = SensorReading(
            device_id=sensor_data.device_id,
            timestamp=timestamp,
            accel_x=sensor_data.accelerometer.x,
            accel_y=sensor_data.accelerometer.y,
            accel_z=sensor_data.accelerometer.z,
            gyro_x=sensor_data.gyroscope.x,
            gyro_y=sensor_data.gyroscope.y,
            gyro_z=sensor_data.gyroscope.z,
            magnetometer_available=sensor_data.magnetometer_available,
            temperature=sensor_data.temperature,
            session_id=session_id
        )
        
        # Add magnetometer data if available
        if sensor_data.magnetometer_available and sensor_data.magnetometer:
            db_reading.mag_x = sensor_data.magnetometer.x
            db_reading.mag_y = sensor_data.magnetometer.y
            db_reading.mag_z = sensor_data.magnetometer.z
        
        db.add(db_reading)
        db.commit()
        db.refresh(db_reading)
        
        # Add to real-time inference buffer
        inference_engine.add_sensor_data(sensor_data.device_id, sensor_data)
        
        # Check for active workout and process rep detection
        active_workout = (
            db.query(WorkoutSession)
            .filter(
                WorkoutSession.device_id == sensor_data.device_id,
                WorkoutSession.status == "active"
            )
            .first()
        )
        
        if active_workout:
            # Process sensor data for rep detection
            await workout_manager.process_sensor_data(
                sensor_data.device_id, 
                sensor_data,
                active_workout.id
            )
        
        logger.debug(f"Received sensor data from {sensor_data.device_id}")
        
        return APIResponse(
            success=True,
            message="Sensor data received successfully",
            data={"id": db_reading.id, "timestamp": db_reading.timestamp}
        )
        
    except Exception as e:
        logger.error(f"Error receiving sensor data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch", response_model=APIResponse)
async def receive_sensor_data_batch(
    sensor_data_list: List[SensorDataInput],
    session_id: Optional[int] = None,
    db: Session = Depends(get_sync_db)
):
    """
    Receive multiple sensor data readings in a batch.
    More efficient for high-frequency data collection.
    """
    try:
        db_readings = []
        
        for sensor_data in sensor_data_list:
            # Convert timestamp if provided
            timestamp = None
            if sensor_data.timestamp:
                timestamp = datetime.fromtimestamp(sensor_data.timestamp / 1000)
            
            # Create sensor reading record
            db_reading = SensorReading(
                device_id=sensor_data.device_id,
                timestamp=timestamp,
                accel_x=sensor_data.accelerometer.x,
                accel_y=sensor_data.accelerometer.y,
                accel_z=sensor_data.accelerometer.z,
                gyro_x=sensor_data.gyroscope.x,
                gyro_y=sensor_data.gyroscope.y,
                gyro_z=sensor_data.gyroscope.z,
                magnetometer_available=sensor_data.magnetometer_available,
                temperature=sensor_data.temperature,
                session_id=session_id
            )
            
            # Add magnetometer data if available
            if sensor_data.magnetometer_available and sensor_data.magnetometer:
                db_reading.mag_x = sensor_data.magnetometer.x
                db_reading.mag_y = sensor_data.magnetometer.y
                db_reading.mag_z = sensor_data.magnetometer.z
            
            db_readings.append(db_reading)
            
            # Add to real-time inference buffer
            inference_engine.add_sensor_data(sensor_data.device_id, sensor_data)
        
        # Batch insert
        db.add_all(db_readings)
        db.commit()
        
        logger.info(f"Received {len(sensor_data_list)} sensor readings in batch")
        
        return APIResponse(
            success=True,
            message=f"Batch of {len(sensor_data_list)} sensor readings received successfully",
            data={"count": len(sensor_data_list)}
        )
        
    except Exception as e:
        logger.error(f"Error receiving sensor data batch: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=PaginatedResponse)
async def get_sensor_data(
    device_id: Optional[str] = Query(None, description="Filter by device ID"),
    session_id: Optional[int] = Query(None, description="Filter by session ID"),
    start_time: Optional[datetime] = Query(None, description="Filter from this timestamp"),
    end_time: Optional[datetime] = Query(None, description="Filter to this timestamp"),
    limit: int = Query(1000, le=10000, description="Maximum number of records"),
    offset: int = Query(0, ge=0, description="Number of records to skip"),
    db: Session = Depends(get_sync_db)
):
    """
    Query historical sensor data with filters.
    """
    try:
        # Build query
        query = db.query(SensorReading)
        
        # Apply filters
        if device_id:
            query = query.filter(SensorReading.device_id == device_id)
        if session_id:
            query = query.filter(SensorReading.session_id == session_id)
        if start_time:
            query = query.filter(SensorReading.timestamp >= start_time)
        if end_time:
            query = query.filter(SensorReading.timestamp <= end_time)
        
        # Get total count
        total = query.count()
        
        # Apply pagination and ordering
        readings = query.order_by(desc(SensorReading.timestamp)).offset(offset).limit(limit).all()
        
        # Convert to response models
        response_data = [SensorDataResponse.from_orm(reading) for reading in readings]
        
        return PaginatedResponse(
            items=response_data,
            total=total,
            page=offset // limit + 1,
            size=len(response_data),
            pages=(total + limit - 1) // limit
        )
        
    except Exception as e:
        logger.error(f"Error querying sensor data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/latest/{device_id}", response_model=List[SensorDataResponse])
async def get_latest_sensor_data(
    device_id: str,
    count: int = Query(100, le=1000, description="Number of latest readings"),
    db: Session = Depends(get_sync_db)
):
    """
    Get the latest sensor readings for a specific device.
    """
    try:
        readings = db.query(SensorReading).filter(
            SensorReading.device_id == device_id
        ).order_by(desc(SensorReading.timestamp)).limit(count).all()
        
        if not readings:
            raise HTTPException(status_code=404, detail="No sensor data found for device")
        
        return [SensorDataResponse.from_orm(reading) for reading in readings]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting latest sensor data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats/{device_id}")
async def get_sensor_data_stats(
    device_id: str,
    hours: int = Query(24, description="Number of hours to look back"),
    db: Session = Depends(get_sync_db)
):
    """
    Get statistics about sensor data for a device.
    """
    try:
        # Calculate time range
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)
        
        # Query sensor data in time range
        readings = db.query(SensorReading).filter(
            and_(
                SensorReading.device_id == device_id,
                SensorReading.timestamp >= start_time,
                SensorReading.timestamp <= end_time
            )
        ).all()
        
        if not readings:
            return {
                "device_id": device_id,
                "time_range_hours": hours,
                "total_readings": 0,
                "message": "No data found in time range"
            }
        
        # Calculate statistics
        total_readings = len(readings)
        
        # Time-based stats
        timestamps = [r.timestamp for r in readings]
        duration = (max(timestamps) - min(timestamps)).total_seconds()
        avg_sampling_rate = total_readings / duration if duration > 0 else 0
        
        # Magnetometer availability
        mag_available_count = sum(1 for r in readings if r.magnetometer_available)
        mag_availability_ratio = mag_available_count / total_readings if total_readings > 0 else 0
        
        # Temperature stats (if available)
        temp_readings = [r.temperature for r in readings if r.temperature is not None]
        temp_stats = None
        if temp_readings:
            temp_stats = {
                "min": min(temp_readings),
                "max": max(temp_readings),
                "avg": sum(temp_readings) / len(temp_readings),
                "readings_with_temp": len(temp_readings)
            }
        
        return {
            "device_id": device_id,
            "time_range_hours": hours,
            "total_readings": total_readings,
            "duration_seconds": duration,
            "average_sampling_rate_hz": avg_sampling_rate,
            "magnetometer_availability_ratio": mag_availability_ratio,
            "temperature_stats": temp_stats,
            "first_reading": min(timestamps),
            "last_reading": max(timestamps)
        }
        
    except Exception as e:
        logger.error(f"Error getting sensor data stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{device_id}")
async def delete_sensor_data(
    device_id: str,
    older_than_days: Optional[int] = Query(None, description="Delete data older than N days"),
    confirm: bool = Query(False, description="Confirmation required"),
    db: Session = Depends(get_sync_db)
):
    """
    Delete sensor data for a device.
    Use with caution - this operation cannot be undone.
    """
    if not confirm:
        raise HTTPException(
            status_code=400, 
            detail="Must set confirm=true to delete sensor data"
        )
    
    try:
        query = db.query(SensorReading).filter(SensorReading.device_id == device_id)
        
        if older_than_days:
            cutoff_date = datetime.now() - timedelta(days=older_than_days)
            query = query.filter(SensorReading.timestamp < cutoff_date)
        
        count = query.count()
        query.delete()
        db.commit()
        
        logger.warning(f"Deleted {count} sensor readings for device {device_id}")
        
        return APIResponse(
            success=True,
            message=f"Deleted {count} sensor readings",
            data={"deleted_count": count, "device_id": device_id}
        )
        
    except Exception as e:
        logger.error(f"Error deleting sensor data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/devices", response_model=List[Dict[str, Any]])
async def get_known_devices(db: Session = Depends(get_sync_db)):
    """Get list of all devices that have sent data."""
    try:
        result = db.query(
            SensorReading.device_id,
            func.count(SensorReading.id).label('reading_count'),
            func.max(SensorReading.timestamp).label('last_seen'),
            func.min(SensorReading.timestamp).label('first_seen')
        ).group_by(SensorReading.device_id).all()
        
        devices = []
        for device in result:
            # Check if device_id matches MAC address format (AA:BB:CC:DD:EE:FF)
            mac_pattern = r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$'
            is_esp32 = bool(re.match(mac_pattern, device.device_id))
            
            devices.append({
                "device_id": device.device_id,
                "reading_count": device.reading_count,
                "last_seen": device.last_seen,
                "first_seen": device.first_seen,
                "is_esp32": is_esp32,
                "device_type": "ESP32" if is_esp32 else "Unknown"
            })
        
        logger.info(f"Found {len(devices)} known devices")
        return devices
        
    except Exception as e:
        logger.error(f"Error getting known devices: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/devices/{device_id}/status")
async def get_device_status(
    device_id: str, 
    db: Session = Depends(get_sync_db)
):
    """Get current status and recent activity for a device."""
    try:
        # Recent readings (last 5 minutes)
        recent_cutoff = datetime.now() - timedelta(minutes=5)
        recent_readings = db.query(SensorReading).filter(
            SensorReading.device_id == device_id,
            SensorReading.timestamp >= recent_cutoff
        ).count()
        
        # Last reading
        last_reading = db.query(SensorReading).filter(
            SensorReading.device_id == device_id
        ).order_by(SensorReading.timestamp.desc()).first()
        
        # Total readings
        total_readings = db.query(SensorReading).filter(
            SensorReading.device_id == device_id
        ).count()
        
        # ML model buffer status
        buffer_status = inference_engine.get_buffer_status(device_id)
        
        # Check if device_id matches MAC address format
        mac_pattern = r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$'
        is_esp32 = bool(re.match(mac_pattern, device_id))
        
        return {
            "device_id": device_id,
            "device_type": "ESP32" if is_esp32 else "Unknown",
            "is_online": recent_readings > 0,
            "recent_readings_5min": recent_readings,
            "total_readings": total_readings,
            "last_reading": last_reading.timestamp if last_reading else None,
            "last_reading_data": {
                "accel_x": last_reading.accel_x,
                "accel_y": last_reading.accel_y,
                "accel_z": last_reading.accel_z,
                "temperature": last_reading.temperature
            } if last_reading else None,
            "ml_buffer_status": buffer_status,
            "ready_for_prediction": buffer_status.get('ready_for_prediction', False)
        }
        
    except Exception as e:
        logger.error(f"Error getting device status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/devices/register")
async def register_device(
    device_info: Dict[str, str],
    db: Session = Depends(get_sync_db)
):
    """Register a new device with optional metadata."""
    try:
        device_id = device_info.get("device_id")
        if not device_id:
            raise HTTPException(status_code=400, detail="device_id is required")
        
        # Check if device already exists
        existing_device = db.query(DeviceInfo).filter(DeviceInfo.device_id == device_id).first()
        if existing_device:
            raise HTTPException(status_code=400, detail="Device already registered")
        
        # Create device record
        device = DeviceInfo(
            device_id=device_id,
            device_name=device_info.get("device_name", f"ESP32-{device_id[-5:]}"),
            device_type=device_info.get("device_type", "ESP32"),
            notes=device_info.get("notes")
        )
        
        db.add(device)
        db.commit()
        db.refresh(device)
        
        logger.info(f"Registered new device: {device_id}")
        
        return APIResponse(
            success=True,
            message=f"Device {device.device_id} registered successfully",
            data={
                "device_id": device.device_id,
                "device_name": device.device_name,
                "device_type": device.device_type,
                "registered_at": device.registered_at
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error registering device: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/devices/registered")
async def get_registered_devices(db: Session = Depends(get_sync_db)):
    """Get list of all registered devices."""
    try:
        devices = db.query(DeviceInfo).filter(DeviceInfo.is_active == True).all()
        
        result = []
        for device in devices:
            # Get last sensor reading to update last_seen
            last_reading = db.query(SensorReading).filter(
                SensorReading.device_id == device.device_id
            ).order_by(SensorReading.timestamp.desc()).first()
            
            if last_reading and last_reading.timestamp != device.last_seen:
                device.last_seen = last_reading.timestamp
                db.commit()
            
            result.append({
                "device_id": device.device_id,
                "device_name": device.device_name,
                "device_type": device.device_type,
                "registered_at": device.registered_at,
                "last_seen": device.last_seen,
                "is_active": device.is_active,
                "notes": device.notes
            })
        
        return result
        
    except Exception as e:
        logger.error(f"Error getting registered devices: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/devices/{device_id}/command", response_model=CommandResponse)
async def send_device_command(
    device_id: str, 
    command: CommandRequest,
    db: Session = Depends(get_sync_db)
):
    """Send command to ESP32 device via WebSocket."""
    try:
        # Validate device_id format (MAC address pattern)
        mac_pattern = r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$'
        if not re.match(mac_pattern, device_id):
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid device_id format. Expected MAC address format, got: {device_id}"
            )
        
        # Validate command
        valid_commands = ["bicep", "squat", "rest", "train_complete", "test", "info", "mag_off", "mag_on"]
        if command.command not in valid_commands:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid command. Valid commands are: {', '.join(valid_commands)}"
            )
        
        # Prepare command data
        command_data = {
            "command": command.command,
            "timestamp": command.timestamp.isoformat() if command.timestamp else datetime.now().isoformat()
        }
        
        # Send command via WebSocket manager
        success = await websocket_manager.send_command_to_device(device_id, command_data)
        
        # Log the command attempt
        logger.info(f"Command '{command.command}' {'sent' if success else 'queued'} for device {device_id}")
        
        return CommandResponse(
            success=success,
            message=f"Command '{command.command}' {'sent to' if success else 'queued for'} device {device_id}",
            device_id=device_id,
            command=command.command,
            timestamp=datetime.now()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending command to device {device_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/devices/{device_id}/websocket-status")
async def get_websocket_status(device_id: str):
    """Get WebSocket connection status for a device."""
    try:
        # Validate device_id format (MAC address pattern)
        mac_pattern = r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$'
        if not re.match(mac_pattern, device_id):
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid device_id format. Expected MAC address format, got: {device_id}"
            )
        
        # Get connection status from WebSocket manager
        connection_count = websocket_manager.get_connection_count(device_id)
        is_connected = connection_count > 0
        
        # Get connection statistics
        stats = websocket_manager.get_connection_stats()
        
        return {
            "device_id": device_id,
            "is_connected": is_connected,
            "connection_count": connection_count,
            "queued_messages": len(websocket_manager.message_queue.get(device_id, [])),
            "global_stats": stats,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting WebSocket status for device {device_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
