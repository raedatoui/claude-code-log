#!/usr/bin/env python3
"""Test cases for different message types: summary, user, assistant."""

import json
import tempfile
from pathlib import Path
from claude_code_log.converter import (
    load_transcript,
    generate_html,
)


def test_summary_type_support():
    """Test that summary type messages are properly handled."""
    summary_message = {
        "type": "summary",
        "summary": "User Initializes Project Documentation",
        "leafUuid": "test_msg_001",  # Should match a message UUID
    }

    user_message = {
        "type": "user",
        "timestamp": "2025-06-11T22:45:17.436Z",
        "parentUuid": None,
        "isSidechain": False,
        "userType": "human",
        "cwd": "/tmp",
        "sessionId": "test_session",
        "version": "1.0.0",
        "uuid": "test_msg_001",
        "message": {
            "role": "user",
            "content": [{"type": "text", "text": "Hello, this is a test message."}],
        },
    }

    # Test loading summary messages
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        f.write(json.dumps(summary_message) + "\n")
        f.write(json.dumps(user_message) + "\n")
        f.flush()
        test_file_path = Path(f.name)

    try:
        messages = load_transcript(test_file_path)
        assert len(messages) == 2, f"Expected 2 messages, got {len(messages)}"

        # Generate HTML
        html = generate_html(messages, "Test Transcript")

        # Summary should be attached to session header, not as separate message
        assert "User Initializes Project Documentation" in html, (
            "Summary text should be included"
        )
        assert "session-header" in html, (
            "Summary should appear in session header section"
        )

        print("✓ Test passed: Summary type messages are properly handled")

    finally:
        test_file_path.unlink()


if __name__ == "__main__":
    test_summary_type_support()
    print("\n✅ All message type tests passed!")
