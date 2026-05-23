"""Rate-limiting, caching, and fallback helpers for free API access."""
import json
import logging
import pathlib
import time
import requests
from functools import wraps

logger = logging.getLogger("paper_trading")

CACHE_DIR = pathlib.Path(__file__).parent / "data" / ".cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Track last call time per source
_last_call: dict = {}


def rate_limited(source: str, min_interval: float = 1.0):
    """Decorator: enforce minimum interval between calls to same source."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            key = source
            elapsed = time.time() - _last_call.get(key, 0)
            if elapsed < min_interval:
                time.sleep(min_interval - elapsed)
            try:
                result = func(*args, **kwargs)
                _last_call[key] = time.time()
                return result
            except Exception:
                _last_call[key] = time.time()
                raise
        return wrapper
    return decorator


def cached(ttl_seconds: int = 900):
    """Decorator: cache function result to disk with TTL."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_key = f"{func.__name__}_{'_'.join(str(a) for a in args)}"
            cache_key = cache_key.replace("/", "_").replace(":", "_")[:200]
            cache_file = CACHE_DIR / f"{cache_key}.json"

            if cache_file.is_file():
                try:
                    data = json.loads(cache_file.read_text())
                    if time.time() - data.get("_ts", 0) < ttl_seconds:
                        return data["payload"]
                except Exception:
                    pass

            payload = func(*args, **kwargs)
            try:
                cache_file.write_text(json.dumps({"_ts": time.time(), "payload": payload}))
            except Exception:
                pass
            return payload
        return wrapper
    return decorator


def fetch_json(url: str, params: dict = None, headers: dict = None,
               timeout: int = 15, retries: int = 3) -> dict:
    """Fetch JSON with retry and exponential backoff."""
    hdrs = {"User-Agent": "PaperTrading/1.0"}
    if headers:
        hdrs.update(headers)
    for attempt in range(retries):
        try:
            r = requests.get(url, params=params, headers=hdrs, timeout=timeout)
            if r.status_code == 429:
                wait = int(r.headers.get("Retry-After", str(2 ** (attempt + 1))))
                logger.warning(f"Rate limited on {url}, waiting {wait}s")
                time.sleep(wait)
                continue
            r.raise_for_status()
            return r.json()
        except requests.exceptions.RequestException as e:
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
                continue
            logger.error(f"Failed to fetch {url}: {e}")
            raise
    return {}


def fetch_with_fallback(primary_fn, fallback_fn, *args, **kwargs):
    """Try primary function, fall back to secondary on failure."""
    try:
        return primary_fn(*args, **kwargs)
    except Exception as e:
        logger.warning(f"{primary_fn.__name__} failed ({e}), trying fallback")
        return fallback_fn(*args, **kwargs)
