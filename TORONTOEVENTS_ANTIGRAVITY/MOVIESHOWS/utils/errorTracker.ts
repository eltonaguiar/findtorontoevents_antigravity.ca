/**
 * UPDATE #87: Error Tracking System
 * Track and report errors
 */

interface ErrorReport {
    id: string;
    message: string;
    stack?: string;
    timestamp: string;
    url: string;
    userAgent: string;
    userId?: string;
    severity: 'low' | 'medium' | 'high' | 'critical';
    context?: Record<string, any>;
}

class ErrorTracker {
    private errors: ErrorReport[] = [];
    private readonly MAX_ERRORS = 50;
    private errorHandlers: ((error: ErrorReport) => void)[] = [];

    constructor() {
        // Global error handler
        if (typeof window !== 'undefined') {
            window.addEventListener('error', (event) => {
                this.captureError(event.error || new Error(event.message), 'high');
            });

            window.addEventListener('unhandledrejection', (event) => {
                this.captureError(new Error(event.reason), 'high');
            });
        }
    }

    /**
     * Capture an error
     */
    captureError(error: Error, severity: ErrorReport['severity'] = 'medium', context?: Record<string, any>): void {
        const report: ErrorReport = {
            id: this.generateId(),
            message: error.message,
            stack: error.stack,
            timestamp: new Date().toISOString(),
            url: typeof window !== 'undefined' ? window.location.href : '',
            userAgent: typeof navigator !== 'undefined' ? navigator.userAgent : '',
            severity,
            context
        };

        this.errors.push(report);

        // Limit stored errors
        if (this.errors.length > this.MAX_ERRORS) {
            this.errors.shift();
        }

        // Notify handlers
        this.errorHandlers.forEach(handler => handler(report));

        // Log to console in development
        if (process.env.NODE_ENV === 'development') {
            console.error('Error tracked:', report);
        }

        // Send to server in production
        if (process.env.NODE_ENV === 'production') {
            this.sendToServer(report);
        }
    }

    /**
     * Add error handler
     */
    onError(handler: (error: ErrorReport) => void): () => void {
        this.errorHandlers.push(handler);
        return () => {
            const index = this.errorHandlers.indexOf(handler);
            if (index > -1) {
                this.errorHandlers.splice(index, 1);
            }
        };
    }

    /**
     * Get all errors
     */
    getErrors(): ErrorReport[] {
        return [...this.errors];
    }

    /**
     * Clear errors
     */
    clearErrors(): void {
        this.errors = [];
    }

    /**
     * Get error stats
     */
    getStats(): {
        total: number;
        bySeverity: Record<string, number>;
        recent: ErrorReport[];
    } {
        const bySeverity: Record<string, number> = {
            low: 0,
            medium: 0,
            high: 0,
            critical: 0
        };

        this.errors.forEach(error => {
            bySeverity[error.severity]++;
        });

        return {
            total: this.errors.length,
            bySeverity,
            recent: this.errors.slice(-5)
        };
    }

    private generateId(): string {
        return `${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }

    private async sendToServer(report: ErrorReport): Promise<void> {
        try {
            await fetch('/api/errors', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(report)
            });
        } catch (error) {
            console.error('Failed to send error report:', error);
        }
    }
}

export const errorTracker = new ErrorTracker();

/**
 * React hook for error tracking
 */
import { useEffect } from 'react';

export function useErrorTracking(userId?: string) {
    useEffect(() => {
        const unsubscribe = errorTracker.onError((error) => {
            // Add user context
            if (userId) {
                error.userId = userId;
            }
        });

        return unsubscribe;
    }, [userId]);

    return {
        captureError: (error: Error, severity?: ErrorReport['severity'], context?: Record<string, any>) => {
            errorTracker.captureError(error, severity, context);
        },
        getErrors: () => errorTracker.getErrors(),
        clearErrors: () => errorTracker.clearErrors(),
        getStats: () => errorTracker.getStats()
    };
}

/**
 * Try-catch wrapper with error tracking
 */
export async function withErrorTracking<T>(
    fn: () => Promise<T>,
    context?: Record<string, any>
): Promise<T> {
    try {
        return await fn();
    } catch (error) {
        errorTracker.captureError(
            error instanceof Error ? error : new Error(String(error)),
            'high',
            context
        );
        throw error;
    }
}
