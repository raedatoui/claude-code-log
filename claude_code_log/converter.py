#!/usr/bin/env python3
"""Convert Claude transcript JSONL files to HTML."""

import json
from pathlib import Path
from typing import List, Optional, Union
from datetime import datetime
import dateparser
import html
from .models import (
    TranscriptEntry,
    SummaryTranscriptEntry,
    parse_transcript_entry,
    ContentItem,
    TextContent,
    ToolResultContent,
)


def extract_text_content(content: Union[str, List[ContentItem]]) -> str:
    """Extract text content from Claude message content structure."""
    if isinstance(content, list):
        text_parts: List[str] = []
        for item in content:
            if isinstance(item, TextContent):
                text_parts.append(item.text)
        return "\n".join(text_parts)
    else:
        return str(content) if content else ""


def format_timestamp(timestamp_str: str) -> str:
    """Format ISO timestamp for display."""
    try:
        dt = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, AttributeError):
        return timestamp_str


def parse_timestamp(timestamp_str: str) -> Optional[datetime]:
    """Parse ISO timestamp to datetime object."""
    try:
        return datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def filter_messages_by_date(
    messages: List[TranscriptEntry], from_date: Optional[str], to_date: Optional[str]
) -> List[TranscriptEntry]:
    """Filter messages based on date range."""
    if not from_date and not to_date:
        return messages

    # Parse the date strings using dateparser
    from_dt = None
    to_dt = None

    if from_date:
        from_dt = dateparser.parse(from_date)
        if not from_dt:
            raise ValueError(f"Could not parse from-date: {from_date}")
        # If parsing relative dates like "today", start from beginning of day
        if from_date in ["today", "yesterday"] or "days ago" in from_date:
            from_dt = from_dt.replace(hour=0, minute=0, second=0, microsecond=0)

    if to_date:
        to_dt = dateparser.parse(to_date)
        if not to_dt:
            raise ValueError(f"Could not parse to-date: {to_date}")
        # If parsing relative dates like "today", end at end of day
        if to_date in ["today", "yesterday"] or "days ago" in to_date:
            to_dt = to_dt.replace(hour=23, minute=59, second=59, microsecond=999999)

    filtered_messages: List[TranscriptEntry] = []
    for message in messages:
        # Handle SummaryTranscriptEntry which doesn't have timestamp
        if isinstance(message, SummaryTranscriptEntry):
            filtered_messages.append(message)
            continue
            
        timestamp_str = message.timestamp
        if not timestamp_str:
            continue

        message_dt = parse_timestamp(timestamp_str)
        if not message_dt:
            continue

        # Convert to naive datetime for comparison (dateparser returns naive datetimes)
        if message_dt.tzinfo:
            message_dt = message_dt.replace(tzinfo=None)

        # Check if message falls within date range
        if from_dt and message_dt < from_dt:
            continue
        if to_dt and message_dt > to_dt:
            continue

        filtered_messages.append(message)

    return filtered_messages


def load_transcript(jsonl_path: Path) -> List[TranscriptEntry]:
    """Load and parse JSONL transcript file."""
    messages: List[TranscriptEntry] = []
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entry_dict = json.loads(line)
                    if entry_dict.get("type") in ["user", "assistant", "summary"]:
                        # Parse using Pydantic models
                        entry = parse_transcript_entry(entry_dict)
                        # Add source file info for session tracking
                        entry._source_file = jsonl_path.stem  # type: ignore
                        messages.append(entry)
                except (json.JSONDecodeError, ValueError):
                    # Skip lines that can't be parsed
                    continue
    return messages


def load_directory_transcripts(directory_path: Path) -> List[TranscriptEntry]:
    """Load all JSONL transcript files from a directory and combine them."""
    all_messages: List[TranscriptEntry] = []

    # Find all .jsonl files
    jsonl_files = list(directory_path.glob("*.jsonl"))

    for jsonl_file in jsonl_files:
        messages = load_transcript(jsonl_file)
        all_messages.extend(messages)

    # Sort all messages chronologically
    def get_timestamp(entry: TranscriptEntry) -> str:
        if hasattr(entry, 'timestamp'):
            return entry.timestamp  # type: ignore
        return ''
    
    all_messages.sort(key=get_timestamp)
    return all_messages


def escape_html(text: str) -> str:
    """Escape HTML special characters in text."""
    return html.escape(text)


def extract_command_info(text_content: str) -> tuple[str, str, str]:
    """Extract command info from system message with command tags."""
    import re

    # Extract command name
    command_name_match = re.search(
        r"<command-name>([^<]+)</command-name>", text_content
    )
    command_name = (
        command_name_match.group(1).strip() if command_name_match else "system"
    )

    # Extract command args
    command_args_match = re.search(
        r"<command-args>([^<]*)</command-args>", text_content
    )
    command_args = command_args_match.group(1).strip() if command_args_match else ""

    # Extract command contents
    command_contents_match = re.search(
        r"<command-contents>(.+?)</command-contents>", text_content, re.DOTALL
    )
    command_contents: str = ""
    if command_contents_match:
        contents_text = command_contents_match.group(1).strip()
        # Try to parse as JSON and extract the text field
        try:
            contents_json = json.loads(contents_text)
            if isinstance(contents_json, dict) and "text" in contents_json:
                text_value = contents_json["text"]  # type: ignore
                command_contents = text_value if isinstance(text_value, str) else str(text_value)  # type: ignore
            else:
                command_contents = contents_text
        except json.JSONDecodeError:
            command_contents = contents_text

    return command_name, command_args, command_contents


def is_system_message(text_content: str, message_content: Union[str, List[ContentItem]]) -> bool:
    """Check if a message is a system message that should be filtered out."""
    system_message_patterns = [
        "Caveat: The messages below were generated by the user while running local commands. DO NOT respond to these messages or otherwise consider them in your response unless the user explicitly asks you to.",
        "[Request interrupted by user for tool use]",
    ]

    # Check for tool result messages - these have tool_use_id and type="tool_result"
    if isinstance(message_content, list):
        for item in message_content:
            if isinstance(item, ToolResultContent):
                return True

    return any(pattern in text_content for pattern in system_message_patterns)


def generate_html(messages: List[TranscriptEntry], title: Optional[str] = None) -> str:
    """Generate HTML from transcript messages."""
    if not title:
        title = "Claude Transcript"

    html_parts = [
        "<!DOCTYPE html>",
        "<html lang='en'>",
        "<head>",
        "    <meta charset='UTF-8'>",
        "    <meta name='viewport' content='width=device-width, initial-scale=1.0'>",
        f"    <title>{title}</title>",
        '    <script type="module">',
        "      import { marked } from 'https://cdn.jsdelivr.net/npm/marked/lib/marked.esm.js';",
        "      ",
        "      // Configure marked options",
        "      marked.setOptions({",
        "        breaks: true,",
        "        gfm: true",
        "      });",
        "      ",
        "      document.addEventListener('DOMContentLoaded', function() {",
        "        // Find all content divs and render markdown",
        "        const contentDivs = document.querySelectorAll('.content');",
        "        contentDivs.forEach(div => {",
        "          // Skip if it's already HTML (contains tags)",
        "          if (div.innerHTML.includes('<') && div.innerHTML.includes('>')) {",
        "            return;",
        "          }",
        "          ",
        "          const markdownText = div.textContent;",
        "          if (markdownText.trim()) {",
        "            div.innerHTML = marked.parse(markdownText);",
        "          }",
        "        });",
        "      });",
        "    </script>",
        "    <style>",
        "        body {",
        "            font-family: 'SF Mono', 'Monaco', 'Inconsolata', 'Fira Code', 'Droid Sans Mono', 'Source Code Pro', 'Ubuntu Mono', 'Cascadia Code', 'Menlo', 'Consolas', monospace;",
        "            line-height: 1.5;",
        "            max-width: 1200px;",
        "            margin: 0 auto;",
        "            padding: 10px;",
        "            background-color: #fafafa;",
        "            color: #333;",
        "        }",
        "        .message {",
        "            margin-bottom: 12px;",
        "            padding: 12px;",
        "            border-radius: 6px;",
        "            border-left: 3px solid;",
        "        }",
        "        .session-divider {",
        "            margin: 30px 0;",
        "            padding: 8px 0;",
        "            border-top: 2px solid #ddd;",
        "            text-align: center;",
        "            font-weight: 600;",
        "            color: #666;",
        "            font-size: 0.9em;",
        "        }",
        "        .user {",
        "            background-color: #e3f2fd;",
        "            border-left-color: #2196f3;",
        "        }",
        "        .assistant {",
        "            background-color: #f3e5f5;",
        "            border-left-color: #9c27b0;",
        "        }",
        "        .summary {",
        "            background-color: #e8f5e8;",
        "            border-left-color: #4caf50;",
        "        }",
        "        .system {",
        "            background-color: #fff8e1;",
        "            border-left-color: #ff9800;",
        "        }",
        "        details {",
        "            margin-top: 8px;",
        "        }",
        "        details summary {",
        "            font-weight: 600;",
        "            cursor: pointer;",
        "            padding: 4px 0;",
        "            color: #666;",
        "        }",
        "        details[open] summary {",
        "            margin-bottom: 8px;",
        "        }",
        "        .duplicate-collapsed {",
        "            background-color: #fff3cd;",
        "            border-left-color: #ffc107;",
        "            opacity: 0.7;",
        "        }",
        "        .header {",
        "            font-weight: 600;",
        "            margin-bottom: 8px;",
        "            display: flex;",
        "            justify-content: space-between;",
        "            align-items: center;",
        "        }",
        "        .timestamp {",
        "            font-size: 0.85em;",
        "            color: #666;",
        "            font-weight: normal;",
        "        }",
        "        .content {",
        "            word-wrap: break-word;",
        "        }",
        "        .duplicate-note {",
        "            font-style: italic;",
        "            color: #856404;",
        "            font-size: 0.9em;",
        "            margin-top: 8px;",
        "        }",
        "        h1 {",
        "            text-align: center;",
        "            color: #2c3e50;",
        "            margin-bottom: 20px;",
        "            font-size: 1.8em;",
        "        }",
        "        code {",
        "            background-color: #f5f5f5;",
        "            padding: 2px 4px;",
        "            border-radius: 3px;",
        "            font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;",
        "        }",
        "        pre {",
        "            background-color: #f5f5f5;",
        "            padding: 10px;",
        "            border-radius: 5px;",
        "            overflow-x: auto;",
        "        }",
        "    </style>",
        "</head>",
        "<body>",
        f"    <h1>{title}</h1>",
    ]

    current_session = None
    last_message_content = None

    for message in messages:
        message_type = message.type

        # Extract message content first to check for duplicates
        if isinstance(message, SummaryTranscriptEntry):
            text_content = message.summary
            message_content = message.summary
        else:
            # Must be UserTranscriptEntry or AssistantTranscriptEntry
            message_content = message.message.content  # type: ignore
            text_content = extract_text_content(message_content)
            
        if not text_content.strip():
            continue

        # Handle system messages with command names
        is_system = is_system_message(text_content, message_content)
        is_command_message = (
            "<command-name>" in text_content and "<command-message>" in text_content
        )
        is_local_command_output = "<local-command-stdout>" in text_content

        if is_system and not is_command_message:
            continue

        # Check if we're in a new session
        source_file = getattr(message, '_source_file', 'unknown')
        is_new_session = current_session != source_file

        # Check for duplicate message at session boundary
        is_duplicate = (
            is_new_session
            and last_message_content is not None
            and text_content.strip() == last_message_content.strip()
        )

        if is_new_session:
            if current_session is not None:  # Don't add divider before first session
                html_parts.append(
                    f"    <div class='session-divider'>Session: {source_file}</div>"
                )
            else:
                html_parts.append(
                    f"    <div class='session-divider'>Session: {source_file}</div>"
                )
            current_session = source_file

        # Get timestamp (only for non-summary messages)
        timestamp = getattr(message, 'timestamp', '') if hasattr(message, 'timestamp') else ''
        formatted_timestamp = format_timestamp(timestamp) if timestamp else ""

        # Determine CSS class and content based on message type and duplicate status
        if message_type == "summary":
            css_class = "summary"
            summary_text = message.summary if isinstance(message, SummaryTranscriptEntry) else "Summary"
            content_html = f"<strong>Summary:</strong> {escape_html(str(summary_text))}"
        elif is_command_message:
            css_class = "system"
            command_name, command_args, command_contents = extract_command_info(
                text_content
            )
            escaped_command_name = escape_html(command_name)
            escaped_command_args = escape_html(command_args)

            # Format the command contents with proper line breaks
            formatted_contents = command_contents.replace("\\n", "\n")
            escaped_command_contents = escape_html(formatted_contents)

            # Build the content HTML
            content_parts: List[str] = [
                f"<strong>Command:</strong> {escaped_command_name}"
            ]
            if command_args:
                content_parts.append(f"<strong>Args:</strong> {escaped_command_args}")
            if command_contents:
                content_parts.append(
                    f"<details><summary>Content</summary><div class='content'>{escaped_command_contents}</div></details>"
                )

            content_html = "<br>".join(content_parts)
            message_type = "system"
        elif is_local_command_output:
            css_class = "system"
            # Extract content between <local-command-stdout> tags
            import re
            stdout_match = re.search(r"<local-command-stdout>(.*?)</local-command-stdout>", text_content, re.DOTALL)
            if stdout_match:
                stdout_content = stdout_match.group(1).strip()
                escaped_stdout = escape_html(stdout_content)
                content_html = f"<strong>Command Output:</strong><br><div class='content'>{escaped_stdout}</div>"
            else:
                content_html = escape_html(text_content)
            message_type = "system"
        else:
            css_class = f"{message_type}"
            content_html = escape_html(text_content)

        if is_duplicate:
            css_class += " duplicate-collapsed"
            content_html = "<div class='duplicate-note'>(Duplicate from previous session - collapsed)</div>"

        html_parts.extend(
            [
                f"    <div class='message {css_class}'>",
                "        <div class='header'>",
                f"            <span>{message_type.title()}</span>",
                f"            <span class='timestamp'>{formatted_timestamp}</span>",
                "        </div>",
                f"        <div class='content'>{content_html}</div>",
                "    </div>",
            ]
        )

        # Update last message content for duplicate detection
        last_message_content = text_content

    html_parts.extend(["</body>", "</html>"])

    return "\n".join(html_parts)


def convert_jsonl_to_html(
    input_path: Path,
    output_path: Optional[Path] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
) -> Path:
    """Convert JSONL transcript(s) to HTML file."""
    if not input_path.exists():
        raise FileNotFoundError(f"Input path not found: {input_path}")

    if input_path.is_file():
        # Single file mode
        if output_path is None:
            output_path = input_path.with_suffix(".html")
        messages = load_transcript(input_path)
        title = f"Claude Transcript - {input_path.stem}"
    else:
        # Directory mode
        if output_path is None:
            output_path = input_path / "combined_transcripts.html"
        messages = load_directory_transcripts(input_path)
        title = f"Claude Transcripts - {input_path.name}"

    # Apply date filtering
    messages = filter_messages_by_date(messages, from_date, to_date)

    # Update title to include date range if specified
    if from_date or to_date:
        date_range_parts: List[str] = []
        if from_date:
            date_range_parts.append(f"from {from_date}")
        if to_date:
            date_range_parts.append(f"to {to_date}")
        date_range_str = " ".join(date_range_parts)
        title += f" ({date_range_str})"

    html_content = generate_html(messages, title)
    # output_path is guaranteed to be a Path at this point
    assert output_path is not None
    output_path.write_text(html_content, encoding="utf-8")
    return output_path
