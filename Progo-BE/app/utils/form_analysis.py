"""
Form Analysis Module for Bicep Curl Comparison

This module provides functionality to compare live IMU readings against
reference bicep curl data to provide form feedback and scoring.
"""

import logging
import numpy as np
from typing import List, Dict, Any, Tuple
from datetime import datetime
from .reference_data import ReferenceDataLoader

logger = logging.getLogger(__name__)


class FormAnalyzer:
    """
    Analyzes bicep curl form by comparing live IMU data against reference patterns.
    """
    
    def __init__(self):
        self.reference_loader = ReferenceDataLoader()
        self.reference_data = None
        self._load_reference_data()
    
    def _load_reference_data(self):
        """Load reference bicep curl data on initialization."""
        try:
            self.reference_data = self.reference_loader.load_reference_bicep_curl()
            logger.info(f"Loaded {len(self.reference_data)} reference readings for form analysis")
        except Exception as e:
            logger.error(f"Failed to load reference data: {e}")
            self.reference_data = None
    
    def analyze_form(self, live_readings: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze bicep curl form by comparing live readings against reference data.
        
        Args:
            live_readings: List of IMU readings with accel_x, accel_y, accel_z, 
                          gyro_x, gyro_y, gyro_z, timestamp
        
        Returns:
            Dictionary with form_score, feedback, and detailed analysis
        """
        if not self.reference_data:
            return {
                "form_score": 0,
                "feedback": "Reference data not available",
                "analysis": {
                    "range_score": 0,
                    "smoothness_score": 0,
                    "consistency_score": 0
                }
            }
        
        if not live_readings or len(live_readings) < 5:
            return {
                "form_score": 0,
                "feedback": "Insufficient data for analysis (need at least 5 readings)",
                "analysis": {
                    "range_score": 0,
                    "smoothness_score": 0,
                    "consistency_score": 0
                }
            }
        
        try:
            # Extract data arrays for analysis
            live_data = self._extract_sensor_arrays(live_readings)
            ref_data = self._extract_sensor_arrays(self.reference_data)
            
            # Perform individual analyses
            range_score = self._analyze_range_of_motion(live_data, ref_data)
            smoothness_score = self._analyze_smoothness(live_data)
            consistency_score = self._analyze_consistency(live_data, ref_data)
            
            # Calculate overall form score (weighted average)
            form_score = int(
                range_score * 0.4 +        # 40% weight on range of motion
                smoothness_score * 0.35 +   # 35% weight on smoothness
                consistency_score * 0.25    # 25% weight on consistency
            )
            
            # Generate feedback message
            feedback = self._generate_feedback(form_score, range_score, smoothness_score, consistency_score)
            
            return {
                "form_score": form_score,
                "feedback": feedback,
                "analysis": {
                    "range_score": int(range_score),
                    "smoothness_score": int(smoothness_score),
                    "consistency_score": int(consistency_score)
                }
            }
            
        except Exception as e:
            logger.error(f"Error during form analysis: {e}")
            return {
                "form_score": 0,
                "feedback": f"Analysis error: {str(e)}",
                "analysis": {
                    "range_score": 0,
                    "smoothness_score": 0,
                    "consistency_score": 0
                }
            }
    
    def _extract_sensor_arrays(self, readings: List[Dict[str, Any]]) -> Dict[str, np.ndarray]:
        """Extract sensor data into numpy arrays for analysis."""
        return {
            'accel_x': np.array([r['accel_x'] for r in readings]),
            'accel_y': np.array([r['accel_y'] for r in readings]),
            'accel_z': np.array([r['accel_z'] for r in readings]),
            'gyro_x': np.array([r['gyro_x'] for r in readings]),
            'gyro_y': np.array([r['gyro_y'] for r in readings]),
            'gyro_z': np.array([r['gyro_z'] for r in readings])
        }
    
    def _analyze_range_of_motion(self, live_data: Dict[str, np.ndarray], ref_data: Dict[str, np.ndarray]) -> float:
        """
        Analyze range of motion by comparing gyro_x patterns (primary bicep curl movement).
        """
        try:
            # Calculate range of motion for gyro_x (elbow rotation)
            live_gyro_range = np.max(live_data['gyro_x']) - np.min(live_data['gyro_x'])
            ref_gyro_range = np.max(ref_data['gyro_x']) - np.min(ref_data['gyro_x'])
            
            # Calculate acceleration magnitude range
            live_accel_mag = np.sqrt(live_data['accel_x']**2 + live_data['accel_y']**2 + live_data['accel_z']**2)
            ref_accel_mag = np.sqrt(ref_data['accel_x']**2 + ref_data['accel_y']**2 + ref_data['accel_z']**2)
            
            live_accel_range = np.max(live_accel_mag) - np.min(live_accel_mag)
            ref_accel_range = np.max(ref_accel_mag) - np.min(ref_accel_mag)
            
            # Compare ranges (closer to reference = higher score)
            gyro_similarity = min(live_gyro_range / ref_gyro_range, ref_gyro_range / live_gyro_range) if ref_gyro_range > 0 else 0
            accel_similarity = min(live_accel_range / ref_accel_range, ref_accel_range / live_accel_range) if ref_accel_range > 0 else 0
            
            # Combine scores (weight gyro more heavily for bicep curls)
            range_score = (gyro_similarity * 0.7 + accel_similarity * 0.3) * 100
            
            return min(100, max(0, range_score))
            
        except Exception as e:
            logger.warning(f"Range analysis error: {e}")
            return 50.0
    
    def _analyze_smoothness(self, live_data: Dict[str, np.ndarray]) -> float:
        """
        Analyze movement smoothness by looking at acceleration and gyro jerkiness.
        """
        try:
            # Calculate derivatives (jerk) for smoothness analysis
            accel_mag = np.sqrt(live_data['accel_x']**2 + live_data['accel_y']**2 + live_data['accel_z']**2)
            gyro_mag = np.sqrt(live_data['gyro_x']**2 + live_data['gyro_y']**2 + live_data['gyro_z']**2)
            
            # Calculate jerk (rate of change of acceleration)
            if len(accel_mag) > 1:
                accel_jerk = np.diff(accel_mag)
                gyro_jerk = np.diff(gyro_mag)
                
                # Lower standard deviation = smoother movement
                accel_smoothness = 1 / (1 + np.std(accel_jerk))
                gyro_smoothness = 1 / (1 + np.std(gyro_jerk))
                
                # Combine smoothness scores
                smoothness_score = (accel_smoothness + gyro_smoothness) / 2 * 100
            else:
                smoothness_score = 50.0
            
            return min(100, max(0, smoothness_score))
            
        except Exception as e:
            logger.warning(f"Smoothness analysis error: {e}")
            return 50.0
    
    def _analyze_consistency(self, live_data: Dict[str, np.ndarray], ref_data: Dict[str, np.ndarray]) -> float:
        """
        Analyze consistency by comparing overall movement patterns with reference.
        """
        try:
            # Normalize data lengths for comparison
            live_len = len(live_data['gyro_x'])
            ref_len = len(ref_data['gyro_x'])
            
            if live_len < 5 or ref_len < 5:
                return 50.0
            
            # Resample to same length for comparison
            if live_len != ref_len:
                # Simple linear interpolation approach
                indices = np.linspace(0, live_len - 1, ref_len).astype(int)
                live_gyro_x_resampled = live_data['gyro_x'][indices]
                live_accel_y_resampled = live_data['accel_y'][indices]
            else:
                live_gyro_x_resampled = live_data['gyro_x']
                live_accel_y_resampled = live_data['accel_y']
            
            # Calculate correlation with reference patterns
            gyro_correlation = np.corrcoef(live_gyro_x_resampled, ref_data['gyro_x'])[0, 1]
            accel_correlation = np.corrcoef(live_accel_y_resampled, ref_data['accel_y'])[0, 1]
            
            # Handle NaN correlations
            if np.isnan(gyro_correlation):
                gyro_correlation = 0
            if np.isnan(accel_correlation):
                accel_correlation = 0
            
            # Convert correlations to scores (0-100)
            gyro_score = (gyro_correlation + 1) / 2 * 100  # Convert from [-1,1] to [0,100]
            accel_score = (accel_correlation + 1) / 2 * 100
            
            # Combine scores
            consistency_score = (gyro_score * 0.6 + accel_score * 0.4)
            
            return min(100, max(0, consistency_score))
            
        except Exception as e:
            logger.warning(f"Consistency analysis error: {e}")
            return 50.0
    
    def _generate_feedback(self, form_score: int, range_score: float, smoothness_score: float, consistency_score: float) -> str:
        """Generate human-readable feedback based on analysis scores."""
        
        if form_score >= 90:
            feedback = "Excellent form! "
        elif form_score >= 80:
            feedback = "Good form! "
        elif form_score >= 70:
            feedback = "Decent form. "
        elif form_score >= 60:
            feedback = "Fair form. "
        else:
            feedback = "Form needs improvement. "
        
        # Add specific recommendations
        recommendations = []
        
        if range_score < 70:
            recommendations.append("Try to maintain full range of motion")
        
        if smoothness_score < 70:
            recommendations.append("Focus on smoother, more controlled movements")
        
        if consistency_score < 70:
            recommendations.append("Work on maintaining consistent movement patterns")
        
        if recommendations:
            feedback += " ".join(recommendations) + "."
        else:
            feedback += "Keep up the consistent movement patterns!"
        
        return feedback


# Global instance for use across the application
form_analyzer = FormAnalyzer()
