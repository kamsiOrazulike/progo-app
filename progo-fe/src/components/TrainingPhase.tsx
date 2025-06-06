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
          color: 'text-blue-400',
          bgColor: 'bg-blue-900/20',
          title: 'Collecting Data',
          description: `Collecting training data... ${countdown}s remaining`,
          showProgress: true,
          progress: ((TRAINING_DURATION - countdown) / TRAINING_DURATION) * 100
        };
      case 'training':
        return {
          icon: Loader2,
          color: 'text-yellow-400',
          bgColor: 'bg-yellow-900/20',
          title: 'Training Model',
          description: 'AI model is training...',
          showProgress: true,
          progress: trainingProgress * 100,
          spinning: true
        };
      case 'completed':
        return {
          icon: CheckCircle,
          color: 'text-green-400',
          bgColor: 'bg-green-900/20',
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
          color: 'text-red-400',
          bgColor: 'bg-red-900/20',
          title: 'Training Failed',
          description: 'Training encountered an error. Please try again.',
          showProgress: false
        };
      default:
        return {
          icon: Play,
          color: 'text-gray-400',
          bgColor: 'bg-gray-900/20',
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
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold text-white flex items-center">
          <span className="bg-blue-600 text-white rounded-full w-6 h-6 flex items-center justify-center text-sm font-bold mr-2">
            1
          </span>
          Training Phase
        </h2>
        {isModelReady && (
          <div className="flex items-center text-green-400 text-sm">
            <CheckCircle className="w-4 h-4 mr-1" />
            Model Ready
          </div>
        )}
      </div>

      {/* Status Card */}
      <div className={`${statusInfo.bgColor} rounded-lg p-4 border border-gray-700`}>
        <div className="flex items-center space-x-3 mb-3">
          <StatusIcon 
            className={`w-6 h-6 ${statusInfo.color} ${statusInfo.spinning ? 'animate-spin' : ''}`} 
          />
          <div>
            <div className="font-semibold text-white">{statusInfo.title}</div>
            <div className="text-sm text-gray-300">{statusInfo.description}</div>
          </div>
        </div>

        {/* Progress Bar */}
        {statusInfo.showProgress && (
          <div className="mt-3">
            <div className="flex justify-between text-xs text-gray-400 mb-1">
              <span>Progress</span>
              <span>{Math.round(statusInfo.progress || 0)}%</span>
            </div>
            <div className="w-full bg-gray-700 rounded-full h-2">
              <div 
                className={`h-2 rounded-full transition-all duration-300 ${
                  trainingStatus === 'collecting' ? 'bg-blue-500' : 'bg-yellow-500'
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
            className="flex-1 px-6 py-3 rounded-lg font-semibold text-white transition-all duration-200 flex items-center justify-center space-x-2 bg-green-600 hover:bg-green-700 active:bg-green-800"
          >
            <Play className="w-5 h-5" />
            <span>Start Workout</span>
          </button>
        ) : (
          <button
            onClick={handleStartTraining}
            disabled={!canStartTraining || isTrainingActive}
            className={`flex-1 px-6 py-3 rounded-lg font-semibold text-white transition-all duration-200 flex items-center justify-center space-x-2 ${
              canStartTraining && !isTrainingActive
                ? 'bg-blue-600 hover:bg-blue-700 active:bg-blue-800'
                : 'bg-gray-700 cursor-not-allowed opacity-50'
            }`}
          >
            {isTrainingActive ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                <span>{trainingStatus === 'collecting' ? 'Collecting...' : 'Training...'}</span>
              </>
            ) : (
              <>
                <Play className="w-5 h-5" />
                <span>Start Training</span>
              </>
            )}
          </button>
        )}

        {/* Countdown Display */}
        {isCountingDown && (
          <div className="flex items-center justify-center bg-blue-900/40 px-4 py-3 rounded-lg border border-blue-600">
            <div className="text-center">
              <div className="text-2xl font-bold text-blue-400">{countdown}</div>
              <div className="text-xs text-blue-300">seconds</div>
            </div>
          </div>
        )}
      </div>

      {/* Instructions */}
      {trainingStatus === 'idle' && (
        <div className="bg-gray-800/50 rounded-lg p-3 border border-gray-700">
          <div className="text-sm text-gray-300">
            <div className="font-medium text-white mb-1">Training Instructions:</div>
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
