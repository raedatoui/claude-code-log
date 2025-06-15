#!/usr/bin/env python3
"""Convert Claude transcript JSONL files to HTML."""

import json
from pathlib import Path
from typing import List, Optional, Union, Dict, Any, cast
from datetime import datetime
import dateparser
import html
from jinja2 import Environment, FileSystemLoader
from .models import (
    AssistantTranscriptEntry,
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
                        messages.append(entry)
                    else:
                        print("Unhandled message type:" + str(entry_dict))
                except (json.JSONDecodeError, ValueError) as e:
                    print("Unhandled message:" + str(e))
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
            contents_json: Any = json.loads(contents_text)
            if isinstance(contents_json, dict) and "text" in contents_json:
                text_dict = cast(Dict[str, Any], contents_json)
                text_value = text_dict["text"]
                command_contents = str(text_value)
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


def render_message_content(
    content: Union[str, List[ContentItem]], message_type: str
) -> str:
    """Render message content with proper tool use and tool result formatting."""
    if isinstance(content, str):
        escaped_text = escape_html(content)
        return (
            "<pre>" + escaped_text + "</pre>"
            if message_type == "user"
            else escaped_text
        )

    # content is a list of ContentItem objects
    rendered_parts: List[str] = []

    for item in content:
        if type(item) is TextContent:
            escaped_text = escape_html(item.text)
            rendered_parts.append(
                "<pre>" + escaped_text + "</pre>"
                if message_type == "user"
                else escaped_text
            )
        elif type(item) is ToolUseContent:
            rendered_parts.append(format_tool_use_content(item))  # type: ignore
        elif type(item) is ToolResultContent:
            rendered_parts.append(format_tool_result_content(item))  # type: ignore

    return "\n".join(rendered_parts)


def is_system_message(text_content: str) -> bool:
    """Check if a message is a system message that should be filtered out."""
    system_message_patterns = [
        "Caveat: The messages below were generated by the user while running local commands. DO NOT respond to these messages or otherwise consider them in your response unless the user explicitly asks you to.",
        "[Request interrupted by user for tool use]",
        "<local-command-stdout>",
    ]

    return any(pattern in text_content for pattern in system_message_patterns)


def _get_template_environment() -> Environment:
    """Get Jinja2 template environment."""
    templates_dir = Path(__file__).parent / "templates"
    return Environment(loader=FileSystemLoader(templates_dir))


class TemplateMessage:
    """Structured message data for template rendering."""

    def __init__(
        self,
        message_type: str,
        content_html: str,
        formatted_timestamp: str,
        css_class: str,
        session_summary: Optional[str] = None,
        session_id: Optional[str] = None,
        is_session_header: bool = False,
    ):
        self.type = message_type
        self.content_html = content_html
        self.formatted_timestamp = formatted_timestamp
        self.css_class = css_class
        self.display_type = message_type.title()
        self.session_summary = session_summary
        self.session_id = session_id
        self.is_session_header = is_session_header
        self.session_subtitle: Optional[str] = None


def generate_html(messages: List[TranscriptEntry], title: Optional[str] = None) -> str:
    """Generate HTML from transcript messages using Jinja2 templates."""
    if not title:
        title = "Claude Transcript"

    # Pre-process to find and attach session summaries
    session_summaries: Dict[str, str] = {}
    uuid_to_session: Dict[str, str] = {}
    uuid_to_session_backup: Dict[str, str] = {}

    # Build mapping from message UUID to session ID
    for message in messages:
        if hasattr(message, "uuid") and hasattr(message, "sessionId"):
            message_uuid = getattr(message, "uuid", "")
            session_id = getattr(message, "sessionId", "")
            if message_uuid and session_id:
                # There is often duplication, in that case we want to prioritise the assistant
                # message because summaries are generated from Claude's (last) success message
                if type(message) is AssistantTranscriptEntry:
                    uuid_to_session[message_uuid] = session_id
                else:
                    uuid_to_session_backup[message_uuid] = session_id

    # Map summaries to sessions via leafUuid -> message UUID -> session ID
    for message in messages:
        if isinstance(message, SummaryTranscriptEntry):
            leaf_uuid = message.leafUuid
            if leaf_uuid in uuid_to_session:
                session_summaries[uuid_to_session[leaf_uuid]] = message.summary
            elif (
                leaf_uuid in uuid_to_session_backup
                and uuid_to_session_backup[leaf_uuid] not in session_summaries
            ):
                session_summaries[uuid_to_session_backup[leaf_uuid]] = message.summary

    # Attach summaries to messages
    for message in messages:
        if hasattr(message, "sessionId"):
            session_id = getattr(message, "sessionId", "")
            if session_id in session_summaries:
                setattr(message, "_session_summary", session_summaries[session_id])

    # Group messages by session and collect session info for navigation
    sessions: Dict[str, Dict[str, Any]] = {}
    session_order: List[str] = []
    seen_sessions: set[str] = set()

    # Process messages into template-friendly format
    template_messages: List[TemplateMessage] = []

    for message in messages:
        message_type = message.type

        # Skip summary messages - they should already be attached to their sessions
        if isinstance(message, SummaryTranscriptEntry):
            continue

        # Extract message content first to check for duplicates
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
        session_id = getattr(message, "sessionId", "unknown")
        session_summary = getattr(message, "_session_summary", None)

        # Track sessions for navigation and add session header if new
        if session_id not in sessions:
            # Get the session summary for this session (may be None)
            current_session_summary = getattr(message, "_session_summary", None)

            # Get first user message content for preview
            first_user_message = ""
            if message_type == "user" and hasattr(message, "message"):
                first_user_message = extract_text_content(message.message.content)

            sessions[session_id] = {
                "id": session_id,
                "summary": current_session_summary,
                "first_timestamp": getattr(message, "timestamp", ""),
                "message_count": 0,
                "first_user_message": first_user_message,
            }
            session_order.append(session_id)

            # Add session header message
            if session_id not in seen_sessions:
                seen_sessions.add(session_id)
                # Create a meaningful session title
                session_title = (
                    f"{current_session_summary} • {session_id[:8]}"
                    if current_session_summary
                    else session_id[:8]
                )

                session_header = TemplateMessage(
                    message_type="session_header",
                    content_html=session_title,
                    formatted_timestamp="",
                    css_class="session-header",
                    session_summary=current_session_summary,
                    session_id=session_id,
                    is_session_header=True,
                )
                template_messages.append(session_header)

        # Update first user message if this is a user message and we don't have one yet
        elif message_type == "user" and not sessions[session_id]["first_user_message"]:
            if hasattr(message, "message"):
                sessions[session_id]["first_user_message"] = extract_text_content(
                    message.message.content
                )[:500]  # type: ignore

        sessions[session_id]["message_count"] += 1

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
            content_html = render_message_content(message_content, message_type)

        template_message = TemplateMessage(
            message_type=message_type,
            content_html=content_html,
            formatted_timestamp=formatted_timestamp,
            css_class=css_class,
            session_summary=session_summary,
            session_id=session_id,
        )
        template_messages.append(template_message)

    # Prepare session navigation data
    session_nav: List[Dict[str, Any]] = []
    for session_id in session_order:
        session_info = sessions[session_id]
        session_nav.append(
            {
                "id": session_id,
                "summary": session_info["summary"],
                "first_timestamp": format_timestamp(session_info["first_timestamp"])
                if session_info["first_timestamp"]
                else "",
                "message_count": session_info["message_count"],
                "first_user_message": session_info["first_user_message"],
            }
        )

    # Render template
    env = _get_template_environment()
    template = env.get_template("transcript.html")
    return str(
        template.render(title=title, messages=template_messages, sessions=session_nav)
    )


def process_projects_hierarchy(
    projects_path: Path,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
) -> Path:
    """Process the entire ~/.claude/projects/ hierarchy and create linked HTML files."""
    if not projects_path.exists():
        raise FileNotFoundError(f"Projects path not found: {projects_path}")

    # Find all project directories (those with JSONL files)
    project_dirs: List[Path] = []
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

            last_modified: float = (
                max(f.stat().st_mtime for f in jsonl_files) if jsonl_files else 0.0
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


class TemplateProject:
    """Structured project data for template rendering."""

    def __init__(self, project_data: Dict[str, Any]):
        self.name = project_data["name"]
        self.html_file = project_data["html_file"]
        self.jsonl_count = project_data["jsonl_count"]
        self.message_count = project_data["message_count"]
        self.last_modified = project_data["last_modified"]

        # Format display name (remove leading dash and convert dashes to slashes)
        self.display_name = self.name
        if self.display_name.startswith("-"):
            self.display_name = self.display_name[1:].replace("-", "/")

        # Format last modified date
        last_modified_dt = datetime.fromtimestamp(self.last_modified)
        self.formatted_date = last_modified_dt.strftime("%Y-%m-%d %H:%M")


class TemplateSummary:
    """Summary statistics for template rendering."""

    def __init__(self, project_summaries: List[Dict[str, Any]]):
        self.total_projects = len(project_summaries)
        self.total_jsonl = sum(p["jsonl_count"] for p in project_summaries)
        self.total_messages = sum(p["message_count"] for p in project_summaries)


def generate_projects_index_html(
    project_summaries: List[Dict[str, Any]],
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
) -> str:
    """Generate an index HTML page listing all projects using Jinja2 templates."""
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

    # Convert to template-friendly format
    template_projects = [TemplateProject(project) for project in sorted_projects]
    template_summary = TemplateSummary(project_summaries)

    # Render template
    env = _get_template_environment()
    template = env.get_template("index.html")
    return str(
        template.render(
            title=title, projects=template_projects, summary=template_summary
        )
    )


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
