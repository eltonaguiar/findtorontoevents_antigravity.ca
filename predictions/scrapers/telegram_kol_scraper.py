"""Telegram KOL scraper - monitors Telegram channels for crypto trading predictions.

Requires telethon library and Telegram API credentials.
Gracefully degrades when credentials or library are missing (CI-safe).
"""
import asyncio
import base64
import os
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ---------------------------------------------------------------------------
# Path setup for sibling package imports
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).parent.parent))
from db import get_db, insert_prediction

sys.path.insert(0, str(Path(__file__).parent.parent / "kol"))
from kol_registry import get_kols_by_platform

# ---------------------------------------------------------------------------
# Optional telethon import
# ---------------------------------------------------------------------------
try:
    from telethon import TelegramClient, events
    from telethon.sessions import StringSession
    HAS_TELETHON = True
except ImportError:
    HAS_TELETHON = False

# ---------------------------------------------------------------------------
# Optional symbol_extractor import (may not exist yet)
# ---------------------------------------------------------------------------
try:
    from symbol_extractor import extract_symbols
    HAS_SYMBOL_EXTRACTOR = True
except ImportError:
    HAS_SYMBOL_EXTRACTOR = False

# ---------------------------------------------------------------------------
# Credentials from environment
# ---------------------------------------------------------------------------
TELEGRAM_API_ID = os.getenv("TELEGRAM_API_ID", "")
TELEGRAM_API_HASH = os.getenv("TELEGRAM_API_HASH", "")
TELEGRAM_SESSION = os.getenv("TELEGRAM_SESSION", "")  # base64-encoded session

# ---------------------------------------------------------------------------
# Default channels (fallback when KOL registry has no Telegram entries)
# ---------------------------------------------------------------------------
DEFAULT_CHANNELS = [
    "WhaleTrades",
    "crypto_signals_free",
    "CryptoSignalsFree",
]

# ---------------------------------------------------------------------------
# Regex patterns for price/direction extraction
# ---------------------------------------------------------------------------
ENTRY_RE = re.compile(r'(?:entry|buy|short|long|target\s*1?)\s*[:@=]?\s*\$?([\d,]+\.?\d*)', re.I)
TP_RE = re.compile(r'(?:tp\d?|take\.?profit|target\d?)\s*[:@=]?\s*\$?([\d,]+\.?\d*)', re.I)
SL_RE = re.compile(r'(?:sl|stop\.?loss|stop|invalidation)\s*[:@=]?\s*\$?([\d,]+\.?\d*)', re.I)
DIRECTION_RE = re.compile(r'\b(long|short|bullish|bearish|buy|sell)\b', re.I)

# Fallback symbol regex when symbol_extractor is unavailable
SYMBOL_RE = re.compile(r'\$?(BTC|ETH|SOL|BNB|DOGE|LINK|AVAX|XRP|ADA|DOT|SUI|MATIC|OP|ARB|PEPE|WIF)\b', re.I)


def _get_channels() -> list[str]:
    """Build channel list from KOL registry, falling back to defaults."""
    channels: list[str] = []
    try:
        telegram_kols = get_kols_by_platform("telegram")
        for kol in telegram_kols:
            ch = kol.get("telegram_channel")
            if ch:
                channels.append(ch)
    except Exception as exc:
        print(f"[telegram] Warning: could not load KOL registry: {exc}")

    if not channels:
        print("[telegram] No channels from KOL registry, using defaults")
        channels = list(DEFAULT_CHANNELS)

    return channels


def _extract_symbols_from_text(text: str) -> list[dict]:
    """Extract symbols using symbol_extractor or fallback regex."""
    if HAS_SYMBOL_EXTRACTOR:
        try:
            return extract_symbols(text)
        except Exception:
            pass

    # Fallback: regex extraction
    matches = SYMBOL_RE.findall(text)
    if not matches:
        return []
    seen = set()
    results = []
    for m in matches:
        sym = m.upper() + "USDT"
        if sym not in seen:
            seen.add(sym)
            results.append({"symbol": sym, "raw": m})
    return results


def _parse_direction(text: str) -> str | None:
    """Extract trade direction from message text."""
    match = DIRECTION_RE.search(text)
    if not match:
        return None
    word = match.group(1).lower()
    if word in ("long", "bullish", "buy"):
        return "LONG"
    return "SHORT"


def _parse_price(pattern: re.Pattern, text: str) -> float | None:
    """Extract a price value from text using the given regex pattern."""
    match = pattern.search(text)
    if not match:
        return None
    try:
        return float(match.group(1).replace(",", ""))
    except (ValueError, IndexError):
        return None


async def scrape_telegram_channels() -> list[dict]:
    """Scrape Telegram channels for trading predictions.

    Returns list of prediction dicts in standard format.
    Gracefully returns empty list if telethon or credentials are missing.
    """
    # -----------------------------------------------------------------------
    # Pre-flight checks
    # -----------------------------------------------------------------------
    if not HAS_TELETHON:
        print("[telegram] telethon not installed - pip install telethon")
        return []

    if not TELEGRAM_API_ID or not TELEGRAM_API_HASH:
        print("[telegram] Missing TELEGRAM_API_ID or TELEGRAM_API_HASH env vars")
        return []

    if not TELEGRAM_SESSION:
        print("[telegram] Missing TELEGRAM_SESSION env var (base64-encoded session)")
        return []

    # -----------------------------------------------------------------------
    # Decode session and build client
    # -----------------------------------------------------------------------
    try:
        session_str = base64.b64decode(TELEGRAM_SESSION).decode("utf-8")
    except Exception as exc:
        print(f"[telegram] Failed to decode TELEGRAM_SESSION: {exc}")
        return []

    try:
        api_id = int(TELEGRAM_API_ID)
    except ValueError:
        print(f"[telegram] TELEGRAM_API_ID must be an integer, got: {TELEGRAM_API_ID!r}")
        return []

    client = TelegramClient(StringSession(session_str), api_id, TELEGRAM_API_HASH)

    # -----------------------------------------------------------------------
    # Connect and scrape
    # -----------------------------------------------------------------------
    predictions: list[dict] = []
    channels = _get_channels()
    cutoff = datetime.now(timezone.utc) - timedelta(hours=2)

    try:
        await client.connect()
        if not await client.is_user_authorized():
            print("[telegram] Session is not authorized - re-authenticate")
            return []

        print(f"[telegram] Connected. Scanning {len(channels)} channels...")

        for channel_name in channels:
            try:
                print(f"  Scanning @{channel_name}...")
                msg_count = 0
                async for msg in client.iter_messages(channel_name, limit=50):
                    # Skip old messages
                    if msg.date and msg.date.replace(tzinfo=timezone.utc) < cutoff:
                        break

                    if not msg.text:
                        continue

                    msg_count += 1
                    text = msg.text

                    # Extract symbols
                    symbol_infos = _extract_symbols_from_text(text)
                    if not symbol_infos:
                        continue

                    # Extract direction
                    direction = _parse_direction(text)
                    if not direction:
                        continue

                    # Extract price levels
                    entry = _parse_price(ENTRY_RE, text)
                    tp = _parse_price(TP_RE, text)
                    sl = _parse_price(SL_RE, text)

                    # Build prediction for each symbol found
                    for symbol_info in symbol_infos:
                        predictions.append({
                            "predictor_id": f"telegram:{channel_name}",
                            "platform": "telegram",
                            "display_name": channel_name,
                            "symbol": symbol_info["symbol"],
                            "direction": direction,
                            "entry_price": entry,
                            "take_profit": tp,
                            "stop_loss": sl,
                            "sentiment_score": 0.6,  # default for KOL signals
                            "source_url": f"https://t.me/{channel_name}/{msg.id}",
                            "source_text": text[:500],
                            "scraped_at": datetime.now(timezone.utc).isoformat(),
                            "is_known_analyst": 1,
                            "analyst_category": "telegram_kol",
                        })

                print(f"    Messages checked: {msg_count}")

            except Exception as exc:
                print(f"    Error scanning @{channel_name}: {exc}")
                continue

    except Exception as exc:
        print(f"[telegram] Connection error: {exc}")
    finally:
        try:
            await client.disconnect()
        except Exception:
            pass

    print(f"[telegram] Total predictions extracted: {len(predictions)}")
    return predictions


def main() -> None:
    """Entry point: scrape channels, insert predictions, log results."""
    print("=" * 60)
    print("Telegram KOL Scraper")
    print("=" * 60)

    predictions = asyncio.run(scrape_telegram_channels())

    if not predictions:
        print("[telegram] No predictions found (or missing credentials)")
        # Still log the scrape attempt
        try:
            conn = get_db()
            conn.execute("""
                INSERT INTO scrape_log (platform, scraped_at, posts_found, predictions_extracted, errors)
                VALUES ('telegram', ?, 0, 0, ?)
            """, (
                datetime.now(timezone.utc).isoformat(),
                "no_credentials" if not (TELEGRAM_API_ID and TELEGRAM_API_HASH and TELEGRAM_SESSION) else None,
            ))
            conn.commit()
            conn.close()
        except Exception as exc:
            print(f"[telegram] Could not log to scrape_log: {exc}")
        return

    # Insert predictions into DB
    inserted = 0
    errors: list[str] = []
    try:
        conn = get_db()
        for pred in predictions:
            try:
                insert_prediction(conn, pred)
                inserted += 1
                print(f"  + {pred['symbol']} {pred['direction']} via @{pred['display_name']}")
            except Exception as exc:
                err_msg = f"{pred['symbol']}: {exc}"
                errors.append(err_msg)
                print(f"  DB error: {err_msg}")

        # Log scrape summary
        channels = _get_channels()
        conn.execute("""
            INSERT INTO scrape_log (platform, scraped_at, posts_found, predictions_extracted, errors)
            VALUES ('telegram', ?, ?, ?, ?)
        """, (
            datetime.now(timezone.utc).isoformat(),
            len(predictions),
            inserted,
            "; ".join(errors) if errors else None,
        ))
        conn.commit()
        conn.close()
    except Exception as exc:
        print(f"[telegram] DB connection error: {exc}")

    print(f"\n{'=' * 60}")
    print(f"Telegram scrape complete: {inserted}/{len(predictions)} predictions inserted")
    print(f"Channels scanned: {len(_get_channels())}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
