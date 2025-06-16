#!/usr/bin/env python3
"""Parse and extract data from Claude transcript JSONL files."""

import json
from pathlib import Path
import traceback
from typing import List, Optional, Union, Dict
from datetime import datetime
import dateparser

from .models import (
    TranscriptEntry,
    SummaryTranscriptEntry,
    parse_transcript_entry,
    ContentItem,
    TextContent,
    ThinkingContent,
)


def extract_text_content(content: Union[str, List[ContentItem]]) -> str:
    """Extract text content from Claude message content structure."""
    if isinstance(content, list):
        text_parts: List[str] = []
        for item in content:
            if isinstance(item, TextContent):
                text_parts.append(item.text)
            elif isinstance(item, ThinkingContent):
                # Skip thinking content in main text extraction
                continue
        return "\n".join(text_parts)
    else:
        return str(content) if content else ""


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
    unique_errors: Dict[str, int] = {}
    unhandled_types: Dict[str, int] = {}

    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entry_dict = json.loads(line)
                    entry_type = entry_dict.get("type", "unknown, missing type")

                    if entry_type in ["user", "assistant", "summary"]:
                        # Parse using Pydantic models
                        entry = parse_transcript_entry(entry_dict)
                        messages.append(entry)
                    else:
                        # Track unhandled message types
                        unhandled_types[entry_type] = (
                            unhandled_types.get(entry_type, 0) + 1
                        )
                except json.JSONDecodeError as e:
                    error_key = f"JSON decode error: {str(e)}"
                    unique_errors[error_key] = unique_errors.get(error_key, 0) + 1
                except ValueError as e:
                    # Extract a more descriptive error message
                    error_msg = str(e)
                    if "validation error" in error_msg.lower():
                        error_key = f"Validation error: {str(e)[:200]}..."
                    else:
                        error_key = f"ValueError: {error_msg[:200]}..."
                    unique_errors[error_key] = unique_errors.get(error_key, 0) + 1
                except Exception as e:
                    error_key = f"Unexpected error: {str(e)}\n{traceback.format_exc()}"
                    unique_errors[error_key] = unique_errors.get(error_key, 0) + 1

    # Print summary of errors if any occurred
    if unique_errors or unhandled_types:
        print(f"\nParsing summary for {jsonl_path.name}:")
        if unhandled_types:
            print("Unhandled message types:")
            for msg_type, count in unhandled_types.items():
                print(f"  - {msg_type}: {count} occurrences")
        if unique_errors:
            print("Parsing errors:")
            for error, count in unique_errors.items():
                print(f"  - {error}: {count} occurrences")
        print()

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
