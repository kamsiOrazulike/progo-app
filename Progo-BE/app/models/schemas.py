from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Dict, List, Any
from enum import Enum


class ExerciseType(str, Enum):
    SQUAT = "squat"
    BICEP_CURL = "bicep_curl"
    UNKNOWN = "unknown"


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
