from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import uuid


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
