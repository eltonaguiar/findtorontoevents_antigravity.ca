"""A permanently-rejected Discord webhook must fail loudly, not be swallowed.

Regression guard for 2026-10-03: a deleted webhook returned HTTP 404
({"message": "Unknown Webhook"}) and the code only logged a warning, so every
notification was silently dropped while the workflow stayed green.
"""
import pathlib
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import coinglass_strategies.discord_notify as dn  # noqa: E402


def _resp(status: int, text: str = "") -> MagicMock:
    r = MagicMock()
    r.status_code = status
    r.text = text
    r.json.return_value = {"retry_after": 0}
    return r


@patch.object(dn, "WEBHOOK_URL", "https://discord.com/api/webhooks/1/dead")
@patch.object(dn.requests, "post")
def test_dead_webhook_raises(mock_post):
    mock_post.return_value = _resp(404, '{"message": "Unknown Webhook", "code": 10015}')
    with pytest.raises(dn.DiscordWebhookError):
        dn._post([{"title": "x"}])
    # Permanent 4xx must not be retried three times.
    assert mock_post.call_count == 1


@patch.object(dn, "WEBHOOK_URL", "https://discord.com/api/webhooks/1/ok")
@patch.object(dn.requests, "post")
def test_unauthorized_raises(mock_post):
    mock_post.return_value = _resp(401, "unauthorized")
    with pytest.raises(dn.DiscordWebhookError):
        dn._post([{"title": "x"}])


@patch.object(dn, "WEBHOOK_URL", "https://discord.com/api/webhooks/1/ok")
@patch.object(dn.requests, "post")
def test_success_does_not_raise(mock_post):
    mock_post.return_value = _resp(204)
    dn._post([{"title": "x"}])  # must not raise
    assert mock_post.call_count == 1


@patch.object(dn, "WEBHOOK_URL", "")
@patch.object(dn.requests, "post")
def test_no_webhook_skips(mock_post):
    dn._post([{"title": "x"}])  # warns and returns; no HTTP call
    mock_post.assert_not_called()
