'use client';

import { useEffect } from 'react';
import { useApp } from '@/hooks/useApp';
import DeviceStatus from '@/components/DeviceStatus';
import TrainingPhase from '@/components/TrainingPhase';
import WorkoutPhase from '@/components/WorkoutPhase';
import { Activity, Dumbbell, Smartphone } from 'lucide-react';

export default function HomePage() {
  const { state, actions } = useApp();
  const { 
    connectionStatus,
    deviceStatus, 
    trainingStatus,
    workoutStatus,
    currentSession,
    currentSet,
    totalSets,
    currentReps,
    totalReps
  } = state;

  // Derive phase from training and workout status
  const getPhase = () => {
    if (trainingStatus === 'collecting' || trainingStatus === 'training') {
      return 'TRAINING';
    }
    if (workoutStatus === 'active' || workoutStatus === 'paused') {
      return 'WORKOUT';
    }
    return 'IDLE';
  };

  const phase = getPhase();
  const isConnected = connectionStatus === 'connected';
  const currentWorkout = currentSession;

  useEffect(() => {
    // Initialize WebSocket connection on component mount
    actions.connectToDevice();
    
    return () => {
      // Cleanup WebSocket connection on unmount
      actions.disconnectFromDevice();
    };
  }, [actions]);

  const handleStartTraining = () => {
    actions.startTraining();
  };

  const handleEndWorkout = () => {
    actions.stopWorkout();
  };

  const renderPhaseContent = () => {
    switch (phase) {
      case 'IDLE':
        return (
          <div className="text-center space-y-8">
            <div className="space-y-4">
              <div className="w-24 h-24 mx-auto rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center">
                <Dumbbell className="w-12 h-12 text-white" />
              </div>
              <h1 className="text-3xl font-bold text-white">ProGo Fitness</h1>
              <p className="text-gray-300 text-lg">Real-time AI-powered form tracking</p>
            </div>
            
            <div className="space-y-4">
              <button
                onClick={handleStartTraining}
                disabled={!isConnected || deviceStatus !== 'idle'}
                className="w-full bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 disabled:from-gray-600 disabled:to-gray-700 disabled:cursor-not-allowed text-white font-semibold py-4 px-6 rounded-xl transition-all duration-200 transform hover:scale-105 disabled:hover:scale-100">
                <div className="flex items-center justify-center space-x-2">
                  <Activity className="w-5 h-5" />
                  <span>Start Training Session</span>
                </div>
              </button>
              
              {(!isConnected || deviceStatus !== 'idle') && (
                <p className="text-sm text-amber-400 flex items-center justify-center space-x-2">
                  <Smartphone className="w-4 h-4" />
                  <span>
                    {!isConnected 
                      ? 'Connecting to device...' 
                      : 'Device not ready. Check connection.'
                    }
                  </span>
                </p>
              )}
            </div>
          </div>
        );

      case 'TRAINING':
        return <TrainingPhase />;

      case 'WORKOUT':
        return <WorkoutPhase />;

      default:
        return null;
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-black">
      <div className="container mx-auto px-4 py-8 max-w-md">
        {/* Device Status Header */}
        <div className="mb-8">
          <DeviceStatus />
        </div>

        {/* Main Content */}
        <div className="space-y-6">
          {renderPhaseContent()}
        </div>

        {/* Workout Stats Footer */}
        {(phase === 'WORKOUT' || currentWorkout) && (
          <div className="mt-8 p-4 bg-gray-800/50 rounded-xl border border-gray-700">
            <div className="grid grid-cols-2 gap-4 text-center">
              <div>
                <div className="text-2xl font-bold text-blue-400">{currentSet}</div>
                <div className="text-sm text-gray-400">Current Set</div>
              </div>
              <div>
                <div className="text-2xl font-bold text-green-400">{currentReps}</div>
                <div className="text-sm text-gray-400">Current Reps</div>
              </div>
            </div>
            
            <div className="grid grid-cols-2 gap-4 text-center mt-4">
              <div>
                <div className="text-lg font-semibold text-purple-400">{totalSets}</div>
                <div className="text-xs text-gray-500">Total Sets</div>
              </div>
              <div>
                <div className="text-lg font-semibold text-cyan-400">{totalReps}</div>
                <div className="text-xs text-gray-500">Total Reps</div>
              </div>
            </div>
            
            {phase === 'WORKOUT' && (
              <button
                onClick={handleEndWorkout}
                className="w-full mt-4 bg-red-600 hover:bg-red-700 text-white font-semibold py-3 px-4 rounded-lg transition-colors duration-200"
              >
                End Workout
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}