from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Dict, List, Any
from enum import Enum


class ExerciseType(str, Enum):
    SQUAT = "squat"
    BICEP_CURL = "bicep_curl"
    UNKNOWN = "unknown"


class WorkoutStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class RepEventType(str, Enum):
    REP_COMPLETED = "rep_completed"
    SET_COMPLETED = "set_completed"
    FORM_WARNING = "form_warning"
    POOR_FORM = "poor_form"


# Sensor Data Models
class AccelerometerData(BaseModel):
    x: float
    y: float
    z: float


class GyroscopeData(BaseModel):
    x: float
    y: float
    z: float


class MagnetometerData(BaseModel):
    x: float
    y: float
    z: float


class SensorDataInput(BaseModel):
    device_id: str
    timestamp: Optional[int] = None  # Unix timestamp in milliseconds
    accelerometer: AccelerometerData
    gyroscope: GyroscopeData
    magnetometer: Optional[MagnetometerData] = None
    magnetometer_available: bool = False
    temperature: Optional[float] = None
    exercise_type: Optional[str] = None  # Added for training data collection

    class Config:
        json_schema_extra = {
            "example": {
                "device_id": "AA:BB:CC:DD:EE:FF",
                "timestamp": 1640995200000,
                "magnetometer_available": True,
                "accelerometer": {"x": 0.23, "y": -0.01, "z": 9.85},
                "gyroscope": {"x": 0.01, "y": 0.01, "z": -0.00},
                "magnetometer": {"x": 1617.00, "y": 1119.00, "z": -14421.00},
                "temperature": 26.82
            }
        }


class SensorDataResponse(BaseModel):
    id: int
    device_id: str
    timestamp: datetime
    accel_x: float
    accel_y: float
    accel_z: float
    gyro_x: float
    gyro_y: float
    gyro_z: float
    mag_x: Optional[float]
    mag_y: Optional[float]
    mag_z: Optional[float]
    magnetometer_available: bool
    temperature: Optional[float]
    session_id: Optional[int]

    class Config:
        from_attributes = True


# Exercise Session Models
class ExerciseSessionCreate(BaseModel):
    device_id: str
    exercise_type: Optional[ExerciseType] = None
    notes: Optional[str] = None


class ExerciseSessionUpdate(BaseModel):
    exercise_type: Optional[ExerciseType] = None
    notes: Optional[str] = None
    is_labeled: Optional[bool] = None


class ExerciseSessionResponse(BaseModel):
    id: int
    device_id: str
    start_time: datetime
    end_time: Optional[datetime]
    exercise_type: Optional[str]
    is_labeled: bool
    notes: Optional[str]
    reading_count: Optional[int] = None

    class Config:
        from_attributes = True


# Exercise Label Models
class ExerciseLabelCreate(BaseModel):
    session_id: int
    start_reading_id: int
    end_reading_id: int
    exercise_type: ExerciseType
    repetitions: Optional[int] = None
    quality_score: Optional[float] = Field(None, ge=1, le=10)
    labeled_by: Optional[str] = None


class ExerciseLabelResponse(BaseModel):
    id: int
    session_id: int
    start_reading_id: int
    end_reading_id: int
    exercise_type: str
    repetitions: Optional[int]
    quality_score: Optional[float]
    labeled_by: Optional[str]
    labeled_at: datetime

    class Config:
        from_attributes = True


# ML Model Models
class ModelTrainingRequest(BaseModel):
    model_name: str = "default_classifier"
    model_type: str = "random_forest"
    training_data_filter: Optional[Dict[str, Any]] = None
    hyperparameters: Optional[Dict[str, Any]] = None


class ModelPredictionRequest(BaseModel):
    sensor_data: List[SensorDataInput]
    model_version: Optional[str] = None


class ModelPredictionResponse(BaseModel):
    predicted_exercise: str
    confidence_score: float
    prediction_probabilities: Dict[str, float]
    model_version: str
    processing_time_ms: float
    features_used: Optional[Dict[str, float]] = None


class ModelStatusResponse(BaseModel):
    model_name: str
    version: str
    model_type: str
    is_active: bool
    training_accuracy: Optional[float]
    validation_accuracy: Optional[float]
    training_samples: Optional[int]
    created_at: datetime
    last_prediction_at: Optional[datetime] = None


# Feature Engineering Models
class FeatureWindow(BaseModel):
    window_id: str
    device_id: str
    start_time: datetime
    end_time: datetime
    features: Dict[str, float]
    exercise_label: Optional[str] = None


# API Response Models
class APIResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Any] = None


class PaginatedResponse(BaseModel):
    items: List[Any]
    total: int
    page: int
    size: int
    pages: int


# Query Models
class SensorDataQuery(BaseModel):
    device_id: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    session_id: Optional[int] = None
    limit: int = Field(1000, le=10000)
    offset: int = 0


# Workout Session Models
class WorkoutSessionCreate(BaseModel):
    device_id: str
    exercise_type: ExerciseType
    target_reps: Optional[int] = None
    target_sets: Optional[int] = None


class WorkoutSessionUpdate(BaseModel):
    status: Optional[WorkoutStatus] = None
    current_set: Optional[int] = None
    current_reps: Optional[int] = None
    notes: Optional[str] = None


class WorkoutSessionResponse(BaseModel):
    id: int
    device_id: str
    exercise_type: str
    status: str
    started_at: datetime
    completed_at: Optional[datetime]
    current_set: int
    current_reps: int
    target_reps_per_set: Optional[int]
    target_sets: Optional[int]
    notes: Optional[str]

    class Config:
        from_attributes = True


# Rep Pattern Models
class RepPatternCreate(BaseModel):
    device_id: str
    exercise_type: ExerciseType
    avg_duration_ms: int
    min_duration_ms: int
    max_duration_ms: int
    rep_count: int


class RepPatternResponse(BaseModel):
    id: int
    device_id: str
    exercise_type: str
    avg_duration_ms: int
    min_duration_ms: int
    max_duration_ms: int
    rep_count: int
    last_updated: datetime

    class Config:
        from_attributes = True


# Rep Event Models
class RepEventCreate(BaseModel):
    workout_session_id: int
    event_type: RepEventType
    confidence: float = Field(..., ge=0.0, le=1.0)
    duration_ms: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None


class RepEventResponse(BaseModel):
    id: int
    workout_session_id: int
    event_type: str
    confidence: float
    duration_ms: Optional[int]
    timestamp: datetime
    metadata: Optional[Dict[str, Any]]

    class Config:
        from_attributes = True


# Real-time Rep Detection Models
class RepDetectionRequest(BaseModel):
    device_id: str
    use_personalized_timing: bool = True
    confidence_threshold: float = Field(0.6, ge=0.0, le=1.0)


class RepDetectionResponse(BaseModel):
    device_id: str
    rep_detected: bool
    confidence: float
    event_type: RepEventType
    duration_ms: Optional[int]
    metadata: Dict[str, Any]
    timestamp: datetime


class RepValidationRequest(BaseModel):
    device_id: str
    rep_data: List[SensorDataInput]
    expected_exercise: ExerciseType


class RepValidationResponse(BaseModel):
    is_valid_rep: bool
    confidence: float
    detected_exercise: ExerciseType
    form_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    suggestions: Optional[List[str]] = None


# WebSocket Message Models
class WebSocketMessage(BaseModel):
    type: str
    device_id: str
    data: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class RepCompletedMessage(WebSocketMessage):
    type: str = "rep_completed"
    

class SetCompletedMessage(WebSocketMessage):
    type: str = "set_completed"


class WorkoutCompletedMessage(WebSocketMessage):
    type: str = "workout_completed"


class FormWarningMessage(WebSocketMessage):
    type: str = "form_warning"


# Training Data Collection Models
class RepTrainingDataCreate(BaseModel):
    device_id: str
    exercise_type: ExerciseType
    rep_number: int
    set_number: int
    duration_ms: int
    quality_score: float = Field(..., ge=0.0, le=1.0)
    sensor_data_ids: List[int]
    metadata: Optional[Dict[str, Any]] = None


class RepTrainingDataResponse(BaseModel):
    id: int
    device_id: str
    exercise_type: str
    rep_number: int
    set_number: int
    duration_ms: int
    quality_score: float
    sensor_data_ids: List[int]
    metadata: Optional[Dict[str, Any]]
    created_at: datetime

    class Config:
        from_attributes = True


# Device Command Models
class CommandRequest(BaseModel):
    command: str = Field(..., description="Command to send to ESP32 device")
    timestamp: Optional[datetime] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "command": "bicep",
                "timestamp": "2024-01-01T12:00:00Z"
            }
        }


class CommandResponse(BaseModel):
    success: bool
    message: str
    device_id: str
    command: str
    timestamp: datetime
