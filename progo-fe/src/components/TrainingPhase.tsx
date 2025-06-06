'use client';

import { useState, useEffect } from 'react';
import { Play, Clock, CheckCircle, AlertCircle, Loader2 } from 'lucide-react';
import { useApp } from '@/hooks/useApp';
import { TRAINING_DURATION } from '@/types';

export default function TrainingPhase() {
  const { state, actions } = useApp();
  const { trainingStatus, trainingProgress, trainingAccuracy, isModelReady, connectionStatus } = state;
  const [countdown, setCountdown] = useState(0);
  const [isCountingDown, setIsCountingDown] = useState(false);

  // Countdown timer for training
  useEffect(() => {
    let interval: NodeJS.Timeout;

    if (trainingStatus === 'collecting' && !isCountingDown) {
      setIsCountingDown(true);
      setCountdown(TRAINING_DURATION);
      
      interval = setInterval(() => {
        setCountdown((prev) => {
          if (prev <= 1) {
            setIsCountingDown(false);
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
    }

    return () => {
      if (interval) {
        clearInterval(interval);
      }
    };
  }, [trainingStatus, isCountingDown]);

  // Reset countdown when training is not collecting
  useEffect(() => {
    if (trainingStatus !== 'collecting') {
      setIsCountingDown(false);
      setCountdown(0);
    }
  }, [trainingStatus]);

  const handleStartTraining = async () => {
    if (connectionStatus !== 'connected') {
      return;
    }
    await actions.startTraining();
  };

  const handleStartWorkout = async () => {
    await actions.startWorkout();
  };

  const getTrainingStatusInfo = () => {
    switch (trainingStatus) {
      case 'collecting':
        return {
          icon: Clock,
          color: 'text-blue-600',
          bgColor: 'bg-blue-50',
          borderColor: 'border-blue-200',
          title: 'Collecting Data',
          description: `Collecting training data... ${countdown}s remaining`,
          showProgress: true,
          progress: ((TRAINING_DURATION - countdown) / TRAINING_DURATION) * 100
        };
      case 'training':
        return {
          icon: Loader2,
          color: 'text-purple-600',
          bgColor: 'bg-purple-50',
          borderColor: 'border-purple-200',
          title: 'Training Model',
          description: 'AI model is training...',
          showProgress: true,
          progress: trainingProgress * 100,
          spinning: true
        };
      case 'completed':
        return {
          icon: CheckCircle,
          color: 'text-green-600',
          bgColor: 'bg-green-50',
          borderColor: 'border-green-200',
          title: 'Training Complete',
          description: trainingAccuracy 
            ? `Model ready! Accuracy: ${(trainingAccuracy * 100).toFixed(1)}%`
            : 'Model training completed successfully',
          showProgress: false,
          showWorkoutButton: true
        };
      case 'error':
        return {
          icon: AlertCircle,
          color: 'text-red-600',
          bgColor: 'bg-red-50',
          borderColor: 'border-red-200',
          title: 'Training Failed',
          description: 'Training encountered an error. Please try again.',
          showProgress: false
        };
      default:
        return {
          icon: Play,
          color: 'text-purple-600',
          bgColor: 'bg-white/50',
          borderColor: 'border-purple-200',
          title: 'Ready to Train',
          description: 'Start 8-second training session to calibrate AI model',
          showProgress: false
        };
    }
  };

  const statusInfo = getTrainingStatusInfo();
  const StatusIcon = statusInfo.icon;
  const isTrainingActive = trainingStatus === 'collecting' || trainingStatus === 'training';
  const canStartTraining = connectionStatus === 'connected' && trainingStatus === 'idle';

  return (
    <div className="space-y-4 px-2 sm:px-0">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-lg sm:text-xl font-bold text-purple-900 flex items-center">
          <span className="bg-gradient-to-r from-purple-500 to-blue-400 text-white rounded-full w-5 h-5 sm:w-6 sm:h-6 flex items-center justify-center text-xs sm:text-sm font-bold mr-2">
            1
          </span>
          <span className="text-base sm:text-xl">Training Phase</span>
        </h2>
        {isModelReady && (
          <div className="flex items-center text-green-600 text-xs sm:text-sm">
            <CheckCircle className="w-3 h-3 sm:w-4 sm:h-4 mr-1" />
            <span className="hidden sm:inline">Model Ready</span>
            <span className="sm:hidden">Ready</span>
          </div>
        )}
      </div>

      {/* Status Card */}
      <div className={`${statusInfo.bgColor} rounded-lg p-3 sm:p-4 border ${statusInfo.borderColor} shadow-lg backdrop-blur-sm`}>
        <div className="flex items-center space-x-3 mb-3">
          <StatusIcon 
            className={`w-5 h-5 sm:w-6 sm:h-6 ${statusInfo.color} ${statusInfo.spinning ? 'animate-spin' : ''}`} 
          />
          <div className="min-w-0 flex-1">
            <div className="font-semibold text-purple-900 text-sm sm:text-base">{statusInfo.title}</div>
            <div className="text-xs sm:text-sm text-purple-700 break-words">{statusInfo.description}</div>
          </div>
        </div>

        {/* Progress Bar */}
        {statusInfo.showProgress && (
          <div className="mt-3">
            <div className="flex justify-between text-xs text-purple-600 mb-1">
              <span>Progress</span>
              <span>{Math.round(statusInfo.progress || 0)}%</span>
            </div>
            <div className="w-full bg-purple-200 rounded-full h-2">
              <div 
                className={`h-2 rounded-full transition-all duration-300 ${
                  trainingStatus === 'collecting' ? 'bg-gradient-to-r from-blue-400 to-blue-500' : 'bg-gradient-to-r from-purple-500 to-purple-600'
                }`}
                style={{ width: `${statusInfo.progress || 0}%` }}
              />
            </div>
          </div>
        )}
      </div>

      {/* Training Controls */}
      <div className="flex space-x-3">
        {statusInfo.showWorkoutButton ? (
          <button
            onClick={handleStartWorkout}
            className="flex-1 px-4 sm:px-6 py-2.5 sm:py-3 rounded-lg font-semibold text-white transition-all duration-200 flex items-center justify-center space-x-2 bg-gradient-to-r from-green-500 to-green-600 hover:from-green-600 hover:to-green-700 active:from-green-700 active:to-green-800 shadow-lg text-sm sm:text-base"
          >
            <Play className="w-4 h-4 sm:w-5 sm:h-5" />
            <span>Start Workout</span>
          </button>
        ) : (
          <button
            onClick={handleStartTraining}
            disabled={!canStartTraining || isTrainingActive}
            className={`flex-1 px-4 sm:px-6 py-2.5 sm:py-3 rounded-lg font-semibold text-white transition-all duration-200 flex items-center justify-center space-x-2 shadow-lg text-sm sm:text-base ${
              canStartTraining && !isTrainingActive
                ? 'bg-gradient-to-r from-blue-500 to-blue-600 hover:from-blue-600 hover:to-blue-700 active:from-blue-700 active:to-blue-800'
                : 'bg-gray-400 cursor-not-allowed opacity-50'
            }`}
          >
            {isTrainingActive ? (
              <>
                <Loader2 className="w-4 h-4 sm:w-5 sm:h-5 animate-spin" />
                <span>{trainingStatus === 'collecting' ? 'Collecting...' : 'Training...'}</span>
              </>
            ) : (
              <>
                <Play className="w-4 h-4 sm:w-5 sm:h-5" />
                <span>Start Training</span>
              </>
            )}
          </button>
        )}

        {/* Countdown Display */}
        {isCountingDown && (
          <div className="flex items-center justify-center bg-white/70 backdrop-blur-sm px-3 sm:px-4 py-2.5 sm:py-3 rounded-lg border border-blue-300 shadow-lg">
            <div className="text-center">
              <div className="text-xl sm:text-2xl font-bold text-blue-600">{countdown}</div>
              <div className="text-xs text-blue-500">seconds</div>
            </div>
          </div>
        )}
      </div>

      {/* Instructions */}
      {trainingStatus === 'idle' && (
        <div className="bg-white/60 backdrop-blur-sm rounded-lg p-3 border border-purple-200 shadow-lg">
          <div className="text-xs sm:text-sm text-purple-700">
            <div className="font-medium text-purple-900 mb-1 text-sm">Training Instructions:</div>
            <ul className="space-y-1 text-xs">
              <li>• Ensure ESP32 device is connected and sending data</li>
              <li>• Start training and perform consistent reps for 8 seconds</li>
              <li>• Keep movements steady and controlled</li>
              <li>• Model will train automatically after data collection</li>
            </ul>
          </div>
        </div>
      )}
    </div>
  );
}
