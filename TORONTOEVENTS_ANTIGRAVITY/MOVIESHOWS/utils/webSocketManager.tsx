/**
 * UPDATE #112: WebSocket Real-Time System
 * Real-time updates and notifications
 */

type WebSocketEvent =
    | 'connection'
    | 'disconnect'
    | 'message'
    | 'notification'
    | 'user_online'
    | 'user_offline'
    | 'content_update';

interface WebSocketMessage {
    type: WebSocketEvent;
    payload: any;
    timestamp: string;
}

class WebSocketManager {
    private ws: WebSocket | null = null;
    private reconnectAttempts = 0;
    private maxReconnectAttempts = 5;
    private reconnectDelay = 1000;
    private listeners: Map<WebSocketEvent, Set<(data: any) => void>> = new Map();
    private heartbeatInterval: NodeJS.Timeout | null = null;

    /**
     * Connect to WebSocket server
     */
    connect(url: string, token?: string): void {
        if (this.ws?.readyState === WebSocket.OPEN) {
            console.log('WebSocket already connected');
            return;
        }

        const wsUrl = token ? `${url}?token=${token}` : url;
        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = () => {
            console.log('WebSocket connected');
            this.reconnectAttempts = 0;
            this.startHeartbeat();
            this.emit('connection', { connected: true });
        };

        this.ws.onmessage = (event) => {
            try {
                const message: WebSocketMessage = JSON.parse(event.data);
                this.handleMessage(message);
            } catch (error) {
                console.error('Failed to parse WebSocket message:', error);
            }
        };

        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
        };

        this.ws.onclose = () => {
            console.log('WebSocket disconnected');
            this.stopHeartbeat();
            this.emit('disconnect', { connected: false });
            this.attemptReconnect(url, token);
        };
    }

    /**
     * Disconnect from WebSocket
     */
    disconnect(): void {
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }
        this.stopHeartbeat();
    }

    /**
     * Send message
     */
    send(type: WebSocketEvent, payload: any): void {
        if (this.ws?.readyState === WebSocket.OPEN) {
            const message: WebSocketMessage = {
                type,
                payload,
                timestamp: new Date().toISOString()
            };
            this.ws.send(JSON.stringify(message));
        } else {
            console.warn('WebSocket not connected');
        }
    }

    /**
     * Subscribe to event
     */
    on(event: WebSocketEvent, callback: (data: any) => void): () => void {
        if (!this.listeners.has(event)) {
            this.listeners.set(event, new Set());
        }
        this.listeners.get(event)!.add(callback);

        // Return unsubscribe function
        return () => {
            this.listeners.get(event)?.delete(callback);
        };
    }

    /**
     * Emit event to listeners
     */
    private emit(event: WebSocketEvent, data: any): void {
        const callbacks = this.listeners.get(event);
        if (callbacks) {
            callbacks.forEach(callback => callback(data));
        }
    }

    /**
     * Handle incoming message
     */
    private handleMessage(message: WebSocketMessage): void {
        this.emit(message.type, message.payload);
        this.emit('message', message);
    }

    /**
     * Attempt to reconnect
     */
    private attemptReconnect(url: string, token?: string): void {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            console.error('Max reconnection attempts reached');
            return;
        }

        this.reconnectAttempts++;
        const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);

        console.log(`Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`);

        setTimeout(() => {
            this.connect(url, token);
        }, delay);
    }

    /**
     * Start heartbeat to keep connection alive
     */
    private startHeartbeat(): void {
        this.heartbeatInterval = setInterval(() => {
            this.send('message', { type: 'ping' });
        }, 30000); // Every 30 seconds
    }

    /**
     * Stop heartbeat
     */
    private stopHeartbeat(): void {
        if (this.heartbeatInterval) {
            clearInterval(this.heartbeatInterval);
            this.heartbeatInterval = null;
        }
    }

    /**
     * Get connection status
     */
    isConnected(): boolean {
        return this.ws?.readyState === WebSocket.OPEN;
    }
}

export const webSocketManager = new WebSocketManager();

/**
 * React hook for WebSocket
 */
import { useEffect, useState } from 'react';

export function useWebSocket(url: string, token?: string) {
    const [connected, setConnected] = useState(false);
    const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);

    useEffect(() => {
        webSocketManager.connect(url, token);

        const unsubscribeConnection = webSocketManager.on('connection', () => {
            setConnected(true);
        });

        const unsubscribeDisconnect = webSocketManager.on('disconnect', () => {
            setConnected(false);
        });

        const unsubscribeMessage = webSocketManager.on('message', (message) => {
            setLastMessage(message);
        });

        return () => {
            unsubscribeConnection();
            unsubscribeDisconnect();
            unsubscribeMessage();
            webSocketManager.disconnect();
        };
    }, [url, token]);

    const send = (type: WebSocketEvent, payload: any) => {
        webSocketManager.send(type, payload);
    };

    const subscribe = (event: WebSocketEvent, callback: (data: any) => void) => {
        return webSocketManager.on(event, callback);
    };

    return {
        connected,
        lastMessage,
        send,
        subscribe
    };
}

/**
 * Real-time notifications component
 */
import React from 'react';

export function RealTimeNotifications() {
    const { connected, subscribe } = useWebSocket('wss://api.movieshows.com/ws');
    const [notifications, setNotifications] = useState<any[]>([]);

    useEffect(() => {
        const unsubscribe = subscribe('notification', (notification) => {
            setNotifications(prev => [notification, ...prev].slice(0, 10));
        });

        return unsubscribe;
    }, [subscribe]);

    return (
        <div className="realtime-notifications">
            <div className="connection-status">
                <span className={`status-indicator ${connected ? 'connected' : 'disconnected'}`} />
                {connected ? 'Connected' : 'Disconnected'}
            </div>

            {notifications.length > 0 && (
                <div className="notifications-list">
                    {notifications.map((notification, index) => (
                        <div key={index} className="notification-item">
                            {notification.message}
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}

const styles = `
.realtime-notifications {
  position: fixed;
  top: 1rem;
  right: 1rem;
  z-index: 1000;
}

.connection-status {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  background: rgba(0, 0, 0, 0.8);
  border-radius: 6px;
  font-size: 0.85rem;
}

.status-indicator {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.status-indicator.connected {
  background: #4ade80;
  box-shadow: 0 0 8px #4ade80;
}

.status-indicator.disconnected {
  background: #f87171;
}

.notifications-list {
  margin-top: 0.5rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.notification-item {
  padding: 0.75rem;
  background: rgba(102, 126, 234, 0.2);
  border: 1px solid rgba(102, 126, 234, 0.3);
  border-radius: 6px;
  font-size: 0.9rem;
  animation: slideIn 0.3s ease-out;
}

@keyframes slideIn {
  from {
    transform: translateX(100%);
    opacity: 0;
  }
  to {
    transform: translateX(0);
    opacity: 1;
  }
}
`;
