from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from datetime import datetime

from ..database import get_db
from ..models.database import WorkoutSession, RepEvent, RepPattern, WorkoutStatus
from ..models.schemas import (
    WorkoutSessionCreate, WorkoutSessionUpdate, WorkoutSessionResponse,
    RepEventResponse, RepPatternResponse, APIResponse
)
from ..ml.workout_manager import WorkoutManager
from ..websocket.manager import ConnectionManager

router = APIRouter(prefix="/workouts", tags=["workouts"])

# Global instances
workout_manager = WorkoutManager()
connection_manager = ConnectionManager()


@router.post("/start", response_model=WorkoutSessionResponse)
async def start_workout(
    workout_data: WorkoutSessionCreate,
    db: AsyncSession = Depends(get_db)
):
    """Start a new workout session"""
    try:
        # Create new workout session
        workout_session = WorkoutSession(
            device_id=workout_data.device_id,
            exercise_type=workout_data.exercise_type.value,
            target_reps_per_set=workout_data.target_reps,
            target_sets=workout_data.target_sets,
            status=WorkoutStatus.active,
            current_set=1,
            current_reps=0
        )
        
        db.add(workout_session)
        await db.commit()
        await db.refresh(workout_session)
        
        # Start workout in manager
        await workout_manager.start_workout(
            device_id=workout_data.device_id,
            exercise_type=workout_data.exercise_type,
            workout_session_id=workout_session.id
        )
        
        return workout_session
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start workout: {str(e)}"
        )


@router.post("/", response_model=WorkoutSessionResponse)
async def create_workout(
    workout_data: WorkoutSessionCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create and start a new workout session (alias for /start)"""
    return await start_workout(workout_data, db)


@router.get("/current/{device_id}", response_model=Optional[WorkoutSessionResponse])
async def get_current_workout(device_id: str, db: AsyncSession = Depends(get_db)):
    """Get the current active workout for a device"""
    result = await db.execute(
        select(WorkoutSession).where(
            WorkoutSession.device_id == device_id,
            WorkoutSession.status == "active"
        )
    )
    current_workout = result.scalar_one_or_none()
    
    return current_workout


@router.put("/{workout_id}", response_model=WorkoutSessionResponse)
async def update_workout(
    workout_id: int,
    workout_update: WorkoutSessionUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update an existing workout session"""
    result = await db.execute(
        select(WorkoutSession).where(WorkoutSession.id == workout_id)
    )
    workout = result.scalar_one_or_none()
    
    if not workout:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workout session not found"
        )
    
    # Update fields
    if workout_update.status:
        workout.status = workout_update.status.value
        if workout_update.status.value == "completed":
            workout.completed_at = datetime.utcnow()
    
    if workout_update.current_set is not None:
        workout.current_set = workout_update.current_set
    
    if workout_update.current_reps is not None:
        workout.current_reps = workout_update.current_reps
    
    if workout_update.notes:
        workout.notes = workout_update.notes
    
    await db.commit()
    await db.refresh(workout)
    
    return workout


@router.get("/", response_model=List[WorkoutSessionResponse])
async def list_workouts(
    device_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    """List workout sessions with optional filtering"""
    query = select(WorkoutSession)
    
    if device_id:
        query = query.where(WorkoutSession.device_id == device_id)
    
    if status:
        query = query.where(WorkoutSession.status == status)
    
    query = query.order_by(WorkoutSession.started_at.desc()).limit(limit)
    result = await db.execute(query)
    workouts = result.scalars().all()
    
    if not workouts:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No workouts found"
        )
    
    return workouts


@router.post("/{workout_id}/complete", response_model=APIResponse)
async def complete_workout(workout_id: int, db: AsyncSession = Depends(get_db)):
    """Complete a workout session"""
    result = await db.execute(
        select(WorkoutSession).where(WorkoutSession.id == workout_id)
    )
    workout = result.scalar_one_or_none()
    
    if not workout:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workout session not found"
        )
    
    if workout.status != "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Workout is not active"
        )
    
    # Complete workout
    workout.status = "completed"
    workout.completed_at = datetime.utcnow()
    
    # Update total sets if current set has reps
    if workout.current_reps > 0:
        workout.total_sets = workout.current_set
    else:
        workout.total_sets = max(0, workout.current_set - 1)
    
    await db.commit()
    
    # Stop workout in manager
    await workout_manager.stop_workout(workout.device_id)
    
    # Notify via WebSocket
    await connection_manager.broadcast_to_device(
        workout.device_id,
        {
            "type": "workout_completed",
            "workout_id": workout.id,
            "total_reps": workout.total_reps,
            "total_sets": workout.total_sets,
            "duration_minutes": (workout.completed_at - workout.started_at).total_seconds() / 60
        }
    )
    
    return APIResponse(success=True, message="Workout completed successfully")


@router.post("/{workout_id}/pause", response_model=APIResponse)
async def pause_workout(workout_id: int, db: AsyncSession = Depends(get_db)):
    """Pause a workout session"""
    result = await db.execute(
        select(WorkoutSession).where(WorkoutSession.id == workout_id)
    )
    workout = result.scalar_one_or_none()
    
    if not workout:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workout session not found"
        )
    
    if workout.status != "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Workout is not active"
        )
    
    workout.status = "paused"
    await db.commit()
    
    return APIResponse(success=True, message="Workout paused")


@router.post("/{workout_id}/resume", response_model=APIResponse)
async def resume_workout(workout_id: int, db: AsyncSession = Depends(get_db)):
    """Resume a paused workout session"""
    result = await db.execute(
        select(WorkoutSession).where(WorkoutSession.id == workout_id)
    )
    workout = result.scalar_one_or_none()
    
    if not workout:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workout session not found"
        )
    
    if workout.status != "paused":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Workout is not paused"
        )
    
    workout.status = "active"
    await db.commit()
    
    return APIResponse(success=True, message="Workout resumed")


@router.get("/{workout_id}/events", response_model=List[RepEventResponse])
async def get_workout_events(workout_id: int, db: AsyncSession = Depends(get_db)):
    """Get all rep events for a workout session"""
    result = await db.execute(
        select(RepEvent).where(RepEvent.workout_session_id == workout_id)
        .order_by(RepEvent.timestamp.desc())
    )
    events = result.scalars().all()
    
    return events


@router.get("/history/{device_id}", response_model=List[WorkoutSessionResponse])
async def get_workout_history(
    device_id: str,
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    """Get workout history for a device"""
    result = await db.execute(
        select(WorkoutSession).where(WorkoutSession.device_id == device_id)
        .order_by(WorkoutSession.started_at.desc())
        .offset(offset)
        .limit(limit)
    )
    workouts = result.scalars().all()
    
    return workouts


@router.get("/stats/{device_id}")
async def get_workout_stats(device_id: str, db: AsyncSession = Depends(get_db)):
    """Get workout statistics for a device"""
    from sqlalchemy import func
    
    # Total workouts
    total_workouts_result = await db.execute(
        select(func.count(WorkoutSession.id)).where(WorkoutSession.device_id == device_id)
    )
    total_workouts = total_workouts_result.scalar()
    
    # Completed workouts
    completed_workouts_result = await db.execute(
        select(func.count(WorkoutSession.id)).where(
            WorkoutSession.device_id == device_id,
            WorkoutSession.status == "completed"
        )
    )
    completed_workouts = completed_workouts_result.scalar()
    
    # Total reps across all workouts
    total_reps_result = await db.execute(
        select(WorkoutSession.total_reps).where(
            WorkoutSession.device_id == device_id,
            WorkoutSession.status == "completed"
        )
    )
    total_reps = total_reps_result.scalars().all()
    
    total_reps_sum = sum(reps or 0 for reps in total_reps)
    
    # Average reps per workout
    avg_reps = total_reps_sum / completed_workouts if completed_workouts > 0 else 0
    
    return {
        "total_workouts": total_workouts,
        "completed_workouts": completed_workouts,
        "total_reps": total_reps_sum,
        "average_reps_per_workout": round(avg_reps, 1),
        "completion_rate": round(completed_workouts / total_workouts * 100, 1) if total_workouts > 0 else 0
    }
