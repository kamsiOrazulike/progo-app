// Types for WebSocket connection states
export type ConnectionStatus = 'connected' | 'connecting' | 'disconnected' | 'error';

// Types for device states
export type DeviceStatus = 'connected' | 'idle' | 'disconnected';

// Types for training workflow
export type TrainingStatus = 'idle' | 'collecting' | 'training' | 'completed' | 'error';

// Types for workout session
export type WorkoutStatus = 'idle' | 'active' | 'paused' | 'completed';

// Device configuration
export interface DeviceConfig {
  deviceId: string;
  name: string;
}

// WebSocket message types based on backend implementation
export interface WSMessage {
  type: 'device_status' | 'training_update' | 'rep_detected' | 'workout_status' | 'error';
  data: Record<string, unknown>;
  timestamp?: string;
}

// Device status message
export interface DeviceStatusMessage {
  type: 'device_status';
  data: {
    device_id: string;
    status: 'connected' | 'idle' | 'disconnected';
    last_data_time?: string;
  };
}

// Training update message
export interface TrainingUpdateMessage {
  type: 'training_update';
  data: {
    status: 'started' | 'collecting' | 'training' | 'completed' | 'error';
    progress?: number;
    accuracy?: number;
    message?: string;
  };
}

// Rep detection message
export interface RepDetectedMessage {
  type: 'rep_detected';
  data: {
    rep_count: number;
    set_count: number;
    confidence: number;
    form_feedback: 'good' | 'fair' | 'poor';
    workout_session_id?: string;
  };
}

// Workout status message
export interface WorkoutStatusMessage {
  type: 'workout_status';
  data: {
    status: 'active' | 'paused' | 'completed';
    session_id?: string;
    total_reps: number;
    total_sets: number;
  };
}

// Error message
export interface ErrorMessage {
  type: 'error';
  data: {
    code: string;
    message: string;
    details?: Record<string, unknown>;
  };
}

// Training session data
export interface TrainingSession {
  id: string;
  device_id: string;
  status: TrainingStatus;
  started_at: string;
  completed_at?: string;
  accuracy?: number;
  data_points_collected?: number;
}

// Workout session data
export interface WorkoutSession {
  id: string;
  device_id: string;
  status: WorkoutStatus;
  started_at: string;
  completed_at?: string;
  total_reps: number;
  total_sets: number;
  current_reps: number;
  current_set: number;
}

// Rep detection data
export interface RepDetection {
  id: string;
  workout_session_id: string;
  rep_number: number;
  set_number: number;
  confidence: number;
  form_feedback: 'good' | 'fair' | 'poor';
  detected_at: string;
}

// Application state
export interface AppState {
  // Connection state
  connectionStatus: ConnectionStatus;
  deviceStatus: DeviceStatus;
  lastDataTime?: Date;
  
  // Training state
  trainingStatus: TrainingStatus;
  trainingProgress: number;
  trainingAccuracy?: number;
  isModelReady: boolean;
  
  // Workout state
  workoutStatus: WorkoutStatus;
  currentSession?: WorkoutSession;
  currentReps: number;
  currentSet: number;
  totalReps: number;
  totalSets: number;
  formFeedback: 'good' | 'fair' | 'poor';
  
  // Error state
  lastError?: string;
}

// API response types
export interface ApiResponse<T = Record<string, unknown>> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}

// Training API endpoints
export interface StartTrainingRequest {
  device_id: string;
  duration?: number; // seconds, default 8
}

export interface StartTrainingResponse {
  session_id: string;
  message: string;
  duration: number;
}

// Workout API endpoints
export interface StartWorkoutRequest {
  device_id: string;
  exercise_type?: string;
}

export interface StartWorkoutResponse {
  session_id: string;
  message: string;
  started_at: string;
}

export interface StopWorkoutRequest {
  session_id: string;
}

export interface StopWorkoutResponse {
  session_id: string;
  total_reps: number;
  total_sets: number;
  duration: number;
  completed_at: string;
}

// Constants
export const DEVICE_ID = 'CC:BA:97:01:3D:18';
export const WEBSOCKET_TIMEOUT = 30000; // 30 seconds
export const TRAINING_DURATION = 8; // 8 seconds
export const REPS_PER_SET = 8; // 8 reps per set
export const CONNECTION_RETRY_DELAY = 3000; // 3 seconds
