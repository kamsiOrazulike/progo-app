import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import numpy as np


def calculate_movement_metrics(sensor_readings: List[Dict]) -> Dict[str, float]:
    """
    Calculate movement metrics from sensor data.
    
    Args:
        sensor_readings: List of sensor reading dictionaries
        
    Returns:
        Dictionary of movement metrics
    """
    if not sensor_readings:
        return {}
    
    # Extract accelerometer data
    accel_data = np.array([
        [r['accel_x'], r['accel_y'], r['accel_z']] 
        for r in sensor_readings
    ])
    
    # Calculate magnitude
    accel_magnitude = np.sqrt(np.sum(accel_data ** 2, axis=1))
    
    # Basic movement metrics
    metrics = {
        'movement_intensity': float(np.mean(accel_magnitude)),
        'movement_variability': float(np.std(accel_magnitude)),
        'max_acceleration': float(np.max(accel_magnitude)),
        'min_acceleration': float(np.min(accel_magnitude)),
        'duration_seconds': len(sensor_readings) * 0.05,  # Assuming 20Hz sampling
        'total_samples': len(sensor_readings)
    }
    
    # Activity detection (above/below baseline)
    baseline = np.mean(accel_magnitude)
    active_samples = np.sum(accel_magnitude > baseline * 1.2)
    metrics['activity_ratio'] = float(active_samples / len(accel_magnitude))
    
    return metrics


def validate_sensor_data(sensor_data: Dict) -> bool:
    """
    Validate that sensor data is within reasonable ranges.
    
    Args:
        sensor_data: Dictionary containing sensor readings
        
    Returns:
        True if data is valid, False otherwise
    """
    # Accelerometer range check (±16g typically)
    accel_limit = 160  # m/s²
    if (abs(sensor_data.get('accel_x', 0)) > accel_limit or
        abs(sensor_data.get('accel_y', 0)) > accel_limit or
        abs(sensor_data.get('accel_z', 0)) > accel_limit):
        return False
    
    # Gyroscope range check (±2000 dps typically)
    gyro_limit = 35  # rad/s (roughly 2000 dps)
    if (abs(sensor_data.get('gyro_x', 0)) > gyro_limit or
        abs(sensor_data.get('gyro_y', 0)) > gyro_limit or
        abs(sensor_data.get('gyro_z', 0)) > gyro_limit):
        return False
    
    # Magnetometer range check (if available)
    if sensor_data.get('magnetometer_available', False):
        mag_limit = 50000  # µT
        if (abs(sensor_data.get('mag_x', 0)) > mag_limit or
            abs(sensor_data.get('mag_y', 0)) > mag_limit or
            abs(sensor_data.get('mag_z', 0)) > mag_limit):
            return False
    
    # Temperature range check (if available)
    if sensor_data.get('temperature') is not None:
        temp = sensor_data['temperature']
        if temp < -40 or temp > 85:  # Typical sensor range
            return False
    
    return True


def detect_exercise_segments(sensor_readings: List[Dict], threshold_ratio: float = 1.5) -> List[Dict]:
    """
    Detect potential exercise segments in sensor data based on activity level.
    
    Args:
        sensor_readings: List of sensor reading dictionaries
        threshold_ratio: Multiplier for baseline to detect activity
        
    Returns:
        List of detected segments with start/end indices
    """
    if len(sensor_readings) < 10:
        return []
    
    # Calculate movement intensity
    accel_data = np.array([
        [r['accel_x'], r['accel_y'], r['accel_z']] 
        for r in sensor_readings
    ])
    accel_magnitude = np.sqrt(np.sum(accel_data ** 2, axis=1))
    
    # Smooth the signal
    window_size = min(5, len(accel_magnitude) // 4)
    smoothed = np.convolve(accel_magnitude, np.ones(window_size)/window_size, mode='same')
    
    # Calculate baseline (median of lower 25% of values)
    baseline = np.percentile(smoothed, 25)
    threshold = baseline * threshold_ratio
    
    # Find segments above threshold
    above_threshold = smoothed > threshold
    
    segments = []
    in_segment = False
    start_idx = 0
    
    for i, is_active in enumerate(above_threshold):
        if is_active and not in_segment:
            # Start of segment
            start_idx = i
            in_segment = True
        elif not is_active and in_segment:
            # End of segment
            if i - start_idx >= 10:  # Minimum segment length
                segments.append({
                    'start_index': start_idx,
                    'end_index': i - 1,
                    'duration_samples': i - start_idx,
                    'max_intensity': float(np.max(smoothed[start_idx:i])),
                    'avg_intensity': float(np.mean(smoothed[start_idx:i]))
                })
            in_segment = False
    
    # Handle case where last segment extends to end
    if in_segment and len(above_threshold) - start_idx >= 10:
        segments.append({
            'start_index': start_idx,
            'end_index': len(above_threshold) - 1,
            'duration_samples': len(above_threshold) - start_idx,
            'max_intensity': float(np.max(smoothed[start_idx:])),
            'avg_intensity': float(np.mean(smoothed[start_idx:]))
        })
    
    return segments


def calculate_sampling_rate(timestamps: List[int]) -> float:
    """
    Calculate the sampling rate from timestamps.
    
    Args:
        timestamps: List of timestamps in milliseconds
        
    Returns:
        Estimated sampling rate in Hz
    """
    if len(timestamps) < 2:
        return 0.0
    
    # Calculate intervals
    intervals = np.diff(timestamps)
    
    # Remove outliers (keep middle 80%)
    intervals_sorted = np.sort(intervals)
    start_idx = int(len(intervals_sorted) * 0.1)
    end_idx = int(len(intervals_sorted) * 0.9)
    clean_intervals = intervals_sorted[start_idx:end_idx]
    
    if len(clean_intervals) == 0:
        return 0.0
    
    # Calculate average interval in milliseconds
    avg_interval_ms = np.mean(clean_intervals)
    
    # Convert to Hz
    if avg_interval_ms > 0:
        return 1000.0 / avg_interval_ms
    else:
        return 0.0


def format_duration(seconds: float) -> str:
    """
    Format duration in seconds to human-readable string.
    
    Args:
        seconds: Duration in seconds
        
    Returns:
        Formatted duration string
    """
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}h"


def generate_session_id() -> str:
    """
    Generate a unique session ID based on current timestamp.
    
    Returns:
        Unique session ID string
    """
    return f"session_{int(time.time() * 1000)}"


def is_within_time_window(timestamp: datetime, window_minutes: int = 5) -> bool:
    """
    Check if a timestamp is within a recent time window.
    
    Args:
        timestamp: Timestamp to check
        window_minutes: Time window in minutes
        
    Returns:
        True if timestamp is within the window
    """
    now = datetime.now()
    cutoff = now - timedelta(minutes=window_minutes)
    return timestamp >= cutoff
