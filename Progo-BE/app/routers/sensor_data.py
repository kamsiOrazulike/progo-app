from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_
from typing import List, Optional
from datetime import datetime, timedelta

from app.database import get_sync_db
from app.models.schemas import (
    SensorDataInput, SensorDataResponse, SensorDataQuery, 
    APIResponse, PaginatedResponse
)
from app.models.database import SensorReading, ExerciseSession
from app.ml.inference import inference_engine
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sensor-data", tags=["Sensor Data"])


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
