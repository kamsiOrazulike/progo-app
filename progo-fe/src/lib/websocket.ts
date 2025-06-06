import { toast } from 'react-toastify';
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
          
          toast.success('Connected to device successfully!');
          resolve();
        };

        this.ws.onmessage = (event) => {
          try {
            const message: WSMessage = JSON.parse(event.data);
            console.log('WebSocket message received:', message);
            this.handleMessage(message);
          } catch (error) {
            console.error('Error parsing WebSocket message:', error);
            toast.error('Error processing server message');
          }
        };

        this.ws.onclose = (event) => {
          console.log('WebSocket closed:', event.code, event.reason);
          clearTimeout(connectTimeout);
          this.stopHeartbeat();
          this.updateConnectionStatus('disconnected');
          
          if (event.code !== 1000) { // Not a normal closure
            toast.warning('Connection lost - attempting to reconnect...');
            this.scheduleReconnect();
          }
        };

        this.ws.onerror = (error) => {
          console.error('WebSocket error:', error);
          clearTimeout(connectTimeout);
          this.updateConnectionStatus('error');
          
          if (this.ws?.readyState === WebSocket.CONNECTING) {
            reject(new Error('Failed to connect to server'));
          } else {
            toast.error('Connection error occurred');
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
    
    switch (status) {
      case 'connected':
        toast.success('ESP32 device connected and sending data');
        break;
      case 'idle':
        toast.info('ESP32 device connected but idle');
        break;
      case 'disconnected':
        toast.warning('ESP32 device disconnected');
        break;
    }
  }

  private handleTrainingUpdate(message: TrainingUpdateMessage) {
    const { status, accuracy, message: msg } = message.data;
    
    switch (status) {
      case 'started':
        toast.info('Training session started');
        break;
      case 'collecting':
        // Don't show toast for each update during collection
        break;
      case 'training':
        toast.info('Training AI model...');
        break;
      case 'completed':
        if (accuracy !== undefined) {
          toast.success(`Model training completed! Accuracy: ${(accuracy * 100).toFixed(1)}%`);
        } else {
          toast.success('Model training completed!');
        }
        break;
      case 'error':
        toast.error(`Training failed: ${msg || 'Unknown error'}`);
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
    
    toast.success(
      `Rep ${rep_count} detected! ${feedbackEmoji} Form: ${form_feedback} (${(confidence * 100).toFixed(0)}%)`
    );
  }

  private handleWorkoutStatus(message: WorkoutStatusMessage) {
    const { status } = message.data;
    
    switch (status) {
      case 'active':
        toast.info('Workout session started - start your reps!');
        break;
      case 'paused':
        toast.info('Workout session paused');
        break;
      case 'completed':
        toast.success('Workout session completed!');
        break;
    }
  }

  private handleError(message: ErrorMessage) {
    const { code, message: errorMsg } = message.data;
    console.error('Server error:', code, errorMsg);
    toast.error(`Error ${code}: ${errorMsg}`);
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
      toast.error('Unable to reconnect. Please refresh the page.');
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

  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }

  send(message: Record<string, unknown>) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    } else {
      console.warn('WebSocket not connected, cannot send message:', message);
      toast.warning('Not connected to server');
    }
  }
}

// Singleton instance
export const wsManager = new WebSocketManager();
