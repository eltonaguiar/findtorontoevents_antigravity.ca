/**
 * UPDATE #122: API Marketplace
 * Public API for developers
 */

interface APIKey {
    id: string;
    userId: number;
    key: string;
    name: string;
    scopes: string[];
    rateLimit: number;
    createdAt: string;
    lastUsed?: string;
    expiresAt?: string;
    active: boolean;
}

interface APIUsage {
    apiKeyId: string;
    endpoint: string;
    method: string;
    timestamp: string;
    responseTime: number;
    statusCode: number;
}

class APIMarketplace {
    private apiKeys: Map<string, APIKey> = new Map();
    private usage: APIUsage[] = [];
    private availableScopes = [
        'movies:read',
        'movies:write',
        'users:read',
        'users:write',
        'analytics:read',
        'subscriptions:read',
        'subscriptions:write'
    ];

    /**
     * Create API key
     */
    createAPIKey(
        userId: number,
        name: string,
        scopes: string[],
        rateLimit: number = 1000
    ): APIKey {
        // Validate scopes
        const invalidScopes = scopes.filter(s => !this.availableScopes.includes(s));
        if (invalidScopes.length > 0) {
            throw new Error(`Invalid scopes: ${invalidScopes.join(', ')}`);
        }

        const apiKey: APIKey = {
            id: `key_${Date.now()}`,
            userId,
            key: this.generateAPIKey(),
            name,
            scopes,
            rateLimit,
            createdAt: new Date().toISOString(),
            active: true
        };

        this.apiKeys.set(apiKey.key, apiKey);
        return apiKey;
    }

    /**
     * Validate API key
     */
    validateAPIKey(key: string, requiredScope?: string): APIKey | null {
        const apiKey = this.apiKeys.get(key);

        if (!apiKey) return null;
        if (!apiKey.active) return null;

        // Check expiration
        if (apiKey.expiresAt && new Date(apiKey.expiresAt) < new Date()) {
            return null;
        }

        // Check scope
        if (requiredScope && !apiKey.scopes.includes(requiredScope)) {
            return null;
        }

        // Update last used
        apiKey.lastUsed = new Date().toISOString();

        return apiKey;
    }

    /**
     * Track API usage
     */
    trackUsage(usage: APIUsage): void {
        this.usage.push(usage);

        // Keep only last 10000 entries
        if (this.usage.length > 10000) {
            this.usage = this.usage.slice(-10000);
        }
    }

    /**
     * Get API key usage stats
     */
    getUsageStats(apiKeyId: string): {
        totalRequests: number;
        requestsByEndpoint: Record<string, number>;
        averageResponseTime: number;
        errorRate: number;
    } {
        const keyUsage = this.usage.filter(u => u.apiKeyId === apiKeyId);

        const requestsByEndpoint: Record<string, number> = {};
        let totalResponseTime = 0;
        let errorCount = 0;

        keyUsage.forEach(usage => {
            requestsByEndpoint[usage.endpoint] = (requestsByEndpoint[usage.endpoint] || 0) + 1;
            totalResponseTime += usage.responseTime;
            if (usage.statusCode >= 400) errorCount++;
        });

        return {
            totalRequests: keyUsage.length,
            requestsByEndpoint,
            averageResponseTime: keyUsage.length > 0 ? totalResponseTime / keyUsage.length : 0,
            errorRate: keyUsage.length > 0 ? (errorCount / keyUsage.length) * 100 : 0
        };
    }

    /**
     * Revoke API key
     */
    revokeAPIKey(key: string): void {
        const apiKey = this.apiKeys.get(key);
        if (apiKey) {
            apiKey.active = false;
        }
    }

    /**
     * Get user's API keys
     */
    getUserAPIKeys(userId: number): APIKey[] {
        return Array.from(this.apiKeys.values()).filter(k => k.userId === userId);
    }

    /**
     * Generate random API key
     */
    private generateAPIKey(): string {
        const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
        let key = 'ms_';
        for (let i = 0; i < 32; i++) {
            key += chars.charAt(Math.floor(Math.random() * chars.length));
        }
        return key;
    }

    /**
     * Get available scopes
     */
    getAvailableScopes(): string[] {
        return this.availableScopes;
    }
}

export const apiMarketplace = new APIMarketplace();

/**
 * API documentation generator
 */
export const apiDocs = {
    endpoints: [
        {
            path: '/api/v1/movies',
            method: 'GET',
            description: 'Get list of movies',
            scope: 'movies:read',
            parameters: [
                { name: 'page', type: 'number', required: false },
                { name: 'limit', type: 'number', required: false },
                { name: 'genre', type: 'string', required: false }
            ],
            response: {
                data: 'Movie[]',
                total: 'number',
                page: 'number'
            }
        },
        {
            path: '/api/v1/movies/:id',
            method: 'GET',
            description: 'Get movie by ID',
            scope: 'movies:read',
            parameters: [
                { name: 'id', type: 'number', required: true }
            ],
            response: 'Movie'
        },
        {
            path: '/api/v1/users/:id',
            method: 'GET',
            description: 'Get user by ID',
            scope: 'users:read',
            parameters: [
                { name: 'id', type: 'number', required: true }
            ],
            response: 'User'
        }
    ]
};

/**
 * API Key management component
 */
import React, { useState } from 'react';

interface APIKeyManagerProps {
    userId: number;
}

export function APIKeyManager({ userId }: APIKeyManagerProps) {
    const [keys, setKeys] = useState<APIKey[]>(apiMarketplace.getUserAPIKeys(userId));
    const [showCreateForm, setShowCreateForm] = useState(false);

    const handleCreateKey = (name: string, scopes: string[]) => {
        const newKey = apiMarketplace.createAPIKey(userId, name, scopes);
        setKeys([...keys, newKey]);
        setShowCreateForm(false);
    };

    const handleRevokeKey = (key: string) => {
        apiMarketplace.revokeAPIKey(key);
        setKeys(keys.map(k => k.key === key ? { ...k, active: false } : k));
    };

    return (
        <div className="api-key-manager">
            <div className="header">
                <h2>API Keys</h2>
                <button onClick={() => setShowCreateForm(true)}>Create New Key</button>
            </div>

            <div className="keys-list">
                {keys.map(key => (
                    <div key={key.id} className={`key-card ${!key.active ? 'revoked' : ''}`}>
                        <div className="key-info">
                            <h3>{key.name}</h3>
                            <code className="key-value">{key.key}</code>
                            <div className="key-meta">
                                <span>Scopes: {key.scopes.join(', ')}</span>
                                <span>Rate Limit: {key.rateLimit}/hour</span>
                                <span>Created: {new Date(key.createdAt).toLocaleDateString()}</span>
                            </div>
                        </div>
                        {key.active && (
                            <button onClick={() => handleRevokeKey(key.key)} className="revoke-btn">
                                Revoke
                            </button>
                        )}
                    </div>
                ))}
            </div>
        </div>
    );
}

const styles = `
.api-key-manager {
  padding: 2rem;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;
}

.header h2 {
  margin: 0;
}

.header button {
  padding: 0.75rem 1.5rem;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border: none;
  border-radius: 8px;
  color: white;
  font-weight: 700;
  cursor: pointer;
}

.keys-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.key-card {
  padding: 1.5rem;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.key-card.revoked {
  opacity: 0.5;
}

.key-info h3 {
  margin: 0 0 0.5rem;
}

.key-value {
  display: block;
  padding: 0.5rem;
  background: rgba(0, 0, 0, 0.3);
  border-radius: 4px;
  font-family: monospace;
  font-size: 0.9rem;
  margin-bottom: 0.75rem;
}

.key-meta {
  display: flex;
  gap: 1rem;
  font-size: 0.85rem;
  opacity: 0.7;
}

.revoke-btn {
  padding: 0.5rem 1rem;
  background: rgba(248, 113, 113, 0.2);
  border: 1px solid rgba(248, 113, 113, 0.3);
  border-radius: 6px;
  color: #f87171;
  cursor: pointer;
}
`;
