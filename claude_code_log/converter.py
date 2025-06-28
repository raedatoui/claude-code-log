#!/usr/bin/env python3
"""Convert Claude transcript JSONL files to HTML."""

from pathlib import Path
import traceback
from typing import List, Optional, Dict, Any
from .utils import should_use_as_session_starter

from .parser import (
    load_transcript,
    load_directory_transcripts,
    filter_messages_by_date,
)
from .models import (
    TranscriptEntry,
    AssistantTranscriptEntry,
    SummaryTranscriptEntry,
    UserTranscriptEntry,
)
from .renderer import (
    generate_html,
    generate_session_html,
    generate_projects_index_html,
)


def convert_jsonl_to_html(
    input_path: Path,
    output_path: Optional[Path] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    generate_individual_sessions: bool = True,
) -> Path:
    """Convert JSONL transcript(s) to HTML file(s)."""
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

    # Generate combined HTML file
    html_content = generate_html(messages, title)
    assert output_path is not None
    output_path.write_text(html_content, encoding="utf-8")

    # Generate individual session files if requested and in directory mode
    if generate_individual_sessions and input_path.is_dir():
        _generate_individual_session_files(messages, input_path, from_date, to_date)

    return output_path


def _collect_project_sessions(messages: List[TranscriptEntry]) -> List[Dict[str, Any]]:
    """Collect session data for project index navigation."""
    from .parser import extract_text_content

    # Pre-process to find and attach session summaries
    # This matches the logic from renderer.py generate_html() exactly
    session_summaries: Dict[str, str] = {}
    uuid_to_session: Dict[str, str] = {}
    uuid_to_session_backup: Dict[str, str] = {}

    # Build mapping from message UUID to session ID across ALL messages
    # This allows summaries from later sessions to be matched to earlier sessions
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
    # Summaries can be in different sessions than the messages they summarize
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

    # Group messages by session
    sessions: Dict[str, Dict[str, Any]] = {}
    for message in messages:
        if hasattr(message, "sessionId") and not isinstance(
            message, SummaryTranscriptEntry
        ):
            session_id = getattr(message, "sessionId", "")
            if not session_id:
                continue

            if session_id not in sessions:
                sessions[session_id] = {
                    "id": session_id,
                    "summary": session_summaries.get(session_id),
                    "first_timestamp": getattr(message, "timestamp", ""),
                    "last_timestamp": getattr(message, "timestamp", ""),
                    "message_count": 0,
                    "first_user_message": "",
                }

            sessions[session_id]["message_count"] += 1
            current_timestamp = getattr(message, "timestamp", "")
            if current_timestamp:
                sessions[session_id]["last_timestamp"] = current_timestamp

            # Get first user message for preview (skip system messages)
            if (
                isinstance(message, UserTranscriptEntry)
                and not sessions[session_id]["first_user_message"]
                and hasattr(message, "message")
            ):
                first_user_content = extract_text_content(message.message.content)
                if should_use_as_session_starter(first_user_content):
                    sessions[session_id]["first_user_message"] = first_user_content[
                        :500
                    ]

    # Convert to list format with formatted timestamps
    session_list: List[Dict[str, Any]] = []
    for session_data in sessions.values():
        from .renderer import format_timestamp

        first_ts = session_data["first_timestamp"]
        last_ts = session_data["last_timestamp"]
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

        session_dict: Dict[str, Any] = {
            "id": session_data["id"],
            "summary": session_data["summary"],
            "timestamp_range": timestamp_range,
            "message_count": session_data["message_count"],
            "first_user_message": session_data["first_user_message"]
            if session_data["first_user_message"] != ""
            else "[No user message found in session.]",
        }
        session_list.append(session_dict)

    # Sort by first timestamp (ascending order, oldest first like transcript page)
    return sorted(
        session_list, key=lambda s: s.get("timestamp_range", ""), reverse=False
    )


def _generate_individual_session_files(
    messages: List[TranscriptEntry],
    output_dir: Path,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
) -> None:
    """Generate individual HTML files for each session."""
    # Find all unique session IDs
    session_ids: set[str] = set()
    for message in messages:
        if hasattr(message, "sessionId"):
            session_id: str = getattr(message, "sessionId")
            if session_id:
                session_ids.add(session_id)

    # Generate HTML file for each session
    for session_id in session_ids:
        # Create session-specific title
        session_title = f"Session {session_id[:8]}"
        if from_date or to_date:
            date_range_parts: List[str] = []
            if from_date:
                date_range_parts.append(f"from {from_date}")
            if to_date:
                date_range_parts.append(f"to {to_date}")
            date_range_str = " ".join(date_range_parts)
            session_title += f" ({date_range_str})"

        # Generate session HTML
        session_html = generate_session_html(messages, session_id, session_title)

        # Write session file
        session_file_path = output_dir / f"session-{session_id}.html"
        session_file_path.write_text(session_html, encoding="utf-8")


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
            # Generate HTML for this project (including individual session files)
            output_path = convert_jsonl_to_html(
                project_dir, None, from_date, to_date, True
            )

            # Get project info for index
            jsonl_files = list(project_dir.glob("*.jsonl"))
            jsonl_count = len(jsonl_files)
            messages = load_directory_transcripts(project_dir)
            if from_date or to_date:
                messages = filter_messages_by_date(messages, from_date, to_date)

            last_modified: float = (
                max(f.stat().st_mtime for f in jsonl_files) if jsonl_files else 0.0
            )

            # Calculate token usage aggregation and find first/last interaction timestamps
            total_input_tokens = 0
            total_output_tokens = 0
            total_cache_creation_tokens = 0
            total_cache_read_tokens = 0
            latest_timestamp = ""
            earliest_timestamp = ""

            # Track requestIds to avoid double-counting tokens
            seen_request_ids: set[str] = set()

            # Collect session data for this project
            sessions_data = _collect_project_sessions(messages)

            for message in messages:
                # Track latest and earliest timestamps across all messages
                if hasattr(message, "timestamp"):
                    message_timestamp = getattr(message, "timestamp", "")
                    if message_timestamp:
                        # Track latest timestamp
                        if not latest_timestamp or message_timestamp > latest_timestamp:
                            latest_timestamp = message_timestamp

                        # Track earliest timestamp
                        if (
                            not earliest_timestamp
                            or message_timestamp < earliest_timestamp
                        ):
                            earliest_timestamp = message_timestamp

                # Calculate token usage for assistant messages
                if message.type == "assistant" and hasattr(message, "message"):
                    assistant_message = getattr(message, "message")
                    request_id = getattr(message, "requestId", None)

                    if (
                        hasattr(assistant_message, "usage")
                        and assistant_message.usage
                        and request_id
                        and request_id not in seen_request_ids
                    ):
                        # Mark requestId as seen to avoid double-counting
                        seen_request_ids.add(request_id)

                        usage = assistant_message.usage
                        total_input_tokens += usage.input_tokens
                        total_output_tokens += usage.output_tokens
                        if usage.cache_creation_input_tokens:
                            total_cache_creation_tokens += (
                                usage.cache_creation_input_tokens
                            )
                        if usage.cache_read_input_tokens:
                            total_cache_read_tokens += usage.cache_read_input_tokens

            project_summaries.append(
                {
                    "name": project_dir.name,
                    "path": project_dir,
                    "html_file": f"{project_dir.name}/{output_path.name}",
                    "jsonl_count": jsonl_count,
                    "message_count": len(messages),
                    "last_modified": last_modified,
                    "total_input_tokens": total_input_tokens,
                    "total_output_tokens": total_output_tokens,
                    "total_cache_creation_tokens": total_cache_creation_tokens,
                    "total_cache_read_tokens": total_cache_read_tokens,
                    "latest_timestamp": latest_timestamp,
                    "earliest_timestamp": earliest_timestamp,
                    "sessions": sessions_data,
                }
            )
        except Exception as e:
            print(
                f"Warning: Failed to process {project_dir}: {e}\n"
                f"Previous (in alphabetical order) file before error: {project_summaries[-1]}"
                f"\n{traceback.format_exc()}"
            )
            continue

    # Generate index HTML
    index_path = projects_path / "index.html"
    index_html = generate_projects_index_html(project_summaries, from_date, to_date)
    index_path.write_text(index_html, encoding="utf-8")

    return index_path
