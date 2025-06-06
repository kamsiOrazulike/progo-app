import { notifications } from './notifications';
import {
  WSMessage,
  DeviceStatusMessage,
  TrainingUpdateMessage,
  RepDetectedMessage,
  WorkoutStatusMessage,
  ErrorMessage,
  ConnectionStatus,
  DEVICE_ID,
  WEBSOCKET_TIMEOUT,
  CONNECTION_RETRY_DELAY
} from '@/types';

export type MessageHandler = (message: WSMessage) => void;

export class WebSocketManager {
  private ws: WebSocket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectTimeout: NodeJS.Timeout | null = null;
  private heartbeatInterval: NodeJS.Timeout | null = null;
  private messageHandlers: Set<MessageHandler> = new Set();
  private connectionStatusCallback: ((status: ConnectionStatus) => void) | null = null;
  private baseUrl: string;
  private lastConnectionState: string = 'disconnected';

  constructor(baseUrl: string = 'wss://progo-be.onrender.com') {
    this.baseUrl = baseUrl;
  }

  setConnectionStatusCallback(callback: (status: ConnectionStatus) => void) {
    this.connectionStatusCallback = callback;
  }

  addMessageHandler(handler: MessageHandler) {
    this.messageHandlers.add(handler);
  }

  removeMessageHandler(handler: MessageHandler) {
    this.messageHandlers.delete(handler);
  }

  private updateConnectionStatus(status: ConnectionStatus) {
    if (this.connectionStatusCallback) {
      this.connectionStatusCallback(status);
    }
    this.showConnectionStatus(status);
  }

  private showConnectionStatus(status: ConnectionStatus) {
    if (this.lastConnectionState !== status) {
      this.lastConnectionState = status;
      
      switch(status) {
        case 'connected':
          notifications.success('Connected to device successfully!', 'connection-status');
          break;
        case 'disconnected':
          notifications.warning('Device disconnected', 'connection-status');
          break;
        case 'error':
          notifications.error('Connection failed', 'connection-status');
          break;
        case 'connecting':
          // Don't show notification for connecting state to reduce noise
          break;
      }
    }
  }

  private notifyHandlers(message: WSMessage) {
    this.messageHandlers.forEach(handler => {
      try {
        handler(message);
      } catch (error) {
        console.error('Error in message handler:', error);
      }
    });
  }

  connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      try {
        this.updateConnectionStatus('connecting');
        
        // Construct WebSocket URL with device ID
        const wsUrl = `${this.baseUrl}/ws/${DEVICE_ID}`;
        console.log('Connecting to WebSocket:', wsUrl);
        
        this.ws = new WebSocket(wsUrl);

        const connectTimeout = setTimeout(() => {
          if (this.ws?.readyState === WebSocket.CONNECTING) {
            this.ws.close();
            reject(new Error('Connection timeout'));
          }
        }, WEBSOCKET_TIMEOUT);

        this.ws.onopen = () => {
          console.log('WebSocket connected successfully');
          clearTimeout(connectTimeout);
          this.updateConnectionStatus('connected');
          this.reconnectAttempts = 0;
          this.startHeartbeat();
          
          resolve();
        };

        this.ws.onmessage = (event) => {
          try {
            const message: WSMessage = JSON.parse(event.data);
            console.log('WebSocket message received:', message);
            this.handleMessage(message);
          } catch (error) {
            console.error('Error parsing WebSocket message:', error);
            notifications.error('Error processing server message');
          }
        };

        this.ws.onclose = (event) => {
          console.log('WebSocket closed:', event.code, event.reason);
          clearTimeout(connectTimeout);
          this.stopHeartbeat();
          this.updateConnectionStatus('disconnected');
          
          if (event.code !== 1000) { // Not a normal closure
            this.scheduleReconnect();
          }
        };

        this.ws.onerror = (error) => {
          console.error('WebSocket error:', error);
          clearTimeout(connectTimeout);
          this.updateConnectionStatus('error');
          
          if (this.ws?.readyState === WebSocket.CONNECTING) {
            reject(new Error('Failed to connect to server'));
          }
        };

      } catch (error) {
        console.error('Error creating WebSocket:', error);
        this.updateConnectionStatus('error');
        reject(error);
      }
    });
  }

  private handleMessage(message: WSMessage) {
    // Add timestamp if not present
    if (!message.timestamp) {
      message.timestamp = new Date().toISOString();
    }

    // Handle specific message types
    switch (message.type) {
      case 'device_status':
        this.handleDeviceStatus(message as DeviceStatusMessage);
        break;
      case 'training_update':
        this.handleTrainingUpdate(message as TrainingUpdateMessage);
        break;
      case 'rep_detected':
        this.handleRepDetected(message as RepDetectedMessage);
        break;
      case 'workout_status':
        this.handleWorkoutStatus(message as WorkoutStatusMessage);
        break;
      case 'error':
        this.handleError(message as ErrorMessage);
        break;
      default:
        console.log('Unknown message type:', message.type);
    }

    // Notify all handlers
    this.notifyHandlers(message);
  }

  private handleDeviceStatus(message: DeviceStatusMessage) {
    const { status } = message.data;
    
    // Only show device status notifications for significant changes
    switch (status) {
      case 'connected':
        notifications.once('success', 'ESP32 device connected and sending data', 'device-connected');
        break;
      case 'disconnected':
        notifications.once('warning', 'ESP32 device disconnected', 'device-disconnected');
        break;
      // Don't show notification for 'idle' status to reduce noise
    }
  }

  private handleTrainingUpdate(message: TrainingUpdateMessage) {
    const { status, accuracy, message: msg } = message.data;
    
    switch (status) {
      case 'started':
        notifications.info('Training session started');
        break;
      case 'collecting':
        // Don't show toast for each update during collection
        break;
      case 'training':
        notifications.info('Training AI model...');
        break;
      case 'completed':
        if (accuracy !== undefined) {
          notifications.success(`Model training completed! Accuracy: ${(accuracy * 100).toFixed(1)}%`);
        } else {
          notifications.success('Model training completed!');
        }
        break;
      case 'error':
        notifications.error(`Training failed: ${msg || 'Unknown error'}`);
        break;
    }
  }

  private handleRepDetected(message: RepDetectedMessage) {
    const { rep_count, confidence, form_feedback } = message.data;
    
    // Show rep detection with form feedback
    const feedbackEmoji = {
      'good': '🟢',
      'fair': '🟡', 
      'poor': '🔴'
    }[form_feedback];
    
    notifications.success(
      `Rep ${rep_count} detected! ${feedbackEmoji} Form: ${form_feedback} (${(confidence * 100).toFixed(0)}%)`
    );
  }

  private handleWorkoutStatus(message: WorkoutStatusMessage) {
    const { status } = message.data;
    
    switch (status) {
      case 'active':
        notifications.info('Workout session started - start your reps!');
        break;
      case 'paused':
        notifications.info('Workout session paused');
        break;
      case 'completed':
        notifications.success('Workout session completed!');
        break;
    }
  }

  private handleError(message: ErrorMessage) {
    const { code, message: errorMsg } = message.data;
    console.error('Server error:', code, errorMsg);
    notifications.error(`Error ${code}: ${errorMsg}`);
  }

  private startHeartbeat() {
    this.heartbeatInterval = setInterval(() => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        this.ws.send(JSON.stringify({ type: 'ping' }));
      }
    }, 30000); // Send ping every 30 seconds
  }

  private stopHeartbeat() {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }
  }

  private scheduleReconnect() {
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
    }

    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.log('Max reconnection attempts reached');
      // Don't show error notification - let user manually reconnect via UI
      return;
    }

    this.reconnectAttempts++;
    const delay = CONNECTION_RETRY_DELAY * Math.pow(2, this.reconnectAttempts - 1); // Exponential backoff
    
    console.log(`Scheduling reconnection attempt ${this.reconnectAttempts} in ${delay}ms`);
    
    this.reconnectTimeout = setTimeout(() => {
      if (this.ws?.readyState !== WebSocket.OPEN) {
        console.log(`Reconnection attempt ${this.reconnectAttempts}`);
        this.connect().catch(error => {
          console.error('Reconnection failed:', error);
        });
      }
    }, delay);
  }

  disconnect() {
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }

    this.stopHeartbeat();

    if (this.ws) {
      this.ws.close(1000, 'Client disconnect');
      this.ws = null;
    }

    this.updateConnectionStatus('disconnected');
  }

  // Manual reconnection method for user-triggered reconnection
  reconnect(): Promise<void> {
    console.log('Manual reconnection requested');
    
    // Cancel any pending automatic reconnection
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }

    // Reset reconnection attempts for manual reconnection
    this.reconnectAttempts = 0;

    // Disconnect current connection if any
    if (this.ws) {
      this.ws.close(1000, 'Manual reconnect');
      this.ws = null;
    }

    // Attempt to connect
    return this.connect();
  }

  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }

  send(message: Record<string, unknown>) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    } else {
      console.warn('WebSocket not connected, cannot send message:', message);
      notifications.warning('Not connected to server');
    }
  }
}

// Singleton instance
export const wsManager = new WebSocketManager();
