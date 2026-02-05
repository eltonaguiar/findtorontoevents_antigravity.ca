import { getAuthBase } from "./auth";

/** Same-origin server proxy (no CORS). Tried first when available. */
function getServerProxyUrl(targetUrl: string): string | null {
    if (typeof window === "undefined") return null;
    const base = getAuthBase();
    if (!base) return null;
    return `${base}/proxy.php?url=${encodeURIComponent(targetUrl)}`;
}

/** Public CORS proxies (fallback when server proxy fails). allorigins.win removed — often CORS/429. */
const PROXIES = [
    (url: string) => `https://corsproxy.io/?${encodeURIComponent(url)}`,
    (url: string) => `https://api.codetabs.com/v1/proxy?url=${encodeURIComponent(url)}`,
    (url: string) => `https://thingproxy.freeboard.io/fetch/${url}`,
    (url: string) => `https://r.jina.ai/${url}`,
];

export async function fetchWithTimeout(
    url: string,
    timeoutMs: number = 8000,
): Promise<Response> {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeoutMs);
    try {
        const response = await fetch(url, { signal: controller.signal });
        clearTimeout(timeoutId);
        return response;
    } catch (e) {
        clearTimeout(timeoutId);
        throw e;
    }
}

export async function fetchViaProxy(
    targetUrl: string,
    timeoutMs: number = 10000,
    retriesPerProxy: number = 1
): Promise<string | null> {
    const isDev = typeof window !== "undefined" && /localhost|127\.0\.0\.1/.test(window.location?.hostname ?? "");

    // 1. Try same-origin server proxy first (avoids CORS and 429 from public proxies)
    const serverUrl = getServerProxyUrl(targetUrl);
    if (serverUrl) {
        for (let attempt = 0; attempt <= 1; attempt++) {
            try {
                if (attempt > 0) await new Promise((r) => setTimeout(r, 400));
                const response = await fetchWithTimeout(serverUrl, timeoutMs);
                if (response.ok) {
                    const text = await response.text();
                    if (text != null && text.length > 0) {
                        if (isDev) console.log("[FC API] PROXY fetch", targetUrl, "→ 200 OK (server)");
                        return text;
                    }
                }
            } catch {
                /* fall through to public proxies */
            }
        }
    }

    // 2. Fall back to public CORS proxies
    if (isDev) console.log("[FC API] PROXY fetch", targetUrl);
    for (const proxyFn of PROXIES) {
        const proxyUrl = proxyFn(targetUrl);
        for (let attempt = 0; attempt <= retriesPerProxy; attempt++) {
            try {
                if (attempt > 0) await new Promise((resolve) => setTimeout(resolve, 500 * attempt));
                const response = await fetchWithTimeout(proxyUrl, timeoutMs);
                if (response.ok) {
                    const text = await response.text();
                    if (text && text.length > 10) {
                        if (isDev) console.log("[FC API] PROXY fetch", targetUrl, "→ 200 OK");
                        return text;
                    }
                }
            } catch {
                /* next proxy */
            }
        }
    }

    return null;
}
