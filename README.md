# Claude Logbook

A Python CLI tool that converts Claude transcript JSONL files into readable HTML format.

## Project Overview

This tool processes Claude Code transcript files (stored as JSONL) and generates clean, minimalist HTML pages showing user prompts chronologically. It's designed to create a readable log of your Claude interactions.

## Key Features

- **Single File or Directory Processing**: Convert individual JSONL files or entire directories
- **Chronological Ordering**: All messages sorted by timestamp across sessions
- **Session Demarcation**: Clear visual separators between different transcript sessions
- **User-Focused**: Shows only user messages by default (assistant responses filtered out)
- **Date Range Filtering**: Filter messages by date range using natural language (e.g., "today", "yesterday", "last week")
- **Summary Support**: Display summary messages with highlighted formatting
- **System Command Visibility**: Show system commands (like `init`) in expandable details
- **Markdown Rendering**: Automatic markdown rendering in message content using marked.js
- **Space-Efficient Layout**: Compact design optimized for content density
- **CLI Interface**: Simple command-line tool using Click

## Usage

```bash
# Single file
claude-logbook transcript.jsonl

# Entire directory
claude-logbook /path/to/transcript/directory

# Custom output location
claude-logbook /path/to/directory -o combined_transcripts.html

# Open in browser after conversion
claude-logbook /path/to/directory --open-browser

# Filter by date range (supports natural language)
claude-logbook /path/to/directory --from-date "yesterday" --to-date "today"
claude-logbook /path/to/directory --from-date "last week"
claude-logbook /path/to/directory --from-date "3 days ago" --to-date "yesterday"
```

## File Structure

- `claude_logbook/converter.py` - Core conversion logic
- `claude_logbook/cli.py` - Command-line interface
- `pyproject.toml` - Project configuration with Click dependency

## Development

The project uses:

- Python 3.12+ with uv
- Click for CLI
- dateparser for natural language date parsing
- Standard library for JSON/HTML processing
- Minimal dependencies for portability
- marked.js (CDN) for client-side markdown rendering

## Testing

Run tests with:

```bash
python test_converter.py
python test_new_features.py
python test_date_filtering.py
python test_filtering.py
python test_path_conversion.py
```

Test with Claude transcript JSONL files typically found in `~/.claude/projects/` directories.

## Message Types Supported

- **User Messages**: Regular user inputs and prompts
- **Assistant Messages**: Claude's responses (when not filtered)
- **Summary Messages**: Session summaries with special formatting
- **System Commands**: Commands like `init` shown in expandable details

## HTML Output Features

- **Responsive Design**: Works on desktop and mobile
- **Syntax Highlighting**: Code blocks properly formatted
- **Markdown Support**: Full markdown rendering including:
  - Headers, lists, emphasis
  - Code blocks and inline code
  - Links and images
  - GitHub Flavored Markdown features
- **Session Navigation**: Clear visual breaks between transcript sessions
- **Command Visibility**: System commands shown with context but not cluttering the main view

## TODO

- Rename from claude-logbook to claude-code-log
- Escape HTML / XML tags in messages so they get rendered properly
- Process entire `~/.claude/projects/` hierarchy and render as multiple linked HTML files as CLI tool default
- Migrate to Pytest
- Add linting with Ruff and pyright
- Github Action CI
- Move HTML template into a separate file (use Jinja or similar)
- Tool use rendering
- Metadata rendering (timestamps, durations, token use, etc)
- Navigation between sessions within page
- In page filtering
- Push to PyPi with secure token
