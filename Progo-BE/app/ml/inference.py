import numpy as np
import pickle
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
import time
import logging
from pathlib import Path
from collections import deque

from app.ml.preprocessing import FeatureExtractor
from app.models.database import MLModel, ModelPrediction
from app.models.schemas import SensorDataInput, ModelPredictionResponse
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class RealTimeInference:
    """
    Real-time inference engine for exercise classification.
    Maintains sliding windows of sensor data and provides predictions.
    """
    
    def __init__(self, model_dir: str = "app/ml/models", buffer_size: int = 500):
        self.model_dir = Path(model_dir)
        self.buffer_size = buffer_size
        
        # Active model and components
        self.active_model = None
        self.model_package = None
        self.feature_extractor = None
        
        # Data buffers for real-time processing
        self.sensor_buffers = {}  # device_id -> deque of sensor readings
        
        # Performance tracking
        self.prediction_count = 0
        self.total_inference_time = 0.0
        
    def load_active_model(self, db: Session, model_name: str = "default_classifier") -> bool:
        """
        Load the active model from database.
        
        Args:
            db: Database session
            model_name: Name of the model to load
            
        Returns:
            True if model loaded successfully, False otherwise
        """
        try:
            # Get active model from database
            db_model = db.query(MLModel).filter(
                MLModel.model_name == model_name,
                MLModel.is_active == True
            ).first()
            
            if not db_model:
                logger.error(f"No active model found with name: {model_name}")
                return False
            
            # Load model package
            model_path = db_model.model_file_path
            if not model_path or not Path(model_path).exists():
                logger.error(f"Model file not found: {model_path}")
                return False
            
            with open(model_path, 'rb') as f:
                self.model_package = pickle.load(f)
            
            self.active_model = db_model
            
            # Initialize feature extractor with saved config
            fe_config = self.model_package.get('feature_extractor_config', {})
            self.feature_extractor = FeatureExtractor(
                window_size=fe_config.get('window_size', 200),
                overlap=fe_config.get('overlap', 0.5)
            )
            
            logger.info(f"Loaded model: {model_name} {db_model.version}")
            logger.info(f"Model accuracy: {db_model.validation_accuracy:.4f}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            return False
    
    def add_sensor_data(self, device_id: str, sensor_data: SensorDataInput) -> None:
        """
        Add new sensor data to the buffer for a device.
        
        Args:
            device_id: Device identifier
            sensor_data: New sensor reading
        """
        if device_id not in self.sensor_buffers:
            self.sensor_buffers[device_id] = deque(maxlen=self.buffer_size)
        
        # Convert sensor data to dictionary format
        sensor_dict = {
            'timestamp': sensor_data.timestamp or int(time.time() * 1000),
            'accel_x': sensor_data.accelerometer.x,
            'accel_y': sensor_data.accelerometer.y,
            'accel_z': sensor_data.accelerometer.z,
            'gyro_x': sensor_data.gyroscope.x,
            'gyro_y': sensor_data.gyroscope.y,
            'gyro_z': sensor_data.gyroscope.z,
        }
        
        # Add magnetometer data if available
        if sensor_data.magnetometer_available and sensor_data.magnetometer:
            sensor_dict.update({
                'mag_x': sensor_data.magnetometer.x,
                'mag_y': sensor_data.magnetometer.y,
                'mag_z': sensor_data.magnetometer.z,
            })
        
        self.sensor_buffers[device_id].append(sensor_dict)
        
    def predict_exercise(
        self, 
        device_id: str, 
        return_features: bool = False
    ) -> Optional[ModelPredictionResponse]:
        """
        Predict exercise type from current sensor buffer.
        
        Args:
            device_id: Device identifier
            return_features: Whether to include features in response
            
        Returns:
            Prediction response or None if not enough data
        """
        if not self.model_package or not self.feature_extractor:
            logger.error("No model loaded for inference")
            return None
        
        if device_id not in self.sensor_buffers:
            logger.warning(f"No sensor data found for device: {device_id}")
            return None
        
        buffer = self.sensor_buffers[device_id]
        
        if len(buffer) < self.feature_extractor.window_size:
            logger.debug(f"Insufficient data for prediction: {len(buffer)} < {self.feature_extractor.window_size}")
            return None
        
        start_time = time.time()
        
        try:
            # Get the latest window of data
            latest_readings = list(buffer)[-self.feature_extractor.window_size:]
            
            # Extract features
            features = self.feature_extractor.extract_features_from_readings(latest_readings)
            
            # Prepare feature vector
            feature_names = self.model_package['feature_names']
            feature_vector = np.array([features.get(name, 0.0) for name in feature_names]).reshape(1, -1)
            
            # Scale features
            scaler = self.model_package['scaler']
            feature_vector_scaled = scaler.transform(feature_vector)
            
            # Make prediction
            model = self.model_package['model']
            prediction = model.predict(feature_vector_scaled)[0]
            prediction_proba = model.predict_proba(feature_vector_scaled)[0]
            
            # Decode prediction
            label_encoder = self.model_package['label_encoder']
            predicted_exercise = label_encoder.inverse_transform([prediction])[0]
            
            # Create probability dictionary
            class_names = label_encoder.classes_
            probabilities = dict(zip(class_names, prediction_proba.astype(float)))
            
            # Calculate confidence (max probability)
            confidence = float(np.max(prediction_proba))
            
            # Calculate processing time
            processing_time = (time.time() - start_time) * 1000  # milliseconds
            
            # Update performance tracking
            self.prediction_count += 1
            self.total_inference_time += processing_time
            
            response = ModelPredictionResponse(
                predicted_exercise=predicted_exercise,
                confidence_score=confidence,
                prediction_probabilities=probabilities,
                model_version=self.active_model.version,
                processing_time_ms=processing_time
            )
            
            if return_features:
                response.features_used = features
            
            logger.debug(f"Prediction: {predicted_exercise} (confidence: {confidence:.3f})")
            
            return response
            
        except Exception as e:
            logger.error(f"Prediction failed: {e}")
            return None
    
    def predict_from_sensor_list(
        self, 
        sensor_data_list: List[SensorDataInput],
        return_features: bool = False
    ) -> Optional[ModelPredictionResponse]:
        """
        Predict exercise type from a list of sensor readings.
        
        Args:
            sensor_data_list: List of sensor readings
            return_features: Whether to include features in response
            
        Returns:
            Prediction response or None if not enough data
        """
        if not self.model_package or not self.feature_extractor:
            logger.error("No model loaded for inference")
            return None
        
        if len(sensor_data_list) < self.feature_extractor.window_size:
            logger.warning(f"Insufficient data for prediction: {len(sensor_data_list)} < {self.feature_extractor.window_size}")
            return None
        
        start_time = time.time()
        
        try:
            # Convert sensor data to dictionary format
            readings = []
            for sensor_data in sensor_data_list:
                sensor_dict = {
                    'timestamp': sensor_data.timestamp or int(time.time() * 1000),
                    'accel_x': sensor_data.accelerometer.x,
                    'accel_y': sensor_data.accelerometer.y,
                    'accel_z': sensor_data.accelerometer.z,
                    'gyro_x': sensor_data.gyroscope.x,
                    'gyro_y': sensor_data.gyroscope.y,
                    'gyro_z': sensor_data.gyroscope.z,
                }
                
                # Add magnetometer data if available
                if sensor_data.magnetometer_available and sensor_data.magnetometer:
                    sensor_dict.update({
                        'mag_x': sensor_data.magnetometer.x,
                        'mag_y': sensor_data.magnetometer.y,
                        'mag_z': sensor_data.magnetometer.z,
                    })
                
                readings.append(sensor_dict)
            
            # Use the latest window_size readings
            latest_readings = readings[-self.feature_extractor.window_size:]
            
            # Extract features
            features = self.feature_extractor.extract_features_from_readings(latest_readings)
            
            # Prepare feature vector
            feature_names = self.model_package['feature_names']
            feature_vector = np.array([features.get(name, 0.0) for name in feature_names]).reshape(1, -1)
            
            # Scale features
            scaler = self.model_package['scaler']
            feature_vector_scaled = scaler.transform(feature_vector)
            
            # Make prediction
            model = self.model_package['model']
            prediction = model.predict(feature_vector_scaled)[0]
            prediction_proba = model.predict_proba(feature_vector_scaled)[0]
            
            # Decode prediction
            label_encoder = self.model_package['label_encoder']
            predicted_exercise = label_encoder.inverse_transform([prediction])[0]
            
            # Create probability dictionary
            class_names = label_encoder.classes_
            probabilities = dict(zip(class_names, prediction_proba.astype(float)))
            
            # Calculate confidence (max probability)
            confidence = float(np.max(prediction_proba))
            
            # Calculate processing time
            processing_time = (time.time() - start_time) * 1000  # milliseconds
            
            response = ModelPredictionResponse(
                predicted_exercise=predicted_exercise,
                confidence_score=confidence,
                prediction_probabilities=probabilities,
                model_version=self.active_model.version,
                processing_time_ms=processing_time
            )
            
            if return_features:
                response.features_used = features
            
            return response
            
        except Exception as e:
            logger.error(f"Prediction failed: {e}")
            return None
    
    async def save_prediction(
        self, 
        db: Session, 
        prediction: ModelPredictionResponse,
        session_id: Optional[int] = None,
        features: Optional[Dict[str, float]] = None
    ) -> ModelPrediction:
        """
        Save prediction results to database.
        
        Args:
            db: Database session
            prediction: Prediction response
            session_id: Optional exercise session ID
            features: Optional features used for prediction
            
        Returns:
            Saved ModelPrediction record
        """
        db_prediction = ModelPrediction(
            session_id=session_id,
            model_version=prediction.model_version,
            predicted_exercise=prediction.predicted_exercise,
            confidence_score=prediction.confidence_score,
            prediction_probabilities=prediction.prediction_probabilities,
            features=features,
            processing_time_ms=prediction.processing_time_ms
        )
        
        db.add(db_prediction)
        db.commit()
        db.refresh(db_prediction)
        
        return db_prediction
    
    def get_buffer_status(self, device_id: str) -> Dict[str, Any]:
        """
        Get status of sensor data buffer for a device.
        
        Args:
            device_id: Device identifier
            
        Returns:
            Dictionary with buffer status information
        """
        if device_id not in self.sensor_buffers:
            return {
                'device_id': device_id,
                'buffer_size': 0,
                'max_buffer_size': self.buffer_size,
                'ready_for_prediction': False,
                'required_samples': self.feature_extractor.window_size if self.feature_extractor else 0
            }
        
        buffer = self.sensor_buffers[device_id]
        required_samples = self.feature_extractor.window_size if self.feature_extractor else 0
        
        return {
            'device_id': device_id,
            'buffer_size': len(buffer),
            'max_buffer_size': self.buffer_size,
            'ready_for_prediction': len(buffer) >= required_samples,
            'required_samples': required_samples,
            'latest_timestamp': buffer[-1]['timestamp'] if buffer else None
        }
    
    def clear_buffer(self, device_id: str) -> bool:
        """
        Clear sensor data buffer for a device.
        
        Args:
            device_id: Device identifier
            
        Returns:
            True if buffer was cleared, False if device not found
        """
        if device_id in self.sensor_buffers:
            self.sensor_buffers[device_id].clear()
            logger.info(f"Cleared buffer for device: {device_id}")
            return True
        return False
    
    def get_performance_stats(self) -> Dict[str, float]:
        """
        Get inference performance statistics.
        
        Returns:
            Dictionary with performance metrics
        """
        avg_inference_time = (
            self.total_inference_time / self.prediction_count 
            if self.prediction_count > 0 else 0.0
        )
        
        return {
            'total_predictions': self.prediction_count,
            'total_inference_time_ms': self.total_inference_time,
            'average_inference_time_ms': avg_inference_time,
            'model_loaded': self.active_model is not None,
            'model_version': self.active_model.version if self.active_model else None,
            'active_devices': len(self.sensor_buffers)
        }


# Global inference engine instance
inference_engine = RealTimeInference()
