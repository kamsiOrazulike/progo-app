import { notifications } from './notifications';
import {
  ApiResponse,
  StartTrainingRequest,
  StartTrainingResponse,
  StartWorkoutRequest,
  StartWorkoutResponse,
  StopWorkoutRequest,
  StopWorkoutResponse,
  DEVICE_ID
} from '@/types';

const API_BASE_URL = 'https://progo-be.onrender.com';

class ApiService {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  private async fetchWithErrorHandling<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<ApiResponse<T>> {
    try {
      const url = `${this.baseUrl}${endpoint}`;
      console.log(`API Request: ${options.method || 'GET'} ${url}`);

      const response = await fetch(url, {
        headers: {
          'Content-Type': 'application/json',
          ...options.headers,
        },
        ...options,
      });

      const data = await response.json();
      console.log(`API Response: ${response.status}`, data);

      if (!response.ok) {
        const errorMessage = data.detail || data.message || `HTTP ${response.status}`;
        console.error('API Error:', errorMessage);
        notifications.error(`API Error: ${errorMessage}`);
        
        return {
          success: false,
          error: errorMessage,
          data: data
        };
      }

      return {
        success: true,
        data: data
      };
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Network error';
      console.error('Network Error:', error);
      notifications.error(`Network Error: ${errorMessage}`);
      
      return {
        success: false,
        error: errorMessage
      };
    }
  }

  // Health check
  async healthCheck(): Promise<ApiResponse> {
    return this.fetchWithErrorHandling('/health');
  }

  // Device status
  async getDeviceStatus(deviceId: string = DEVICE_ID): Promise<ApiResponse> {
    return this.fetchWithErrorHandling(`/api/devices/${deviceId}/status`);
  }

  // Training endpoints
  async startTraining(request: StartTrainingRequest = { device_id: DEVICE_ID }): Promise<ApiResponse<StartTrainingResponse>> {
    return this.fetchWithErrorHandling<StartTrainingResponse>('/api/ml/train', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  async getTrainingStatus(deviceId: string = DEVICE_ID): Promise<ApiResponse> {
    return this.fetchWithErrorHandling(`/api/ml/training-status/${deviceId}`);
  }

  async getModelStatus(deviceId: string = DEVICE_ID): Promise<ApiResponse> {
    return this.fetchWithErrorHandling(`/api/ml/model-status/${deviceId}`);
  }

  // Workout endpoints
  async startWorkout(request: StartWorkoutRequest = { device_id: DEVICE_ID }): Promise<ApiResponse<StartWorkoutResponse>> {
    return this.fetchWithErrorHandling<StartWorkoutResponse>('/api/workouts/start', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  async stopWorkout(request: StopWorkoutRequest): Promise<ApiResponse<StopWorkoutResponse>> {
    return this.fetchWithErrorHandling<StopWorkoutResponse>('/api/workouts/stop', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  async getActiveWorkout(deviceId: string = DEVICE_ID): Promise<ApiResponse> {
    return this.fetchWithErrorHandling(`/api/workouts/active/${deviceId}`);
  }

  async getWorkoutHistory(deviceId: string = DEVICE_ID): Promise<ApiResponse> {
    return this.fetchWithErrorHandling(`/api/workouts/history/${deviceId}`);
  }

  // Rep detection endpoints
  async getRepHistory(workoutSessionId: string): Promise<ApiResponse> {
    return this.fetchWithErrorHandling(`/api/reps/session/${workoutSessionId}`);
  }

  async getLatestReps(deviceId: string = DEVICE_ID, limit: number = 10): Promise<ApiResponse> {
    return this.fetchWithErrorHandling(`/api/reps/latest/${deviceId}?limit=${limit}`);
  }

  // Sensor data endpoints
  async getLatestSensorData(deviceId: string = DEVICE_ID): Promise<ApiResponse> {
    return this.fetchWithErrorHandling(`/api/sensor-data/latest/${deviceId}`);
  }

  async getSensorDataHistory(deviceId: string = DEVICE_ID, limit: number = 100): Promise<ApiResponse> {
    return this.fetchWithErrorHandling(`/api/sensor-data/history/${deviceId}?limit=${limit}`);
  }

  // Calibration endpoints
  async startCalibration(deviceId: string = DEVICE_ID): Promise<ApiResponse> {
    return this.fetchWithErrorHandling('/api/ml/calibrate', {
      method: 'POST',
      body: JSON.stringify({ device_id: deviceId }),
    });
  }

  async getCalibrationStatus(deviceId: string = DEVICE_ID): Promise<ApiResponse> {
    return this.fetchWithErrorHandling(`/api/ml/calibration-status/${deviceId}`);
  }

  // Session management
  async getSessionHistory(deviceId: string = DEVICE_ID): Promise<ApiResponse> {
    return this.fetchWithErrorHandling(`/api/sessions/history/${deviceId}`);
  }

  async getSessionDetails(sessionId: string): Promise<ApiResponse> {
    return this.fetchWithErrorHandling(`/api/sessions/${sessionId}`);
  }

  // Statistics
  async getWorkoutStats(deviceId: string = DEVICE_ID): Promise<ApiResponse> {
    return this.fetchWithErrorHandling(`/api/workouts/stats/${deviceId}`);
  }

  // Test endpoints for development
  async simulateRepDetection(deviceId: string = DEVICE_ID): Promise<ApiResponse> {
    return this.fetchWithErrorHandling('/api/test/simulate-rep', {
      method: 'POST',
      body: JSON.stringify({ device_id: deviceId }),
    });
  }

  async testConnection(): Promise<ApiResponse> {
    return this.fetchWithErrorHandling('/api/test/connection');
  }
}

// Singleton instance
export const apiService = new ApiService();

// Helper functions for common operations
export const api = {
  // Quick health check
  async ping(): Promise<boolean> {
    const result = await apiService.healthCheck();
    return result.success;
  },

  // Start training workflow
  async startTrainingWorkflow(): Promise<boolean> {
    console.log('Starting training workflow...');
    const result = await apiService.startTraining();
    
    if (result.success) {
      notifications.success('Training started successfully!');
      return true;
    } else {
      notifications.error(`Failed to start training: ${result.error}`);
      return false;
    }
  },

  // Start workout workflow
  async startWorkoutWorkflow(): Promise<string | null> {
    console.log('Starting workout workflow...');
    const result = await apiService.startWorkout();
    
    if (result.success && result.data) {
      notifications.success('Workout started successfully!');
      return result.data.session_id;
    } else {
      notifications.error(`Failed to start workout: ${result.error}`);
      return null;
    }
  },

  // Stop workout workflow
  async stopWorkoutWorkflow(sessionId: string): Promise<boolean> {
    console.log('Stopping workout workflow...');
    const result = await apiService.stopWorkout({ session_id: sessionId });
    
    if (result.success && result.data) {
      const { total_reps, total_sets, duration } = result.data;
      notifications.success(
        `Workout completed! ${total_reps} reps, ${total_sets} sets in ${Math.round(duration/60)} minutes`
      );
      return true;
    } else {
      notifications.error(`Failed to stop workout: ${result.error}`);
      return false;
    }
  },

  // Check if model is ready
  async checkModelReady(): Promise<boolean> {
    const result = await apiService.getModelStatus();
    
    if (result.success && result.data) {
      return result.data.is_trained === true;
    }
    
    return false;
  }
};
