import numpy as np
import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from collections import deque
from dataclasses import dataclass
from enum import Enum
import math
from scipy import signal
from scipy.stats import pearsonr

from app.models.schemas import SensorDataInput
from sqlalchemy.orm import Session
from app.models.database import RepPattern, WorkoutSession, RepEvent, RepEventType

logger = logging.getLogger(__name__)


class MotionPhase(Enum):
    """Exercise motion phases"""
    REST = "rest"
    UP_MOTION = "up_motion"
    PEAK = "peak"
    DOWN_MOTION = "down_motion"
    TRANSITION = "transition"


class RepDetectionMethod(Enum):
    """Detection method types"""
    MOTION_CYCLE = "motion_cycle"
    ML_CONFIDENCE = "ml_confidence"
    HYBRID = "hybrid"


@dataclass
class RepCandidate:
    """Potential rep detection"""
    start_time: datetime
    end_time: datetime
    confidence: float
    motion_quality: float
    duration: float
    detection_method: RepDetectionMethod
    motion_data: Dict[str, Any]


class MotionCycleAnalyzer:
    """
    Analyzes accelerometer and gyroscope data to detect exercise motion cycles.
    """
    
    def __init__(self, window_size: int = 50):
        self.window_size = window_size
        self.motion_buffer = deque(maxlen=window_size)
        self.current_phase = MotionPhase.REST
        self.phase_start_time = datetime.now()
        self.last_peak_time = None
        
        # Motion detection parameters
        self.rest_threshold = 1.5  # m/s² - below this is considered rest
        self.motion_threshold = 3.0  # m/s² - above this is active motion
        self.peak_threshold = 8.0  # m/s² - peak motion threshold
        self.min_phase_duration = 0.3  # seconds - minimum phase duration
        
    def add_sensor_data(self, sensor_data: Dict[str, float], timestamp: datetime):
        """Add new sensor data point and analyze motion."""
        # Calculate acceleration magnitude
        accel_mag = math.sqrt(
            sensor_data['accel_x']**2 + 
            sensor_data['accel_y']**2 + 
            sensor_data['accel_z']**2
        )
        
        # Calculate gyroscope magnitude
        gyro_mag = math.sqrt(
            sensor_data['gyro_x']**2 + 
            sensor_data['gyro_y']**2 + 
            sensor_data['gyro_z']**2
        )
        
        motion_point = {
            'timestamp': timestamp,
            'accel_mag': accel_mag,
            'gyro_mag': gyro_mag,
            'accel_x': sensor_data['accel_x'],
            'accel_y': sensor_data['accel_y'],
            'accel_z': sensor_data['accel_z'],
            'gyro_x': sensor_data['gyro_x'],
            'gyro_y': sensor_data['gyro_y'],
            'gyro_z': sensor_data['gyro_z']
        }
        
        self.motion_buffer.append(motion_point)
        
        # Analyze current motion phase
        return self._analyze_motion_phase(timestamp)
    
    def _analyze_motion_phase(self, current_time: datetime) -> Optional[MotionPhase]:
        """Analyze current motion phase based on recent data."""
        if len(self.motion_buffer) < 10:
            return None
            
        # Get recent motion data
        recent_data = list(self.motion_buffer)[-10:]
        avg_accel = np.mean([p['accel_mag'] for p in recent_data])
        avg_gyro = np.mean([p['gyro_mag'] for p in recent_data])
        
        # Calculate phase duration
        phase_duration = (current_time - self.phase_start_time).total_seconds()
        
        new_phase = None
        
        # State machine for motion phases
        if self.current_phase == MotionPhase.REST:
            if avg_accel > self.motion_threshold and phase_duration > self.min_phase_duration:
                new_phase = MotionPhase.UP_MOTION
                
        elif self.current_phase == MotionPhase.UP_MOTION:
            if avg_accel > self.peak_threshold:
                new_phase = MotionPhase.PEAK
            elif avg_accel < self.rest_threshold and phase_duration > self.min_phase_duration:
                new_phase = MotionPhase.REST
                
        elif self.current_phase == MotionPhase.PEAK:
            if avg_accel < self.motion_threshold and phase_duration > 0.1:
                new_phase = MotionPhase.DOWN_MOTION
                
        elif self.current_phase == MotionPhase.DOWN_MOTION:
            if avg_accel < self.rest_threshold and phase_duration > self.min_phase_duration:
                new_phase = MotionPhase.REST
                
        # Update phase if changed
        if new_phase and new_phase != self.current_phase:
            self.current_phase = new_phase
            self.phase_start_time = current_time
            
            if new_phase == MotionPhase.PEAK:
                self.last_peak_time = current_time
                
        return self.current_phase
    
    def detect_rep_cycle(self) -> Optional[Dict[str, Any]]:
        """Detect if a complete rep cycle has occurred."""
        if len(self.motion_buffer) < self.window_size:
            return None
            
        # Look for rest -> motion -> peak -> motion -> rest cycle
        if (self.current_phase == MotionPhase.REST and 
            self.last_peak_time and 
            (datetime.now() - self.last_peak_time).total_seconds() < 5.0):
            
            # Calculate motion quality metrics
            recent_data = list(self.motion_buffer)[-30:]
            motion_smoothness = self._calculate_motion_smoothness(recent_data)
            motion_consistency = self._calculate_motion_consistency(recent_data)
            
            rep_data = {
                'detected_at': datetime.now(),
                'motion_quality': (motion_smoothness + motion_consistency) / 2,
                'peak_time': self.last_peak_time,
                'motion_smoothness': motion_smoothness,
                'motion_consistency': motion_consistency
            }
            
            # Reset peak time to avoid double counting
            self.last_peak_time = None
            
            return rep_data
            
        return None
    
    def _calculate_motion_smoothness(self, motion_data: List[Dict]) -> float:
        """Calculate how smooth the motion is (0-1)."""
        if len(motion_data) < 10:
            return 0.5
            
        # Calculate acceleration jerk (derivative of acceleration)
        accel_values = [p['accel_mag'] for p in motion_data]
        jerk = np.diff(np.diff(accel_values))
        
        # Lower jerk = smoother motion
        avg_jerk = np.mean(np.abs(jerk))
        smoothness = max(0.0, min(1.0, 1.0 - (avg_jerk / 10.0)))
        
        return smoothness
    
    def _calculate_motion_consistency(self, motion_data: List[Dict]) -> float:
        """Calculate motion consistency (0-1)."""
        if len(motion_data) < 10:
            return 0.5
            
        # Check for consistent motion patterns
        accel_values = [p['accel_mag'] for p in motion_data]
        
        # Calculate variance - lower variance = more consistent
        motion_variance = np.var(accel_values)
        consistency = max(0.0, min(1.0, 1.0 - (motion_variance / 25.0)))
        
        return consistency


class MLConfidenceTracker:
    """
    Tracks ML prediction confidence over time to detect confidence cycles.
    """
    
    def __init__(self, window_size: int = 50):
        self.window_size = window_size
        self.confidence_buffer = deque(maxlen=window_size)
        self.prediction_buffer = deque(maxlen=window_size)
        
        # Confidence detection parameters
        self.high_confidence_threshold = 0.8
        self.low_confidence_threshold = 0.6
        self.stability_window = 10
        
    def add_prediction(self, prediction: str, confidence: float, timestamp: datetime):
        """Add ML prediction result."""
        self.confidence_buffer.append({
            'timestamp': timestamp,
            'prediction': prediction,
            'confidence': confidence
        })
        self.prediction_buffer.append(prediction)
    
    def detect_confidence_cycle(self) -> Optional[Dict[str, Any]]:
        """Detect confidence cycles that indicate rep completion."""
        if len(self.confidence_buffer) < self.stability_window * 2:
            return None
            
        recent_data = list(self.confidence_buffer)[-self.stability_window*2:]
        
        # Split into two halves
        first_half = recent_data[:self.stability_window]
        second_half = recent_data[self.stability_window:]
        
        # Check for high confidence -> transition -> high confidence
        first_avg_conf = np.mean([p['confidence'] for p in first_half])
        second_avg_conf = np.mean([p['confidence'] for p in second_half])
        
        # Check prediction stability
        first_predictions = [p['prediction'] for p in first_half]
        second_predictions = [p['prediction'] for p in second_half]
        
        first_stable = len(set(first_predictions)) <= 2
        second_stable = len(set(second_predictions)) <= 2
        
        if (first_avg_conf > self.high_confidence_threshold and 
            second_avg_conf > self.high_confidence_threshold and
            first_stable and second_stable):
            
            return {
                'detected_at': recent_data[-1]['timestamp'],
                'confidence_pattern': True,
                'avg_confidence': (first_avg_conf + second_avg_conf) / 2,
                'prediction_stability': first_stable and second_stable
            }
            
        return None


class PersonalizedTimingValidator:
    """
    Validates rep timing against learned user patterns.
    """
    
    def __init__(self, device_id: str, exercise_type: str):
        self.device_id = device_id
        self.exercise_type = exercise_type
        self.rep_pattern = None
        self.last_rep_time = None
        
        # Default timing parameters (will be overridden by learned patterns)
        self.default_min_rep_duration = 1.0  # seconds
        self.default_max_rep_duration = 8.0  # seconds
        self.default_min_rest_time = 0.5    # seconds
        
    def load_rep_pattern(self, db: Session):
        """Load learned rep pattern from database."""
        pattern = db.query(RepPattern).filter(
            RepPattern.device_id == self.device_id,
            RepPattern.exercise_type == self.exercise_type
        ).first()
        
        if pattern:
            self.rep_pattern = pattern
            logger.debug(f"Loaded rep pattern for {self.device_id}: {self.exercise_type}")
        else:
            logger.debug(f"No rep pattern found for {self.device_id}: {self.exercise_type}")
    
    def validate_rep_timing(self, rep_candidate: RepCandidate) -> bool:
        """Validate rep timing against learned patterns."""
        rep_duration = rep_candidate.duration
        current_time = rep_candidate.end_time
        
        # Check minimum rest time between reps
        if self.last_rep_time:
            time_since_last_rep = (current_time - self.last_rep_time).total_seconds()
            min_rest_time = (self.rep_pattern.avg_rest_between_reps * 0.5 
                           if self.rep_pattern else self.default_min_rest_time)
            
            if time_since_last_rep < min_rest_time:
                logger.debug(f"Rep rejected: too soon after last rep ({time_since_last_rep:.2f}s)")
                return False
        
        # Check rep duration
        if self.rep_pattern:
            min_duration = max(self.rep_pattern.min_rep_duration * 0.7, 0.8)
            max_duration = min(self.rep_pattern.max_rep_duration * 1.5, 12.0)
        else:
            min_duration = self.default_min_rep_duration
            max_duration = self.default_max_rep_duration
            
        if not (min_duration <= rep_duration <= max_duration):
            logger.debug(f"Rep rejected: duration {rep_duration:.2f}s outside range [{min_duration:.2f}, {max_duration:.2f}]")
            return False
            
        return True
    
    def update_last_rep_time(self, rep_time: datetime):
        """Update the last rep time."""
        self.last_rep_time = rep_time
    
    def validate_timing(self, device_id: str, exercise_type, duration_ms: int) -> float:
        """Validate timing and return confidence score (0-1)."""
        duration_seconds = duration_ms / 1000.0
        
        if self.rep_pattern:
            # Use learned patterns
            min_duration = max(self.rep_pattern.min_rep_duration * 0.7, 0.8)
            max_duration = min(self.rep_pattern.max_rep_duration * 1.5, 12.0)
            optimal_duration = self.rep_pattern.avg_rep_duration
        else:
            # Use defaults
            min_duration = self.default_min_rep_duration
            max_duration = self.default_max_rep_duration
            optimal_duration = (min_duration + max_duration) / 2
        
        # Calculate confidence based on how close to optimal timing
        if min_duration <= duration_seconds <= max_duration:
            # Within acceptable range - calculate confidence based on distance from optimal
            distance_from_optimal = abs(duration_seconds - optimal_duration)
            max_acceptable_distance = max(optimal_duration - min_duration, max_duration - optimal_duration)
            confidence = max(0.0, 1.0 - (distance_from_optimal / max_acceptable_distance))
            return confidence
        else:
            # Outside acceptable range
            return 0.0
    
    def clear_patterns(self, device_id: str):
        """Clear cached patterns for a device."""
        if hasattr(self, 'device_id') and self.device_id == device_id:
            self.rep_pattern = None
            logger.info(f"Cleared patterns for device: {device_id}")
    
    # ...existing code...


class RepStateMachine:
    """
    State machine for combining motion and ML signals into rep detection.
    """
    
    def __init__(self):
        self.current_state = "waiting"
        self.motion_signal = False
        self.ml_signal = False
        self.rep_start_time = None
        
    def update(self, motion_phase: MotionPhase, ml_confidence_data: Optional[Dict]) -> Optional[RepCandidate]:
        """Update state machine with new signals."""
        # Update motion signal
        self.motion_signal = (motion_phase in [MotionPhase.UP_MOTION, MotionPhase.PEAK, MotionPhase.DOWN_MOTION])
        
        # Update ML signal
        self.ml_signal = ml_confidence_data is not None
        
        current_time = datetime.now()
        
        if self.current_state == "waiting":
            if self.motion_signal or self.ml_signal:
                self.current_state = "detecting"
                self.rep_start_time = current_time
                
        elif self.current_state == "detecting":
            # Check for rep completion signals
            motion_complete = (motion_phase == MotionPhase.REST and 
                             self.rep_start_time and 
                             (current_time - self.rep_start_time).total_seconds() > 1.0)
            
            ml_complete = self.ml_signal
            
            if motion_complete or ml_complete:
                # Create rep candidate
                rep_duration = (current_time - self.rep_start_time).total_seconds()
                
                # Determine detection method and confidence
                if motion_complete and ml_complete:
                    method = RepDetectionMethod.HYBRID
                    confidence = 0.9
                elif motion_complete:
                    method = RepDetectionMethod.MOTION_CYCLE
                    confidence = 0.7
                else:
                    method = RepDetectionMethod.ML_CONFIDENCE
                    confidence = ml_confidence_data.get('avg_confidence', 0.6) if ml_confidence_data else 0.6
                
                # Calculate motion quality
                motion_quality = 0.8  # Default, would be calculated from motion data
                if ml_confidence_data:
                    motion_quality = max(motion_quality, ml_confidence_data.get('avg_confidence', 0.8))
                
                rep_candidate = RepCandidate(
                    start_time=self.rep_start_time,
                    end_time=current_time,
                    confidence=confidence,
                    motion_quality=motion_quality,
                    duration=rep_duration,
                    detection_method=method,
                    motion_data={
                        'motion_complete': motion_complete,
                        'ml_complete': ml_complete,
                        'motion_phase': motion_phase.value if motion_phase else None
                    }
                )
                
                # Reset state
                self.current_state = "waiting"
                self.rep_start_time = None
                
                return rep_candidate
                
        return None


class RepDetectionEngine:
    """
    Main rep detection engine combining motion analysis, ML confidence, and timing validation.
    """
    
    def __init__(self, device_id: str, exercise_type: str):
        self.device_id = device_id
        self.exercise_type = exercise_type
        
        # Initialize components
        self.motion_analyzer = MotionCycleAnalyzer()
        self.ml_confidence_tracker = MLConfidenceTracker()
        self.timing_validator = PersonalizedTimingValidator(device_id, exercise_type)
        self.rep_state_machine = RepStateMachine()
        
        # Load patterns from database
        self.patterns_loaded = False
        
    def load_patterns(self, db: Session):
        """Load learned patterns from database."""
        if not self.patterns_loaded:
            self.timing_validator.load_rep_pattern(db)
            self.patterns_loaded = True
    
    def process_sensor_data(self, sensor_data: Dict[str, float], timestamp: datetime, 
                          ml_prediction: Optional[Dict] = None) -> Optional[RepCandidate]:
        """Process sensor data and detect reps."""
        
        # 1. Motion cycle analysis
        motion_phase = self.motion_analyzer.add_sensor_data(sensor_data, timestamp)
        
        # 2. ML confidence analysis
        ml_confidence_data = None
        if ml_prediction:
            self.ml_confidence_tracker.add_prediction(
                ml_prediction['predicted_exercise'],
                ml_prediction['confidence_score'],
                timestamp
            )
            ml_confidence_data = self.ml_confidence_tracker.detect_confidence_cycle()
        
        # 3. Combine signals in state machine
        rep_candidate = self.rep_state_machine.update(motion_phase, ml_confidence_data)
        
        # 4. Validate timing if we have a candidate
        if rep_candidate:
            if self.timing_validator.validate_rep_timing(rep_candidate):
                self.timing_validator.update_last_rep_time(rep_candidate.end_time)
                return rep_candidate
            else:
                logger.debug(f"Rep candidate rejected by timing validator")
                
        return None
    
    def get_status(self) -> Dict[str, Any]:
        """Get current detection engine status."""
        return {
            "device_id": self.device_id,
            "exercise_type": self.exercise_type,
            "motion_phase": self.motion_analyzer.current_phase.value,
            "motion_buffer_size": len(self.motion_analyzer.motion_buffer),
            "confidence_buffer_size": len(self.ml_confidence_tracker.confidence_buffer),
            "patterns_loaded": self.patterns_loaded,
            "state_machine_state": self.rep_state_machine.current_state,
            "last_rep_time": self.timing_validator.last_rep_time.isoformat() if self.timing_validator.last_rep_time else None
        }