/**
 * UPDATE #115: Load Balancing System
 * Distribute traffic across multiple servers
 */

interface ServerNode {
    id: string;
    url: string;
    region: string;
    healthy: boolean;
    load: number; // 0-100
    latency: number; // ms
    lastCheck: string;
}

type LoadBalancingStrategy = 'round-robin' | 'least-connections' | 'least-latency' | 'geographic';

class LoadBalancer {
    private servers: Map<string, ServerNode> = new Map();
    private currentIndex = 0;
    private strategy: LoadBalancingStrategy = 'least-latency';
    private healthCheckInterval: NodeJS.Timeout | null = null;

    /**
     * Add server to pool
     */
    addServer(server: Omit<ServerNode, 'healthy' | 'load' | 'latency' | 'lastCheck'>): void {
        this.servers.set(server.id, {
            ...server,
            healthy: true,
            load: 0,
            latency: 0,
            lastCheck: new Date().toISOString()
        });
    }

    /**
     * Remove server from pool
     */
    removeServer(serverId: string): void {
        this.servers.delete(serverId);
    }

    /**
     * Get next server based on strategy
     */
    getNextServer(): ServerNode | null {
        const healthyServers = Array.from(this.servers.values()).filter(s => s.healthy);

        if (healthyServers.length === 0) {
            console.error('No healthy servers available');
            return null;
        }

        switch (this.strategy) {
            case 'round-robin':
                return this.getRoundRobinServer(healthyServers);

            case 'least-connections':
                return this.getLeastConnectionsServer(healthyServers);

            case 'least-latency':
                return this.getLeastLatencyServer(healthyServers);

            case 'geographic':
                return this.getGeographicServer(healthyServers);

            default:
                return healthyServers[0];
        }
    }

    /**
     * Round-robin selection
     */
    private getRoundRobinServer(servers: ServerNode[]): ServerNode {
        const server = servers[this.currentIndex % servers.length];
        this.currentIndex++;
        return server;
    }

    /**
     * Least connections selection
     */
    private getLeastConnectionsServer(servers: ServerNode[]): ServerNode {
        return servers.reduce((min, server) =>
            server.load < min.load ? server : min
        );
    }

    /**
     * Least latency selection
     */
    private getLeastLatencyServer(servers: ServerNode[]): ServerNode {
        return servers.reduce((min, server) =>
            server.latency < min.latency ? server : min
        );
    }

    /**
     * Geographic selection (closest to user)
     */
    private getGeographicServer(servers: ServerNode[]): ServerNode {
        // In production, use user's geolocation
        const userRegion = 'us-east'; // Example

        const regionalServer = servers.find(s => s.region === userRegion);
        return regionalServer || servers[0];
    }

    /**
     * Health check for server
     */
    async checkServerHealth(serverId: string): Promise<boolean> {
        const server = this.servers.get(serverId);
        if (!server) return false;

        try {
            const startTime = Date.now();
            const response = await fetch(`${server.url}/health`, {
                method: 'GET',
                signal: AbortSignal.timeout(5000)
            });

            const latency = Date.now() - startTime;

            if (response.ok) {
                server.healthy = true;
                server.latency = latency;
                server.lastCheck = new Date().toISOString();
                return true;
            } else {
                server.healthy = false;
                return false;
            }
        } catch (error) {
            server.healthy = false;
            return false;
        }
    }

    /**
     * Start health checks
     */
    startHealthChecks(intervalMs: number = 30000): void {
        this.healthCheckInterval = setInterval(async () => {
            const checks = Array.from(this.servers.keys()).map(id =>
                this.checkServerHealth(id)
            );
            await Promise.all(checks);
        }, intervalMs);
    }

    /**
     * Stop health checks
     */
    stopHealthChecks(): void {
        if (this.healthCheckInterval) {
            clearInterval(this.healthCheckInterval);
            this.healthCheckInterval = null;
        }
    }

    /**
     * Set load balancing strategy
     */
    setStrategy(strategy: LoadBalancingStrategy): void {
        this.strategy = strategy;
    }

    /**
     * Get server stats
     */
    getStats(): {
        total: number;
        healthy: number;
        unhealthy: number;
        averageLatency: number;
        averageLoad: number;
    } {
        const servers = Array.from(this.servers.values());
        const healthy = servers.filter(s => s.healthy);

        return {
            total: servers.length,
            healthy: healthy.length,
            unhealthy: servers.length - healthy.length,
            averageLatency: healthy.reduce((sum, s) => sum + s.latency, 0) / (healthy.length || 1),
            averageLoad: healthy.reduce((sum, s) => sum + s.load, 0) / (healthy.length || 1)
        };
    }

    /**
     * Make request through load balancer
     */
    async request(path: string, options: RequestInit = {}): Promise<Response> {
        const server = this.getNextServer();

        if (!server) {
            throw new Error('No servers available');
        }

        const url = `${server.url}${path}`;

        try {
            const response = await fetch(url, options);

            // Update server load (simplified)
            server.load = Math.min(100, server.load + 1);
            setTimeout(() => {
                server.load = Math.max(0, server.load - 1);
            }, 1000);

            return response;
        } catch (error) {
            // Mark server as unhealthy on error
            server.healthy = false;

            // Retry with another server
            const nextServer = this.getNextServer();
            if (nextServer && nextServer.id !== server.id) {
                return this.request(path, options);
            }

            throw error;
        }
    }
}

export const loadBalancer = new LoadBalancer();

// Add default servers
loadBalancer.addServer({
    id: 'us-east-1',
    url: 'https://api-us-east-1.movieshows.com',
    region: 'us-east'
});

loadBalancer.addServer({
    id: 'us-west-1',
    url: 'https://api-us-west-1.movieshows.com',
    region: 'us-west'
});

loadBalancer.addServer({
    id: 'eu-west-1',
    url: 'https://api-eu-west-1.movieshows.com',
    region: 'eu-west'
});

// Start health checks
loadBalancer.startHealthChecks();

/**
 * React hook for load-balanced requests
 */
import { useState, useCallback } from 'react';

export function useLoadBalancedRequest() {
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<Error | null>(null);

    const request = useCallback(async (path: string, options?: RequestInit) => {
        setLoading(true);
        setError(null);

        try {
            const response = await loadBalancer.request(path, options);
            return response;
        } catch (err) {
            const error = err instanceof Error ? err : new Error('Request failed');
            setError(error);
            throw error;
        } finally {
            setLoading(false);
        }
    }, []);

    return { request, loading, error };
}
