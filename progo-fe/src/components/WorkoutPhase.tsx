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
        return { color: 'text-green-400', bg: 'bg-green-900/20', emoji: '🟢', text: 'Good Form' };
      case 'fair':
        return { color: 'text-yellow-400', bg: 'bg-yellow-900/20', emoji: '🟡', text: 'Fair Form' };
      case 'poor':
        return { color: 'text-red-400', bg: 'bg-red-900/20', emoji: '🔴', text: 'Poor Form' };
      default:
        return { color: 'text-gray-400', bg: 'bg-gray-900/20', emoji: '⚫', text: 'No Data' };
    }
  };

  const getWorkoutStatusInfo = () => {
    switch (workoutStatus) {
      case 'active':
        return {
          title: 'Workout Active',
          description: 'Perform your reps - AI is detecting automatically',
          color: 'text-green-400',
          bg: 'bg-green-900/20'
        };
      case 'completed':
        return {
          title: 'Workout Complete',
          description: 'Great job! Your workout session has ended.',
          color: 'text-blue-400',
          bg: 'bg-blue-900/20'
        };
      default:
        return {
          title: 'Ready to Workout',
          description: 'Start your workout session for real-time rep detection',
          color: 'text-gray-400',
          bg: 'bg-gray-900/20'
        };
    }
  };

  const canStartWorkout = connectionStatus === 'connected' && isModelReady && workoutStatus === 'idle';
  const formInfo = getFormFeedbackInfo();
  const statusInfo = getWorkoutStatusInfo();

  // Calculate progress within current set
  const setProgress = currentReps > 0 ? (currentReps / REPS_PER_SET) * 100 : 0;

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold text-white flex items-center">
          <span className="bg-green-600 text-white rounded-full w-6 h-6 flex items-center justify-center text-sm font-bold mr-2">
            2
          </span>
          Workout Phase
        </h2>
        {workoutStatus === 'active' && (
          <div className="flex items-center text-green-400 text-sm">
            <Target className="w-4 h-4 mr-1 animate-pulse" />
            Live Detection
          </div>
        )}
      </div>

      {/* Prerequisites Check */}
      {(!isModelReady || connectionStatus !== 'connected') && (
        <div className="bg-yellow-900/20 border border-yellow-600 rounded-lg p-3">
          <div className="flex items-center text-yellow-400 text-sm">
            <AlertCircle className="w-4 h-4 mr-2" />
            <div>
              <div className="font-medium">Prerequisites Required</div>
              <div className="text-xs text-yellow-300 mt-1">
                {!isModelReady && '• Complete training phase first'}
                {connectionStatus !== 'connected' && '• Device must be connected'}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Status Card */}
      <div className={`${statusInfo.bg} rounded-lg p-4 border border-gray-700`}>
        <div className="flex items-center justify-between mb-3">
          <div>
            <div className={`font-semibold ${statusInfo.color}`}>{statusInfo.title}</div>
            <div className="text-sm text-gray-300">{statusInfo.description}</div>
          </div>
          {workoutStatus === 'active' && (
            <div className="w-3 h-3 bg-green-400 rounded-full animate-pulse" />
          )}
        </div>
      </div>

      {/* Rep Counter Display */}
      <div className="grid grid-cols-2 gap-4">
        {/* Current Reps */}
        <div className="bg-gray-800/50 rounded-lg p-4 border border-gray-700">
          <div className="text-center">
            <div className="text-3xl font-bold text-blue-400">{currentReps}</div>
            <div className="text-sm text-gray-400">Current Reps</div>
            <div className="text-xs text-gray-500 mt-1">Set {currentSet}</div>
          </div>
          
          {/* Set Progress Bar */}
          {workoutStatus === 'active' && currentReps > 0 && (
            <div className="mt-3">
              <div className="w-full bg-gray-700 rounded-full h-1">
                <div 
                  className="bg-blue-500 h-1 rounded-full transition-all duration-300"
                  style={{ width: `${Math.min(setProgress, 100)}%` }}
                />
              </div>
              <div className="text-xs text-gray-500 text-center mt-1">
                {REPS_PER_SET - currentReps} reps to next set
              </div>
            </div>
          )}
        </div>

        {/* Total Stats */}
        <div className="bg-gray-800/50 rounded-lg p-4 border border-gray-700">
          <div className="space-y-2">
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-400">Total Reps:</span>
              <span className="text-lg font-semibold text-white">{totalReps}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-400">Total Sets:</span>
              <span className="text-lg font-semibold text-white">{totalSets}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Form Feedback */}
      {workoutStatus === 'active' && (
        <div className={`${formInfo.bg} rounded-lg p-3 border border-gray-700`}>
          <div className="flex items-center justify-center space-x-2">
            <span className="text-2xl">{formInfo.emoji}</span>
            <div className="text-center">
              <div className={`font-semibold ${formInfo.color}`}>{formInfo.text}</div>
              <div className="text-xs text-gray-400">Real-time form analysis</div>
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
            className={`flex-1 px-6 py-3 rounded-lg font-semibold text-white transition-all duration-200 flex items-center justify-center space-x-2 ${
              canStartWorkout
                ? 'bg-green-600 hover:bg-green-700 active:bg-green-800'
                : 'bg-gray-700 cursor-not-allowed opacity-50'
            }`}
          >
            <Play className="w-5 h-5" />
            <span>Start Workout</span>
          </button>
        ) : (
          <button
            onClick={handleStopWorkout}
            className="flex-1 px-6 py-3 rounded-lg font-semibold text-white bg-red-600 hover:bg-red-700 active:bg-red-800 transition-all duration-200 flex items-center justify-center space-x-2"
          >
            <Square className="w-5 h-5" />
            <span>Stop Workout</span>
          </button>
        )}
      </div>

      {/* Workout Instructions */}
      {workoutStatus === 'idle' && isModelReady && (
        <div className="bg-gray-800/50 rounded-lg p-3 border border-gray-700">
          <div className="text-sm text-gray-300">
            <div className="font-medium text-white mb-1">Workout Instructions:</div>
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
        <div className="bg-blue-900/20 rounded-lg p-4 border border-blue-600">
          <div className="text-center">
            <CheckCircle className="w-8 h-8 text-green-400 mx-auto mb-2" />
            <div className="font-semibold text-white mb-2">Workout Complete!</div>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <div className="text-2xl font-bold text-blue-400">{totalReps}</div>
                <div className="text-gray-300">Total Reps</div>
              </div>
              <div>
                <div className="text-2xl font-bold text-green-400">{totalSets}</div>
                <div className="text-gray-300">Total Sets</div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
