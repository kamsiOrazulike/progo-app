'use client';

import { createContext, useContext, useReducer, useEffect, ReactNode } from 'react';
import { notifications } from '@/lib/notifications';
import {
  AppState,
  WSMessage,
  ConnectionStatus,
  DeviceStatus,
  TrainingStatus,
  WorkoutStatus,
  WorkoutSession,
  RepDetectedMessage,
  TrainingUpdateMessage,
  DeviceStatusMessage,
  WorkoutStatusMessage,
  ErrorMessage,
  REPS_PER_SET
} from '@/types';
import { wsManager } from '@/lib/websocket';
import { api } from '@/lib/api';

// Initial state
const initialState: AppState = {
  connectionStatus: 'disconnected',
  deviceStatus: 'disconnected',
  trainingStatus: 'idle',
  trainingProgress: 0,
  isModelReady: false,
  workoutStatus: 'idle',
  currentReps: 0,
  currentSet: 1,
  totalReps: 0,
  totalSets: 0,
  formFeedback: 'good',
};

// Action types
type Action =
  | { type: 'SET_CONNECTION_STATUS'; payload: ConnectionStatus }
  | { type: 'SET_DEVICE_STATUS'; payload: DeviceStatus }
  | { type: 'SET_LAST_DATA_TIME'; payload: Date }
  | { type: 'SET_TRAINING_STATUS'; payload: TrainingStatus }
  | { type: 'SET_TRAINING_PROGRESS'; payload: number }
  | { type: 'SET_TRAINING_ACCURACY'; payload: number }
  | { type: 'SET_MODEL_READY'; payload: boolean }
  | { type: 'SET_WORKOUT_STATUS'; payload: WorkoutStatus }
  | { type: 'SET_CURRENT_SESSION'; payload: WorkoutSession | undefined }
  | { type: 'UPDATE_REP_COUNT'; payload: { reps: number; sets: number; feedback: 'good' | 'fair' | 'poor' } }
  | { type: 'RESET_WORKOUT' }
  | { type: 'SET_ERROR'; payload: string }
  | { type: 'CLEAR_ERROR' }
  | { type: 'RESET_TRAINING' };

// Reducer
function appReducer(state: AppState, action: Action): AppState {
  switch (action.type) {
    case 'SET_CONNECTION_STATUS':
      return { ...state, connectionStatus: action.payload };
    
    case 'SET_DEVICE_STATUS':
      return { ...state, deviceStatus: action.payload };
    
    case 'SET_LAST_DATA_TIME':
      return { ...state, lastDataTime: action.payload };
    
    case 'SET_TRAINING_STATUS':
      return { ...state, trainingStatus: action.payload };
    
    case 'SET_TRAINING_PROGRESS':
      return { ...state, trainingProgress: action.payload };
    
    case 'SET_TRAINING_ACCURACY':
      return { ...state, trainingAccuracy: action.payload };
    
    case 'SET_MODEL_READY':
      return { ...state, isModelReady: action.payload };
    
    case 'SET_WORKOUT_STATUS':
      return { ...state, workoutStatus: action.payload };
    
    case 'SET_CURRENT_SESSION':
      return { ...state, currentSession: action.payload };
    
    case 'UPDATE_REP_COUNT':
      const { reps, sets, feedback } = action.payload;
      return {
        ...state,
        currentReps: reps,
        currentSet: sets,
        totalReps: reps + (sets - 1) * REPS_PER_SET,
        totalSets: sets,
        formFeedback: feedback,
      };
    
    case 'RESET_WORKOUT':
      return {
        ...state,
        workoutStatus: 'idle',
        currentSession: undefined,
        currentReps: 0,
        currentSet: 1,
        totalReps: 0,
        totalSets: 0,
        formFeedback: 'good',
      };
    
    case 'RESET_TRAINING':
      return {
        ...state,
        trainingStatus: 'idle',
        trainingProgress: 0,
        trainingAccuracy: undefined,
      };
    
    case 'SET_ERROR':
      return { ...state, lastError: action.payload };
    
    case 'CLEAR_ERROR':
      return { ...state, lastError: undefined };
    
    default:
      return state;
  }
}

// Context
interface AppContextType {
  state: AppState;
  actions: {
    connectToDevice: () => Promise<void>;
    disconnectFromDevice: () => void;
    startTraining: () => Promise<void>;
    startWorkout: () => Promise<void>;
    stopWorkout: () => Promise<void>;
    checkModelStatus: () => Promise<void>;
    clearError: () => void;
  };
}

const AppContext = createContext<AppContextType | undefined>(undefined);

// Provider component
interface AppProviderProps {
  children: ReactNode;
}

export function AppProvider({ children }: AppProviderProps) {
  const [state, dispatch] = useReducer(appReducer, initialState);

  // WebSocket message handler
  const handleWebSocketMessage = (message: WSMessage) => {
    console.log('Handling WebSocket message:', message);

    switch (message.type) {
      case 'device_status':
        const deviceMsg = message as DeviceStatusMessage;
        dispatch({ type: 'SET_DEVICE_STATUS', payload: deviceMsg.data.status as DeviceStatus });
        if (deviceMsg.data.last_data_time) {
          dispatch({ type: 'SET_LAST_DATA_TIME', payload: new Date(deviceMsg.data.last_data_time) });
        }
        break;

      case 'training_update':
        const trainingMsg = message as TrainingUpdateMessage;
        const { status, progress, accuracy } = trainingMsg.data;
        
        dispatch({ type: 'SET_TRAINING_STATUS', payload: status as TrainingStatus });
        
        if (progress !== undefined) {
          dispatch({ type: 'SET_TRAINING_PROGRESS', payload: progress });
        }
        
        if (accuracy !== undefined) {
          dispatch({ type: 'SET_TRAINING_ACCURACY', payload: accuracy });
          dispatch({ type: 'SET_MODEL_READY', payload: true });
        }
        break;

      case 'rep_detected':
        const repMsg = message as RepDetectedMessage;
        const { rep_count, set_count, form_feedback } = repMsg.data;
        
        dispatch({
          type: 'UPDATE_REP_COUNT',
          payload: {
            reps: rep_count,
            sets: set_count,
            feedback: form_feedback
          }
        });
        break;

      case 'workout_status':
        const workoutMsg = message as WorkoutStatusMessage;
        dispatch({ type: 'SET_WORKOUT_STATUS', payload: workoutMsg.data.status as WorkoutStatus });
        break;

      case 'error':
        const errorMsg = message as ErrorMessage;
        dispatch({ type: 'SET_ERROR', payload: errorMsg.data.message });
        break;

      default:
        console.log('Unhandled message type:', message.type);
    }
  };

  // Connection status handler
  const handleConnectionStatus = (status: ConnectionStatus) => {
    dispatch({ type: 'SET_CONNECTION_STATUS', payload: status });
  };

  // Actions
  const connectToDevice = async () => {
    try {
      dispatch({ type: 'CLEAR_ERROR' });
      
      // Set up WebSocket handlers
      wsManager.setConnectionStatusCallback(handleConnectionStatus);
      wsManager.addMessageHandler(handleWebSocketMessage);
      
      // Connect to WebSocket
      await wsManager.connect();
      
      // Check initial model status
      await checkModelStatus();
      
    } catch (error) {
      console.error('Failed to connect to device:', error);
      const errorMessage = error instanceof Error ? error.message : 'Connection failed';
      dispatch({ type: 'SET_ERROR', payload: errorMessage });
      notifications.error(`Connection failed: ${errorMessage}`);
    }
  };

  const disconnectFromDevice = () => {
    wsManager.removeMessageHandler(handleWebSocketMessage);
    wsManager.disconnect();
    dispatch({ type: 'SET_CONNECTION_STATUS', payload: 'disconnected' });
    dispatch({ type: 'SET_DEVICE_STATUS', payload: 'disconnected' });
  };

  const startTraining = async () => {
    try {
      dispatch({ type: 'CLEAR_ERROR' });
      dispatch({ type: 'RESET_TRAINING' });
      dispatch({ type: 'SET_TRAINING_STATUS', payload: 'collecting' });
      
      const success = await api.startTrainingWorkflow();
      
      if (!success) {
        dispatch({ type: 'SET_TRAINING_STATUS', payload: 'error' });
        dispatch({ type: 'SET_ERROR', payload: 'Failed to start training' });
      }
    } catch (error) {
      console.error('Training start failed:', error);
      const errorMessage = error instanceof Error ? error.message : 'Training failed';
      dispatch({ type: 'SET_TRAINING_STATUS', payload: 'error' });
      dispatch({ type: 'SET_ERROR', payload: errorMessage });
    }
  };

  const startWorkout = async () => {
    try {
      dispatch({ type: 'CLEAR_ERROR' });
      dispatch({ type: 'RESET_WORKOUT' });
      
      const sessionId = await api.startWorkoutWorkflow();
      
      if (sessionId) {
        dispatch({ type: 'SET_WORKOUT_STATUS', payload: 'active' });
        const session: WorkoutSession = {
          id: sessionId,
          device_id: 'CC:BA:97:01:3D:18',
          status: 'active',
          started_at: new Date().toISOString(),
          total_reps: 0,
          total_sets: 0,
          current_reps: 0,
          current_set: 1
        };
        dispatch({ type: 'SET_CURRENT_SESSION', payload: session });
      } else {
        dispatch({ type: 'SET_ERROR', payload: 'Failed to start workout' });
      }
    } catch (error) {
      console.error('Workout start failed:', error);
      const errorMessage = error instanceof Error ? error.message : 'Workout start failed';
      dispatch({ type: 'SET_ERROR', payload: errorMessage });
    }
  };

  const stopWorkout = async () => {
    try {
      dispatch({ type: 'CLEAR_ERROR' });
      
      if (state.currentSession?.id) {
        const success = await api.stopWorkoutWorkflow(state.currentSession.id);
        
        if (success) {
          dispatch({ type: 'SET_WORKOUT_STATUS', payload: 'completed' });
          
          // Reset after a brief delay to show completion status
          setTimeout(() => {
            dispatch({ type: 'RESET_WORKOUT' });
          }, 3000);
        } else {
          dispatch({ type: 'SET_ERROR', payload: 'Failed to stop workout' });
        }
      } else {
        // No active session, just reset
        dispatch({ type: 'RESET_WORKOUT' });
      }
    } catch (error) {
      console.error('Workout stop failed:', error);
      const errorMessage = error instanceof Error ? error.message : 'Workout stop failed';
      dispatch({ type: 'SET_ERROR', payload: errorMessage });
    }
  };

  const checkModelStatus = async () => {
    try {
      const isReady = await api.checkModelReady();
      dispatch({ type: 'SET_MODEL_READY', payload: isReady });
    } catch (error) {
      console.error('Failed to check model status:', error);
    }
  };

  const clearError = () => {
    dispatch({ type: 'CLEAR_ERROR' });
  };

  // Auto-connect on mount
  useEffect(() => {
    const connect = async () => {
      try {
        dispatch({ type: 'CLEAR_ERROR' });
        
        // Set up WebSocket handlers
        wsManager.setConnectionStatusCallback(handleConnectionStatus);
        wsManager.addMessageHandler(handleWebSocketMessage);
        
        // Connect to WebSocket
        await wsManager.connect();
        
        // Check initial model status
        await checkModelStatus();
        
      } catch (error) {
        console.error('Failed to connect to device:', error);
        const errorMessage = error instanceof Error ? error.message : 'Connection failed';
        dispatch({ type: 'SET_ERROR', payload: errorMessage });
      }
    };

    connect();
    
    // Cleanup on unmount
    return () => {
      wsManager.removeMessageHandler(handleWebSocketMessage);
      wsManager.disconnect();
      dispatch({ type: 'SET_CONNECTION_STATUS', payload: 'disconnected' });
      dispatch({ type: 'SET_DEVICE_STATUS', payload: 'disconnected' });
    };
  }, []);

  // Check model status periodically
  useEffect(() => {
    const interval = setInterval(() => {
      if (state.connectionStatus === 'connected' && !state.isModelReady) {
        checkModelStatus();
      }
    }, 10000); // Check every 10 seconds

    return () => clearInterval(interval);
  }, [state.connectionStatus, state.isModelReady]);

  const contextValue: AppContextType = {
    state,
    actions: {
      connectToDevice,
      disconnectFromDevice,
      startTraining,
      startWorkout,
      stopWorkout,
      checkModelStatus,
      clearError,
    },
  };

  return (
    <AppContext.Provider value={contextValue}>
      {children}
    </AppContext.Provider>
  );
}

// Hook to use the context
export function useApp() {
  const context = useContext(AppContext);
  if (context === undefined) {
    throw new Error('useApp must be used within an AppProvider');
  }
  return context;
}
