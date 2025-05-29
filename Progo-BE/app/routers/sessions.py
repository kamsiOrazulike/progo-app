from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, func
from typing import List, Optional
from datetime import datetime

from app.database import get_sync_db
from app.models.schemas import (
    ExerciseSessionCreate, ExerciseSessionUpdate, ExerciseSessionResponse,
    ExerciseLabelCreate, ExerciseLabelResponse, APIResponse, PaginatedResponse
)
from app.models.database import ExerciseSession, ExerciseLabel, SensorReading
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sessions", tags=["Exercise Sessions"])


@router.post("/", response_model=ExerciseSessionResponse)
async def create_exercise_session(
    session_data: ExerciseSessionCreate,
    db: Session = Depends(get_sync_db)
):
    """
    Create a new exercise session.
    """
    try:
        db_session = ExerciseSession(
            device_id=session_data.device_id,
            exercise_type=session_data.exercise_type,
            notes=session_data.notes
        )
        
        db.add(db_session)
        db.commit()
        db.refresh(db_session)
        
        logger.info(f"Created exercise session {db_session.id} for device {session_data.device_id}")
        
        return ExerciseSessionResponse.from_orm(db_session)
        
    except Exception as e:
        logger.error(f"Error creating exercise session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=PaginatedResponse)
async def get_exercise_sessions(
    device_id: Optional[str] = Query(None, description="Filter by device ID"),
    exercise_type: Optional[str] = Query(None, description="Filter by exercise type"),
    is_labeled: Optional[bool] = Query(None, description="Filter by label status"),
    start_date: Optional[datetime] = Query(None, description="Filter from this date"),
    end_date: Optional[datetime] = Query(None, description="Filter to this date"),
    limit: int = Query(50, le=200, description="Maximum number of sessions"),
    offset: int = Query(0, ge=0, description="Number of sessions to skip"),
    db: Session = Depends(get_sync_db)
):
    """
    Get exercise sessions with filters and pagination.
    """
    try:
        # Build query with reading count
        query = db.query(
            ExerciseSession,
            func.count(SensorReading.id).label('reading_count')
        ).outerjoin(SensorReading, ExerciseSession.id == SensorReading.session_id).group_by(ExerciseSession.id)
        
        # Apply filters
        if device_id:
            query = query.filter(ExerciseSession.device_id == device_id)
        if exercise_type:
            query = query.filter(ExerciseSession.exercise_type == exercise_type)
        if is_labeled is not None:
            query = query.filter(ExerciseSession.is_labeled == is_labeled)
        if start_date:
            query = query.filter(ExerciseSession.start_time >= start_date)
        if end_date:
            query = query.filter(ExerciseSession.start_time <= end_date)
        
        # Get total count
        total = query.count()
        
        # Apply pagination and ordering
        results = query.order_by(desc(ExerciseSession.start_time)).offset(offset).limit(limit).all()
        
        # Convert to response models
        response_data = []
        for session, reading_count in results:
            session_response = ExerciseSessionResponse.from_orm(session)
            session_response.reading_count = reading_count
            response_data.append(session_response)
        
        return PaginatedResponse(
            items=response_data,
            total=total,
            page=offset // limit + 1,
            size=len(response_data),
            pages=(total + limit - 1) // limit
        )
        
    except Exception as e:
        logger.error(f"Error getting exercise sessions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{session_id}", response_model=ExerciseSessionResponse)
async def get_exercise_session(
    session_id: int,
    db: Session = Depends(get_sync_db)
):
    """
    Get a specific exercise session by ID.
    """
    try:
        # Get session with reading count
        result = db.query(
            ExerciseSession,
            func.count(SensorReading.id).label('reading_count')
        ).outerjoin(
            SensorReading, ExerciseSession.id == SensorReading.session_id
        ).filter(
            ExerciseSession.id == session_id
        ).group_by(ExerciseSession.id).first()
        
        if not result:
            raise HTTPException(status_code=404, detail="Exercise session not found")
        
        session, reading_count = result
        session_response = ExerciseSessionResponse.from_orm(session)
        session_response.reading_count = reading_count
        
        return session_response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting exercise session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{session_id}", response_model=ExerciseSessionResponse)
async def update_exercise_session(
    session_id: int,
    session_update: ExerciseSessionUpdate,
    db: Session = Depends(get_sync_db)
):
    """
    Update an exercise session.
    """
    try:
        db_session = db.query(ExerciseSession).filter(ExerciseSession.id == session_id).first()
        
        if not db_session:
            raise HTTPException(status_code=404, detail="Exercise session not found")
        
        # Update fields
        update_data = session_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_session, field, value)
        
        db.commit()
        db.refresh(db_session)
        
        logger.info(f"Updated exercise session {session_id}")
        
        return ExerciseSessionResponse.from_orm(db_session)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating exercise session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{session_id}/end", response_model=ExerciseSessionResponse)
async def end_exercise_session(
    session_id: int,
    db: Session = Depends(get_sync_db)
):
    """
    End an exercise session by setting the end time.
    """
    try:
        db_session = db.query(ExerciseSession).filter(ExerciseSession.id == session_id).first()
        
        if not db_session:
            raise HTTPException(status_code=404, detail="Exercise session not found")
        
        if db_session.end_time:
            raise HTTPException(status_code=400, detail="Session already ended")
        
        db_session.end_time = datetime.now()
        db.commit()
        db.refresh(db_session)
        
        logger.info(f"Ended exercise session {session_id}")
        
        return ExerciseSessionResponse.from_orm(db_session)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error ending exercise session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{session_id}")
async def delete_exercise_session(
    session_id: int,
    db: Session = Depends(get_sync_db)
):
    """
    Delete an exercise session and all associated data.
    """
    try:
        db_session = db.query(ExerciseSession).filter(ExerciseSession.id == session_id).first()
        
        if not db_session:
            raise HTTPException(status_code=404, detail="Exercise session not found")
        
        # Delete associated sensor readings
        reading_count = db.query(SensorReading).filter(SensorReading.session_id == session_id).count()
        db.query(SensorReading).filter(SensorReading.session_id == session_id).delete()
        
        # Delete associated labels
        label_count = db.query(ExerciseLabel).filter(ExerciseLabel.session_id == session_id).count()
        db.query(ExerciseLabel).filter(ExerciseLabel.session_id == session_id).delete()
        
        # Delete session
        db.delete(db_session)
        db.commit()
        
        logger.warning(f"Deleted exercise session {session_id} with {reading_count} readings and {label_count} labels")
        
        return APIResponse(
            success=True,
            message=f"Deleted session with {reading_count} readings and {label_count} labels",
            data={"session_id": session_id, "readings_deleted": reading_count, "labels_deleted": label_count}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting exercise session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Exercise Labeling Endpoints

@router.post("/{session_id}/labels", response_model=ExerciseLabelResponse)
async def create_exercise_label(
    session_id: int,
    label_data: ExerciseLabelCreate,
    db: Session = Depends(get_sync_db)
):
    """
    Create a label for a segment of an exercise session.
    """
    try:
        # Verify session exists
        session = db.query(ExerciseSession).filter(ExerciseSession.id == session_id).first()
        if not session:
            raise HTTPException(status_code=404, detail="Exercise session not found")
        
        # Verify that the reading IDs exist and belong to this session
        start_reading = db.query(SensorReading).filter(
            SensorReading.id == label_data.start_reading_id,
            SensorReading.session_id == session_id
        ).first()
        
        end_reading = db.query(SensorReading).filter(
            SensorReading.id == label_data.end_reading_id,
            SensorReading.session_id == session_id
        ).first()
        
        if not start_reading or not end_reading:
            raise HTTPException(
                status_code=400, 
                detail="Start or end reading not found in this session"
            )
        
        if start_reading.timestamp >= end_reading.timestamp:
            raise HTTPException(
                status_code=400, 
                detail="Start reading must be before end reading"
            )
        
        # Create label
        db_label = ExerciseLabel(
            session_id=session_id,
            start_reading_id=label_data.start_reading_id,
            end_reading_id=label_data.end_reading_id,
            exercise_type=label_data.exercise_type,
            repetitions=label_data.repetitions,
            quality_score=label_data.quality_score,
            labeled_by=label_data.labeled_by
        )
        
        db.add(db_label)
        
        # Mark session as labeled
        session.is_labeled = True
        
        db.commit()
        db.refresh(db_label)
        
        logger.info(f"Created exercise label for session {session_id}: {label_data.exercise_type}")
        
        return ExerciseLabelResponse.from_orm(db_label)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating exercise label: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{session_id}/labels", response_model=List[ExerciseLabelResponse])
async def get_exercise_labels(
    session_id: int,
    db: Session = Depends(get_sync_db)
):
    """
    Get all labels for an exercise session.
    """
    try:
        # Verify session exists
        session = db.query(ExerciseSession).filter(ExerciseSession.id == session_id).first()
        if not session:
            raise HTTPException(status_code=404, detail="Exercise session not found")
        
        labels = db.query(ExerciseLabel).filter(
            ExerciseLabel.session_id == session_id
        ).order_by(ExerciseLabel.labeled_at).all()
        
        return [ExerciseLabelResponse.from_orm(label) for label in labels]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting exercise labels: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/labels/{label_id}")
async def delete_exercise_label(
    label_id: int,
    db: Session = Depends(get_sync_db)
):
    """
    Delete an exercise label.
    """
    try:
        label = db.query(ExerciseLabel).filter(ExerciseLabel.id == label_id).first()
        
        if not label:
            raise HTTPException(status_code=404, detail="Exercise label not found")
        
        session_id = label.session_id
        db.delete(label)
        
        # Check if session still has labels
        remaining_labels = db.query(ExerciseLabel).filter(ExerciseLabel.session_id == session_id).count()
        if remaining_labels == 0:
            # Mark session as not labeled
            session = db.query(ExerciseSession).filter(ExerciseSession.id == session_id).first()
            if session:
                session.is_labeled = False
        
        db.commit()
        
        logger.info(f"Deleted exercise label {label_id}")
        
        return APIResponse(
            success=True,
            message="Exercise label deleted successfully",
            data={"label_id": label_id}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting exercise label: {e}")
        raise HTTPException(status_code=500, detail=str(e))
