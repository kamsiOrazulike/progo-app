"""
Reference data loader for bicep curl form comparison.

This module provides utilities to load and access the reference bicep curl data
that serves as a baseline for form comparison analysis.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class ReferenceDataLoader:
    """Loads and provides access to reference bicep curl data."""
    
    def __init__(self):
        self._reference_data: Optional[Dict[str, Any]] = None
        self._data_file = Path(__file__).parent.parent / "data" / "reference_bicep_curl.json"
    
    def load_reference_data(self) -> Dict[str, Any]:
        """
        Load the reference bicep curl data from JSON file.
        
        Returns:
            Dict containing metadata and IMU readings
            
        Raises:
            FileNotFoundError: If reference data file doesn't exist
            ValueError: If data format is invalid
        """
        if self._reference_data is not None:
            return self._reference_data
            
        try:
            if not self._data_file.exists():
                raise FileNotFoundError(f"Reference data file not found: {self._data_file}")
            
            with open(self._data_file, 'r') as f:
                data = json.load(f)
            
            # Validate data structure
            if 'metadata' not in data or 'readings' not in data:
                raise ValueError("Invalid reference data format: missing 'metadata' or 'readings'")
            
            if not isinstance(data['readings'], list):
                raise ValueError("Invalid reference data format: 'readings' must be a list")
            
            # Cache the loaded data
            self._reference_data = data
            
            logger.info(f"Loaded reference bicep curl data: {len(data['readings'])} readings")
            logger.info(f"Session date: {data['metadata'].get('session_date')}")
            logger.info(f"Total reps: {data['metadata'].get('reps_performed')}")
            
            return data
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in reference data file: {e}")
        except Exception as e:
            logger.error(f"Error loading reference data: {e}")
            raise
    
    def get_readings(self) -> List[Dict[str, Any]]:
        """
        Get the list of IMU readings from reference data.
        
        Returns:
            List of IMU reading dictionaries
        """
        data = self.load_reference_data()
        return data['readings']
    
    def get_metadata(self) -> Dict[str, Any]:
        """
        Get metadata about the reference bicep curl session.
        
        Returns:
            Dictionary containing session metadata
        """
        data = self.load_reference_data()
        return data['metadata']
    
    def get_reading_count(self) -> int:
        """Get the total number of readings in the reference data."""
        return len(self.get_readings())
    
    def get_time_range(self) -> tuple[Optional[str], Optional[str]]:
        """
        Get the time range of the reference data.
        
        Returns:
            Tuple of (start_timestamp, end_timestamp) or (None, None) if no data
        """
        readings = self.get_readings()
        if not readings:
            return None, None
        
        # Data is already in chronological order
        start_time = readings[0]['timestamp']
        end_time = readings[-1]['timestamp']
        
        return start_time, end_time
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the reference data for API responses.
        
        Returns:
            Dictionary with summary information
        """
        metadata = self.get_metadata()
        readings = self.get_readings()
        start_time, end_time = self.get_time_range()
        
        return {
            "description": metadata.get("description"),
            "total_readings": len(readings),
            "reps_performed": metadata.get("reps_performed"),
            "duration_seconds": metadata.get("duration_seconds"),
            "session_date": metadata.get("session_date"),
            "time_range": {
                "start": start_time,
                "end": end_time
            },
            "exercise_type": metadata.get("exercise_type"),
            "sampling_rate_hz": metadata.get("sampling_rate_hz"),
            "data_loaded": True
        }


# Global instance
reference_loader = ReferenceDataLoader()


def get_reference_data() -> Dict[str, Any]:
    """Convenience function to get reference data."""
    return reference_loader.load_reference_data()


def get_reference_readings() -> List[Dict[str, Any]]:
    """Convenience function to get reference readings."""
    return reference_loader.get_readings()


def get_reference_summary() -> Dict[str, Any]:
    """Convenience function to get reference data summary."""
    return reference_loader.get_summary()
