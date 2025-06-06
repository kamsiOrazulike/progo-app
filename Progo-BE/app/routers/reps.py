from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from datetime import datetime, timedelta

from ..database import get_db
from ..models.database import RepPattern, RepEvent, WorkoutSession
from ..models.schemas import (
    RepPatternResponse, RepDetectionRequest, RepDetectionResponse,
    RepValidationRequest, RepValidationResponse, ExerciseType,
    RepEventType, APIResponse
)
from ..ml.rep_detection import (
    MotionCycleAnalyzer, MLConfidenceTracker, 
    PersonalizedTimingValidator, RepStateMachine
)
from ..ml.workout_manager import WorkoutManager

router = APIRouter(prefix="/reps", tags=["rep-detection"])

# Global instances that don't require initialization parameters
motion_analyzer = MotionCycleAnalyzer()  
ml_tracker = MLConfidenceTracker()
rep_state_machine = RepStateMachine()
workout_manager = WorkoutManager()

# Helper function to create timing validator instances
def create_timing_validator(device_id: str, exercise_type: str) -> PersonalizedTimingValidator:
    """Create a PersonalizedTimingValidator instance for the given device and exercise."""
    return PersonalizedTimingValidator(device_id, exercise_type)


@router.get("/{device_id}/patterns", response_model=List[RepPatternResponse])
async def get_rep_patterns(device_id: str, db: AsyncSession = Depends(get_db)):
    """Get learned rep patterns for a device"""
    result = await db.execute(
        select(RepPattern).where(RepPattern.device_id == device_id)
        .order_by(RepPattern.last_updated.desc())
    )
    patterns = result.scalars().all()
    
    return patterns


@router.get("/{device_id}/patterns/{exercise_type}", response_model=Optional[RepPatternResponse])
async def get_rep_pattern(
    device_id: str, 
    exercise_type: ExerciseType, 
    db: AsyncSession = Depends(get_db)
):
    """Get rep pattern for specific exercise type"""
    result = await db.execute(
        select(RepPattern).where(
            RepPattern.device_id == device_id,
            RepPattern.exercise_type == exercise_type.value
        )
    )
    pattern = result.scalar_one_or_none()
    
    return pattern


@router.post("/validate", response_model=RepValidationResponse)
async def validate_rep(
    validation_request: RepValidationRequest,
    db: AsyncSession = Depends(get_db)
):
    """Validate if sensor data represents a valid rep"""
    try:
        # Get rep pattern for personalized validation
        result = await db.execute(
            select(RepPattern).where(
                RepPattern.device_id == validation_request.device_id,
                RepPattern.exercise_type == validation_request.expected_exercise.value
            )
        )
        pattern = result.scalar_one_or_none()
        
        # Extract sensor data
        sensor_data = []
        for data_point in validation_request.rep_data:
            sensor_data.append({
                'accel_x': data_point.accelerometer.x,
                'accel_y': data_point.accelerometer.y,
                'accel_z': data_point.accelerometer.z,
                'gyro_x': data_point.gyroscope.x,
                'gyro_y': data_point.gyroscope.y,
                'gyro_z': data_point.gyroscope.z,
                'timestamp': data_point.timestamp or int(datetime.utcnow().timestamp() * 1000)
            })
        
        # Motion cycle analysis
        motion_confidence = motion_analyzer.analyze_motion_cycle(sensor_data)
        
        # ML confidence analysis
        ml_confidence = ml_tracker.analyze_confidence_cycle(sensor_data)
        
        # Timing validation if pattern exists
        timing_confidence = 1.0
        if pattern:
            timing_validator = create_timing_validator(validation_request.device_id, validation_request.expected_exercise)
            rep_duration = sensor_data[-1]['timestamp'] - sensor_data[0]['timestamp']
            timing_confidence = timing_validator.validate_timing(
                validation_request.device_id,
                validation_request.expected_exercise,
                rep_duration
            )
        
        # Combine confidences
        overall_confidence = (motion_confidence + ml_confidence + timing_confidence) / 3
        
        # Determine if valid rep
        is_valid = overall_confidence >= 0.6
        
        # Generate form score and suggestions
        form_score = min(overall_confidence * 1.2, 1.0)  # Boost slightly for form score
        suggestions = []
        
        if motion_confidence < 0.5:
            suggestions.append("Improve movement consistency and range of motion")
        if ml_confidence < 0.5:
            suggestions.append("Check exercise form - movement pattern not recognized")
        if timing_confidence < 0.5:
            suggestions.append("Adjust rep timing - too fast or too slow compared to your usual pace")
        
        return RepValidationResponse(
            is_valid_rep=is_valid,
            confidence=overall_confidence,
            detected_exercise=validation_request.expected_exercise,
            form_score=form_score,
            suggestions=suggestions if suggestions else None
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Rep validation failed: {str(e)}"
        )


@router.post("/detect/{device_id}", response_model=RepDetectionResponse)
async def detect_rep_realtime(
    device_id: str,
    detection_request: RepDetectionRequest,
    db: AsyncSession = Depends(get_db)
):
    """Real-time rep detection for a device"""
    try:
        # Check if there's an active workout
        result = await db.execute(
            select(WorkoutSession).where(
                WorkoutSession.device_id == device_id,
                WorkoutSession.status == "active"
            )
        )
        active_workout = result.scalar_one_or_none()
        
        if not active_workout:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No active workout session found for this device"
            )
        
        # Get the latest detection result from workout manager
        detection_result = await workout_manager.get_latest_detection(device_id)
        
        if not detection_result:
            return RepDetectionResponse(
                device_id=device_id,
                rep_detected=False,
                confidence=0.0,
                event_type=RepEventType.REP_COMPLETED,
                duration_ms=None,
                metadata={},
                timestamp=datetime.utcnow()
            )
        
        return RepDetectionResponse(
            device_id=device_id,
            rep_detected=detection_result['rep_detected'],
            confidence=detection_result['confidence'],
            event_type=RepEventType(detection_result['event_type']),
            duration_ms=detection_result.get('duration_ms'),
            metadata=detection_result.get('metadata', {}),
            timestamp=datetime.utcnow()
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Rep detection failed: {str(e)}"
        )


@router.post("/{device_id}/calibrate", response_model=APIResponse)
async def calibrate_rep_detection(device_id: str, db: AsyncSession = Depends(get_db)):
    """Calibrate rep detection for a device"""
    try:
        # Reset rep patterns to trigger recalibration
        result = await db.execute(
            select(RepPattern).where(RepPattern.device_id == device_id)
        )
        patterns = result.scalars().all()
        
        for pattern in patterns:
            pattern.rep_count = 0  # Reset count to trigger recalibration
            pattern.last_updated = datetime.utcnow()
        
        await db.commit()
        
        # Reset state machine
        rep_state_machine.reset_state(device_id)
        
        return APIResponse(
            success=True,
            message="Rep detection calibration reset successfully"
        )
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Calibration failed: {str(e)}"
        )


@router.get("/{device_id}/detection-status")
async def get_detection_status(device_id: str, db: AsyncSession = Depends(get_db)):
    """Get current rep detection status for a device"""
    try:
        # Check active workout
        active_workout = (
            db.query(WorkoutSession)
            .filter(
                WorkoutSession.device_id == device_id,
                WorkoutSession.status == "active"
            )
            .first()
        )
        
        # Get rep patterns
        patterns = (
            db.query(RepPattern)
            .filter(RepPattern.device_id == device_id)
            .all()
        )
        
        # Get recent rep events (last 10 minutes)
        recent_events = (
            db.query(RepEvent)
            .join(WorkoutSession)
            .filter(
                WorkoutSession.device_id == device_id,
                RepEvent.timestamp >= datetime.utcnow() - timedelta(minutes=10)
            )
            .order_by(RepEvent.timestamp.desc())
            .limit(10)
            .all()
        )
        
        return {
            "device_id": device_id,
            "has_active_workout": active_workout is not None,
            "active_workout_id": active_workout.id if active_workout else None,
            "exercise_type": active_workout.exercise_type if active_workout else None,
            "patterns_learned": len(patterns),
            "recent_detections": len(recent_events),
            "last_detection": recent_events[0].timestamp if recent_events else None,
            "detection_active": workout_manager.is_detection_active(device_id)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get detection status: {str(e)}"
        )


@router.delete("/{device_id}/patterns", response_model=APIResponse)
async def clear_rep_patterns(device_id: str, db: AsyncSession = Depends(get_db)):
    """Clear all learned rep patterns for a device"""
    try:
        result = await db.execute(
            select(RepPattern).where(RepPattern.device_id == device_id)
        )
        patterns = result.scalars().all()
        
        for pattern in patterns:
            await db.delete(pattern)
        
        await db.commit()
        
        # Reset timing validator cache
        # Note: Since timing_validator is created per request, we don't need to clear global cache
        # The patterns are cleared from the database above
        
        return APIResponse(
            success=True,
            message=f"Cleared {len(patterns)} rep patterns for device {device_id}"
        )
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear patterns: {str(e)}"
        )
