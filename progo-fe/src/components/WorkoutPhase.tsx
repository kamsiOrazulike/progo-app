'use client';

import { Play, Square, Target, CheckCircle, AlertCircle } from 'lucide-react';
import { useApp } from '@/hooks/useApp';
import { REPS_PER_SET } from '@/types';

export default function WorkoutPhase() {
  const { state, actions } = useApp();
  const { 
    workoutStatus, 
    currentReps, 
    currentSet, 
    totalReps, 
    totalSets, 
    formFeedback, 
    isModelReady, 
    connectionStatus 
  } = state;

  const handleStartWorkout = async () => {
    if (!canStartWorkout) return;
    await actions.startWorkout();
  };

  const handleStopWorkout = async () => {
    await actions.stopWorkout();
  };

  const getFormFeedbackInfo = () => {
    switch (formFeedback) {
      case 'good':
        return { color: 'text-green-600', bg: 'bg-green-50', emoji: '🟢', text: 'Good Form' };
      case 'fair':
        return { color: 'text-yellow-600', bg: 'bg-yellow-50', emoji: '🟡', text: 'Fair Form' };
      case 'poor':
        return { color: 'text-red-600', bg: 'bg-red-50', emoji: '🔴', text: 'Poor Form' };
      default:
        return { color: 'text-purple-600', bg: 'bg-purple-50', emoji: '⚫', text: 'No Data' };
    }
  };

  const getWorkoutStatusInfo = () => {
    switch (workoutStatus) {
      case 'active':
        return {
          title: 'Workout Active',
          description: 'Perform your reps - AI is detecting automatically',
          color: 'text-green-600',
          bg: 'bg-green-50'
        };
      case 'completed':
        return {
          title: 'Workout Complete',
          description: 'Great job! Your workout session has ended.',
          color: 'text-blue-600',
          bg: 'bg-blue-50'
        };
      default:
        return {
          title: 'Ready to Workout',
          description: 'Start your workout session for real-time rep detection',
          color: 'text-purple-600',
          bg: 'bg-white/70'
        };
    }
  };

  const canStartWorkout = connectionStatus === 'connected' && isModelReady && workoutStatus === 'idle';
  const formInfo = getFormFeedbackInfo();
  const statusInfo = getWorkoutStatusInfo();

  // Calculate progress within current set
  const setProgress = currentReps > 0 ? (currentReps / REPS_PER_SET) * 100 : 0;

  return (
    <div className="space-y-4 px-2 sm:px-0">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-lg sm:text-xl font-bold text-purple-900 flex items-center">
          <span className="bg-gradient-to-r from-green-500 to-green-600 text-white rounded-full w-5 h-5 sm:w-6 sm:h-6 flex items-center justify-center text-xs sm:text-sm font-bold mr-2">
            2
          </span>
          <span className="text-base sm:text-xl">Workout Phase</span>
        </h2>
        {workoutStatus === 'active' && (
          <div className="flex items-center text-green-600 text-xs sm:text-sm">
            <Target className="w-3 h-3 sm:w-4 sm:h-4 mr-1 animate-pulse" />
            <span className="hidden sm:inline">Live Detection</span>
            <span className="sm:hidden">Live</span>
          </div>
        )}
      </div>

      {/* Prerequisites Check */}
      {(!isModelReady || connectionStatus !== 'connected') && (
        <div className="bg-yellow-50 border border-yellow-300 rounded-lg p-3 shadow-lg backdrop-blur-sm">
          <div className="flex items-center text-yellow-700 text-xs sm:text-sm">
            <AlertCircle className="w-4 h-4 mr-2 flex-shrink-0" />
            <div className="min-w-0">
              <div className="font-medium">Prerequisites Required</div>
              <div className="text-xs text-yellow-600 mt-1">
                {!isModelReady && '• Complete training phase first'}
                {connectionStatus !== 'connected' && '• Device must be connected'}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Status Card */}
      <div className={`${statusInfo.bg} backdrop-blur-sm rounded-lg p-3 sm:p-4 border ${workoutStatus === 'active' ? 'border-green-200' : workoutStatus === 'completed' ? 'border-blue-200' : 'border-purple-200'} shadow-lg`}>
        <div className="flex items-center justify-between mb-3">
          <div className="min-w-0 flex-1">
            <div className={`font-semibold ${statusInfo.color} text-sm sm:text-base`}>{statusInfo.title}</div>
            <div className="text-xs sm:text-sm text-purple-700 break-words">{statusInfo.description}</div>
          </div>
          {workoutStatus === 'active' && (
            <div className="w-2.5 h-2.5 sm:w-3 sm:h-3 bg-green-500 rounded-full animate-pulse flex-shrink-0" />
          )}
        </div>
      </div>

      {/* Rep Counter Display */}
      <div className="grid grid-cols-2 gap-3 sm:gap-4">
        {/* Current Reps */}
        <div className="bg-white/70 backdrop-blur-sm rounded-lg p-3 sm:p-4 border border-purple-200 shadow-lg">
          <div className="text-center">
            <div className="text-2xl sm:text-3xl font-bold text-blue-600">{currentReps}</div>
            <div className="text-xs sm:text-sm text-purple-600">Current Reps</div>
            <div className="text-xs text-purple-500 mt-1">Set {currentSet}</div>
          </div>
          
          {/* Set Progress Bar */}
          {workoutStatus === 'active' && currentReps > 0 && (
            <div className="mt-2 sm:mt-3">
              <div className="w-full bg-purple-200 rounded-full h-1">
                <div 
                  className="bg-gradient-to-r from-blue-500 to-blue-600 h-1 rounded-full transition-all duration-300"
                  style={{ width: `${Math.min(setProgress, 100)}%` }}
                />
              </div>
              <div className="text-xs text-purple-500 text-center mt-1">
                {REPS_PER_SET - currentReps} reps to next set
              </div>
            </div>
          )}
        </div>

        {/* Total Stats */}
        <div className="bg-white/70 backdrop-blur-sm rounded-lg p-3 sm:p-4 border border-purple-200 shadow-lg">
          <div className="space-y-2">
            <div className="flex justify-between items-center">
              <span className="text-xs sm:text-sm text-purple-600">Total Reps:</span>
              <span className="text-base sm:text-lg font-semibold text-purple-900">{totalReps}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-xs sm:text-sm text-purple-600">Total Sets:</span>
              <span className="text-base sm:text-lg font-semibold text-purple-900">{totalSets}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Form Feedback */}
      {workoutStatus === 'active' && (
        <div className={`${formInfo.bg} backdrop-blur-sm rounded-lg p-3 border ${formFeedback === 'good' ? 'border-green-200' : formFeedback === 'fair' ? 'border-yellow-200' : formFeedback === 'poor' ? 'border-red-200' : 'border-purple-200'} shadow-lg`}>
          <div className="flex items-center justify-center space-x-2">
            <span className="text-xl sm:text-2xl">{formInfo.emoji}</span>
            <div className="text-center">
              <div className={`font-semibold ${formInfo.color} text-sm sm:text-base`}>{formInfo.text}</div>
              <div className="text-xs text-purple-600">Real-time form analysis</div>
            </div>
          </div>
        </div>
      )}

      {/* Workout Controls */}
      <div className="flex space-x-3">
        {workoutStatus !== 'active' ? (
          <button
            onClick={handleStartWorkout}
            disabled={!canStartWorkout}
            className={`flex-1 px-4 sm:px-6 py-2.5 sm:py-3 rounded-lg font-semibold text-white transition-all duration-200 flex items-center justify-center space-x-2 shadow-lg text-sm sm:text-base ${
              canStartWorkout
                ? 'bg-gradient-to-r from-green-500 to-green-600 hover:from-green-600 hover:to-green-700 active:from-green-700 active:to-green-800'
                : 'bg-gray-400 cursor-not-allowed opacity-50'
            }`}
          >
            <Play className="w-4 h-4 sm:w-5 sm:h-5" />
            <span>Start Workout</span>
          </button>
        ) : (
          <button
            onClick={handleStopWorkout}
            className="flex-1 px-4 sm:px-6 py-2.5 sm:py-3 rounded-lg font-semibold text-white bg-gradient-to-r from-red-500 to-red-600 hover:from-red-600 hover:to-red-700 active:from-red-700 active:to-red-800 shadow-lg transition-all duration-200 flex items-center justify-center space-x-2 text-sm sm:text-base"
          >
            <Square className="w-4 h-4 sm:w-5 sm:h-5" />
            <span>Stop Workout</span>
          </button>
        )}
      </div>

      {/* Workout Instructions */}
      {workoutStatus === 'idle' && isModelReady && (
        <div className="bg-white/60 backdrop-blur-sm rounded-lg p-3 border border-purple-200 shadow-lg">
          <div className="text-xs sm:text-sm text-purple-700">
            <div className="font-medium text-purple-900 mb-1 text-sm">Workout Instructions:</div>
            <ul className="space-y-1 text-xs">
              <li>• AI model is ready for real-time rep detection</li>
              <li>• Perform reps with consistent form and speed</li>
              <li>• Sets automatically increment after {REPS_PER_SET} reps</li>
              <li>• Form feedback will appear in real-time</li>
              <li>• Stop workout when you&apos;re finished</li>
            </ul>
          </div>
        </div>
      )}

      {/* Session Summary */}
      {workoutStatus === 'completed' && totalReps > 0 && (
        <div className="bg-blue-50 backdrop-blur-sm rounded-lg p-4 border border-blue-200 shadow-lg">
          <div className="text-center">
            <CheckCircle className="w-6 h-6 sm:w-8 sm:h-8 text-green-600 mx-auto mb-2" />
            <div className="font-semibold text-purple-900 mb-2 text-sm sm:text-base">Workout Complete!</div>
            <div className="grid grid-cols-2 gap-4 text-xs sm:text-sm">
              <div>
                <div className="text-xl sm:text-2xl font-bold text-blue-600">{totalReps}</div>
                <div className="text-purple-700">Total Reps</div>
              </div>
              <div>
                <div className="text-xl sm:text-2xl font-bold text-green-600">{totalSets}</div>
                <div className="text-purple-700">Total Sets</div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
