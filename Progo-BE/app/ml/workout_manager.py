import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.database import WorkoutSession, RepEvent, RepPattern, WorkoutStatus, RepEventType
from app.ml.rep_detection import RepDetectionEngine, RepCandidate
from app.websocket.manager import websocket_manager

logger = logging.getLogger(__name__)


class WorkoutManager:
    """
    Manages active workout sessions and coordinates rep detection with WebSocket updates.
    """
    
    def __init__(self):
        # Active workout sessions: device_id -> workout_session_id
        self.active_workouts: Dict[str, int] = {}
        
        # Rep detection engines: device_id -> RepDetectionEngine
        self.rep_engines: Dict[str, RepDetectionEngine] = {}
        
        # Session performance tracking
        self.session_stats: Dict[int, Dict[str, Any]] = {}
        
    def start_workout(self, db: Session, device_id: str, exercise_type: str, 
                     target_sets: int = 3, target_reps_per_set: int = 10,
                     notes: Optional[str] = None) -> WorkoutSession:
        """Start a new workout session."""
        
        # End any existing active workout for this device
        self.end_workout(db, device_id)
        
        # Create new workout session
        workout = WorkoutSession(
            device_id=device_id,
            exercise_type=exercise_type,
            target_sets=target_sets,
            target_reps_per_set=target_reps_per_set,
            status=WorkoutStatus.active,
            notes=notes
        )
        
        db.add(workout)
        db.commit()
        db.refresh(workout)
        
        # Track active workout
        self.active_workouts[device_id] = workout.id
        
        # Initialize rep detection engine
        rep_engine = RepDetectionEngine(device_id, exercise_type)
        rep_engine.load_patterns(db)
        self.rep_engines[device_id] = rep_engine
        
        # Initialize session stats
        self.session_stats[workout.id] = {
            "total_reps": 0,
            "sets_completed": 0,
            "avg_rep_duration": 0.0,
            "avg_confidence": 0.0,
            "form_warnings": 0,
            "rep_durations": []
        }
        
        logger.info(f"Started workout for device {device_id}: {exercise_type}")
        
        return workout
    
    def process_rep_detection(self, db: Session, device_id: str, sensor_data: Dict[str, float], 
                            ml_prediction: Optional[Dict] = None) -> Optional[RepEvent]:
        """Process sensor data for rep detection during active workout."""
        
        if device_id not in self.active_workouts:
            return None
            
        workout_id = self.active_workouts[device_id]
        workout = db.query(WorkoutSession).filter(WorkoutSession.id == workout_id).first()
        
        if not workout or workout.status != WorkoutStatus.active:
            return None
            
        # Get rep detection engine
        rep_engine = self.rep_engines.get(device_id)
        if not rep_engine:
            logger.warning(f"No rep detection engine for device {device_id}")
            return None
            
        # Process sensor data
        rep_candidate = rep_engine.process_sensor_data(
            sensor_data, 
            datetime.now(), 
            ml_prediction
        )
        
        if rep_candidate:
            return self._handle_rep_detected(db, workout, rep_candidate)
            
        return None
    
    def _handle_rep_detected(self, db: Session, workout: WorkoutSession, 
                           rep_candidate: RepCandidate) -> RepEvent:
        """Handle a detected rep and update workout progress."""
        
        # Create rep event
        rep_event = RepEvent(
            device_id=workout.device_id,
            workout_session_id=workout.id,
            rep_number=workout.current_reps + 1,
            set_number=workout.current_set,
            event_type=RepEventType.rep_completed,
            confidence_score=rep_candidate.confidence,
            motion_quality=rep_candidate.motion_quality,
            rep_duration=rep_candidate.duration,
            detection_method=rep_candidate.detection_method.value
        )
        
        db.add(rep_event)
        
        # Update workout progress
        workout.current_reps += 1
        
        # Update session stats
        stats = self.session_stats[workout.id]
        stats["total_reps"] += 1
        stats["rep_durations"].append(rep_candidate.duration)
        stats["avg_rep_duration"] = sum(stats["rep_durations"]) / len(stats["rep_durations"])
        stats["avg_confidence"] = (stats["avg_confidence"] * (stats["total_reps"] - 1) + rep_candidate.confidence) / stats["total_reps"]
        
        # Check for form warnings
        if rep_candidate.motion_quality < 0.6:
            stats["form_warnings"] += 1
            self._send_form_warning(workout.device_id, rep_candidate.motion_quality)
        
        # Check if set is completed
        set_completed = False
        workout_completed = False
        
        if workout.current_reps >= workout.target_reps_per_set:
            set_completed = True
            stats["sets_completed"] += 1
            
            # Create set completion event
            set_event = RepEvent(
                device_id=workout.device_id,
                workout_session_id=workout.id,
                rep_number=0,  # Not applicable for set events
                set_number=workout.current_set,
                event_type=RepEventType.set_completed,
                confidence_score=stats["avg_confidence"],
                motion_quality=rep_candidate.motion_quality
            )
            db.add(set_event)
            
            # Check if workout is completed
            if workout.current_set >= workout.target_sets:
                workout_completed = True
                workout.status = WorkoutStatus.completed
                workout.completed_at = datetime.now()
                
                # Clean up
                if workout.device_id in self.active_workouts:
                    del self.active_workouts[workout.device_id]
                if workout.device_id in self.rep_engines:
                    del self.rep_engines[workout.device_id]
                    
            else:
                # Move to next set
                workout.current_set += 1
                workout.current_reps = 0
        
        db.commit()
        db.refresh(rep_event)
        
        # Send WebSocket updates
        self._send_rep_completed(workout.device_id, rep_event, workout)
        
        if set_completed:
            self._send_set_completed(workout.device_id, workout, stats)
            
        if workout_completed:
            self._send_workout_completed(workout.device_id, workout, stats)
            # Update rep patterns based on workout data
            self._update_rep_patterns(db, workout)
        
        logger.info(f"Rep detected for {workout.device_id}: Set {workout.current_set}, Rep {rep_event.rep_number}")
        
        return rep_event
    
    def _send_rep_completed(self, device_id: str, rep_event: RepEvent, workout: WorkoutSession):
        """Send rep completion WebSocket message."""
        rep_data = {
            "rep_number": rep_event.rep_number,
            "set_number": rep_event.set_number,
            "confidence": rep_event.confidence_score,
            "rep_duration": rep_event.rep_duration,
            "form_quality": "excellent" if rep_event.motion_quality > 0.8 else "good" if rep_event.motion_quality > 0.6 else "needs_improvement",
            "motion_quality_score": rep_event.motion_quality,
            "detection_method": rep_event.detection_method,
            "workout_progress": {
                "current_set": workout.current_set,
                "current_reps": workout.current_reps,
                "target_sets": workout.target_sets,
                "target_reps_per_set": workout.target_reps_per_set
            }
        }
        
        asyncio.create_task(websocket_manager.broadcast_rep_completed(device_id, rep_data))
    
    def _send_set_completed(self, device_id: str, workout: WorkoutSession, stats: Dict):
        """Send set completion WebSocket message."""
        set_data = {
            "set_number": workout.current_set - 1,  # Previous set that was completed
            "total_reps": workout.target_reps_per_set,
            "set_duration": sum(stats["rep_durations"][-workout.target_reps_per_set:]) if len(stats["rep_durations"]) >= workout.target_reps_per_set else 0,
            "avg_rep_quality": stats["avg_confidence"],
            "workout_progress": {
                "sets_completed": stats["sets_completed"],
                "total_sets": workout.target_sets,
                "workout_completion_percentage": (stats["sets_completed"] / workout.target_sets) * 100
            }
        }
        
        asyncio.create_task(websocket_manager.broadcast_set_completed(device_id, set_data))
    
    def _send_workout_completed(self, device_id: str, workout: WorkoutSession, stats: Dict):
        """Send workout completion WebSocket message."""
        workout_duration = (workout.completed_at - workout.started_at).total_seconds()
        
        workout_data = {
            "total_sets": stats["sets_completed"],
            "total_reps": stats["total_reps"],
            "workout_duration": workout_duration,
            "avg_performance": stats["avg_confidence"],
            "avg_rep_duration": stats["avg_rep_duration"],
            "form_warnings": stats["form_warnings"],
            "exercise_type": workout.exercise_type,
            "started_at": workout.started_at.isoformat(),
            "completed_at": workout.completed_at.isoformat()
        }
        
        asyncio.create_task(websocket_manager.broadcast_workout_completed(device_id, workout_data))
    
    def _send_form_warning(self, device_id: str, motion_quality: float):
        """Send form quality warning."""
        warning_data = {
            "message": "Form quality below optimal - focus on controlled movement",
            "motion_quality_score": motion_quality,
            "suggestion": "Slow down and focus on proper form" if motion_quality < 0.4 else "Maintain steady tempo"
        }
        
        asyncio.create_task(websocket_manager.broadcast_form_warning(device_id, warning_data))
    
    def _update_rep_patterns(self, db: Session, workout: WorkoutSession):
        """Update learned rep patterns based on completed workout."""
        stats = self.session_stats.get(workout.id, {})
        rep_durations = stats.get("rep_durations", [])
        
        if len(rep_durations) < 3:  # Need minimum samples
            return
            
        # Get or create rep pattern
        pattern = db.query(RepPattern).filter(
            RepPattern.device_id == workout.device_id,
            RepPattern.exercise_type == workout.exercise_type
        ).first()
        
        if not pattern:
            pattern = RepPattern(
                device_id=workout.device_id,
                exercise_type=workout.exercise_type,
                avg_rep_duration=np.mean(rep_durations),
                min_rep_duration=np.min(rep_durations),
                max_rep_duration=np.max(rep_durations),
                avg_rest_between_reps=2.0,  # Default
                training_session_count=1,
                confidence_score=0.7
            )
            db.add(pattern)
        else:
            # Update existing pattern with weighted average
            old_weight = pattern.training_session_count / (pattern.training_session_count + 1)
            new_weight = 1 / (pattern.training_session_count + 1)
            
            pattern.avg_rep_duration = (pattern.avg_rep_duration * old_weight + 
                                      np.mean(rep_durations) * new_weight)
            pattern.min_rep_duration = min(pattern.min_rep_duration, np.min(rep_durations))
            pattern.max_rep_duration = max(pattern.max_rep_duration, np.max(rep_durations))
            pattern.training_session_count += 1
            pattern.confidence_score = min(0.95, pattern.confidence_score + 0.05)
            pattern.last_updated = datetime.now()
        
        db.commit()
        logger.info(f"Updated rep patterns for {workout.device_id}: {workout.exercise_type}")
    
    def end_workout(self, db: Session, device_id: str) -> Optional[WorkoutSession]:
        """End active workout for device."""
        if device_id not in self.active_workouts:
            return None
            
        workout_id = self.active_workouts[device_id]
        workout = db.query(WorkoutSession).filter(WorkoutSession.id == workout_id).first()
        
        if workout and workout.status == WorkoutStatus.active:
            workout.status = WorkoutStatus.completed
            workout.completed_at = datetime.now()
            db.commit()
            
            # Clean up
            del self.active_workouts[device_id]
            if device_id in self.rep_engines:
                del self.rep_engines[device_id]
            if workout.id in self.session_stats:
                del self.session_stats[workout.id]
                
            logger.info(f"Ended workout for device {device_id}")
            
            return workout
            
        return None
    
    def get_current_workout(self, db: Session, device_id: str) -> Optional[WorkoutSession]:
        """Get current active workout for device."""
        if device_id not in self.active_workouts:
            return None
            
        workout_id = self.active_workouts[device_id]
        return db.query(WorkoutSession).filter(WorkoutSession.id == workout_id).first()
    
    def get_workout_status(self, device_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed workout status."""
        if device_id not in self.active_workouts:
            return None
            
        workout_id = self.active_workouts[device_id]
        stats = self.session_stats.get(workout_id, {})
        
        rep_engine = self.rep_engines.get(device_id)
        rep_engine_status = rep_engine.get_status() if rep_engine else {}
        
        return {
            "workout_id": workout_id,
            "is_active": True,
            "stats": stats,
            "rep_detection_status": rep_engine_status,
            "websocket_connections": websocket_manager.get_connection_count(device_id)
        }
    
    def get_active_workouts(self) -> List[str]:
        """Get list of devices with active workouts."""
        return list(self.active_workouts.keys())

    async def start_workout(self, device_id: str, exercise_type: str, 
                           workout_session_id: int):
        """Start workout tracking for async router compatibility."""
        self.active_workouts[device_id] = workout_session_id
        
        # Initialize rep detection engine for this workout
        if device_id not in self.rep_engines:
            self.rep_engines[device_id] = RepDetectionEngine(device_id, exercise_type)
        
        logger.info(f"Started workout tracking for device {device_id}, session {workout_session_id}")

    async def stop_workout(self, device_id: str):
        """Stop workout tracking for async router compatibility."""
        if device_id in self.active_workouts:
            del self.active_workouts[device_id]
        
        if device_id in self.rep_engines:
            del self.rep_engines[device_id]
        
        logger.info(f"Stopped workout tracking for device {device_id}")

    async def get_latest_detection(self, device_id: str) -> Optional[Dict[str, Any]]:
        """Get the latest rep detection result for a device."""
        if device_id not in self.rep_engines:
            return None
        
        engine = self.rep_engines[device_id]
        
        # Return mock detection data for now
        # This would be replaced with actual detection results from the engine
        return {
            'rep_detected': False,
            'confidence': 0.0,
            'event_type': 'rep_completed',
            'duration_ms': None,
            'metadata': {}
        }

    def is_detection_active(self, device_id: str) -> bool:
        """Check if rep detection is active for a device."""
        return device_id in self.active_workouts

    async def process_sensor_data(self, device_id: str, sensor_data, workout_session_id: int, db: Session):
        """Process incoming sensor data for rep detection."""
        if device_id not in self.active_workouts:
            return
        
        if device_id not in self.rep_engines:
            # Get the current workout to determine exercise type
            workout = db.query(WorkoutSession).filter(WorkoutSession.id == workout_session_id).first()
            if workout:
                self.rep_engines[device_id] = RepDetectionEngine(device_id, workout.exercise_type)
            else:
                logger.warning(f"Could not find workout session {workout_session_id} for device {device_id}")
                return
        
        # Process the sensor data through the rep detection engine
        # This is where the real-time rep detection would happen
        engine = self.rep_engines[device_id]
        
        # Convert sensor data to the format expected by rep detection
        sensor_dict = {
            'accel_x': sensor_data.accelerometer.x,
            'accel_y': sensor_data.accelerometer.y,
            'accel_z': sensor_data.accelerometer.z,
            'gyro_x': sensor_data.gyroscope.x,
            'gyro_y': sensor_data.gyroscope.y,
            'gyro_z': sensor_data.gyroscope.z,
            'timestamp': sensor_data.timestamp or int(datetime.utcnow().timestamp() * 1000)
        }
        
        # This would trigger rep detection and WebSocket updates
        # For now, we'll just log the data reception
        logger.debug(f"Processed sensor data for device {device_id}")

    async def start_detection(self, device_id: str, exercise_type: str):
        """Start rep detection for a device."""
        if device_id not in self.rep_engines:
            self.rep_engines[device_id] = RepDetectionEngine(device_id, exercise_type)
        
        logger.info(f"Started rep detection for device {device_id}, exercise: {exercise_type}")

    async def stop_detection(self, device_id: str):
        """Stop rep detection for a device."""
        if device_id in self.rep_engines:
            del self.rep_engines[device_id]
        
        logger.info(f"Stopped rep detection for device {device_id}")

    async def calibrate_detection(self, device_id: str, db: Session):
        """Calibrate rep detection for a device."""
        if device_id in self.rep_engines and device_id in self.active_workouts:
            # Get the current workout to determine exercise type
            workout_session_id = self.active_workouts[device_id]
            workout = db.query(WorkoutSession).filter(WorkoutSession.id == workout_session_id).first()
            if workout:
                # Reset the detection engine state
                self.rep_engines[device_id] = RepDetectionEngine(device_id, workout.exercise_type)
                logger.info(f"Calibrated rep detection for device {device_id}, exercise: {workout.exercise_type}")
            else:
                logger.warning(f"Could not find workout session {workout_session_id} for calibration")
        else:
            logger.warning(f"No active workout found for device {device_id} during calibration")

# Global workout manager instance
import asyncio
import numpy as np
workout_manager = WorkoutManager()
