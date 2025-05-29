import numpy as np
import pandas as pd
import pickle
import joblib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split, cross_val_score, GridSearchCV
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
from sqlalchemy.orm import Session
import logging

from app.models.database import ExerciseLabel, SensorReading, MLModel
from app.ml.preprocessing import FeatureExtractor

logger = logging.getLogger(__name__)


class ModelTrainer:
    """
    ML model training pipeline for exercise classification.
    """
    
    def __init__(self, model_save_dir: str = "app/ml/models"):
        self.model_save_dir = Path(model_save_dir)
        self.model_save_dir.mkdir(exist_ok=True)
        
        self.feature_extractor = FeatureExtractor()
        self.scaler = StandardScaler()
        self.label_encoder = LabelEncoder()
        
        # Model configurations
        self.model_configs = {
            'random_forest': {
                'model_class': RandomForestClassifier,
                'default_params': {
                    'n_estimators': 100,
                    'max_depth': 10,
                    'min_samples_split': 5,
                    'min_samples_leaf': 2,
                    'random_state': 42
                },
                'param_grid': {
                    'n_estimators': [50, 100, 200],
                    'max_depth': [5, 10, 15, None],
                    'min_samples_split': [2, 5, 10],
                    'min_samples_leaf': [1, 2, 4]
                }
            }
        }
    
    async def prepare_training_data(self, db: Session, min_samples_per_class: int = 20) -> Tuple[np.ndarray, np.ndarray, List[str]]:
        """
        Prepare training data from labeled exercise sessions.
        
        Args:
            db: Database session
            min_samples_per_class: Minimum number of samples required per exercise class
            
        Returns:
            Tuple of (features, labels, feature_names)
        """
        logger.info("Preparing training data from labeled sessions")
        
        # Get all labeled exercise data
        labeled_exercises = db.query(ExerciseLabel).all()
        
        if not labeled_exercises:
            raise ValueError("No labeled exercise data found")
        
        features_list = []
        labels_list = []
        
        for label in labeled_exercises:
            try:
                # Get sensor readings for this labeled segment
                readings = db.query(SensorReading).filter(
                    SensorReading.id >= label.start_reading_id,
                    SensorReading.id <= label.end_reading_id
                ).order_by(SensorReading.timestamp).all()
                
                if len(readings) < self.feature_extractor.window_size:
                    logger.warning(f"Skipping label {label.id}: insufficient readings ({len(readings)})")
                    continue
                
                # Convert readings to dictionaries
                reading_dicts = []
                for reading in readings:
                    reading_dict = {
                        'accel_x': reading.accel_x,
                        'accel_y': reading.accel_y,
                        'accel_z': reading.accel_z,
                        'gyro_x': reading.gyro_x,
                        'gyro_y': reading.gyro_y,
                        'gyro_z': reading.gyro_z,
                        'timestamp': reading.timestamp.timestamp() * 1000,  # Convert to milliseconds
                    }
                    
                    # Add magnetometer data if available
                    if reading.magnetometer_available and reading.mag_x is not None:
                        reading_dict.update({
                            'mag_x': reading.mag_x,
                            'mag_y': reading.mag_y,
                            'mag_z': reading.mag_z,
                        })
                    
                    reading_dicts.append(reading_dict)
                
                # Create sliding windows and extract features
                windows = self.feature_extractor.create_windows_from_readings(reading_dicts)
                
                for window_features in windows:
                    features_list.append(window_features)
                    labels_list.append(label.exercise_type)
                
            except Exception as e:
                logger.error(f"Error processing label {label.id}: {e}")
                continue
        
        if not features_list:
            raise ValueError("No valid training samples could be created")
        
        # Convert to DataFrame for easier handling
        features_df = pd.DataFrame(features_list)
        labels_series = pd.Series(labels_list)
        
        # Check class distribution
        class_counts = labels_series.value_counts()
        logger.info(f"Class distribution: {class_counts.to_dict()}")
        
        # Filter out classes with too few samples
        valid_classes = class_counts[class_counts >= min_samples_per_class].index
        if len(valid_classes) < 2:
            raise ValueError(f"Need at least 2 classes with {min_samples_per_class}+ samples each")
        
        # Filter data to only include valid classes
        valid_indices = labels_series.isin(valid_classes)
        features_df = features_df[valid_indices]
        labels_series = labels_series[valid_indices]
        
        # Handle missing values
        features_df = features_df.fillna(0)
        
        # Get feature names
        feature_names = features_df.columns.tolist()
        
        # Convert to numpy arrays
        X = features_df.values
        y = labels_series.values
        
        logger.info(f"Prepared {len(X)} training samples with {len(feature_names)} features")
        logger.info(f"Final class distribution: {pd.Series(y).value_counts().to_dict()}")
        
        return X, y, feature_names
    
    def train_model(
        self,
        X: np.ndarray,
        y: np.ndarray,
        model_type: str = "random_forest",
        hyperparameter_tuning: bool = True,
        cv_folds: int = 5
    ) -> Tuple[Any, Dict[str, float]]:
        """
        Train a machine learning model.
        
        Args:
            X: Feature matrix
            y: Target labels
            model_type: Type of model to train
            hyperparameter_tuning: Whether to perform hyperparameter tuning
            cv_folds: Number of cross-validation folds
            
        Returns:
            Tuple of (trained_model, metrics)
        """
        logger.info(f"Training {model_type} model")
        
        if model_type not in self.model_configs:
            raise ValueError(f"Unsupported model type: {model_type}")
        
        # Encode labels
        y_encoded = self.label_encoder.fit_transform(y)
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y_encoded, test_size=0.2, random_state=42, stratify=y_encoded
        )
        
        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        # Get model configuration
        config = self.model_configs[model_type]
        
        if hyperparameter_tuning:
            # Hyperparameter tuning with GridSearchCV
            logger.info("Performing hyperparameter tuning")
            grid_search = GridSearchCV(
                config['model_class'](),
                config['param_grid'],
                cv=cv_folds,
                scoring='accuracy',
                n_jobs=-1,
                verbose=1
            )
            grid_search.fit(X_train_scaled, y_train)
            model = grid_search.best_estimator_
            best_params = grid_search.best_params_
            logger.info(f"Best parameters: {best_params}")
        else:
            # Use default parameters
            model = config['model_class'](**config['default_params'])
            model.fit(X_train_scaled, y_train)
        
        # Evaluate model
        train_accuracy = model.score(X_train_scaled, y_train)
        test_accuracy = model.score(X_test_scaled, y_test)
        
        # Cross-validation score
        cv_scores = cross_val_score(model, X_train_scaled, y_train, cv=cv_folds)
        cv_mean = cv_scores.mean()
        cv_std = cv_scores.std()
        
        # Predictions for detailed metrics
        y_pred = model.predict(X_test_scaled)
        
        # Classification report
        class_names = self.label_encoder.classes_
        report = classification_report(y_test, y_pred, target_names=class_names, output_dict=True)
        
        metrics = {
            'training_accuracy': float(train_accuracy),
            'validation_accuracy': float(test_accuracy),
            'cv_mean_accuracy': float(cv_mean),
            'cv_std_accuracy': float(cv_std),
            'precision_macro': float(report['macro avg']['precision']),
            'recall_macro': float(report['macro avg']['recall']),
            'f1_macro': float(report['macro avg']['f1-score']),
            'training_samples': len(X_train),
            'test_samples': len(X_test),
            'n_classes': len(class_names),
            'class_names': class_names.tolist()
        }
        
        logger.info(f"Model training completed:")
        logger.info(f"  Training accuracy: {train_accuracy:.4f}")
        logger.info(f"  Validation accuracy: {test_accuracy:.4f}")
        logger.info(f"  CV accuracy: {cv_mean:.4f} (+/- {cv_std * 2:.4f})")
        
        return model, metrics
    
    def save_model(
        self,
        model: Any,
        model_name: str,
        version: str,
        feature_names: List[str],
        metrics: Dict[str, float],
        model_type: str = "random_forest"
    ) -> str:
        """
        Save trained model and associated artifacts.
        
        Args:
            model: Trained model object
            model_name: Name of the model
            version: Model version
            feature_names: List of feature names
            metrics: Model performance metrics
            model_type: Type of model
            
        Returns:
            Path to saved model file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        model_filename = f"{model_name}_{version}_{timestamp}.pkl"
        model_path = self.model_save_dir / model_filename
        
        # Create model package
        model_package = {
            'model': model,
            'scaler': self.scaler,
            'label_encoder': self.label_encoder,
            'feature_names': feature_names,
            'metrics': metrics,
            'model_type': model_type,
            'version': version,
            'created_at': datetime.now(),
            'feature_extractor_config': {
                'window_size': self.feature_extractor.window_size,
                'overlap': self.feature_extractor.overlap
            }
        }
        
        # Save model package
        with open(model_path, 'wb') as f:
            pickle.dump(model_package, f)
        
        logger.info(f"Model saved to {model_path}")
        return str(model_path)
    
    def load_model(self, model_path: str) -> Dict[str, Any]:
        """
        Load a saved model package.
        
        Args:
            model_path: Path to saved model file
            
        Returns:
            Dictionary containing model and associated artifacts
        """
        with open(model_path, 'rb') as f:
            model_package = pickle.load(f)
        
        logger.info(f"Model loaded from {model_path}")
        return model_package
    
    async def train_and_save_model(
        self,
        db: Session,
        model_name: str = "default_classifier",
        model_type: str = "random_forest",
        hyperparameter_tuning: bool = True
    ) -> MLModel:
        """
        Complete training pipeline: prepare data, train model, save model, update database.
        
        Args:
            db: Database session
            model_name: Name for the model
            model_type: Type of model to train
            hyperparameter_tuning: Whether to perform hyperparameter tuning
            
        Returns:
            MLModel database record
        """
        training_started_at = datetime.now()
        
        try:
            # Prepare training data
            X, y, feature_names = await self.prepare_training_data(db)
            
            # Train model
            model, metrics = self.train_model(
                X, y, model_type=model_type, hyperparameter_tuning=hyperparameter_tuning
            )
            
            # Generate version
            version = f"v{training_started_at.strftime('%Y%m%d_%H%M%S')}"
            
            # Save model
            model_path = self.save_model(
                model, model_name, version, feature_names, metrics, model_type
            )
            
            # Create database record
            db_model = MLModel(
                model_name=model_name,
                version=version,
                model_type=model_type,
                training_accuracy=metrics['training_accuracy'],
                validation_accuracy=metrics['validation_accuracy'],
                feature_names=feature_names,
                model_parameters=metrics,
                training_samples=metrics['training_samples'],
                training_started_at=training_started_at,
                training_completed_at=datetime.now(),
                is_active=True,  # Set as active by default
                model_file_path=model_path
            )
            
            # Deactivate other models of the same name
            db.query(MLModel).filter(
                MLModel.model_name == model_name,
                MLModel.is_active == True
            ).update({'is_active': False})
            
            db.add(db_model)
            db.commit()
            db.refresh(db_model)
            
            logger.info(f"Model training completed and saved: {model_name} {version}")
            return db_model
            
        except Exception as e:
            logger.error(f"Model training failed: {e}")
            raise
    
    def get_feature_importance(self, model_package: Dict[str, Any]) -> Dict[str, float]:
        """
        Get feature importance from trained model.
        
        Args:
            model_package: Loaded model package
            
        Returns:
            Dictionary of feature names and their importance scores
        """
        model = model_package['model']
        feature_names = model_package['feature_names']
        
        if hasattr(model, 'feature_importances_'):
            importance_scores = model.feature_importances_
            feature_importance = dict(zip(feature_names, importance_scores))
            
            # Sort by importance
            feature_importance = dict(sorted(
                feature_importance.items(), 
                key=lambda x: x[1], 
                reverse=True
            ))
            
            return feature_importance
        else:
            logger.warning("Model does not support feature importance")
            return {}
