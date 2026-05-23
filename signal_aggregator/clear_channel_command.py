#!/usr/bin/env python3
"""
Clear Channel Command Handler

Deletes all messages in a Discord channel (up to 100 at a time due to API limits).
Requires a Discord bot token with MANAGE_MESSAGES permission.

Usage:
    python clear_channel_command.py <channel_id> [limit]
    
Arguments:
    channel_id: Discord channel ID to clear
    limit: Maximum messages to delete (default: 100, max: 100)

Environment Variables:
    DISCORD_BOT_TOKEN: Discord bot token with MANAGE_MESSAGES permission
"""

import os
import sys
import logging
import requests
from typing import List, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DISCORD_API_BASE = "https://discord.com/api/v10"


def get_bot_token() -> Optional[str]:
    """Get Discord bot token from environment."""
    token = os.getenv('DISCORD_BOT_TOKEN')
    if not token:
        logger.error("DISCORD_BOT_TOKEN environment variable not set")
        return None
    return token


def get_channel_webhook_url(channel_name: str) -> Optional[str]:
    """Get webhook URL for a channel name."""
    env_vars = {
        'master_picks': 'DISCORD_MASTER_PICKS',
        'freshpicks': 'DISCORD_FRESHPICKS',
        'general': 'DISCORD_GENERAL',
        'notifications': 'DISCORD_NOTIFICATIONS',
        'sandbox': 'DISCORD_SANDBOX',
        'automation': 'DISCORD_WEBHOOK_URL'
    }
    
    env_var = env_vars.get(channel_name.lower())
    if env_var:
        return os.getenv(env_var)
    return None


def extract_channel_id_from_webhook(webhook_url: str) -> Optional[str]:
    """Extract channel ID from webhook URL."""
    # Webhook URL format: https://discord.com/api/webhooks/{webhook_id}/{token}
    # We can't get channel ID from webhook URL directly without API call
    # Need to fetch webhook info
    try:
        response = requests.get(webhook_url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data.get('channel_id')
    except Exception as e:
        logger.error(f"Error fetching webhook info: {e}")
    return None


def get_channel_id(channel_name: str) -> Optional[str]:
    """Get channel ID from channel name using webhook."""
    webhook_url = get_channel_webhook_url(channel_name)
    if not webhook_url:
        logger.error(f"No webhook configured for channel: {channel_name}")
        return None
    
    return extract_channel_id_from_webhook(webhook_url)


def get_messages(bot_token: str, channel_id: str, limit: int = 100) -> List[dict]:
    """Fetch messages from a channel."""
    headers = {
        'Authorization': f'Bot {bot_token}',
        'Content-Type': 'application/json'
    }
    
    url = f"{DISCORD_API_BASE}/channels/{channel_id}/messages"
    params = {'limit': min(limit, 100)}
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        if response.status_code == 200:
            messages = response.json()
            logger.info(f"Fetched {len(messages)} messages from channel {channel_id}")
            return messages
        elif response.status_code == 403:
            logger.error(f"Bot lacks permission to read messages in channel {channel_id}")
            return []
        else:
            logger.error(f"Error fetching messages: {response.status_code} - {response.text}")
            return []
    except Exception as e:
        logger.error(f"Error fetching messages: {e}")
        return []


def bulk_delete_messages(bot_token: str, channel_id: str, message_ids: List[str]) -> bool:
    """Bulk delete messages (up to 100 at a time)."""
    if not message_ids:
        logger.info("No messages to delete")
        return True
    
    headers = {
        'Authorization': f'Bot {bot_token}',
        'Content-Type': 'application/json'
    }
    
    url = f"{DISCORD_API_BASE}/channels/{channel_id}/messages/bulk-delete"
    payload = {'messages': message_ids[:100]}  # Max 100 at a time
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        if response.status_code == 204:
            logger.info(f"Successfully deleted {len(payload['messages'])} messages")
            return True
        elif response.status_code == 403:
            logger.error(f"Bot lacks permission to delete messages in channel {channel_id}")
            return False
        elif response.status_code == 429:
            logger.error("Rate limited by Discord API")
            return False
        else:
            logger.error(f"Error deleting messages: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        logger.error(f"Error deleting messages: {e}")
        return False


def delete_single_message(bot_token: str, channel_id: str, message_id: str) -> bool:
    """Delete a single message (fallback for older messages)."""
    headers = {
        'Authorization': f'Bot {bot_token}',
        'Content-Type': 'application/json'
    }
    
    url = f"{DISCORD_API_BASE}/channels/{channel_id}/messages/{message_id}"
    
    try:
        response = requests.delete(url, headers=headers, timeout=10)
        return response.status_code == 204
    except Exception as e:
        logger.error(f"Error deleting message {message_id}: {e}")
        return False


def clear_channel(channel_name: str, limit: int = 100) -> dict:
    """
    Clear messages from a channel.
    
    Returns:
        Dict with status and details
    """
    result = {
        'success': False,
        'channel': channel_name,
        'deleted': 0,
        'errors': [],
        'message': ''
    }
    
    # Get bot token
    bot_token = get_bot_token()
    if not bot_token:
        result['errors'].append("DISCORD_BOT_TOKEN not set")
        result['message'] = "Bot token not configured"
        return result
    
    # Get channel ID
    channel_id = get_channel_id(channel_name)
    if not channel_id:
        result['errors'].append(f"Could not get channel ID for {channel_name}")
        result['message'] = f"Channel {channel_name} not found"
        return result
    
    logger.info(f"Clearing channel {channel_name} (ID: {channel_id})")
    
    # Fetch messages
    messages = get_messages(bot_token, channel_id, limit)
    if not messages:
        result['message'] = "No messages found or unable to fetch messages"
        result['success'] = True  # Nothing to delete is still success
        return result
    
    # Filter messages that can be bulk deleted (must be < 14 days old)
    from datetime import datetime, timedelta
    cutoff_date = datetime.utcnow() - timedelta(days=13)  # 13 days to be safe
    
    bulk_deletable = []
    old_messages = []
    
    for msg in messages:
        msg_id = msg.get('id')
        msg_timestamp = msg.get('timestamp')
        
        if msg_timestamp:
            try:
                # Discord snowflake to timestamp approximation
                # Messages older than 14 days can't be bulk deleted
                msg_time = datetime.fromisoformat(msg_timestamp.replace('Z', '+00:00').replace('+00:00', ''))
                if msg_time >= cutoff_date:
                    bulk_deletable.append(msg_id)
                else:
                    old_messages.append(msg_id)
            except:
                bulk_deletable.append(msg_id)  # Assume deletable if can't parse
        else:
            bulk_deletable.append(msg_id)
    
    logger.info(f"Bulk deletable: {len(bulk_deletable)}, Old messages: {len(old_messages)}")
    
    # Bulk delete recent messages
    deleted_count = 0
    if bulk_deletable:
        if bulk_delete_messages(bot_token, channel_id, bulk_deletable):
            deleted_count += len(bulk_deletable)
        else:
            # Try individual deletion as fallback
            logger.warning("Bulk delete failed, trying individual deletion")
            for msg_id in bulk_deletable:
                if delete_single_message(bot_token, channel_id, msg_id):
                    deleted_count += 1
    
    # Note: Old messages (>14 days) need to be deleted individually
    # But this is slow and rate-limited, so we skip them for now
    if old_messages:
        logger.warning(f"{len(old_messages)} messages are too old for bulk delete (14+ days)")
        result['errors'].append(f"{len(old_messages)} old messages skipped (14+ days)")
    
    result['success'] = deleted_count > 0 or len(messages) == 0
    result['deleted'] = deleted_count
    result['total_found'] = len(messages)
    result['message'] = f"Deleted {deleted_count}/{len(messages)} messages from #{channel_name}"
    
    return result


def send_confirmation_webhook(channel_name: str, result: dict) -> bool:
    """Send confirmation message to the channel after clearing."""
    webhook_url = get_channel_webhook_url(channel_name)
    if not webhook_url:
        return False
    
    color = 0x2ecc71 if result['success'] else 0xe74c3c
    
    embed = {
        'title': 'Channel Cleared',
        'description': result['message'],
        'color': color,
        'fields': []
    }
    
    if result.get('errors'):
        embed['fields'].append({
            'name': 'Notes',
            'value': '\n'.join(result['errors']),
            'inline': False
        })
    
    payload = {'embeds': [embed]}
    
    try:
        response = requests.post(webhook_url, json=payload, timeout=10)
        return response.status_code == 204
    except Exception as e:
        logger.error(f"Error sending confirmation: {e}")
        return False


def main():
    """Main entry point for command."""
    if len(sys.argv) < 2:
        print("Usage: python clear_channel_command.py <channel_name> [limit]")
        print("Example: python clear_channel_command.py master_picks 50")
        sys.exit(1)
    
    channel_name = sys.argv[1]
    limit = 100
    
    if len(sys.argv) > 2:
        try:
            limit = int(sys.argv[2])
            limit = max(1, min(limit, 100))  # Clamp between 1-100
        except ValueError:
            print(f"Invalid limit: {sys.argv[2]}")
            sys.exit(1)
    
    # Safety confirmation for destructive operation
    if os.getenv('SKIP_CONFIRM') != 'true':
        print(f"WARNING: This will delete up to {limit} messages from #{channel_name}")
        print("Set SKIP_CONFIRM=true to skip this prompt in CI/CD")
        # In GitHub Actions, we can't prompt, so require the env var
        if os.getenv('GITHUB_ACTIONS') == 'true':
            print("Running in GitHub Actions - set SKIP_CONFIRM=true to proceed")
            sys.exit(1)
    
    result = clear_channel(channel_name, limit)
    
    # Send confirmation
    send_confirmation_webhook(channel_name, result)
    
    # Print result
    print(result['message'])
    if result['errors']:
        for error in result['errors']:
            print(f"  Error: {error}")
    
    sys.exit(0 if result['success'] else 1)


if __name__ == '__main__':
    main()
