/**
 * UPDATE #125: Enterprise SSO (Single Sign-On)
 * SAML and OAuth2 integration for enterprise auth
 */

interface SSOProvider {
    id: string;
    name: string;
    type: 'saml' | 'oauth2' | 'oidc';
    enabled: boolean;
    config: {
        issuer?: string;
        clientId?: string;
        clientSecret?: string;
        authorizationUrl?: string;
        tokenUrl?: string;
        userInfoUrl?: string;
        callbackUrl: string;
    };
}

interface SSOSession {
    id: string;
    userId: number;
    provider: string;
    accessToken: string;
    refreshToken?: string;
    expiresAt: string;
    createdAt: string;
}

class SSOManager {
    private providers: Map<string, SSOProvider> = new Map();
    private sessions: Map<string, SSOSession> = new Map();

    /**
     * Register SSO provider
     */
    registerProvider(provider: SSOProvider): void {
        this.providers.set(provider.id, provider);
    }

    /**
     * Initiate SSO login
     */
    initiateLogin(providerId: string, redirectUrl?: string): string {
        const provider = this.providers.get(providerId);
        if (!provider || !provider.enabled) {
            throw new Error('Provider not available');
        }

        const state = this.generateState();
        const params = new URLSearchParams({
            client_id: provider.config.clientId || '',
            redirect_uri: provider.config.callbackUrl,
            response_type: 'code',
            scope: 'openid profile email',
            state
        });

        // Store state for validation
        sessionStorage.setItem('sso_state', state);
        if (redirectUrl) {
            sessionStorage.setItem('sso_redirect', redirectUrl);
        }

        return `${provider.config.authorizationUrl}?${params.toString()}`;
    }

    /**
     * Handle SSO callback
     */
    async handleCallback(
        providerId: string,
        code: string,
        state: string
    ): Promise<SSOSession> {
        // Validate state
        const storedState = sessionStorage.getItem('sso_state');
        if (state !== storedState) {
            throw new Error('Invalid state parameter');
        }

        const provider = this.providers.get(providerId);
        if (!provider) {
            throw new Error('Provider not found');
        }

        // Exchange code for tokens
        const tokens = await this.exchangeCode(provider, code);

        // Get user info
        const userInfo = await this.getUserInfo(provider, tokens.access_token);

        // Create or update user
        const userId = await this.createOrUpdateUser(userInfo);

        // Create session
        const session: SSOSession = {
            id: `session_${Date.now()}`,
            userId,
            provider: providerId,
            accessToken: tokens.access_token,
            refreshToken: tokens.refresh_token,
            expiresAt: new Date(Date.now() + tokens.expires_in * 1000).toISOString(),
            createdAt: new Date().toISOString()
        };

        this.sessions.set(session.id, session);

        // Clean up
        sessionStorage.removeItem('sso_state');

        return session;
    }

    /**
     * Exchange authorization code for tokens
     */
    private async exchangeCode(
        provider: SSOProvider,
        code: string
    ): Promise<{ access_token: string; refresh_token?: string; expires_in: number }> {
        const response = await fetch(provider.config.tokenUrl!, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            body: new URLSearchParams({
                grant_type: 'authorization_code',
                code,
                client_id: provider.config.clientId!,
                client_secret: provider.config.clientSecret!,
                redirect_uri: provider.config.callbackUrl
            })
        });

        if (!response.ok) {
            throw new Error('Token exchange failed');
        }

        return response.json();
    }

    /**
     * Get user info from provider
     */
    private async getUserInfo(provider: SSOProvider, accessToken: string): Promise<any> {
        const response = await fetch(provider.config.userInfoUrl!, {
            headers: {
                'Authorization': `Bearer ${accessToken}`
            }
        });

        if (!response.ok) {
            throw new Error('Failed to get user info');
        }

        return response.json();
    }

    /**
     * Create or update user from SSO
     */
    private async createOrUpdateUser(userInfo: any): Promise<number> {
        // In production, create/update user in database
        console.log('Creating/updating user:', userInfo);
        return 1; // Return user ID
    }

    /**
     * Refresh access token
     */
    async refreshToken(sessionId: string): Promise<void> {
        const session = this.sessions.get(sessionId);
        if (!session || !session.refreshToken) {
            throw new Error('Cannot refresh token');
        }

        const provider = this.providers.get(session.provider);
        if (!provider) {
            throw new Error('Provider not found');
        }

        const response = await fetch(provider.config.tokenUrl!, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            body: new URLSearchParams({
                grant_type: 'refresh_token',
                refresh_token: session.refreshToken,
                client_id: provider.config.clientId!,
                client_secret: provider.config.clientSecret!
            })
        });

        if (!response.ok) {
            throw new Error('Token refresh failed');
        }

        const tokens = await response.json();
        session.accessToken = tokens.access_token;
        session.expiresAt = new Date(Date.now() + tokens.expires_in * 1000).toISOString();
    }

    /**
     * Logout from SSO
     */
    async logout(sessionId: string): Promise<void> {
        const session = this.sessions.get(sessionId);
        if (session) {
            this.sessions.delete(sessionId);
        }
    }

    /**
     * Generate random state
     */
    private generateState(): string {
        return Math.random().toString(36).substring(2, 15);
    }

    /**
     * Get all providers
     */
    getProviders(): SSOProvider[] {
        return Array.from(this.providers.values()).filter(p => p.enabled);
    }
}

export const ssoManager = new SSOManager();

// Register common SSO providers
ssoManager.registerProvider({
    id: 'google',
    name: 'Google',
    type: 'oauth2',
    enabled: true,
    config: {
        clientId: process.env.GOOGLE_CLIENT_ID || '',
        clientSecret: process.env.GOOGLE_CLIENT_SECRET || '',
        authorizationUrl: 'https://accounts.google.com/o/oauth2/v2/auth',
        tokenUrl: 'https://oauth2.googleapis.com/token',
        userInfoUrl: 'https://www.googleapis.com/oauth2/v2/userinfo',
        callbackUrl: 'https://movieshows.com/auth/callback/google'
    }
});

ssoManager.registerProvider({
    id: 'microsoft',
    name: 'Microsoft',
    type: 'oauth2',
    enabled: true,
    config: {
        clientId: process.env.MICROSOFT_CLIENT_ID || '',
        clientSecret: process.env.MICROSOFT_CLIENT_SECRET || '',
        authorizationUrl: 'https://login.microsoftonline.com/common/oauth2/v2.0/authorize',
        tokenUrl: 'https://login.microsoftonline.com/common/oauth2/v2.0/token',
        userInfoUrl: 'https://graph.microsoft.com/v1.0/me',
        callbackUrl: 'https://movieshows.com/auth/callback/microsoft'
    }
});

/**
 * SSO login component
 */
import React from 'react';

export function SSOLogin() {
    const providers = ssoManager.getProviders();

    const handleLogin = (providerId: string) => {
        const loginUrl = ssoManager.initiateLogin(providerId, window.location.href);
        window.location.href = loginUrl;
    };

    return (
        <div className="sso-login">
            <h3>Sign in with</h3>
            <div className="sso-providers">
                {providers.map(provider => (
                    <button
                        key={provider.id}
                        onClick={() => handleLogin(provider.id)}
                        className="sso-button"
                    >
                        <span className="provider-icon">{getProviderIcon(provider.id)}</span>
                        {provider.name}
                    </button>
                ))}
            </div>
        </div>
    );
}

function getProviderIcon(providerId: string): string {
    const icons: Record<string, string> = {
        google: '🔵',
        microsoft: '🟦',
        okta: '🔷',
        auth0: '🟧'
    };
    return icons[providerId] || '🔐';
}

const styles = `
.sso-login {
  padding: 2rem;
}

.sso-login h3 {
  margin: 0 0 1.5rem;
  text-align: center;
}

.sso-providers {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.sso-button {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1rem;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  color: white;
  font-size: 1rem;
  cursor: pointer;
  transition: all 0.2s;
}

.sso-button:hover {
  background: rgba(255, 255, 255, 0.1);
  border-color: rgba(255, 255, 255, 0.2);
}

.provider-icon {
  font-size: 1.5rem;
}
`;
