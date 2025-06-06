from .sensor_data import router as sensor_data_router
from .sessions import router as sessions_router
from .ml import router as ml_router
from .workouts import router as workouts_router
from .reps import router as reps_router
from .websocket import router as websocket_router

__all__ = [
    'sensor_data_router',
    'sessions_router', 
    'ml_router',
    'workouts_router',
    'reps_router',
    'websocket_router'
]
