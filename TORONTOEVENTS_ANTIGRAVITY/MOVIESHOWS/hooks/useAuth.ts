/**
 * UPDATE #16: useAuth Hook
 * React hook for authentication state
 */

import { useState, useEffect, useCallback } from 'react';

interface User {
    id: number;
    username: string;
    email?: string;
}

interface UseAuthResult {
    user: User | null;
    isAuthenticated: boolean;
    isLoading: boolean;
    login: (username: string, password: string) => Promise<void>;
    logout: () => Promise<void>;
    checkAuth: () => Promise<void>;
}

export function useAuth(): UseAuthResult {
    const [user, setUser] = useState<User | null>(null);
    const [isLoading, setIsLoading] = useState(true);

    const checkAuth = useCallback(async () => {
        try {
            const response = await fetch('/fc/api/check-auth.php', {
                credentials: 'include'
            });

            if (response.ok) {
                const data = await response.json();
                if (data.authenticated) {
                    setUser(data.user);
                } else {
                    setUser(null);
                }
            } else {
                setUser(null);
            }
        } catch (error) {
            console.error('Auth check failed:', error);
            setUser(null);
        } finally {
            setIsLoading(false);
        }
    }, []);

    useEffect(() => {
        checkAuth();
    }, [checkAuth]);

    const login = useCallback(async (username: string, password: string) => {
        const response = await fetch('/fc/api/login.php', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ username, password })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.message || 'Login failed');
        }

        const data = await response.json();
        setUser(data.user);
    }, []);

    const logout = useCallback(async () => {
        try {
            await fetch('/fc/api/logout.php', {
                method: 'POST',
                credentials: 'include'
            });
        } catch (error) {
            console.error('Logout failed:', error);
        } finally {
            setUser(null);
        }
    }, []);

    return {
        user,
        isAuthenticated: !!user,
        isLoading,
        login,
        logout,
        checkAuth
    };
}
