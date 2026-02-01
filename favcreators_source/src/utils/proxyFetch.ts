
const PROXIES = [
    (url: string) => `https://api.allorigins.win/raw?url=${encodeURIComponent(url)}`,
    (url: string) => `https://r.jina.ai/${url}`,
    (url: string) => `https://corsproxy.io/?${encodeURIComponent(url)}`,
    (url: string) => `https://api.codetabs.com/v1/proxy?url=${encodeURIComponent(url)}`,
    (url: string) => `https://thingproxy.freeboard.io/fetch/${url}`,
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
    for (const proxyFn of PROXIES) {
        const proxyUrl = proxyFn(targetUrl);

        for (let attempt = 0; attempt <= retriesPerProxy; attempt++) {
            try {
                if (attempt > 0) {
                    await new Promise((resolve) => setTimeout(resolve, 500 * attempt));
                }

                const response = await fetchWithTimeout(proxyUrl, timeoutMs);
                if (response.ok) {
                    const text = await response.text();
                    if (text && text.length > 10) { // Basic sanity check
                        return text;
                    }
                } else {
                    console.warn(`Proxy ${proxyUrl} returned status ${response.status}`);
                }
            } catch (e) {
                console.warn(`Proxy fetch failed for ${proxyUrl}`, e);
            }
        }
    }

    return null;
}
