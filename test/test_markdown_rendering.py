#!/usr/bin/env python3
"""Test cases for markdown rendering and JavaScript setup."""

import json
import tempfile
from pathlib import Path
from claude_code_log.converter import (
    load_transcript,
    generate_html,
)


def test_markdown_script_inclusion():
    """Test that marked.js script is included in HTML output."""
    user_message = {
        "type": "user",
        "timestamp": "2025-06-11T22:44:17.436Z",
        "parentUuid": None,
        "isSidechain": False,
        "userType": "human",
        "cwd": "/tmp",
        "sessionId": "test_session",
        "version": "1.0.0",
        "uuid": "test_md_001",
        "message": {
            "role": "user",
            "content": [
                {"type": "text", "text": "# Test Markdown\n\nThis is **bold** text."}
            ],
        },
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        f.write(json.dumps(user_message) + "\n")
        f.flush()
        test_file_path = Path(f.name)

    try:
        messages = load_transcript(test_file_path)
        html = generate_html(messages, "Test Transcript")

        # Should include marked.js script
        assert "marked" in html, "Should include marked.js reference"
        assert "import { marked }" in html, "Should import marked module"
        assert "marked.parse" in html, "Should use marked.parse function"
        assert "DOMContentLoaded" in html, "Should wait for DOM to load"

        print("✓ Test passed: Markdown script is included in HTML")

    finally:
        test_file_path.unlink()


if __name__ == "__main__":
    test_markdown_script_inclusion()
    print("\n✅ All markdown rendering tests passed!")
