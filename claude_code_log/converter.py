#!/usr/bin/env python3
"""Convert Claude transcript JSONL files to HTML."""

from pathlib import Path
import traceback
from typing import List, Optional, Dict, Any

from .utils import should_use_as_session_starter, extract_init_command_description
from .cache import CacheManager, SessionCacheData, get_library_version
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
    use_cache: bool = True,
) -> Path:
    """Convert JSONL transcript(s) to HTML file(s)."""
    if not input_path.exists():
        raise FileNotFoundError(f"Input path not found: {input_path}")

    # Initialize cache manager for directory mode
    cache_manager = None
    if use_cache and input_path.is_dir():
        try:
            library_version = get_library_version()
            cache_manager = CacheManager(input_path, library_version)
        except Exception as e:
            print(f"Warning: Failed to initialize cache manager: {e}")

    if input_path.is_file():
        # Single file mode - cache only available for directory mode
        if output_path is None:
            output_path = input_path.with_suffix(".html")
        messages = load_transcript(input_path)
        title = f"Claude Transcript - {input_path.stem}"
    else:
        # Directory mode
        if output_path is None:
            output_path = input_path / "combined_transcripts.html"
        messages = load_directory_transcripts(
            input_path, cache_manager, from_date, to_date
        )
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

    # Update cache with session and project data if available
    if cache_manager is not None and input_path.is_dir():
        _update_cache_with_session_data(cache_manager, messages)

    return output_path


def _update_cache_with_session_data(
    cache_manager: CacheManager, messages: List[TranscriptEntry]
) -> None:
    """Update cache with session and project aggregate data."""
    from .parser import extract_text_content

    # Collect session data (similar to _collect_project_sessions but for cache)
    session_summaries: Dict[str, str] = {}
    uuid_to_session: Dict[str, str] = {}
    uuid_to_session_backup: Dict[str, str] = {}

    # Build mapping from message UUID to session ID
    for message in messages:
        if hasattr(message, "uuid") and hasattr(message, "sessionId"):
            message_uuid = getattr(message, "uuid", "")
            session_id = getattr(message, "sessionId", "")
            if message_uuid and session_id:
                if type(message) is AssistantTranscriptEntry:
                    uuid_to_session[message_uuid] = session_id
                else:
                    uuid_to_session_backup[message_uuid] = session_id

    # Map summaries to sessions
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

    # Group messages by session and calculate session data
    sessions_cache_data: Dict[str, SessionCacheData] = {}

    # Track token usage and timestamps for project aggregates
    total_input_tokens = 0
    total_output_tokens = 0
    total_cache_creation_tokens = 0
    total_cache_read_tokens = 0
    total_message_count = len(messages)
    earliest_timestamp = ""
    latest_timestamp = ""
    seen_request_ids: set[str] = set()

    for message in messages:
        # Update project-level timestamp tracking
        if hasattr(message, "timestamp"):
            message_timestamp = getattr(message, "timestamp", "")
            if message_timestamp:
                if not latest_timestamp or message_timestamp > latest_timestamp:
                    latest_timestamp = message_timestamp
                if not earliest_timestamp or message_timestamp < earliest_timestamp:
                    earliest_timestamp = message_timestamp

        # Process session-level data (skip summaries)
        if hasattr(message, "sessionId") and not isinstance(
            message, SummaryTranscriptEntry
        ):
            session_id = getattr(message, "sessionId", "")
            if not session_id:
                continue

            if session_id not in sessions_cache_data:
                sessions_cache_data[session_id] = SessionCacheData(
                    session_id=session_id,
                    summary=session_summaries.get(session_id),
                    first_timestamp=getattr(message, "timestamp", ""),
                    last_timestamp=getattr(message, "timestamp", ""),
                    message_count=0,
                    first_user_message="",
                )

            session_cache = sessions_cache_data[session_id]
            session_cache.message_count += 1
            current_timestamp = getattr(message, "timestamp", "")
            if current_timestamp:
                session_cache.last_timestamp = current_timestamp

            # Get first user message for preview
            if (
                isinstance(message, UserTranscriptEntry)
                and not session_cache.first_user_message
                and hasattr(message, "message")
            ):
                first_user_content = extract_text_content(message.message.content)
                if should_use_as_session_starter(first_user_content):
                    preview_content = extract_init_command_description(
                        first_user_content
                    )
                    session_cache.first_user_message = preview_content[:500]

        # Calculate token usage for assistant messages
        if message.type == "assistant" and hasattr(message, "message"):
            assistant_message = getattr(message, "message")
            request_id = getattr(message, "requestId", None)
            session_id = getattr(message, "sessionId", "")

            if (
                hasattr(assistant_message, "usage")
                and assistant_message.usage
                and request_id
                and request_id not in seen_request_ids
            ):
                seen_request_ids.add(request_id)
                usage = assistant_message.usage

                # Add to project totals
                total_input_tokens += usage.input_tokens or 0
                total_output_tokens += usage.output_tokens or 0
                if usage.cache_creation_input_tokens:
                    total_cache_creation_tokens += usage.cache_creation_input_tokens
                if usage.cache_read_input_tokens:
                    total_cache_read_tokens += usage.cache_read_input_tokens

                # Add to session totals
                if session_id in sessions_cache_data:
                    session_cache = sessions_cache_data[session_id]
                    session_cache.total_input_tokens += usage.input_tokens or 0
                    session_cache.total_output_tokens += usage.output_tokens or 0
                    if usage.cache_creation_input_tokens:
                        session_cache.total_cache_creation_tokens += (
                            usage.cache_creation_input_tokens
                        )
                    if usage.cache_read_input_tokens:
                        session_cache.total_cache_read_tokens += (
                            usage.cache_read_input_tokens
                        )

    # Update cache with session data
    cache_manager.update_session_cache(sessions_cache_data)

    # Update cache with project aggregates
    cache_manager.update_project_aggregates(
        total_message_count=total_message_count,
        total_input_tokens=total_input_tokens,
        total_output_tokens=total_output_tokens,
        total_cache_creation_tokens=total_cache_creation_tokens,
        total_cache_read_tokens=total_cache_read_tokens,
        earliest_timestamp=earliest_timestamp,
        latest_timestamp=latest_timestamp,
    )


def _format_session_timestamp_range(first_timestamp: str, last_timestamp: str) -> str:
    """Format session timestamp range for display."""
    from .renderer import format_timestamp

    if first_timestamp and last_timestamp:
        if first_timestamp == last_timestamp:
            return format_timestamp(first_timestamp)
        else:
            return f"{format_timestamp(first_timestamp)} - {format_timestamp(last_timestamp)}"
    elif first_timestamp:
        return format_timestamp(first_timestamp)
    else:
        return ""


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
                    preview_content = extract_init_command_description(
                        first_user_content
                    )
                    sessions[session_id]["first_user_message"] = preview_content[:500]

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
    use_cache: bool = True,
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

    # Get library version for cache management
    library_version = get_library_version()

    # Process each project directory
    project_summaries: List[Dict[str, Any]] = []
    for project_dir in sorted(project_dirs):
        try:
            # Initialize cache manager for this project
            cache_manager = None
            if use_cache:
                try:
                    cache_manager = CacheManager(project_dir, library_version)
                except Exception as e:
                    print(f"Warning: Failed to initialize cache for {project_dir}: {e}")

            # Check if we can use cached project data
            cached_project_data = None
            if cache_manager is not None:
                cached_project_data = cache_manager.get_cached_project_data()

                # Check if all files are still cached and no date filtering is applied
                if cached_project_data is not None and not from_date and not to_date:
                    jsonl_files = list(project_dir.glob("*.jsonl"))
                    modified_files = cache_manager.get_modified_files(jsonl_files)

                    if not modified_files:
                        # All files are cached, use cached project data
                        print(f"Using cached data for project {project_dir.name}")
                        project_summaries.append(
                            {
                                "name": project_dir.name,
                                "path": project_dir,
                                "html_file": f"{project_dir.name}/combined_transcripts.html",
                                "jsonl_count": len(cached_project_data.cached_files),
                                "message_count": cached_project_data.total_message_count,
                                "last_modified": max(
                                    info.source_mtime
                                    for info in cached_project_data.cached_files.values()
                                )
                                if cached_project_data.cached_files
                                else 0.0,
                                "total_input_tokens": cached_project_data.total_input_tokens,
                                "total_output_tokens": cached_project_data.total_output_tokens,
                                "total_cache_creation_tokens": cached_project_data.total_cache_creation_tokens,
                                "total_cache_read_tokens": cached_project_data.total_cache_read_tokens,
                                "latest_timestamp": cached_project_data.latest_timestamp,
                                "earliest_timestamp": cached_project_data.earliest_timestamp,
                                "sessions": [
                                    {
                                        "id": session_data.session_id,
                                        "summary": session_data.summary,
                                        "timestamp_range": _format_session_timestamp_range(
                                            session_data.first_timestamp,
                                            session_data.last_timestamp,
                                        ),
                                        "message_count": session_data.message_count,
                                        "first_user_message": session_data.first_user_message
                                        or "[No user message found in session.]",
                                    }
                                    for session_data in cached_project_data.sessions.values()
                                ],
                            }
                        )
                        continue

            # Generate HTML for this project (including individual session files)
            output_path = convert_jsonl_to_html(
                project_dir, None, from_date, to_date, True, use_cache
            )

            # Get project info for index - use cached data if available
            jsonl_files = list(project_dir.glob("*.jsonl"))
            jsonl_count = len(jsonl_files)
            last_modified: float = (
                max(f.stat().st_mtime for f in jsonl_files) if jsonl_files else 0.0
            )

            # Try to use cached project data if no date filtering
            if cache_manager is not None and not from_date and not to_date:
                cached_project_data = cache_manager.get_cached_project_data()
                if cached_project_data is not None:
                    # Use cached aggregation data
                    project_summaries.append(
                        {
                            "name": project_dir.name,
                            "path": project_dir,
                            "html_file": f"{project_dir.name}/{output_path.name}",
                            "jsonl_count": jsonl_count,
                            "message_count": cached_project_data.total_message_count,
                            "last_modified": last_modified,
                            "total_input_tokens": cached_project_data.total_input_tokens,
                            "total_output_tokens": cached_project_data.total_output_tokens,
                            "total_cache_creation_tokens": cached_project_data.total_cache_creation_tokens,
                            "total_cache_read_tokens": cached_project_data.total_cache_read_tokens,
                            "latest_timestamp": cached_project_data.latest_timestamp,
                            "earliest_timestamp": cached_project_data.earliest_timestamp,
                            "sessions": [
                                {
                                    "id": session_data.session_id,
                                    "summary": session_data.summary,
                                    "timestamp_range": _format_session_timestamp_range(
                                        session_data.first_timestamp,
                                        session_data.last_timestamp,
                                    ),
                                    "message_count": session_data.message_count,
                                    "first_user_message": session_data.first_user_message
                                    or "[No user message found in session.]",
                                }
                                for session_data in cached_project_data.sessions.values()
                            ],
                        }
                    )
                    continue

            # Fallback: process messages normally (needed when date filtering or cache unavailable)
            messages = load_directory_transcripts(
                project_dir, cache_manager, from_date, to_date
            )
            if from_date or to_date:
                messages = filter_messages_by_date(messages, from_date, to_date)

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
                        total_input_tokens += usage.input_tokens or 0
                        total_output_tokens += usage.output_tokens or 0
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
