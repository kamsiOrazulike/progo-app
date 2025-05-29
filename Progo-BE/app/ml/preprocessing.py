import numpy as np
import pandas as pd
from typing import List, Dict, Tuple, Optional
from scipy import signal
from scipy.stats import skew, kurtosis
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class FeatureExtractor:
    """
    Feature extraction pipeline for IMU sensor data.
    Converts raw sensor readings into ML-ready features.
    """
    
    def __init__(self, window_size: int = 200, overlap: float = 0.5):
        self.window_size = window_size
        self.overlap = overlap
        self.hop_size = int(window_size * (1 - overlap))
        
    def extract_features_from_readings(self, readings: List[Dict]) -> Dict[str, float]:
        """
        Extract features from a list of sensor readings.
        
        Args:
            readings: List of sensor reading dictionaries
            
        Returns:
            Dictionary of extracted features
        """
        if len(readings) < 10:  # Minimum readings needed
            raise ValueError("Need at least 10 readings for feature extraction")
            
        # Convert to structured arrays
        accel_data = np.array([[r['accel_x'], r['accel_y'], r['accel_z']] for r in readings])
        gyro_data = np.array([[r['gyro_x'], r['gyro_y'], r['gyro_z']] for r in readings])
        
        # Check if magnetometer data is available
        has_mag = all('mag_x' in r and r['mag_x'] is not None for r in readings)
        if has_mag:
            mag_data = np.array([[r['mag_x'], r['mag_y'], r['mag_z']] for r in readings])
        else:
            mag_data = None
            
        features = {}
        
        # Extract accelerometer features
        features.update(self._extract_sensor_features(accel_data, 'accel'))
        
        # Extract gyroscope features
        features.update(self._extract_sensor_features(gyro_data, 'gyro'))
        
        # Extract magnetometer features if available
        if has_mag:
            features.update(self._extract_sensor_features(mag_data, 'mag'))
        
        # Extract cross-sensor features
        features.update(self._extract_cross_sensor_features(accel_data, gyro_data))
        
        # Extract temporal features
        timestamps = [r.get('timestamp', 0) for r in readings]
        features.update(self._extract_temporal_features(timestamps, accel_data, gyro_data))
        
        return features
    
    def _extract_sensor_features(self, data: np.ndarray, prefix: str) -> Dict[str, float]:
        """Extract statistical and frequency features from sensor data."""
        features = {}
        
        # Calculate magnitude
        magnitude = np.sqrt(np.sum(data ** 2, axis=1))
        
        # Statistical features for each axis
        for i, axis in enumerate(['x', 'y', 'z']):
            axis_data = data[:, i]
            features.update({
                f'{prefix}_{axis}_mean': float(np.mean(axis_data)),
                f'{prefix}_{axis}_std': float(np.std(axis_data)),
                f'{prefix}_{axis}_min': float(np.min(axis_data)),
                f'{prefix}_{axis}_max': float(np.max(axis_data)),
                f'{prefix}_{axis}_range': float(np.max(axis_data) - np.min(axis_data)),
                f'{prefix}_{axis}_skew': float(skew(axis_data)),
                f'{prefix}_{axis}_kurtosis': float(kurtosis(axis_data)),
                f'{prefix}_{axis}_rms': float(np.sqrt(np.mean(axis_data ** 2))),
            })
            
            # Zero crossing rate
            features[f'{prefix}_{axis}_zcr'] = float(self._zero_crossing_rate(axis_data))
            
            # Peak features
            peaks, _ = signal.find_peaks(axis_data, height=np.mean(axis_data))
            features[f'{prefix}_{axis}_peak_count'] = len(peaks)
            features[f'{prefix}_{axis}_peak_freq'] = len(peaks) / len(axis_data) if len(axis_data) > 0 else 0
        
        # Magnitude features
        features.update({
            f'{prefix}_mag_mean': float(np.mean(magnitude)),
            f'{prefix}_mag_std': float(np.std(magnitude)),
            f'{prefix}_mag_min': float(np.min(magnitude)),
            f'{prefix}_mag_max': float(np.max(magnitude)),
            f'{prefix}_mag_range': float(np.max(magnitude) - np.min(magnitude)),
        })
        
        # Frequency domain features (if enough samples)
        if len(data) >= 32:
            features.update(self._extract_frequency_features(data, prefix))
            
        return features
    
    def _extract_frequency_features(self, data: np.ndarray, prefix: str) -> Dict[str, float]:
        """Extract frequency domain features using FFT."""
        features = {}
        
        for i, axis in enumerate(['x', 'y', 'z']):
            axis_data = data[:, i]
            
            # FFT
            fft = np.fft.fft(axis_data)
            fft_mag = np.abs(fft[:len(fft)//2])
            freqs = np.fft.fftfreq(len(axis_data))[:len(fft)//2]
            
            # Spectral features
            features[f'{prefix}_{axis}_spectral_centroid'] = float(np.sum(freqs * fft_mag) / np.sum(fft_mag)) if np.sum(fft_mag) > 0 else 0
            features[f'{prefix}_{axis}_spectral_rolloff'] = float(self._spectral_rolloff(fft_mag, freqs))
            features[f'{prefix}_{axis}_spectral_flux'] = float(np.sum(np.diff(fft_mag) ** 2))
            
            # Dominant frequency
            dominant_freq_idx = np.argmax(fft_mag)
            features[f'{prefix}_{axis}_dominant_freq'] = float(freqs[dominant_freq_idx])
            features[f'{prefix}_{axis}_dominant_freq_mag'] = float(fft_mag[dominant_freq_idx])
            
        return features
    
    def _extract_cross_sensor_features(self, accel_data: np.ndarray, gyro_data: np.ndarray) -> Dict[str, float]:
        """Extract features that combine accelerometer and gyroscope data."""
        features = {}
        
        # Calculate correlations between accel and gyro axes
        for i, axis in enumerate(['x', 'y', 'z']):
            corr = np.corrcoef(accel_data[:, i], gyro_data[:, i])[0, 1]
            features[f'accel_gyro_{axis}_correlation'] = float(corr) if not np.isnan(corr) else 0.0
        
        # Movement intensity
        accel_mag = np.sqrt(np.sum(accel_data ** 2, axis=1))
        gyro_mag = np.sqrt(np.sum(gyro_data ** 2, axis=1))
        
        features['movement_intensity'] = float(np.mean(accel_mag) * np.mean(gyro_mag))
        features['accel_gyro_ratio'] = float(np.mean(accel_mag) / np.mean(gyro_mag)) if np.mean(gyro_mag) > 0 else 0
        
        return features
    
    def _extract_temporal_features(self, timestamps: List, accel_data: np.ndarray, gyro_data: np.ndarray) -> Dict[str, float]:
        """Extract time-based features."""
        features = {}
        
        # Sampling rate estimation
        if len(timestamps) > 1:
            time_diffs = np.diff(timestamps)
            avg_sampling_interval = np.mean(time_diffs)
            features['estimated_sampling_rate'] = float(1000 / avg_sampling_interval) if avg_sampling_interval > 0 else 0
            features['sampling_jitter'] = float(np.std(time_diffs))
        else:
            features['estimated_sampling_rate'] = 0.0
            features['sampling_jitter'] = 0.0
        
        # Movement pattern features
        accel_mag = np.sqrt(np.sum(accel_data ** 2, axis=1))
        
        # Activity periods (above/below mean)
        mean_activity = np.mean(accel_mag)
        active_periods = accel_mag > mean_activity
        features['activity_ratio'] = float(np.sum(active_periods) / len(active_periods))
        
        # Rhythm detection (autocorrelation peaks)
        if len(accel_mag) > 20:
            autocorr = np.correlate(accel_mag, accel_mag, mode='full')
            autocorr = autocorr[autocorr.size // 2:]
            
            # Find peaks in autocorrelation
            peaks, _ = signal.find_peaks(autocorr[1:20], height=np.max(autocorr) * 0.3)
            features['rhythm_strength'] = float(np.max(autocorr[1:20]) / autocorr[0]) if autocorr[0] > 0 else 0
            features['primary_rhythm_period'] = float(peaks[0] + 1) if len(peaks) > 0 else 0
        else:
            features['rhythm_strength'] = 0.0
            features['primary_rhythm_period'] = 0.0
            
        return features
    
    def _zero_crossing_rate(self, data: np.ndarray) -> float:
        """Calculate zero crossing rate."""
        zero_crossings = np.where(np.diff(np.signbit(data)))[0]
        return len(zero_crossings) / len(data) if len(data) > 0 else 0
    
    def _spectral_rolloff(self, fft_mag: np.ndarray, freqs: np.ndarray, rolloff_threshold: float = 0.85) -> float:
        """Calculate spectral rolloff frequency."""
        total_energy = np.sum(fft_mag ** 2)
        threshold_energy = rolloff_threshold * total_energy
        
        cumulative_energy = np.cumsum(fft_mag ** 2)
        rolloff_idx = np.where(cumulative_energy >= threshold_energy)[0]
        
        return freqs[rolloff_idx[0]] if len(rolloff_idx) > 0 else 0.0
    
    def create_windows_from_readings(self, readings: List[Dict]) -> List[Dict[str, float]]:
        """
        Create sliding windows from sensor readings and extract features.
        
        Args:
            readings: List of sensor reading dictionaries
            
        Returns:
            List of feature dictionaries, one per window
        """
        if len(readings) < self.window_size:
            logger.warning(f"Not enough readings ({len(readings)}) for window size {self.window_size}")
            return []
        
        windows = []
        
        for start_idx in range(0, len(readings) - self.window_size + 1, self.hop_size):
            end_idx = start_idx + self.window_size
            window_readings = readings[start_idx:end_idx]
            
            try:
                features = self.extract_features_from_readings(window_readings)
                features['window_start_idx'] = start_idx
                features['window_end_idx'] = end_idx - 1
                features['window_size'] = len(window_readings)
                
                windows.append(features)
            except Exception as e:
                logger.error(f"Error extracting features for window {start_idx}-{end_idx}: {e}")
                continue
                
        return windows
    
    def get_feature_names(self) -> List[str]:
        """Get list of all possible feature names."""
        # This is a static list of all features that can be extracted
        base_features = [
            'mean', 'std', 'min', 'max', 'range', 'skew', 'kurtosis', 'rms', 'zcr',
            'peak_count', 'peak_freq', 'spectral_centroid', 'spectral_rolloff',
            'spectral_flux', 'dominant_freq', 'dominant_freq_mag'
        ]
        
        sensors = ['accel', 'gyro', 'mag']
        axes = ['x', 'y', 'z', 'mag']
        
        feature_names = []
        
        # Per-sensor, per-axis features
        for sensor in sensors:
            for axis in axes:
                for feature in base_features:
                    feature_names.append(f'{sensor}_{axis}_{feature}')
        
        # Cross-sensor features
        cross_features = [
            'accel_gyro_x_correlation', 'accel_gyro_y_correlation', 'accel_gyro_z_correlation',
            'movement_intensity', 'accel_gyro_ratio'
        ]
        feature_names.extend(cross_features)
        
        # Temporal features
        temporal_features = [
            'estimated_sampling_rate', 'sampling_jitter', 'activity_ratio',
            'rhythm_strength', 'primary_rhythm_period'
        ]
        feature_names.extend(temporal_features)
        
        return feature_names
