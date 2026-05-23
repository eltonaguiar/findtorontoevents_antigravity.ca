"""
Failover Notification System
============================
Multi-channel notification system with automatic failover.
Ensures critical alerts always get delivered even if primary channels fail.

Channels (in priority order):
  1. Discord Webhooks (Primary)
  2. Discord Bot API (Fallback 1)
  3. Email SMTP (Fallback 2)
  4. File/Log Persistence (Fallback 3 - always works)
  5. External Services (PagerDuty, Slack, etc.)

Usage:
    from shared.failover_notifications import notify, notify_critical
    
    notify("Trade executed", {"symbol": "BTCUSDT", "pnl": 5.2})
    notify_critical("System failure", {"error": "Database connection lost"})
"""

import os
import json
import time
import logging
import smtplib
import urllib.request
import urllib.error
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
import threading

logger = logging.getLogger("FailoverNotifications")

# ============================================================================
# CONFIGURATION
# ============================================================================

# Load from environment or config file
# Uses existing Discord webhooks from the codebase:
# - DISCORD_WEBHOOK_URL (main)
# - DISCORD_WEBHOOK_PAPERTRADE (paper trading - has default fallback)
# - DISCORD_WEBHOOK_DNA_MASTER (DNA master picks)
# - DISCORD_WEBHOOK_SANDBOX (sandbox/testing)
# - DISCORD_WEBHOOK_PORTFOLIO (portfolio updates)
# - DISCORD_WEBHOOK_FRESHPICKS (fresh picks)
CONFIG = {
    # Discord - Primary webhooks (using existing system webhooks)
    "discord_webhook_url": os.getenv(
        "DISCORD_WEBHOOK_URL",
        os.getenv(
            "DISCORD_WEBHOOK_PAPERTRADE",
            "https://discord.com/api/webhooks/1478588243459965008/9TZAjAtrgz5dTvWpV3TP7FO8Fo5JRDCz03PkPiTaSlef0EcIEdHEDUmz8Zi13sZrqgA3"
        )
    ),
    "discord_webhook_alerts": os.getenv("DISCORD_WEBHOOK_URL", ""),
    "discord_webhook_portfolio": os.getenv("DISCORD_WEBHOOK_PORTFOLIO", ""),
    "discord_webhook_dna": os.getenv("DISCORD_WEBHOOK_DNA_MASTER", ""),
    "discord_bot_token": os.getenv("DISCORD_BOT_TOKEN", ""),
    "discord_channel_id": os.getenv("DISCORD_ML_CHANNEL_ID", os.getenv("DISCORD_CHANNEL_ID", "")),
    
    # Email - Uses same SMTP config as FINDTORONTOEVENTS.CA Database Backups
    # Server: mail.50webs.com (from .github/workflows/db-backup-email.yml)
    "smtp_host": os.getenv("SMTP_HOST", "mail.50webs.com"),
    "smtp_port": int(os.getenv("SMTP_PORT", "465")),  # SSL port
    "smtp_secure": os.getenv("SMTP_SECURE", "true").lower() == "true",  # Use SSL
    "smtp_user": os.getenv("SMTP_USER", "support@findtorontoevents.ca"),
    "smtp_pass": os.getenv("SMTP_PASS", os.getenv("EMAIL_SMTP_PASS", "")),  # Same secret as backup workflow
    "alert_email_to": os.getenv("ALERT_EMAIL_TO", "zerounderscore@gmail.com,eaguiar2015@yahoo.ca").split(",") if os.getenv("ALERT_EMAIL_TO") else ["zerounderscore@gmail.com", "eaguiar2015@yahoo.ca"],
    
    # External Services
    "pagerduty_key": os.getenv("PAGERDUTY_INTEGRATION_KEY", ""),
    "slack_webhook": os.getenv("SLACK_WEBHOOK_URL", ""),
    
    # File fallback
    "fallback_log_dir": os.path.join(os.path.dirname(__file__), "..", "logs", "notifications"),
    
    # Behavior
    "max_retries": 3,
    "retry_delay": 1.0,
    "batch_window_seconds": 5,  # Batch non-critical notifications
    "rate_limit_per_minute": 30,
}

# Ensure log directory exists
os.makedirs(CONFIG["fallback_log_dir"], exist_ok=True)

# Notification levels
class Level:
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

LEVEL_EMOJI = {
    Level.DEBUG: "🔍",
    Level.INFO: "ℹ️",
    Level.WARNING: "⚠️",
    Level.ERROR: "❌",
    Level.CRITICAL: "🚨",
}

LEVEL_PRIORITY = {
    Level.DEBUG: 1,
    Level.INFO: 2,
    Level.WARNING: 3,
    Level.ERROR: 4,
    Level.CRITICAL: 5,
}

# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class NotificationResult:
    """Result of a notification attempt."""
    success: bool
    channel: str
    message_id: str = None
    error: str = None
    timestamp: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow().isoformat()


@dataclass
class QueuedNotification:
    """A notification in the queue."""
    level: str
    title: str
    data: dict
    timestamp: datetime
    id: str = None
    
    def __post_init__(self):
        if self.id is None:
            self.id = f"{int(time.time() * 1000)}_{hash(self.title) % 10000}"


# ============================================================================
# RATE LIMITER
# ============================================================================

class RateLimiter:
    """Simple token bucket rate limiter."""
    
    def __init__(self, max_per_minute: int):
        self.max_per_minute = max_per_minute
        self.tokens = max_per_minute
        self.last_update = time.time()
        self._lock = threading.Lock()
    
    def acquire(self) -> bool:
        """Try to acquire a token. Returns True if allowed."""
        with self._lock:
            now = time.time()
            elapsed = now - self.last_update
            # Add tokens based on elapsed time
            self.tokens = min(self.max_per_minute, 
                            self.tokens + elapsed * (self.max_per_minute / 60))
            self.last_update = now
            
            if self.tokens >= 1:
                self.tokens -= 1
                return True
            return False
    
    def wait_time(self) -> float:
        """Get time to wait before next token is available."""
        with self._lock:
            if self.tokens >= 1:
                return 0
            return (1 - self.tokens) * (60 / self.max_per_minute)


# ============================================================================
# CHANNEL IMPLEMENTATIONS
# ============================================================================

class NotificationChannel:
    """Base class for notification channels."""
    
    def __init__(self, name: str):
        self.name = name
        self.healthy = True
        self.last_error = None
        self.success_count = 0
        self.failure_count = 0
    
    def send(self, level: str, title: str, data: dict) -> NotificationResult:
        raise NotImplementedError
    
    def is_available(self) -> bool:
        return self.healthy
    
    def record_success(self):
        self.healthy = True
        self.success_count += 1
        self.last_error = None
    
    def record_failure(self, error: str):
        self.failure_count += 1
        self.last_error = error
        # Mark unhealthy after 3 consecutive failures
        if self.failure_count >= 3:
            self.healthy = False


class DiscordWebhookChannel(NotificationChannel):
    """Discord webhook notification channel."""
    
    def __init__(self, webhook_url: str = None, name: str = "discord_webhook"):
        super().__init__(name)
        self.webhook_url = webhook_url or CONFIG["discord_webhook_url"]
        self.available = bool(self.webhook_url)
    
    def is_available(self) -> bool:
        return self.available and self.healthy
    
    def send(self, level: str, title: str, data: dict) -> NotificationResult:
        if not self.is_available():
            return NotificationResult(False, self.name, error="Not available")
        
        try:
            color = {
                Level.DEBUG: 0x808080,
                Level.INFO: 0x3498db,
                Level.WARNING: 0xf39c12,
                Level.ERROR: 0xe74c3c,
                Level.CRITICAL: 0x9b59b6,
            }.get(level, 0x808080)
            
            embed = {
                "title": f"{LEVEL_EMOJI.get(level, '')} {title}",
                "color": color,
                "timestamp": datetime.utcnow().isoformat(),
                "fields": [
                    {"name": k.replace("_", " ").title(), "value": str(v)[:1000], "inline": True}
                    for k, v in data.items()
                ],
            }
            
            payload = {"embeds": [embed]}
            
            req = urllib.request.Request(
                self.webhook_url,
                data=json.dumps(payload).encode(),
                headers={"Content-Type": "application/json", "User-Agent": "QuanEngine/1.0"},
                method="POST"
            )
            
            with urllib.request.urlopen(req, timeout=10) as resp:
                resp.read()
            
            self.record_success()
            return NotificationResult(True, self.name)
            
        except Exception as e:
            self.record_failure(str(e))
            return NotificationResult(False, self.name, error=str(e))


class DiscordBotChannel(NotificationChannel):
    """Discord bot API notification channel (fallback)."""
    
    def __init__(self):
        super().__init__("discord_bot")
        self.token = CONFIG["discord_bot_token"]
        self.channel_id = CONFIG["discord_channel_id"]
        self.available = bool(self.token and self.channel_id)
    
    def is_available(self) -> bool:
        return self.available and self.healthy
    
    def send(self, level: str, title: str, data: dict) -> NotificationResult:
        if not self.is_available():
            return NotificationResult(False, self.name, error="Not available")
        
        try:
            content = f"{LEVEL_EMOJI.get(level, '')} **{title}**\n"
            content += "\n".join([f"`{k}`: {v}" for k, v in data.items()])
            
            payload = {"content": content[:2000]}  # Discord limit
            
            url = f"https://discord.com/api/v10/channels/{self.channel_id}/messages"
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode(),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bot {self.token}",
                    "User-Agent": "QuanEngine/1.0"
                },
                method="POST"
            )
            
            with urllib.request.urlopen(req, timeout=10) as resp:
                response_data = json.loads(resp.read().decode())
            
            self.record_success()
            return NotificationResult(True, self.name, message_id=response_data.get("id"))
            
        except Exception as e:
            self.record_failure(str(e))
            return NotificationResult(False, self.name, error=str(e))


class EmailChannel(NotificationChannel):
    """Email notification channel using FINDTORONTOEVENTS.CA SMTP config."""
    
    def __init__(self):
        super().__init__("email")
        self.host = CONFIG["smtp_host"]
        self.port = CONFIG["smtp_port"]
        self.use_ssl = CONFIG.get("smtp_secure", True)  # SSL for port 465
        self.user = CONFIG["smtp_user"]
        self.password = CONFIG["smtp_pass"]
        self.to_emails = CONFIG["alert_email_to"]
        self.available = bool(self.user and self.password and self.to_emails)
    
    def is_available(self) -> bool:
        return self.available and self.healthy
    
    def send(self, level: str, title: str, data: dict) -> NotificationResult:
        if not self.is_available():
            return NotificationResult(False, self.name, error="Not available")
        
        try:
            msg = MIMEMultipart()
            msg["From"] = self.user
            msg["To"] = ", ".join(self.to_emails)
            msg["Subject"] = f"[{level.upper()}] {title}"
            
            body = f"Notification Level: {level}\n"
            body += f"Time: {datetime.utcnow().isoformat()}\n\n"
            body += "Data:\n"
            body += json.dumps(data, indent=2)
            
            msg.attach(MIMEText(body, "plain"))
            
            if self.use_ssl:
                # SSL connection (port 465)
                with smtplib.SMTP_SSL(self.host, self.port) as server:
                    server.login(self.user, self.password)
                    server.send_message(msg)
            else:
                # STARTTLS connection (port 587)
                with smtplib.SMTP(self.host, self.port) as server:
                    server.starttls()
                    server.login(self.user, self.password)
                    server.send_message(msg)
            
            self.record_success()
            return NotificationResult(True, self.name)
            
        except Exception as e:
            self.record_failure(str(e))
            return NotificationResult(False, self.name, error=str(e))


class FileFallbackChannel(NotificationChannel):
    """File-based fallback that always works."""
    
    def __init__(self):
        super().__init__("file_fallback")
        self.log_dir = CONFIG["fallback_log_dir"]
        os.makedirs(self.log_dir, exist_ok=True)
        self.available = True  # Always available
    
    def is_available(self) -> bool:
        return True
    
    def send(self, level: str, title: str, data: dict) -> NotificationResult:
        try:
            entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "level": level,
                "title": title,
                "data": data,
            }
            
            # Write to daily log file
            date_str = datetime.utcnow().strftime("%Y-%m-%d")
            log_file = os.path.join(self.log_dir, f"notifications_{date_str}.jsonl")
            
            with open(log_file, "a") as f:
                f.write(json.dumps(entry) + "\n")
            
            self.record_success()
            return NotificationResult(True, self.name)
            
        except Exception as e:
            self.record_failure(str(e))
            return NotificationResult(False, self.name, error=str(e))


class SlackWebhookChannel(NotificationChannel):
    """Slack webhook notification channel."""
    
    def __init__(self):
        super().__init__("slack_webhook")
        self.webhook_url = CONFIG["slack_webhook"]
        self.available = bool(self.webhook_url)
    
    def is_available(self) -> bool:
        return self.available and self.healthy
    
    def send(self, level: str, title: str, data: dict) -> NotificationResult:
        if not self.is_available():
            return NotificationResult(False, self.name, error="Not available")
        
        try:
            color = {
                Level.DEBUG: "#808080",
                Level.INFO: "#3498db",
                Level.WARNING: "#f39c12",
                Level.ERROR: "#e74c3c",
                Level.CRITICAL: "#9b59b6",
            }.get(level, "#808080")
            
            payload = {
                "attachments": [{
                    "color": color,
                    "title": f"{LEVEL_EMOJI.get(level, '')} {title}",
                    "fields": [
                        {"title": k.replace("_", " ").title(), "value": str(v)[:1000], "short": True}
                        for k, v in data.items()
                    ],
                    "footer": "QuanEngine",
                    "ts": int(time.time()),
                }]
            }
            
            req = urllib.request.Request(
                self.webhook_url,
                data=json.dumps(payload).encode(),
                headers={"Content-Type": "application/json", "User-Agent": "QuanEngine/1.0"},
                method="POST"
            )
            
            with urllib.request.urlopen(req, timeout=10) as resp:
                resp.read()
            
            self.record_success()
            return NotificationResult(True, self.name)
            
        except Exception as e:
            self.record_failure(str(e))
            return NotificationResult(False, self.name, error=str(e))


# ============================================================================
# NOTIFICATION MANAGER
# ============================================================================

class NotificationManager:
    """Manages all notification channels with automatic failover."""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        
        # Initialize channels in priority order
        # Uses existing Discord webhooks from the project
        self.channels: List[NotificationChannel] = [
            # Primary Discord webhook (DISCORD_WEBHOOK_URL or DISCORD_WEBHOOK_PAPERTRADE)
            DiscordWebhookChannel(
                webhook_url=CONFIG["discord_webhook_url"],
                name="discord_primary"
            ),
            # Portfolio webhook if different from primary
            DiscordWebhookChannel(
                webhook_url=CONFIG["discord_webhook_portfolio"] or CONFIG["discord_webhook_url"],
                name="discord_portfolio"
            ),
            # DNA Master webhook
            DiscordWebhookChannel(
                webhook_url=CONFIG["discord_webhook_dna"] or CONFIG["discord_webhook_url"],
                name="discord_dna"
            ),
            DiscordBotChannel(),
            EmailChannel(),
            SlackWebhookChannel(),
            FileFallbackChannel(),  # Always last - guaranteed to work
        ]
        
        self.rate_limiter = RateLimiter(CONFIG["rate_limit_per_minute"])
        
        # Batching for non-critical notifications
        self._batch_queue: List[QueuedNotification] = []
        self._batch_timer = None
        self._batch_lock = threading.Lock()
    
    def _get_available_channels(self, min_priority: int = 1) -> List[NotificationChannel]:
        """Get channels that are currently available."""
        return [c for c in self.channels if c.is_available()]
    
    def send(self, level: str, title: str, data: dict = None, 
             batch: bool = False, require_ack: bool = False) -> List[NotificationResult]:
        """
        Send notification through available channels.
        
        Args:
            level: Notification level (debug, info, warning, error, critical)
            title: Notification title
            data: Additional data dict
            batch: If True, batch with other non-critical notifications
            require_ack: If True, keep trying until at least one channel succeeds
        
        Returns:
            List of results from each channel
        """
        if data is None:
            data = {}
        
        # Handle batching for non-critical notifications
        if batch and LEVEL_PRIORITY.get(level, 3) < LEVEL_PRIORITY[Level.ERROR]:
            return self._queue_for_batch(level, title, data)
        
        return self._send_immediate(level, title, data, require_ack)
    
    def _queue_for_batch(self, level: str, title: str, data: dict) -> List[NotificationResult]:
        """Queue notification for batching."""
        with self._batch_lock:
            notification = QueuedNotification(level, title, data, datetime.utcnow())
            self._batch_queue.append(notification)
            
            # Start batch timer if not running
            if self._batch_timer is None:
                self._batch_timer = threading.Timer(
                    CONFIG["batch_window_seconds"], 
                    self._flush_batch
                )
                self._batch_timer.start()
            
            return [NotificationResult(True, "batched", message_id=notification.id)]
    
    def _flush_batch(self):
        """Send all queued notifications as a batch."""
        with self._batch_lock:
            notifications = self._batch_queue[:]
            self._batch_queue.clear()
            self._batch_timer = None
        
        if not notifications:
            return
        
        # Group by level
        by_level = {}
        for n in notifications:
            by_level.setdefault(n.level, []).append(n)
        
        # Send batched summary
        for level, items in by_level.items():
            title = f"Batched Notifications ({len(items)} items)"
            data = {
                "notifications": [
                    {"title": n.title, "time": n.timestamp.isoformat()}
                    for n in items[:10]  # Limit to first 10
                ]
            }
            if len(items) > 10:
                data["truncated"] = f"... and {len(items) - 10} more"
            
            self._send_immediate(level, title, data, require_ack=False)
    
    def _send_immediate(self, level: str, title: str, data: dict, 
                        require_ack: bool) -> List[NotificationResult]:
        """Send notification immediately through all available channels."""
        results = []
        channels = self._get_available_channels()
        
        # Rate limiting
        if not self.rate_limiter.acquire():
            wait_time = self.rate_limiter.wait_time()
            logger.warning(f"Rate limit hit, waiting {wait_time:.1f}s")
            time.sleep(wait_time)
        
        for channel in channels:
            try:
                result = channel.send(level, title, data)
                results.append(result)
                
                if result.success and not require_ack:
                    # If we don't require ack and got success, stop
                    break
                    
            except Exception as e:
                logger.error(f"Channel {channel.name} failed: {e}")
                results.append(NotificationResult(False, channel.name, error=str(e)))
        
        # If require_ack and all failed, retry after delay
        if require_ack and not any(r.success for r in results):
            logger.error(f"All channels failed for critical notification, will retry")
            time.sleep(CONFIG["retry_delay"])
            return self._send_immediate(level, title, data, require_ack)
        
        return results
    
    def get_health(self) -> dict:
        """Get health status of all channels."""
        return {
            c.name: {
                "available": c.is_available(),
                "healthy": c.healthy,
                "success_count": c.success_count,
                "failure_count": c.failure_count,
                "last_error": c.last_error,
            }
            for c in self.channels
        }


# ============================================================================
# PUBLIC API
# ============================================================================

def notify(title: str, data: dict = None, level: str = Level.INFO, 
           batch: bool = False) -> List[NotificationResult]:
    """
    Send a notification through available channels.
    
    Args:
        title: Notification title
        data: Additional data to include
        level: Notification level
        batch: Whether to batch with other notifications
    
    Returns:
        List of results from each channel
    """
    manager = NotificationManager()
    return manager.send(level, title, data, batch=batch)


def notify_critical(title: str, data: dict = None) -> List[NotificationResult]:
    """Send a critical notification (guaranteed delivery)."""
    manager = NotificationManager()
    return manager.send(Level.CRITICAL, title, data, batch=False, require_ack=True)


def notify_error(title: str, data: dict = None) -> List[NotificationResult]:
    """Send an error notification."""
    manager = NotificationManager()
    return manager.send(Level.ERROR, title, data, batch=False)


def notify_warning(title: str, data: dict = None, batch: bool = True) -> List[NotificationResult]:
    """Send a warning notification."""
    manager = NotificationManager()
    return manager.send(Level.WARNING, title, data, batch=batch)


def notify_info(title: str, data: dict = None, batch: bool = True) -> List[NotificationResult]:
    """Send an info notification."""
    manager = NotificationManager()
    return manager.send(Level.INFO, title, data, batch=batch)


def get_notification_health() -> dict:
    """Get health status of all notification channels."""
    manager = NotificationManager()
    return manager.get_health()


# ============================================================================
# TESTING
# ============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("Testing Failover Notification System...")
    print("=" * 60)
    
    # Test different notification levels
    print("\n1. Testing notify_info (batched)...")
    for i in range(3):
        results = notify_info(f"Test info {i}", {"index": i, "test": True}, batch=True)
        print(f"   Info {i}: {results[0].channel} - Success: {results[0].success}")
    
    # Force flush
    time.sleep(CONFIG["batch_window_seconds"] + 1)
    
    print("\n2. Testing notify_error...")
    results = notify_error("Test error", {"error_code": 500, "details": "Something went wrong"})
    for r in results:
        print(f"   {r.channel}: Success={r.success}, Error={r.error}")
    
    print("\n3. Testing notify_critical...")
    results = notify_critical("CRITICAL: System down", {"component": "database", "reason": "connection timeout"})
    for r in results:
        print(f"   {r.channel}: Success={r.success}")
    
    print("\n4. Health Status...")
    health = get_notification_health()
    print(json.dumps(health, indent=2))
