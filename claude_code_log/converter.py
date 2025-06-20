#!/usr/bin/env python3
"""Convert Claude transcript JSONL files to HTML."""

from pathlib import Path
import traceback
from typing import List, Optional, Dict, Any

from .parser import (
    load_transcript,
    load_directory_transcripts,
    filter_messages_by_date,
)
from .renderer import (
    generate_html,
    generate_projects_index_html,
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

            # Calculate token usage aggregation and find first/last interaction timestamps
            total_input_tokens = 0
            total_output_tokens = 0
            total_cache_creation_tokens = 0
            total_cache_read_tokens = 0
            latest_timestamp = ""
            earliest_timestamp = ""

            # Track requestIds to avoid double-counting tokens
            seen_request_ids: set[str] = set()

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
