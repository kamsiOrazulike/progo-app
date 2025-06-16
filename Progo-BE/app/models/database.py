from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Text, JSON, Enum, func
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import uuid
import enum


class WorkoutStatus(enum.Enum):
    active = "active"
    paused = "paused"
    completed = "completed"
    cancelled = "cancelled"


class RepEventType(enum.Enum):
    rep_completed = "rep_completed"
    set_completed = "set_completed"
    rest_started = "rest_started"
    form_warning = "form_warning"


class SensorReading(Base):
    __tablename__ = "sensor_readings"
    
    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String, nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Accelerometer data
    accel_x = Column(Float, nullable=False)
    accel_y = Column(Float, nullable=False)
    accel_z = Column(Float, nullable=False)
    
    # Gyroscope data
    gyro_x = Column(Float, nullable=False)
    gyro_y = Column(Float, nullable=False)
    gyro_z = Column(Float, nullable=False)
    
    # Magnetometer data (optional)
    mag_x = Column(Float, nullable=True)
    mag_y = Column(Float, nullable=True)
    mag_z = Column(Float, nullable=True)
    magnetometer_available = Column(Boolean, default=False)
    
    # Additional sensor data
    temperature = Column(Float, nullable=True)
    exercise_type = Column(String, nullable=True)  # For training data collection
    
    # Foreign key to exercise session
    session_id = Column(Integer, ForeignKey("exercise_sessions.id"), nullable=True)
    session = relationship("ExerciseSession", back_populates="readings")


class ExerciseSession(Base):
    __tablename__ = "exercise_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String, nullable=False, index=True)
    start_time = Column(DateTime(timezone=True), server_default=func.now())
    end_time = Column(DateTime(timezone=True), nullable=True)
    exercise_type = Column(String, nullable=True)  # 'squat', 'bicep_curl', etc.
    is_labeled = Column(Boolean, default=False)
    notes = Column(Text, nullable=True)
    
    # Relationships
    readings = relationship("SensorReading", back_populates="session")
    labels = relationship("ExerciseLabel", back_populates="session")
    predictions = relationship("ModelPrediction", back_populates="session")


class ExerciseLabel(Base):
    __tablename__ = "exercise_labels"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("exercise_sessions.id"), nullable=False)
    start_reading_id = Column(Integer, ForeignKey("sensor_readings.id"), nullable=False)
    end_reading_id = Column(Integer, ForeignKey("sensor_readings.id"), nullable=False)
    
    exercise_type = Column(String, nullable=False)  # 'squat', 'bicep_curl'
    repetitions = Column(Integer, nullable=True)
    quality_score = Column(Float, nullable=True)  # 1-10 scale
    labeled_by = Column(String, nullable=True)  # user who labeled
    labeled_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    session = relationship("ExerciseSession", back_populates="labels")


class ModelPrediction(Base):
    __tablename__ = "model_predictions"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("exercise_sessions.id"), nullable=True)
    model_version = Column(String, nullable=False)
    
    # Prediction results
    predicted_exercise = Column(String, nullable=False)
    confidence_score = Column(Float, nullable=False)
    prediction_probabilities = Column(JSON, nullable=True)  # {'squat': 0.8, 'bicep_curl': 0.2}
    
    # Features used for prediction
    features = Column(JSON, nullable=True)
    
    # Metadata
    predicted_at = Column(DateTime(timezone=True), server_default=func.now())
    processing_time_ms = Column(Float, nullable=True)
    
    # Relationships
    session = relationship("ExerciseSession", back_populates="predictions")


class MLModel(Base):
    __tablename__ = "ml_models"
    
    id = Column(Integer, primary_key=True, index=True)
    model_name = Column(String, nullable=False)
    version = Column(String, nullable=False)
    model_type = Column(String, nullable=False)  # 'random_forest', 'svm', etc.
    
    # Model metadata
    training_accuracy = Column(Float, nullable=True)
    validation_accuracy = Column(Float, nullable=True)
    feature_names = Column(JSON, nullable=True)
    model_parameters = Column(JSON, nullable=True)
    
    # Training info
    training_samples = Column(Integer, nullable=True)
    training_started_at = Column(DateTime(timezone=True), nullable=True)
    training_completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Status
    is_active = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # File path to saved model
    model_file_path = Column(String, nullable=True)


class DeviceInfo(Base):
    """Optional device registration and metadata tracking"""
    __tablename__ = "device_info"
    
    device_id = Column(String, primary_key=True)  # MAC address
    device_name = Column(String, nullable=True)   # User-friendly name
    device_type = Column(String, default="ESP32")
    registered_at = Column(DateTime(timezone=True), server_default=func.now())
    last_seen = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True)
    notes = Column(Text, nullable=True)


class WorkoutSession(Base):
    """Active workout sessions for real-time rep tracking"""
    __tablename__ = "workout_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String, nullable=False, index=True)
    exercise_type = Column(String, nullable=False)  # 'squat', 'bicep_curl', etc.
    
    # Workout plan
    target_sets = Column(Integer, default=3)
    target_reps_per_set = Column(Integer, default=10)
    
    # Current progress
    current_set = Column(Integer, default=1)
    current_reps = Column(Integer, default=0)
    
    # Status and timing
    status = Column(Enum(WorkoutStatus), default=WorkoutStatus.active)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Optional metadata
    notes = Column(Text, nullable=True)
    
    # Relationships
    rep_events = relationship("RepEvent", back_populates="workout_session")


class RepPattern(Base):
    """Learned rep patterns for personalized detection"""
    __tablename__ = "rep_patterns"
    
    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String, nullable=False, index=True)
    exercise_type = Column(String, nullable=False)
    
    # Timing patterns (in seconds)
    avg_rep_duration = Column(Float, nullable=False)
    min_rep_duration = Column(Float, nullable=False)
    max_rep_duration = Column(Float, nullable=False)
    avg_rest_between_reps = Column(Float, nullable=False)
    
    # Motion patterns (JSON stored signatures)
    motion_signature = Column(JSON, nullable=True)
    
    # Training metadata
    training_session_count = Column(Integer, default=1)
    last_updated = Column(DateTime(timezone=True), server_default=func.now())
    confidence_score = Column(Float, default=0.5)  # How reliable this pattern is


class RepEvent(Base):
    """Real-time rep detection events"""
    __tablename__ = "rep_events"
    
    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String, nullable=False, index=True)
    workout_session_id = Column(Integer, ForeignKey("workout_sessions.id"), nullable=False)
    
    # Rep details
    rep_number = Column(Integer, nullable=False)  # Rep number in current set
    set_number = Column(Integer, nullable=False)  # Current set number
    event_type = Column(Enum(RepEventType), default=RepEventType.rep_completed)
    
    # Detection metrics
    detected_at = Column(DateTime(timezone=True), server_default=func.now())
    confidence_score = Column(Float, nullable=False)
    motion_quality = Column(Float, nullable=True)  # 0-1 scale for form quality
    validated = Column(Boolean, default=True)  # Manual validation flag
    
    # Technical details
    rep_duration = Column(Float, nullable=True)  # Duration in seconds
    detection_method = Column(String, nullable=True)  # 'motion_cycle', 'ml_confidence', 'hybrid'
    
    # Relationships
    workout_session = relationship("WorkoutSession", back_populates="rep_events")
