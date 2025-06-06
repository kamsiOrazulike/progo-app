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
        color: 'text-red-400',
        bgColor: 'bg-red-900/20',
        status: 'Device Disconnected',
        description: 'WebSocket connection lost'
      };
    }

    if (connectionStatus === 'connecting') {
      return {
        icon: Wifi,
        color: 'text-yellow-400',
        bgColor: 'bg-yellow-900/20',
        status: 'Connecting...',
        description: 'Establishing connection'
      };
    }

    switch (deviceStatus) {
      case 'connected':
        return {
          icon: Activity,
          color: 'text-green-400',
          bgColor: 'bg-green-900/20',
          status: 'Device Connected',
          description: 'ESP32 sending data'
        };
      case 'idle':
        return {
          icon: Wifi,
          color: 'text-yellow-400',
          bgColor: 'bg-yellow-900/20',
          status: 'Device Idle',
          description: 'Connected but no recent data'
        };
      default:
        return {
          icon: AlertCircle,
          color: 'text-red-400',
          bgColor: 'bg-red-900/20',
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
    <div className={`${statusInfo.bgColor} rounded-lg p-4 border border-gray-700 ${className}`}>
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center space-x-2">
          <StatusIcon className={`w-5 h-5 ${statusInfo.color}`} />
          <span className="font-medium text-white">{statusInfo.status}</span>
        </div>
        <div className={`w-3 h-3 rounded-full ${
          deviceStatus === 'connected' ? 'bg-green-400 pulse-success' :
          deviceStatus === 'idle' ? 'bg-yellow-400 pulse-warning' :
          'bg-red-400 pulse-error'
        }`} />
      </div>
      
      <div className="text-sm text-gray-300 space-y-1">
        <div>Device: <span className="font-mono text-blue-300">{DEVICE_ID}</span></div>
        <div>{statusInfo.description}</div>
        {lastDataTime && (
          <div>Last data: <span className="text-gray-400">{formatLastDataTime()}</span></div>
        )}
      </div>
    </div>
  );
}
