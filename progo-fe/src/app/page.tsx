'use client';

import { useEffect } from 'react';
import { useApp } from '@/hooks/useApp';
import DeviceStatus from '@/components/DeviceStatus';
import TrainingPhase from '@/components/TrainingPhase';
import WorkoutPhase from '@/components/WorkoutPhase';
import { Activity, Dumbbell, Smartphone, RefreshCw } from 'lucide-react';

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

  const handleRetryConnection = () => {
    actions.reconnectToDevice();
  };

  const renderPhaseContent = () => {
    switch (phase) {
      case 'IDLE':
        return (
          <div className="text-center space-y-6">
            <div className="space-y-4">
              <div className="w-20 h-20 sm:w-24 sm:h-24 mx-auto rounded-full bg-gradient-to-br from-purple-500 to-blue-400 flex items-center justify-center shadow-lg">
                <Dumbbell className="w-10 h-10 sm:w-12 sm:h-12 text-white" />
              </div>
              <h1 className="text-2xl sm:text-3xl font-bold text-purple-900">ProGo Fitness</h1>
              <p className="text-purple-700 text-base sm:text-lg px-2">Real-time AI-powered form tracking</p>
            </div>
            
            <div className="space-y-4 w-full max-w-full">
              <button
                onClick={handleStartTraining}
                disabled={!isConnected || deviceStatus !== 'idle'}
                className="w-full bg-gradient-to-r from-purple-500 to-blue-400 hover:from-purple-600 hover:to-blue-500 disabled:from-gray-400 disabled:to-gray-500 disabled:cursor-not-allowed text-white font-semibold py-3 sm:py-4 px-4 sm:px-6 rounded-xl transition-all duration-200 transform hover:scale-105 disabled:hover:scale-100 shadow-lg">
                <div className="flex items-center justify-center space-x-2">
                  <Activity className="w-4 h-4 sm:w-5 sm:h-5" />
                  <span className="text-sm sm:text-base">Start Training Session</span>
                </div>
              </button>
              
              {/* Connection Status and Retry */}
              {(connectionStatus === 'error' || connectionStatus === 'disconnected') && (
                <div className="w-full max-w-full">
                  <div className="bg-red-50 border border-red-200 rounded-xl p-4 sm:p-6 text-center">
                    <p className="text-red-700 text-sm mb-4 flex items-center justify-center space-x-2">
                      <Smartphone className="w-4 h-4" />
                      <span>Device disconnected. Please reconnect.</span>
                    </p>
                    <button
                      onClick={handleRetryConnection}
                      className="w-full bg-gradient-to-r from-red-500 to-red-600 hover:from-red-600 hover:to-red-700 text-white font-semibold py-2.5 px-4 rounded-lg transition-all duration-200 shadow-md">
                      <div className="flex items-center justify-center space-x-2">
                        <RefreshCw className="w-4 h-4" />
                        <span className="text-sm">Reconnect Device</span>
                      </div>
                    </button>
                  </div>
                </div>
              )}
              
              {connectionStatus === 'connecting' && (
                <div className="w-full max-w-full">
                  <div className="bg-purple-50 border border-purple-200 rounded-xl p-4 sm:p-6 text-center">
                    <p className="text-purple-700 text-sm mb-4 flex items-center justify-center space-x-2">
                      <Smartphone className="w-4 h-4" />
                      <span>Connecting to device...</span>
                    </p>
                    <button
                      disabled
                      className="w-full bg-gray-400 cursor-not-allowed text-white font-semibold py-2.5 px-4 rounded-lg transition-all duration-200 shadow-md opacity-50">
                      <div className="flex items-center justify-center space-x-2">
                        <RefreshCw className="w-4 h-4 animate-spin" />
                        <span className="text-sm">Connecting...</span>
                      </div>
                    </button>
                  </div>
                </div>
              )}
              
              {isConnected && deviceStatus !== 'idle' && (
                <div className="w-full max-w-full">
                  <div className="bg-yellow-50 border border-yellow-200 rounded-xl p-4 sm:p-6 text-center">
                    <p className="text-yellow-700 text-sm flex items-center justify-center space-x-2">
                      <Smartphone className="w-4 h-4" />
                      <span>Device not ready. Check connection.</span>
                    </p>
                  </div>
                </div>
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
    <div className="min-h-screen bg-gradient-to-br from-purple-100 via-purple-50 to-white overflow-x-hidden">
      <div className="max-w-md mx-auto px-4 py-6 sm:px-8 sm:py-12">
        {/* Device Status Header */}
        <div className="mb-6 sm:mb-8">
          <DeviceStatus />
        </div>

        {/* Main Content */}
        <div className="space-y-6">
          {renderPhaseContent()}
        </div>

        {/* Workout Stats Footer */}
        {(phase === 'WORKOUT' || currentWorkout) && (
          <div className="mt-6 sm:mt-8 w-full max-w-full">
            <div className="bg-white/70 backdrop-blur-sm rounded-xl border border-purple-200 shadow-lg p-4 sm:p-6">
              <div className="grid grid-cols-2 gap-3 sm:gap-4 text-center">
                <div>
                  <div className="text-xl sm:text-2xl font-bold text-purple-600">{currentSet}</div>
                  <div className="text-xs sm:text-sm text-purple-700">Current Set</div>
                </div>
                <div>
                  <div className="text-xl sm:text-2xl font-bold text-purple-600">{currentReps}</div>
                  <div className="text-xs sm:text-sm text-purple-700">Current Reps</div>
                </div>
              </div>
              
              <div className="grid grid-cols-2 gap-3 sm:gap-4 text-center mt-3 sm:mt-4">
                <div>
                  <div className="text-base sm:text-lg font-semibold text-purple-500">{totalSets}</div>
                  <div className="text-xs text-purple-600">Total Sets</div>
                </div>
                <div>
                  <div className="text-base sm:text-lg font-semibold text-blue-400">{totalReps}</div>
                  <div className="text-xs text-purple-600">Total Reps</div>
                </div>
              </div>
              
              {phase === 'WORKOUT' && (
                <button
                  onClick={handleEndWorkout}
                  className="w-full mt-3 sm:mt-4 bg-gradient-to-r from-red-400 to-red-500 hover:from-red-500 hover:to-red-600 text-white font-semibold py-2.5 sm:py-3 px-4 rounded-lg transition-all duration-200 shadow-lg text-sm sm:text-base"
                >
                  End Workout
                </button>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}