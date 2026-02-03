/**
 * UPDATE #47: Notification System
 * Toast notifications for user feedback
 */

import React, { createContext, useContext, useState, useCallback } from 'react';

interface Notification {
    id: string;
    type: 'success' | 'error' | 'info' | 'warning';
    message: string;
    duration?: number;
}

interface NotificationContextType {
    notifications: Notification[];
    addNotification: (type: Notification['type'], message: string, duration?: number) => void;
    removeNotification: (id: string) => void;
}

const NotificationContext = createContext<NotificationContextType | null>(null);

export function NotificationProvider({ children }: { children: React.ReactNode }) {
    const [notifications, setNotifications] = useState<Notification[]>([]);

    const addNotification = useCallback((type: Notification['type'], message: string, duration = 3000) => {
        const id = Math.random().toString(36).substr(2, 9);
        const notification = { id, type, message, duration };

        setNotifications(prev => [...prev, notification]);

        if (duration > 0) {
            setTimeout(() => {
                removeNotification(id);
            }, duration);
        }
    }, []);

    const removeNotification = useCallback((id: string) => {
        setNotifications(prev => prev.filter(n => n.id !== id));
    }, []);

    return (
        <NotificationContext.Provider value={{ notifications, addNotification, removeNotification }}>
            {children}
            <NotificationContainer notifications={notifications} onRemove={removeNotification} />
        </NotificationContext.Provider>
    );
}

export function useNotification() {
    const context = useContext(NotificationContext);
    if (!context) throw new Error('useNotification must be used within NotificationProvider');
    return context;
}

function NotificationContainer({ notifications, onRemove }: {
    notifications: Notification[];
    onRemove: (id: string) => void;
}) {
    return (
        <div className="notification-container">
            {notifications.map(notification => (
                <div key={notification.id} className={`notification ${notification.type}`}>
                    <span className="notification-icon">
                        {notification.type === 'success' && '✓'}
                        {notification.type === 'error' && '✗'}
                        {notification.type === 'info' && 'ℹ'}
                        {notification.type === 'warning' && '⚠'}
                    </span>
                    <span className="notification-message">{notification.message}</span>
                    <button onClick={() => onRemove(notification.id)} className="notification-close">×</button>
                </div>
            ))}
        </div>
    );
}

const styles = `
.notification-container {
  position: fixed;
  top: 1rem;
  right: 1rem;
  z-index: 9999;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.notification {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 1rem 1.5rem;
  background: rgba(0, 0, 0, 0.9);
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
  animation: slideIn 0.3s ease-out;
  min-width: 300px;
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

.notification.success {
  border-left: 4px solid #4caf50;
}

.notification.error {
  border-left: 4px solid #f44336;
}

.notification.info {
  border-left: 4px solid #2196f3;
}

.notification.warning {
  border-left: 4px solid #ff9800;
}

.notification-icon {
  font-size: 1.5rem;
}

.notification-message {
  flex: 1;
  color: white;
}

.notification-close {
  background: none;
  border: none;
  color: white;
  font-size: 1.5rem;
  cursor: pointer;
  opacity: 0.7;
  transition: opacity 0.2s;
}

.notification-close:hover {
  opacity: 1;
}
`;
