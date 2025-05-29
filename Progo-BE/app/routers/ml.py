from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional

from app.database import get_sync_db
from app.models.schemas import (
    ModelTrainingRequest, ModelPredictionRequest, ModelPredictionResponse,
    ModelStatusResponse, APIResponse, SensorDataInput
)
from app.models.database import MLModel, ModelPrediction
from app.ml.training import ModelTrainer
from app.ml.inference import inference_engine
import logging
import asyncio

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ml", tags=["Machine Learning"])


@router.post("/train", response_model=APIResponse)
async def train_model(
    training_request: ModelTrainingRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_sync_db)
):
    """
    Trigger model training in the background.
    """
    try:
        # Check if there's already a model training
        existing_training = db.query(MLModel).filter(
            MLModel.model_name == training_request.model_name,
            MLModel.training_completed_at.is_(None)
        ).first()
        
        if existing_training:
            raise HTTPException(
                status_code=400, 
                detail="Model training already in progress"
            )
        
        # Start training in background
        background_tasks.add_task(
            _train_model_background,
            training_request,
            db
        )
        
        logger.info(f"Started background training for model: {training_request.model_name}")
        
        return APIResponse(
            success=True,
            message=f"Model training started for {training_request.model_name}",
            data={"model_name": training_request.model_name, "status": "training_started"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting model training: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def _train_model_background(training_request: ModelTrainingRequest, db: Session):
    """
    Background task for model training.
    """
    try:
        trainer = ModelTrainer()
        
        # Train and save model
        trained_model = await trainer.train_and_save_model(
            db=db,
            model_name=training_request.model_name,
            model_type=training_request.model_type,
            hyperparameter_tuning=True
        )
        
        # Load the new model in inference engine
        inference_engine.load_active_model(db, training_request.model_name)
        
        logger.info(f"Background training completed for model: {training_request.model_name}")
        
    except Exception as e:
        logger.error(f"Background training failed: {e}")


@router.post("/predict", response_model=ModelPredictionResponse)
async def predict_exercise(
    prediction_request: ModelPredictionRequest,
    save_prediction: bool = True,
    db: Session = Depends(get_sync_db)
):
    """
    Predict exercise type from sensor data.
    """
    try:
        # Check if model is loaded
        if not inference_engine.model_package:
            # Try to load the active model
            if not inference_engine.load_active_model(db, "default_classifier"):
                raise HTTPException(
                    status_code=503, 
                    detail="No trained model available for prediction"
                )
        
        # Make prediction
        prediction = inference_engine.predict_from_sensor_list(
            prediction_request.sensor_data,
            return_features=True
        )
        
        if not prediction:
            raise HTTPException(
                status_code=400, 
                detail="Unable to make prediction - insufficient data or processing error"
            )
        
        # Save prediction to database if requested
        if save_prediction:
            await inference_engine.save_prediction(
                db=db,
                prediction=prediction,
                features=prediction.features_used
            )
        
        logger.info(f"Prediction made: {prediction.predicted_exercise} (confidence: {prediction.confidence_score:.3f})")
        
        return prediction
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error making prediction: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/predict/realtime/{device_id}", response_model=ModelPredictionResponse)
async def predict_exercise_realtime(
    device_id: str,
    save_prediction: bool = True,
    db: Session = Depends(get_sync_db)
):
    """
    Predict exercise type from real-time sensor buffer for a device.
    """
    try:
        # Check if model is loaded
        if not inference_engine.model_package:
            # Try to load the active model
            if not inference_engine.load_active_model(db, "default_classifier"):
                raise HTTPException(
                    status_code=503, 
                    detail="No trained model available for prediction"
                )
        
        # Check buffer status
        buffer_status = inference_engine.get_buffer_status(device_id)
        if not buffer_status['ready_for_prediction']:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient data for prediction. Need {buffer_status['required_samples']} samples, have {buffer_status['buffer_size']}"
            )
        
        # Make prediction
        prediction = inference_engine.predict_exercise(device_id, return_features=True)
        
        if not prediction:
            raise HTTPException(
                status_code=400, 
                detail="Unable to make prediction from buffer data"
            )
        
        # Save prediction to database if requested
        if save_prediction:
            await inference_engine.save_prediction(
                db=db,
                prediction=prediction,
                features=prediction.features_used
            )
        
        logger.info(f"Real-time prediction for {device_id}: {prediction.predicted_exercise} (confidence: {prediction.confidence_score:.3f})")
        
        return prediction
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error making real-time prediction: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/models", response_model=List[ModelStatusResponse])
async def get_models(
    model_name: Optional[str] = None,
    active_only: bool = False,
    db: Session = Depends(get_sync_db)
):
    """
    Get information about available ML models.
    """
    try:
        query = db.query(MLModel)
        
        if model_name:
            query = query.filter(MLModel.model_name == model_name)
        if active_only:
            query = query.filter(MLModel.is_active == True)
        
        models = query.order_by(desc(MLModel.created_at)).all()
        
        return [ModelStatusResponse.from_orm(model) for model in models]
        
    except Exception as e:
        logger.error(f"Error getting models: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/models/{model_id}", response_model=ModelStatusResponse)
async def get_model(
    model_id: int,
    db: Session = Depends(get_sync_db)
):
    """
    Get information about a specific ML model.
    """
    try:
        model = db.query(MLModel).filter(MLModel.id == model_id).first()
        
        if not model:
            raise HTTPException(status_code=404, detail="Model not found")
        
        return ModelStatusResponse.from_orm(model)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting model: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/models/{model_id}/activate", response_model=APIResponse)
async def activate_model(
    model_id: int,
    db: Session = Depends(get_sync_db)
):
    """
    Activate a specific model for inference.
    """
    try:
        model = db.query(MLModel).filter(MLModel.id == model_id).first()
        
        if not model:
            raise HTTPException(status_code=404, detail="Model not found")
        
        # Deactivate other models with the same name
        db.query(MLModel).filter(
            MLModel.model_name == model.model_name,
            MLModel.is_active == True
        ).update({'is_active': False})
        
        # Activate this model
        model.is_active = True
        db.commit()
        
        # Load model in inference engine
        success = inference_engine.load_active_model(db, model.model_name)
        
        if not success:
            raise HTTPException(
                status_code=500, 
                detail="Model activated but failed to load for inference"
            )
        
        logger.info(f"Activated model: {model.model_name} {model.version}")
        
        return APIResponse(
            success=True,
            message=f"Model {model.model_name} {model.version} activated",
            data={"model_id": model_id, "model_name": model.model_name, "version": model.version}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error activating model: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/models/{model_id}")
async def delete_model(
    model_id: int,
    db: Session = Depends(get_sync_db)
):
    """
    Delete a ML model and its associated files.
    """
    try:
        model = db.query(MLModel).filter(MLModel.id == model_id).first()
        
        if not model:
            raise HTTPException(status_code=404, detail="Model not found")
        
        if model.is_active:
            raise HTTPException(
                status_code=400, 
                detail="Cannot delete active model. Activate another model first."
            )
        
        # Delete associated predictions
        prediction_count = db.query(ModelPrediction).filter(
            ModelPrediction.model_version == model.version
        ).count()
        
        db.query(ModelPrediction).filter(
            ModelPrediction.model_version == model.version
        ).delete()
        
        # Delete model file if it exists
        import os
        if model.model_file_path and os.path.exists(model.model_file_path):
            os.remove(model.model_file_path)
        
        # Delete model record
        db.delete(model)
        db.commit()
        
        logger.warning(f"Deleted model {model.model_name} {model.version} and {prediction_count} predictions")
        
        return APIResponse(
            success=True,
            message=f"Model deleted along with {prediction_count} predictions",
            data={"model_id": model_id, "predictions_deleted": prediction_count}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting model: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_ml_status(db: Session = Depends(get_sync_db)):
    """
    Get current ML system status.
    """
    try:
        # Get active model info
        active_model = db.query(MLModel).filter(MLModel.is_active == True).first()
        
        # Get inference engine status
        performance_stats = inference_engine.get_performance_stats()
        
        # Get buffer status for all devices
        device_buffers = {}
        for device_id in inference_engine.sensor_buffers.keys():
            device_buffers[device_id] = inference_engine.get_buffer_status(device_id)
        
        # Count total predictions made
        total_predictions = db.query(ModelPrediction).count()
        
        return {
            "active_model": {
                "name": active_model.model_name if active_model else None,
                "version": active_model.version if active_model else None,
                "accuracy": active_model.validation_accuracy if active_model else None,
                "created_at": active_model.created_at if active_model else None
            },
            "inference_engine": performance_stats,
            "device_buffers": device_buffers,
            "total_predictions_in_db": total_predictions,
            "system_ready": inference_engine.model_package is not None
        }
        
    except Exception as e:
        logger.error(f"Error getting ML status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/buffer/{device_id}/clear", response_model=APIResponse)
async def clear_device_buffer(device_id: str):
    """
    Clear the sensor data buffer for a specific device.
    """
    try:
        success = inference_engine.clear_buffer(device_id)
        
        if success:
            return APIResponse(
                success=True,
                message=f"Buffer cleared for device {device_id}",
                data={"device_id": device_id}
            )
        else:
            raise HTTPException(status_code=404, detail="Device buffer not found")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error clearing device buffer: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/buffer/{device_id}/status")
async def get_device_buffer_status(device_id: str):
    """
    Get the status of sensor data buffer for a specific device.
    """
    try:
        buffer_status = inference_engine.get_buffer_status(device_id)
        return buffer_status
        
    except Exception as e:
        logger.error(f"Error getting device buffer status: {e}")
        raise HTTPException(status_code=500, detail=str(e))
