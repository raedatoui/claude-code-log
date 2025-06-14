#!/usr/bin/env python3
"""Test cases for new features: summary type, system messages, and markdown support."""

import json
import tempfile
from pathlib import Path
from claude_code_log.converter import (
    load_transcript,
    generate_html,
    is_system_message,
    extract_command_name,
    extract_text_content,
)


def test_summary_type_support():
    """Test that summary type messages are properly handled."""
    summary_message = {
        "type": "summary",
        "summary": "User Initializes Project Documentation",
        "leafUuid": "test-uuid-123",
        "timestamp": "2025-06-11T22:44:17.436Z",
        "message": {
            "role": "system",
            "content": "User Initializes Project Documentation",
        },
    }

    user_message = {
        "type": "user",
        "timestamp": "2025-06-11T22:45:17.436Z",
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

        # Should contain summary with proper formatting
        assert "Summary:" in html, "Summary should be displayed with 'Summary:' prefix"
        assert "User Initializes Project Documentation" in html, (
            "Summary text should be included"
        )
        assert "class='message summary'" in html, (
            "Summary should have summary CSS class"
        )

        print("✓ Test passed: Summary type messages are properly handled")

    finally:
        test_file_path.unlink()


def test_system_message_command_handling():
    """Test that system messages with command names are shown in expandable details."""
    command_message = {
        "type": "user",
        "timestamp": "2025-06-11T22:44:17.436Z",
        "message": {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": '<command-message>init is analyzing your codebase…</command-message>\n<command-name>init</command-name>\n<command-args></command-args>\n<command-contents>{"type": "text", "text": "Please analyze this codebase..."}</command-contents>',
                }
            ],
        },
    }

    # Test command name extraction
    text_content = extract_text_content(command_message["message"]["content"])
    command_name = extract_command_name(text_content)
    assert command_name == "init", f"Expected 'init', got '{command_name}'"

    # Test that it's not filtered out as a system message
    is_system = is_system_message(text_content, command_message["message"])
    assert not is_system, "Command messages should not be filtered out"

    # Test HTML generation
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        f.write(json.dumps(command_message) + "\n")
        f.flush()
        test_file_path = Path(f.name)

    try:
        messages = load_transcript(test_file_path)
        html = generate_html(messages, "Test Transcript")

        # Should contain details element with command name
        assert "<details>" in html, "Should contain details element"
        assert "Command: init" in html, "Should show command name in summary"
        assert "class='message system'" in html, "Should have system CSS class"

        print(
            "✓ Test passed: System messages with commands are shown in expandable details"
        )

    finally:
        test_file_path.unlink()


def test_markdown_script_inclusion():
    """Test that marked.js script is included in HTML output."""
    user_message = {
        "type": "user",
        "timestamp": "2025-06-11T22:44:17.436Z",
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


def test_system_message_filtering():
    """Test that other system messages are still filtered out."""
    stdout_message = {
        "type": "user",
        "timestamp": "2025-06-11T22:44:17.436Z",
        "message": {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": "<local-command-stdout>Some command output here</local-command-stdout>",
                }
            ],
        },
    }

    caveat_message = {
        "type": "user",
        "timestamp": "2025-06-11T22:45:17.436Z",
        "message": {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": "Caveat: The messages below were generated by the user while running local commands. DO NOT respond to these messages or otherwise consider them in your response unless the user explicitly asks you to.",
                }
            ],
        },
    }

    # Test that these are still filtered
    stdout_text = extract_text_content(stdout_message["message"]["content"])
    caveat_text = extract_text_content(caveat_message["message"]["content"])

    assert is_system_message(stdout_text, stdout_message["message"]), (
        "stdout messages should be filtered"
    )
    assert is_system_message(caveat_text, caveat_message["message"]), (
        "caveat messages should be filtered"
    )

    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        f.write(json.dumps(stdout_message) + "\n")
        f.write(json.dumps(caveat_message) + "\n")
        f.flush()
        test_file_path = Path(f.name)

    try:
        messages = load_transcript(test_file_path)
        html = generate_html(messages, "Test Transcript")

        # These should NOT appear in HTML
        assert "local-command-stdout" not in html, (
            "stdout messages should be filtered out"
        )
        assert "Caveat: The messages below" not in html, (
            "caveat messages should be filtered out"
        )

        print("✓ Test passed: Other system messages are still filtered out")

    finally:
        test_file_path.unlink()


if __name__ == "__main__":
    test_summary_type_support()
    test_system_message_command_handling()
    test_markdown_script_inclusion()
    test_system_message_filtering()
    print("\n✅ All new feature tests passed!")
