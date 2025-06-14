# Claude Code Log

A Python CLI tool that converts Claude transcript JSONL files into readable HTML format.

## Project Overview

This tool processes Claude Code transcript files (stored as JSONL) and generates clean, minimalist HTML pages showing user prompts chronologically. It's designed to create a readable log of your Claude interactions.

## Key Features

- **Single File or Directory Processing**: Convert individual JSONL files or entire directories
- **Chronological Ordering**: All messages sorted by timestamp across sessions
- **Session Demarcation**: Clear visual separators between different transcript sessions
- **User-Focused**: Shows only user messages by default (assistant responses filtered out)
- **Date Range Filtering**: Filter messages by date range using natural language (e.g., "today", "yesterday", "last week")
- **Space-Efficient Layout**: Compact design optimized for content density
- **CLI Interface**: Simple command-line tool using Click

## Usage

```bash
# Single file
claude-code-log transcript.jsonl

# Entire directory
claude-code-log /path/to/transcript/directory

# Custom output location
claude-code-log /path/to/directory -o combined_transcripts.html

# Open in browser after conversion
claude-code-log /path/to/directory --open-browser

# Filter by date range (supports natural language)
claude-code-log /path/to/directory --from-date "yesterday" --to-date "today"
claude-code-log /path/to/directory --from-date "last week"
claude-code-log /path/to/directory --to-date "2025-06-01"
claude-code-log /path/to/directory --from-date "3 days ago" --to-date "yesterday"
```

## File Structure

- `claude_code_log/converter.py` - Core conversion logic
- `claude_code_log/cli.py` - Command-line interface
- `pyproject.toml` - Project configuration with Click dependency

## Development

The project uses:

- Python 3.12+
- Click for CLI
- dateparser for natural language date parsing
- Standard library for JSON/HTML processing

## Development Commands

### Testing

Run tests with:

```bash
uv run pytest
```

### Code Quality

- **Format code**: `ruff format`
- **Lint and fix**: `ruff check --fix`
- **Type checking**: `uv run pyright`

### Testing & Style Guide

- **Unit Tests**: See [test/README.md](test/README.md) for comprehensive testing documentation
- **Visual Style Guide**: `uv run python scripts/generate_style_guide.py`
- **Manual Testing**: Use representative test data in `test/test_data/`

Test with Claude transcript JSONL files typically found in `~/.claude/projects/` directories.
