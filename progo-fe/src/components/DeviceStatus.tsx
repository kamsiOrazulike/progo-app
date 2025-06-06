'use client';

import { Activity, Wifi, WifiOff, AlertCircle } from 'lucide-react';
import { useApp } from '@/hooks/useApp';
import { DEVICE_ID } from '@/types';

interface DeviceStatusProps {
  className?: string;
}

export default function DeviceStatus({ className = '' }: DeviceStatusProps) {
  const { state } = useApp();
  const { connectionStatus, deviceStatus, lastDataTime } = state;

  const getStatusInfo = () => {
    if (connectionStatus === 'disconnected' || connectionStatus === 'error') {
      return {
        icon: WifiOff,
        color: 'text-red-600',
        bgColor: 'bg-red-50',
        borderColor: 'border-red-200',
        status: 'Connection Failed',
        description: 'Use retry button below'
      };
    }

    if (connectionStatus === 'connecting') {
      return {
        icon: Wifi,
        color: 'text-purple-600',
        bgColor: 'bg-purple-50',
        borderColor: 'border-purple-200',
        status: 'Connecting...',
        description: 'Establishing connection'
      };
    }

    switch (deviceStatus) {
      case 'connected':
        return {
          icon: Activity,
          color: 'text-green-600',
          bgColor: 'bg-green-50',
          borderColor: 'border-green-200',
          status: 'Device Connected',
          description: 'ESP32 sending data'
        };
      case 'idle':
        return {
          icon: Wifi,
          color: 'text-blue-600',
          bgColor: 'bg-blue-50',
          borderColor: 'border-blue-200',
          status: 'Device Idle',
          description: 'Connected but no recent data'
        };
      default:
        return {
          icon: AlertCircle,
          color: 'text-gray-600',
          bgColor: 'bg-gray-50',
          borderColor: 'border-gray-200',
          status: 'Device Disconnected',
          description: 'No data received'
        };
    }
  };

  const statusInfo = getStatusInfo();
  const StatusIcon = statusInfo.icon;

  const formatLastDataTime = () => {
    if (!lastDataTime) return 'Never';
    
    const now = new Date();
    const diff = now.getTime() - lastDataTime.getTime();
    const seconds = Math.floor(diff / 1000);
    
    if (seconds < 60) return `${seconds}s ago`;
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
    return `${Math.floor(seconds / 3600)}h ago`;
  };

  return (
    <div className={`${statusInfo.bgColor} rounded-lg p-3 sm:p-4 border ${statusInfo.borderColor} ${className} shadow-lg backdrop-blur-sm mx-2 sm:mx-0`}>
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center space-x-2">
          <StatusIcon className={`w-4 h-4 sm:w-5 sm:h-5 ${statusInfo.color}`} />
          <span className="font-medium text-purple-900 text-sm sm:text-base">{statusInfo.status}</span>
        </div>
        <div className={`w-2.5 h-2.5 sm:w-3 sm:h-3 rounded-full ${
          deviceStatus === 'connected' ? 'bg-green-500 animate-pulse' :
          deviceStatus === 'idle' ? 'bg-purple-500 animate-pulse' :
          'bg-red-500 animate-pulse'
        }`} />
      </div>
      
      <div className="text-xs sm:text-sm text-purple-700 space-y-1">
        <div>Device: <span className="font-mono text-purple-600 text-xs">{DEVICE_ID}</span></div>
        <div>{statusInfo.description}</div>
        {lastDataTime && (
          <div>Last data: <span className="text-purple-600">{formatLastDataTime()}</span></div>
        )}
      </div>
    </div>
  );
}
