#!/usr/bin/env python3
"""Render Claude transcript data to HTML format."""

import json
from pathlib import Path
from typing import List, Optional, Union, Dict, Any, cast
from datetime import datetime
import html
import mistune
from jinja2 import Environment, FileSystemLoader

from .models import (
    AssistantTranscriptEntry,
    TranscriptEntry,
    SummaryTranscriptEntry,
    ContentItem,
    TextContent,
    ToolResultContent,
    ToolUseContent,
    ThinkingContent,
    ImageContent,
)
from .parser import extract_text_content


def format_timestamp(timestamp_str: str) -> str:
    """Format ISO timestamp for display, converting to UTC."""
    try:
        dt = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        # Convert to UTC if timezone-aware
        if dt.tzinfo is not None:
            dt = dt.utctimetuple()
            dt = datetime(*dt[:6])  # Convert back to naive datetime in UTC
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, AttributeError):
        return timestamp_str


def escape_html(text: str) -> str:
    """Escape HTML special characters in text."""
    return html.escape(text)


def create_collapsible_details(
    summary: str, content: str, css_classes: str = ""
) -> str:
    """Create a collapsible details element with consistent styling and preview functionality."""
    class_attr = ' class="collapsible-details"'
    wrapper_classes = f"tool-content{' ' + css_classes if css_classes else ''}"

    if len(content) <= 200:
        return f"""
        <div class="{wrapper_classes}">
            {summary}
            <div class="details-content">
                {content}
            </div>
        </div>
        """

    # Get first ~200 characters, break at word boundaries
    preview_text = content[:200] + "..."

    return f"""
    <div class="{wrapper_classes}">
        <details{class_attr}>
            <summary>
                {summary}
                <div class="preview-content">{preview_text}</div>
            </summary>
            <div class="details-content">
                {content}
            </div>
        </details>
    </div>
    """


def render_markdown(text: str) -> str:
    """Convert markdown text to HTML using mistune."""
    # Configure mistune with GitHub-flavored markdown features
    renderer = mistune.create_markdown(
        plugins=[
            "strikethrough",
            "footnotes",
            "table",
            "url",
            "task_lists",
            "def_list",
        ],
        escape=False,  # Don't escape HTML since we want to render markdown properly
    )
    return str(renderer(text))


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


def format_todowrite_content(tool_use: ToolUseContent) -> str:
    """Format TodoWrite tool use content as an actual todo list with checkboxes."""
    # Parse todos from input
    todos_data = tool_use.input.get("todos", [])
    if not todos_data:
        return """
        <div class="todo-content">
            <p><em>No todos found</em></p>
        </div>
        """

    # Status emojis
    status_emojis = {"pending": "⏳", "in_progress": "🔄", "completed": "✅"}

    # Build todo list HTML
    todo_items: List[str] = []
    for todo in todos_data:
        try:
            todo_id = escape_html(str(todo.get("id", "")))
            content = escape_html(str(todo.get("content", "")))
            status = todo.get("status", "pending")
            priority = todo.get("priority", "medium")
            status_emoji = status_emojis.get(status, "⏳")

            # Determine checkbox state
            checked = "checked" if status == "completed" else ""
            disabled = "disabled" if status == "completed" else ""

            # CSS class for styling
            item_class = f"todo-item {status} {priority}"

            todo_items.append(f"""
                <div class="{item_class}">
                    <input type="checkbox" {checked} {disabled} readonly>
                    <span class="todo-status">{status_emoji}</span>
                    <span class="todo-content">{content}</span>
                    <span class="todo-id">#{todo_id}</span>
                </div>
            """)
        except AttributeError:
            todo_items.append(f"""
                <div class="todo-item pending medium">
                    <input type="checkbox" readonly>
                    <span class="todo-status">⏳</span>
                    <span class="todo-content">{str(todo)}</span>
                </div>
            """)

    todos_html = "".join(todo_items)

    return f"""
    <div class="todo-list">
        {todos_html}
    </div>
    """


def format_tool_use_content(tool_use: ToolUseContent) -> str:
    """Format tool use content as HTML."""
    # Special handling for TodoWrite
    if tool_use.name == "TodoWrite":
        return format_todowrite_content(tool_use)

    # Format the input parameters
    try:
        formatted_input = json.dumps(tool_use.input, indent=2)
        escaped_input = escape_html(formatted_input)
    except (TypeError, ValueError):
        escaped_input = escape_html(str(tool_use.input))

    # For simple content, show directly without collapsible wrapper
    if len(escaped_input) <= 200:
        return f"<pre>{escaped_input}</pre>"

    # For longer content, use collapsible details but no extra wrapper
    preview_text = escaped_input[:200] + "..."
    return f"""
    <details class="collapsible-details">
        <summary>
            <div class="preview-content"><pre>{preview_text}</pre></div>
        </summary>
        <div class="details-content">
            <pre>{escaped_input}</pre>
        </div>
    </details>
    """


def format_tool_result_content(tool_result: ToolResultContent) -> str:
    """Format tool result content as HTML."""
    # Handle both string and structured content
    if isinstance(tool_result.content, str):
        escaped_content = escape_html(tool_result.content)
    else:
        # Content is a list of structured items, extract text
        content_parts: List[str] = []
        for item in tool_result.content:
            if isinstance(item, dict) and item.get("type") == "text":  # type: ignore
                text_value = item.get("text")
                if isinstance(text_value, str):
                    content_parts.append(text_value)
        escaped_content = escape_html("\n".join(content_parts))

    # For simple content, show directly without collapsible wrapper
    if len(escaped_content) <= 200:
        return f"<pre>{escaped_content}</pre>"

    # For longer content, use collapsible details but no extra wrapper
    preview_text = escaped_content[:200] + "..."
    return f"""
    <details class="collapsible-details">
        <summary>
            <div class="preview-content"><pre>{preview_text}</pre></div>
        </summary>
        <div class="details-content">
            <pre>{escaped_content}</pre>
        </div>
    </details>
    """


def format_thinking_content(thinking: ThinkingContent) -> str:
    """Format thinking content as HTML."""
    escaped_thinking = escape_html(thinking.thinking.strip())

    # For simple content, show directly without collapsible wrapper
    if len(escaped_thinking) <= 200:
        return f'<div class="thinking-text">{escaped_thinking}</div>'

    # For longer content, use collapsible details but no extra wrapper
    preview_text = escaped_thinking[:200] + "..."
    return f"""
    <details class="collapsible-details">
        <summary>
            <div class="preview-content"><div class="thinking-text">{preview_text}</div></div>
        </summary>
        <div class="details-content">
            <div class="thinking-text">{escaped_thinking}</div>
        </div>
    </details>
    """


def format_image_content(image: ImageContent) -> str:
    """Format image content as HTML."""
    # Create a data URL from the base64 image data
    data_url = f"data:{image.source.media_type};base64,{image.source.data}"

    return f'<img src="{data_url}" alt="Uploaded image" style="max-width: 100%; height: auto; border: 1px solid #ddd; border-radius: 4px; margin: 10px 0;" />'


def render_message_content(
    content: Union[str, List[ContentItem]], message_type: str
) -> str:
    """Render message content with proper tool use and tool result formatting."""
    if isinstance(content, str):
        if message_type == "user":
            # User messages are shown as-is in preformatted blocks
            escaped_text = escape_html(content)
            return "<pre>" + escaped_text + "</pre>"
        else:
            # Assistant messages get markdown rendering
            return render_markdown(content)

    # content is a list of ContentItem objects
    rendered_parts: List[str] = []

    for item in content:
        if type(item) is TextContent:
            if message_type == "user":
                # User messages are shown as-is in preformatted blocks
                escaped_text = escape_html(item.text)
                rendered_parts.append("<pre>" + escaped_text + "</pre>")
            else:
                # Assistant messages get markdown rendering
                rendered_parts.append(render_markdown(item.text))
        elif type(item) is ToolUseContent:
            rendered_parts.append(format_tool_use_content(item))  # type: ignore
        elif type(item) is ToolResultContent:
            rendered_parts.append(format_tool_result_content(item))  # type: ignore
        elif type(item) is ThinkingContent:
            rendered_parts.append(format_thinking_content(item))  # type: ignore
        elif type(item) is ImageContent:
            rendered_parts.append(format_image_content(item))  # type: ignore

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
        token_usage: Optional[str] = None,
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
        self.token_usage = token_usage


class TemplateProject:
    """Structured project data for template rendering."""

    def __init__(self, project_data: Dict[str, Any]):
        self.name = project_data["name"]
        self.html_file = project_data["html_file"]
        self.jsonl_count = project_data["jsonl_count"]
        self.message_count = project_data["message_count"]
        self.last_modified = project_data["last_modified"]
        self.total_input_tokens = project_data.get("total_input_tokens", 0)
        self.total_output_tokens = project_data.get("total_output_tokens", 0)
        self.total_cache_creation_tokens = project_data.get(
            "total_cache_creation_tokens", 0
        )
        self.total_cache_read_tokens = project_data.get("total_cache_read_tokens", 0)
        self.latest_timestamp = project_data.get("latest_timestamp", "")
        self.earliest_timestamp = project_data.get("earliest_timestamp", "")

        # Format display name (remove leading dash and convert dashes to slashes)
        self.display_name = self.name
        if self.display_name.startswith("-"):
            self.display_name = self.display_name[1:].replace("-", "/")

        # Format last modified date
        last_modified_dt = datetime.fromtimestamp(self.last_modified)
        self.formatted_date = last_modified_dt.strftime("%Y-%m-%d %H:%M:%S")

        # Format interaction time range
        if self.earliest_timestamp and self.latest_timestamp:
            if self.earliest_timestamp == self.latest_timestamp:
                # Single interaction
                self.formatted_time_range = format_timestamp(self.latest_timestamp)
            else:
                # Time range
                earliest_formatted = format_timestamp(self.earliest_timestamp)
                latest_formatted = format_timestamp(self.latest_timestamp)
                self.formatted_time_range = (
                    f"{earliest_formatted} to {latest_formatted}"
                )
        elif self.latest_timestamp:
            self.formatted_time_range = format_timestamp(self.latest_timestamp)
        else:
            self.formatted_time_range = ""

        # Format last interaction timestamp (kept for backward compatibility)
        if self.latest_timestamp:
            self.formatted_last_interaction = format_timestamp(self.latest_timestamp)
        else:
            self.formatted_last_interaction = ""

        # Format token usage
        self.token_summary = ""
        if self.total_input_tokens > 0 or self.total_output_tokens > 0:
            token_parts: List[str] = []
            if self.total_input_tokens > 0:
                token_parts.append(f"Input: {self.total_input_tokens}")
            if self.total_output_tokens > 0:
                token_parts.append(f"Output: {self.total_output_tokens}")
            if self.total_cache_creation_tokens > 0:
                token_parts.append(
                    f"Cache Creation: {self.total_cache_creation_tokens}"
                )
            if self.total_cache_read_tokens > 0:
                token_parts.append(f"Cache Read: {self.total_cache_read_tokens}")
            self.token_summary = " | ".join(token_parts)


class TemplateSummary:
    """Summary statistics for template rendering."""

    def __init__(self, project_summaries: List[Dict[str, Any]]):
        self.total_projects = len(project_summaries)
        self.total_jsonl = sum(p["jsonl_count"] for p in project_summaries)
        self.total_messages = sum(p["message_count"] for p in project_summaries)

        # Calculate aggregated token usage
        self.total_input_tokens = sum(
            p.get("total_input_tokens", 0) for p in project_summaries
        )
        self.total_output_tokens = sum(
            p.get("total_output_tokens", 0) for p in project_summaries
        )
        self.total_cache_creation_tokens = sum(
            p.get("total_cache_creation_tokens", 0) for p in project_summaries
        )
        self.total_cache_read_tokens = sum(
            p.get("total_cache_read_tokens", 0) for p in project_summaries
        )

        # Find the most recent and earliest interaction timestamps across all projects
        self.latest_interaction = ""
        self.earliest_interaction = ""
        for project in project_summaries:
            # Check latest timestamp
            latest_timestamp = project.get("latest_timestamp", "")
            if latest_timestamp and (
                not self.latest_interaction
                or latest_timestamp > self.latest_interaction
            ):
                self.latest_interaction = latest_timestamp

            # Check earliest timestamp
            earliest_timestamp = project.get("earliest_timestamp", "")
            if earliest_timestamp and (
                not self.earliest_interaction
                or earliest_timestamp < self.earliest_interaction
            ):
                self.earliest_interaction = earliest_timestamp

        # Format the latest interaction timestamp
        if self.latest_interaction:
            self.formatted_latest_interaction = format_timestamp(
                self.latest_interaction
            )
        else:
            self.formatted_latest_interaction = ""

        # Format the time range
        if self.earliest_interaction and self.latest_interaction:
            if self.earliest_interaction == self.latest_interaction:
                # Single interaction
                self.formatted_time_range = format_timestamp(self.latest_interaction)
            else:
                # Time range
                earliest_formatted = format_timestamp(self.earliest_interaction)
                latest_formatted = format_timestamp(self.latest_interaction)
                self.formatted_time_range = (
                    f"{earliest_formatted} to {latest_formatted}"
                )
        else:
            self.formatted_time_range = ""

        # Format token usage summary
        self.token_summary = ""
        if self.total_input_tokens > 0 or self.total_output_tokens > 0:
            token_parts: List[str] = []
            if self.total_input_tokens > 0:
                token_parts.append(f"Input: {self.total_input_tokens}")
            if self.total_output_tokens > 0:
                token_parts.append(f"Output: {self.total_output_tokens}")
            if self.total_cache_creation_tokens > 0:
                token_parts.append(
                    f"Cache Creation: {self.total_cache_creation_tokens}"
                )
            if self.total_cache_read_tokens > 0:
                token_parts.append(f"Cache Read: {self.total_cache_read_tokens}")
            self.token_summary = " | ".join(token_parts)


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

    # Track requestIds to avoid double-counting token usage
    seen_request_ids: set[str] = set()
    # Track which messages should show token usage (first occurrence of each requestId)
    show_tokens_for_message: set[str] = set()

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

        # Separate tool/thinking/image content from text content
        tool_items: List[ContentItem] = []
        text_only_content: Union[str, List[ContentItem]] = []

        if isinstance(message_content, list):
            text_only_items: List[ContentItem] = []
            for item in message_content:
                if isinstance(
                    item,
                    (ToolUseContent, ToolResultContent, ThinkingContent, ImageContent),
                ):
                    tool_items.append(item)
                else:
                    text_only_items.append(item)
            text_only_content = text_only_items
        else:
            # Single string content
            text_only_content = message_content

        # Skip if no meaningful content
        if not text_content.strip() and not tool_items:
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
                "last_timestamp": getattr(message, "timestamp", ""),
                "message_count": 0,
                "first_user_message": first_user_message,
                "total_input_tokens": 0,
                "total_output_tokens": 0,
                "total_cache_creation_tokens": 0,
                "total_cache_read_tokens": 0,
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

        # Update last timestamp for this session
        current_timestamp = getattr(message, "timestamp", "")
        if current_timestamp:
            sessions[session_id]["last_timestamp"] = current_timestamp

        # Extract and accumulate token usage for assistant messages
        # Only count tokens for the first message with each requestId to avoid duplicates
        if message_type == "assistant" and hasattr(message, "message"):
            assistant_message = getattr(message, "message")
            request_id = getattr(message, "requestId", None)
            message_uuid = getattr(message, "uuid", "")

            if (
                hasattr(assistant_message, "usage")
                and assistant_message.usage
                and request_id
                and request_id not in seen_request_ids
            ):
                # Mark this requestId as seen to avoid double-counting
                seen_request_ids.add(request_id)
                # Mark this specific message UUID as one that should show token usage
                show_tokens_for_message.add(message_uuid)

                usage = assistant_message.usage
                sessions[session_id]["total_input_tokens"] += usage.input_tokens
                sessions[session_id]["total_output_tokens"] += usage.output_tokens
                if usage.cache_creation_input_tokens:
                    sessions[session_id]["total_cache_creation_tokens"] += (
                        usage.cache_creation_input_tokens
                    )
                if usage.cache_read_input_tokens:
                    sessions[session_id]["total_cache_read_tokens"] += (
                        usage.cache_read_input_tokens
                    )

        # Get timestamp (only for non-summary messages)
        timestamp = (
            getattr(message, "timestamp", "") if hasattr(message, "timestamp") else ""
        )
        formatted_timestamp = format_timestamp(timestamp) if timestamp else ""

        # Extract token usage for assistant messages
        # Only show token usage for the first message with each requestId to avoid duplicates
        token_usage_str: Optional[str] = None
        if message_type == "assistant" and hasattr(message, "message"):
            assistant_message = getattr(message, "message")
            message_uuid = getattr(message, "uuid", "")

            if (
                hasattr(assistant_message, "usage")
                and assistant_message.usage
                and message_uuid in show_tokens_for_message
            ):
                # Only show token usage for messages marked as first occurrence of requestId
                usage = assistant_message.usage
                token_parts = [
                    f"Input: {usage.input_tokens}",
                    f"Output: {usage.output_tokens}",
                ]
                if usage.cache_creation_input_tokens:
                    token_parts.append(
                        f"Cache Creation: {usage.cache_creation_input_tokens}"
                    )
                if usage.cache_read_input_tokens:
                    token_parts.append(f"Cache Read: {usage.cache_read_input_tokens}")
                token_usage_str = " | ".join(token_parts)

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
                details_html = create_collapsible_details(
                    "Content", escaped_command_contents
                )
                content_parts.append(details_html)

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
            # Render only text content for the main message
            content_html = render_message_content(text_only_content, message_type)

        # Create main message (if it has text content)
        if text_only_content and (
            isinstance(text_only_content, str)
            and text_only_content.strip()
            or isinstance(text_only_content, list)
            and text_only_content
        ):
            template_message = TemplateMessage(
                message_type=message_type,
                content_html=content_html,
                formatted_timestamp=formatted_timestamp,
                css_class=css_class,
                session_summary=session_summary,
                session_id=session_id,
                token_usage=token_usage_str,
            )
            template_messages.append(template_message)

        # Create separate messages for each tool/thinking/image item
        for tool_item in tool_items:
            tool_timestamp = getattr(message, "timestamp", "")
            tool_formatted_timestamp = (
                format_timestamp(tool_timestamp) if tool_timestamp else ""
            )

            if isinstance(tool_item, ToolUseContent):
                tool_content_html = format_tool_use_content(tool_item)
                escaped_name = escape_html(tool_item.name)
                escaped_id = escape_html(tool_item.id)
                if tool_item.name == "TodoWrite":
                    tool_message_type = f"📝 Todo List (ID: {escaped_id})"
                else:
                    tool_message_type = f"Tool use: {escaped_name} (ID: {escaped_id})"
                tool_css_class = "tool_use"
            elif isinstance(tool_item, ToolResultContent):
                tool_content_html = format_tool_result_content(tool_item)
                escaped_id = escape_html(tool_item.tool_use_id)
                error_indicator = " (🚨 Error)" if tool_item.is_error else ""
                tool_message_type = f"Tool Result{error_indicator}: {escaped_id}"
                tool_css_class = "tool_result"
            elif isinstance(tool_item, ThinkingContent):
                tool_content_html = format_thinking_content(tool_item)
                tool_message_type = "Thinking"
                tool_css_class = "thinking"
            elif isinstance(tool_item, ImageContent):
                tool_content_html = format_image_content(tool_item)
                tool_message_type = "Image"
                tool_css_class = "image"
            else:
                continue

            tool_template_message = TemplateMessage(
                message_type=tool_message_type,
                content_html=tool_content_html,
                formatted_timestamp=tool_formatted_timestamp,
                css_class=tool_css_class,
                session_summary=session_summary,
                session_id=session_id,
            )
            template_messages.append(tool_template_message)

    # Prepare session navigation data
    session_nav: List[Dict[str, Any]] = []
    for session_id in session_order:
        session_info = sessions[session_id]

        # Format timestamp range
        first_ts = session_info["first_timestamp"]
        last_ts = session_info["last_timestamp"]
        timestamp_range = ""
        if first_ts and last_ts:
            if first_ts == last_ts:
                timestamp_range = format_timestamp(first_ts)
            else:
                timestamp_range = (
                    f"{format_timestamp(first_ts)} - {format_timestamp(last_ts)}"
                )
        elif first_ts:
            timestamp_range = format_timestamp(first_ts)

        # Format token usage summary
        token_summary = ""
        total_input = session_info["total_input_tokens"]
        total_output = session_info["total_output_tokens"]
        total_cache_creation = session_info["total_cache_creation_tokens"]
        total_cache_read = session_info["total_cache_read_tokens"]

        if total_input > 0 or total_output > 0:
            token_parts: List[str] = []
            if total_input > 0:
                token_parts.append(f"Input: {total_input}")
            if total_output > 0:
                token_parts.append(f"Output: {total_output}")
            if total_cache_creation > 0:
                token_parts.append(f"Cache Creation: {total_cache_creation}")
            if total_cache_read > 0:
                token_parts.append(f"Cache Read: {total_cache_read}")
            token_summary = "Token usage – " + " | ".join(token_parts)

        session_nav.append(
            {
                "id": session_id,
                "summary": session_info["summary"],
                "timestamp_range": timestamp_range,
                "message_count": session_info["message_count"],
                "first_user_message": session_info["first_user_message"],
                "token_summary": token_summary,
            }
        )

    # Render template
    env = _get_template_environment()
    template = env.get_template("transcript.html")
    return str(
        template.render(title=title, messages=template_messages, sessions=session_nav)
    )


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
