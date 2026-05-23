from unittest.mock import patch
from cross_aggregation.discord_notify import send_job_failure

@patch("cross_aggregation.discord_notify._post")
@patch("cross_aggregation.discord_notify.WEBHOOK_URL", "https://fake")
def test_send_job_failure_posts_embed(mock_post):
    send_job_failure(
        system_label="ML Crypto Engine",
        job_name="production_run",
        error_msg="ZeroDivisionError: division by zero"
    )
    mock_post.assert_called_once()
    embed = mock_post.call_args[0][0][0]
    assert "FAILURE" in embed["title"]
    assert "ZeroDivisionError" in embed["description"]

@patch("cross_aggregation.discord_notify._post")
@patch("cross_aggregation.discord_notify.WEBHOOK_URL", "")
def test_send_job_failure_skips_when_no_webhook(mock_post):
    send_job_failure("Test", "test_job", "error")
    mock_post.assert_not_called()

@patch("cross_aggregation.discord_notify._post")
@patch("cross_aggregation.discord_notify.WEBHOOK_URL", "https://fake")
def test_send_job_failure_truncates_long_message(mock_post):
    long_msg = "x" * 1000
    send_job_failure("Test", "test_job", long_msg)
    embed = mock_post.call_args[0][0][0]
    assert len(embed["description"]) < 600
