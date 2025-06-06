'use client';

import Image from 'next/image';
import { useEffect } from 'react';
import { useApp } from '@/hooks/useApp';
import DeviceStatus from '@/components/DeviceStatus';
import TrainingPhase from '@/components/TrainingPhase';
import WorkoutPhase from '@/components/WorkoutPhase';
import { Activity, Smartphone, RefreshCw, Zap, Target } from 'lucide-react';
import { wsManager } from '@/lib/websocket';

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
    // No auto-connection - user must manually connect
    console.log('HomePage initialized. Connection is manual only.');
    
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
          <div className="text-center space-y-8">
            {/* Hero Section */}
            <div className="w-full space-y-6 mx-auto">
              <div className="w-24 h-24 sm:w-28 sm:h-28 mx-auto flex items-center justify-center">
                <Image
                  src="/progite_eyes.png"
                  alt="ProGo Mascot"
                  width={112}
                  height={112}
                  className="object-contain w-full h-full"
                  priority
                />
              </div>
              
              <div className="space-y-3">
                <h1 className="text-3xl sm:text-4xl font-bold text-white tracking-tight">
                  ProGo Fitness
                </h1>
                <p className="text-lg sm:text-xl text-white/80 font-medium">
                  AI-Powered Form Tracking
                </p>
                <div className="flex items-center justify-center space-x-2 text-cyan-300">
                  <Zap className="w-4 h-4" />
                  <span className="text-sm font-medium">Real-time Analysis</span>
                </div>
              </div>
            </div>
            
            {/* Main Action Button */}
            <div className="space-y-6 w-full max-w-full">
              <button
                onClick={handleStartTraining}
                disabled={!isConnected || deviceStatus !== 'idle'}
                className="group w-full bg-gradient-to-r from-cyan-500 via-blue-500 to-purple-600 hover:from-cyan-400 hover:via-blue-400 hover:to-purple-500 disabled:from-gray-600 disabled:to-gray-700 disabled:cursor-not-allowed text-white font-bold py-4 sm:py-5 px-6 rounded-2xl transition-all duration-300 transform hover:scale-105 disabled:hover:scale-100 shadow-2xl hover:shadow-cyan-500/25 ring-2 ring-white/20 hover:ring-white/30">
                <div className="flex items-center justify-center space-x-3">
                  <Activity className="w-5 h-5 sm:w-6 sm:h-6 group-hover:animate-pulse" />
                  <span className="text-base sm:text-lg">Start Training Session</span>
                </div>
              </button>
              
              {/* Connection Status Cards */}
              {(connectionStatus === 'error' || connectionStatus === 'disconnected') && (
                <div className="w-full max-w-full">
                  <div className="bg-red-500/20 backdrop-blur-md border border-red-400/30 rounded-2xl p-6 text-center shadow-xl">
                    <div className="space-y-4">
                      <div className="w-12 h-12 mx-auto rounded-full bg-red-500/30 flex items-center justify-center">
                        <Smartphone className="w-6 h-6 text-red-300" />
                      </div>
                      <div>
                        <h3 className="text-white font-semibold text-lg mb-2">Device Disconnected</h3>
                        <p className="text-red-200 text-sm">Please reconnect your ProGo device to continue</p>
                      </div>
                      <button
                        onClick={handleRetryConnection}
                        className="w-full bg-gradient-to-r from-red-500 to-red-600 hover:from-red-400 hover:to-red-500 text-white font-semibold py-3 px-4 rounded-xl transition-all duration-200 shadow-lg hover:shadow-red-500/25 ring-1 ring-red-400/50">
                        <div className="flex items-center justify-center space-x-2">
                          <RefreshCw className="w-4 h-4" />
                          <span>Reconnect Device</span>
                        </div>
                      </button>
                    </div>
                  </div>
                </div>
              )}
              
              {connectionStatus === 'connecting' && (
                <div className="w-full max-w-full">
                  <div className="bg-blue-500/20 backdrop-blur-md border border-blue-400/30 rounded-2xl p-6 text-center shadow-xl">
                    <div className="space-y-4">
                      <div className="w-12 h-12 mx-auto rounded-full bg-blue-500/30 flex items-center justify-center">
                        <Smartphone className="w-6 h-6 text-blue-300 animate-pulse" />
                      </div>
                      <div>
                        <h3 className="text-white font-semibold text-lg mb-2">Connecting...</h3>
                        <p className="text-blue-200 text-sm">Establishing connection to your device</p>
                      </div>
                      <button
                        disabled
                        className="w-full bg-gray-600/50 cursor-not-allowed text-white/60 font-semibold py-3 px-4 rounded-xl shadow-lg opacity-50">
                        <div className="flex items-center justify-center space-x-2">
                          <RefreshCw className="w-4 h-4 animate-spin" />
                          <span>Connecting...</span>
                        </div>
                      </button>
                    </div>
                  </div>
                </div>
              )}
              
              {isConnected && deviceStatus !== 'idle' && (
                <div className="w-full max-w-full">
                  <div className="bg-yellow-500/20 backdrop-blur-md border border-yellow-400/30 rounded-2xl p-6 text-center shadow-xl">
                    <div className="space-y-4">
                      <div className="w-12 h-12 mx-auto rounded-full bg-yellow-500/30 flex items-center justify-center">
                        <Smartphone className="w-6 h-6 text-yellow-300" />
                      </div>
                      <div>
                        <h3 className="text-white font-semibold text-lg mb-2">Device Not Ready</h3>
                        <p className="text-yellow-200 text-sm">Please check your device connection</p>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Connection Success State */}
              {isConnected && deviceStatus === 'idle' && (
                <div className="w-full max-w-full">
                  <div className="bg-green-500/20 backdrop-blur-md border border-green-400/30 rounded-2xl p-4 text-center shadow-xl">
                    <div className="flex items-center justify-center space-x-3">
                      <div className="w-3 h-3 bg-green-400 rounded-full animate-pulse"></div>
                      <span className="text-green-200 font-medium">Device Ready</span>
                      <Target className="w-4 h-4 text-green-400" />
                    </div>
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
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-teal-900 to-slate-800 overflow-x-hidden">
      {/* Animated background elements */}
      <div className="absolute inset-0 overflow-hidden">
        <div className="absolute -top-1/2 -right-1/2 w-full h-full bg-gradient-to-br from-cyan-500/10 to-transparent rounded-full blur-3xl"></div>
        <div className="absolute -bottom-1/2 -left-1/2 w-full h-full bg-gradient-to-tr from-purple-500/10 to-transparent rounded-full blur-3xl"></div>
      </div>

      <div className="relative z-10 max-w-md mx-auto px-4 py-6 sm:px-8 sm:py-12">
        {/* Device Status Header */}
        <div className="mb-8 sm:mb-10">
          <DeviceStatus />
        </div>

        {/* Main Content */}
        <div className="space-y-8">
          {renderPhaseContent()}
        </div>

        {/* Workout Stats Footer */}
        {(phase === 'WORKOUT' || currentWorkout) && (
          <div className="mt-8 sm:mt-10 w-full max-w-full">
            <div className="bg-white/10 backdrop-blur-lg rounded-2xl border border-white/20 shadow-2xl p-6">
              <h3 className="text-white font-bold text-lg mb-4 text-center">Workout Stats</h3>
              
              <div className="grid grid-cols-2 gap-4 mb-4">
                <div className="bg-white/10 rounded-xl p-4 text-center border border-white/10">
                  <div className="text-2xl sm:text-3xl font-bold text-cyan-300 mb-1">{currentSet}</div>
                  <div className="text-xs sm:text-sm text-white/70 font-medium">Current Set</div>
                </div>
                <div className="bg-white/10 rounded-xl p-4 text-center border border-white/10">
                  <div className="text-2xl sm:text-3xl font-bold text-purple-300 mb-1">{currentReps}</div>
                  <div className="text-xs sm:text-sm text-white/70 font-medium">Current Reps</div>
                </div>
              </div>
              
              <div className="grid grid-cols-2 gap-4 mb-4">
                <div className="text-center">
                  <div className="text-lg sm:text-xl font-semibold text-cyan-200">{totalSets}</div>
                  <div className="text-xs text-white/60">Total Sets</div>
                </div>
                <div className="text-center">
                  <div className="text-lg sm:text-xl font-semibold text-purple-200">{totalReps}</div>
                  <div className="text-xs text-white/60">Total Reps</div>
                </div>
              </div>
              
              {phase === 'WORKOUT' && (
                <button
                  onClick={handleEndWorkout}
                  className="w-full bg-gradient-to-r from-red-500 to-red-600 hover:from-red-400 hover:to-red-500 text-white font-semibold py-3 px-4 rounded-xl transition-all duration-200 shadow-lg hover:shadow-red-500/25 ring-1 ring-red-400/50"
                >
                  End Workout
                </button>
              )}
            </div>
          </div>
        )}
      </div>
      
      {/* Emergency Stop Button - Development Only */}
      {process.env.NODE_ENV === 'development' && (
        <button 
          onClick={() => {
            wsManager.emergencyStop();
          }}
          className="fixed bottom-4 right-4 bg-red-600/90 backdrop-blur-sm hover:bg-red-500 text-white px-4 py-2 rounded-xl z-50 shadow-2xl font-semibold text-sm ring-2 ring-red-400/50 hover:ring-red-300/70 transition-all duration-200"
        >
          🛑 STOP
        </button>
      )}
    </div>
  );
}