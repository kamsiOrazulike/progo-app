import { toast, Id } from 'react-toastify';

class NotificationManager {
  private activeToasts = new Map<string, Id>();
  private lastMessages = new Map<string, number>();
  private debounceTime = 3000; // 3 seconds

  private shouldShowToast(key: string): boolean {
    const now = Date.now();
    const lastTime = this.lastMessages.get(key);
    
    if (!lastTime || now - lastTime > this.debounceTime) {
      this.lastMessages.set(key, now);
      return true;
    }
    
    return false;
  }

  private dismissExisting(key: string) {
    const existingToastId = this.activeToasts.get(key);
    if (existingToastId) {
      toast.dismiss(existingToastId);
      this.activeToasts.delete(key);
    }
  }

  success(message: string, key: string = message) {
    if (!this.shouldShowToast(key)) return;
    
    this.dismissExisting(key);
    const id = toast.success(message);
    this.activeToasts.set(key, id);
  }

  error(message: string, key: string = message) {
    if (!this.shouldShowToast(key)) return;
    
    this.dismissExisting(key);
    const id = toast.error(message);
    this.activeToasts.set(key, id);
  }

  warning(message: string, key: string = message) {
    if (!this.shouldShowToast(key)) return;
    
    this.dismissExisting(key);
    const id = toast.warning(message);
    this.activeToasts.set(key, id);
  }

  info(message: string, key: string = message) {
    if (!this.shouldShowToast(key)) return;
    
    this.dismissExisting(key);
    const id = toast.info(message);
    this.activeToasts.set(key, id);
  }

  // For one-time notifications that should only appear once per session
  once(type: 'success' | 'error' | 'warning' | 'info', message: string, key: string) {
    if (this.activeToasts.has(key)) return; // Already shown
    
    const id = toast[type](message);
    this.activeToasts.set(key, id);
  }
}

export const notifications = new NotificationManager();
