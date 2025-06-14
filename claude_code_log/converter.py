#!/usr/bin/env python3
"""Convert Claude transcript JSONL files to HTML."""

import json
from pathlib import Path
from typing import List, Optional, Union, Dict, Any
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
    ToolUseContent,
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
        if hasattr(entry, "timestamp"):
            return entry.timestamp  # type: ignore
        return ""

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
                command_contents = (
                    text_value if isinstance(text_value, str) else str(text_value)
                )  # type: ignore
            else:
                command_contents = contents_text
        except json.JSONDecodeError:
            command_contents = contents_text

    return command_name, command_args, command_contents


def format_tool_use_content(tool_use: ToolUseContent) -> str:
    """Format tool use content as HTML."""
    escaped_name = escape_html(tool_use.name)
    escaped_id = escape_html(tool_use.id)

    # Format the input parameters
    import json

    try:
        formatted_input = json.dumps(tool_use.input, indent=2)
        escaped_input = escape_html(formatted_input)
    except (TypeError, ValueError):
        escaped_input = escape_html(str(tool_use.input))

    return f"""
    <div class="tool-content tool-use">
        <details>
            <summary><strong>Tool Use:</strong> {escaped_name} (ID: {escaped_id})</summary>
            <div class="tool-input">
                <strong>Input:</strong>
                <pre>{escaped_input}</pre>
            </div>
        </details>
    </div>
    """


def format_tool_result_content(tool_result: ToolResultContent) -> str:
    """Format tool result content as HTML."""
    escaped_id = escape_html(tool_result.tool_use_id)
    escaped_content = escape_html(tool_result.content)

    error_indicator = " (Error)" if tool_result.is_error else ""

    return f"""
    <div class="tool-content tool-result">
        <details>
            <summary><strong>Tool Result{error_indicator}:</strong> {escaped_id}</summary>
            <div class="tool-input">
                <pre>{escaped_content}</pre>
            </div>
        </details>
    </div>
    """


def render_message_content(content: Union[str, List[ContentItem]]) -> str:
    """Render message content with proper tool use and tool result formatting."""
    if isinstance(content, str):
        return escape_html(content)

    # content is a list of ContentItem objects
    rendered_parts: List[str] = []

    for item in content:
        item_type = type(item).__name__
        if item_type == "TextContent":
            rendered_parts.append(escape_html(item.text))  # type: ignore
        elif item_type == "ToolUseContent":
            rendered_parts.append(format_tool_use_content(item))  # type: ignore
        elif item_type == "ToolResultContent":
            rendered_parts.append(format_tool_result_content(item))  # type: ignore

    return "\n".join(rendered_parts)


def is_system_message(text_content: str) -> bool:
    """Check if a message is a system message that should be filtered out."""
    system_message_patterns = [
        "Caveat: The messages below were generated by the user while running local commands. DO NOT respond to these messages or otherwise consider them in your response unless the user explicitly asks you to.",
        "[Request interrupted by user for tool use]",
    ]

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
        "        .tool-content {",
        "            background-color: #f8f9fa;",
        "            border: 1px solid #e9ecef;",
        "            border-radius: 4px;",
        "            padding: 8px;",
        "            margin: 8px 0;",
        "            overflow-x: auto;",
        "        }",
        "        .tool-result {",
        "            background-color: #e8f5e8;",
        "            border-left: 3px solid #4caf50;",
        "        }",
        "        .tool-use {",
        "            background-color: #e3f2fd;",
        "            border-left: 3px solid #2196f3;",
        "        }",
        "        .tool-input {",
        "            background-color: #fff3cd;",
        "            border: 1px solid #ffeaa7;",
        "            border-radius: 4px;",
        "            padding: 6px;",
        "            margin: 4px 0;",
        "            font-size: 0.9em;",
        "        }",
        "        .tool-input > pre {",
        "            white-space: pre-wrap;",
        "            word-wrap: break-word;",
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

        # Check if message has tool use or tool result content even if no text
        has_tool_content = False
        if isinstance(message_content, list):
            for item in message_content:
                if isinstance(item, (ToolUseContent, ToolResultContent)):
                    has_tool_content = True
                    break

        if not text_content.strip() and not has_tool_content:
            continue

        # Handle system messages with command names
        is_system = is_system_message(text_content)
        is_command_message = (
            "<command-name>" in text_content and "<command-message>" in text_content
        )
        is_local_command_output = "<local-command-stdout>" in text_content

        if is_system and not is_command_message:
            continue

        # Check if we're in a new session
        source_file = getattr(message, "_source_file", "unknown")
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
        timestamp = (
            getattr(message, "timestamp", "") if hasattr(message, "timestamp") else ""
        )
        formatted_timestamp = format_timestamp(timestamp) if timestamp else ""

        # Determine CSS class and content based on message type and duplicate status
        if message_type == "summary":
            css_class = "summary"
            summary_text = (
                message.summary
                if isinstance(message, SummaryTranscriptEntry)
                else "Summary"
            )
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

            stdout_match = re.search(
                r"<local-command-stdout>(.*?)</local-command-stdout>",
                text_content,
                re.DOTALL,
            )
            if stdout_match:
                stdout_content = stdout_match.group(1).strip()
                escaped_stdout = escape_html(stdout_content)
                content_html = f"<strong>Command Output:</strong><br><div class='content'>{escaped_stdout}</div>"
            else:
                content_html = escape_html(text_content)
            message_type = "system"
        else:
            css_class = f"{message_type}"
            # Use the new render_message_content function to handle tool use
            content_html = render_message_content(message_content)

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


def process_projects_hierarchy(
    projects_path: Path,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
) -> Path:
    """Process the entire ~/.claude/projects/ hierarchy and create linked HTML files."""
    if not projects_path.exists():
        raise FileNotFoundError(f"Projects path not found: {projects_path}")

    # Find all project directories (those with JSONL files)
    project_dirs = []
    for child in projects_path.iterdir():
        if child.is_dir() and list(child.glob("*.jsonl")):
            project_dirs.append(child)

    if not project_dirs:
        raise FileNotFoundError(
            f"No project directories with JSONL files found in {projects_path}"
        )

    # Process each project directory
    project_summaries: List[Dict[str, Any]] = []
    for project_dir in sorted(project_dirs):
        try:
            # Generate HTML for this project
            output_path = convert_jsonl_to_html(project_dir, None, from_date, to_date)

            # Get project info for index
            jsonl_files = list(project_dir.glob("*.jsonl"))
            jsonl_count = len(jsonl_files)
            messages = load_directory_transcripts(project_dir)
            if from_date or to_date:
                messages = filter_messages_by_date(messages, from_date, to_date)

            last_modified = (
                max(f.stat().st_mtime for f in jsonl_files) if jsonl_files else 0
            )

            project_summaries.append(
                {
                    "name": project_dir.name,
                    "path": project_dir,
                    "html_file": f"{project_dir.name}/{output_path.name}",
                    "jsonl_count": jsonl_count,
                    "message_count": len(messages),
                    "last_modified": last_modified,
                }
            )
        except Exception as e:
            print(f"Warning: Failed to process {project_dir}: {e}")
            continue

    # Generate index HTML
    index_path = projects_path / "index.html"
    index_html = generate_projects_index_html(project_summaries, from_date, to_date)
    index_path.write_text(index_html, encoding="utf-8")

    return index_path


def generate_projects_index_html(
    project_summaries: List[Dict[str, Any]],
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
) -> str:
    """Generate an index HTML page listing all projects."""
    import datetime

    title = "Claude Code Projects"
    if from_date or to_date:
        date_range_parts: List[str] = []
        if from_date:
            date_range_parts.append(f"from {from_date}")
        if to_date:
            date_range_parts.append(f"to {to_date}")
        date_range_str = " ".join(date_range_parts)
        title += f" ({date_range_str})"

    # Sort projects by last modified (most recent first)
    sorted_projects = sorted(
        project_summaries, key=lambda p: p["last_modified"], reverse=True
    )

    html_parts = [
        "<!DOCTYPE html>",
        "<html lang='en'>",
        "<head>",
        "    <meta charset='UTF-8'>",
        "    <meta name='viewport' content='width=device-width, initial-scale=1.0'>",
        f"    <title>{title}</title>",
        "    <style>",
        "        body {",
        "            font-family: 'SF Mono', 'Monaco', 'Inconsolata', 'Fira Code', 'Droid Sans Mono', 'Source Code Pro', 'Ubuntu Mono', 'Cascadia Code', 'Menlo', 'Consolas', monospace;",
        "            line-height: 1.6;",
        "            max-width: 1200px;",
        "            margin: 0 auto;",
        "            padding: 20px;",
        "            background-color: #fafafa;",
        "            color: #333;",
        "        }",
        "        h1 {",
        "            text-align: center;",
        "            color: #2c3e50;",
        "            margin-bottom: 30px;",
        "            font-size: 2em;",
        "        }",
        "        .project-list {",
        "            display: grid;",
        "            gap: 15px;",
        "        }",
        "        .project-card {",
        "            background: white;",
        "            border-radius: 8px;",
        "            padding: 20px;",
        "            box-shadow: 0 2px 4px rgba(0,0,0,0.1);",
        "            border-left: 4px solid #2196f3;",
        "        }",
        "        .project-card:hover {",
        "            box-shadow: 0 4px 8px rgba(0,0,0,0.15);",
        "            transform: translateY(-1px);",
        "            transition: all 0.2s ease;",
        "        }",
        "        .project-name {",
        "            font-size: 1.2em;",
        "            font-weight: 600;",
        "            margin-bottom: 10px;",
        "        }",
        "        .project-name a {",
        "            text-decoration: none;",
        "            color: #2196f3;",
        "        }",
        "        .project-name a:hover {",
        "            text-decoration: underline;",
        "        }",
        "        .project-stats {",
        "            color: #666;",
        "            font-size: 0.9em;",
        "            display: flex;",
        "            gap: 20px;",
        "            flex-wrap: wrap;",
        "        }",
        "        .stat {",
        "            display: flex;",
        "            align-items: center;",
        "            gap: 5px;",
        "        }",
        "        .summary {",
        "            text-align: center;",
        "            margin-bottom: 30px;",
        "            padding: 15px;",
        "            background: white;",
        "            border-radius: 8px;",
        "            box-shadow: 0 2px 4px rgba(0,0,0,0.1);",
        "        }",
        "        .summary-stats {",
        "            display: flex;",
        "            justify-content: center;",
        "            gap: 30px;",
        "            flex-wrap: wrap;",
        "        }",
        "        .summary-stat {",
        "            text-align: center;",
        "        }",
        "        .summary-stat .number {",
        "            font-size: 1.5em;",
        "            font-weight: 600;",
        "            color: #2196f3;",
        "        }",
        "        .summary-stat .label {",
        "            color: #666;",
        "            font-size: 0.9em;",
        "        }",
        "    </style>",
        "</head>",
        "<body>",
        f"    <h1>{title}</h1>",
    ]

    # Add summary statistics
    total_projects = len(project_summaries)
    total_jsonl = sum(p["jsonl_count"] for p in project_summaries)
    total_messages = sum(p["message_count"] for p in project_summaries)

    html_parts.extend(
        [
            "    <div class='summary'>",
            "        <div class='summary-stats'>",
            "            <div class='summary-stat'>",
            f"                <div class='number'>{total_projects}</div>",
            "                <div class='label'>Projects</div>",
            "            </div>",
            "            <div class='summary-stat'>",
            f"                <div class='number'>{total_jsonl}</div>",
            "                <div class='label'>Transcript Files</div>",
            "            </div>",
            "            <div class='summary-stat'>",
            f"                <div class='number'>{total_messages}</div>",
            "                <div class='label'>Messages</div>",
            "            </div>",
            "        </div>",
            "    </div>",
        ]
    )

    # Add project list
    html_parts.append("    <div class='project-list'>")

    for project in sorted_projects:
        # Format the project name (remove leading dash and convert dashes to slashes)
        display_name = project["name"]
        if display_name.startswith("-"):
            display_name = display_name[1:].replace("-", "/")

        # Format last modified date
        last_modified = datetime.datetime.fromtimestamp(project["last_modified"])
        formatted_date = last_modified.strftime("%Y-%m-%d %H:%M")

        html_parts.extend(
            [
                "        <div class='project-card'>",
                "            <div class='project-name'>",
                f"                <a href='{project['html_file']}'>{escape_html(display_name)}</a>",
                "            </div>",
                "            <div class='project-stats'>",
                f"                <div class='stat'>📁 {project['jsonl_count']} transcript files</div>",
                f"                <div class='stat'>💬 {project['message_count']} messages</div>",
                f"                <div class='stat'>🕒 {formatted_date}</div>",
                "            </div>",
                "        </div>",
            ]
        )

    html_parts.extend(
        [
            "    </div>",
            "</body>",
            "</html>",
        ]
    )

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
