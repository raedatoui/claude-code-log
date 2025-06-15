# Claude Code Log

A Python CLI tool that converts Claude transcript JSONL files into readable HTML format.

## Project Overview

This tool processes Claude Code transcript files (stored as JSONL) and generates clean, minimalist HTML pages with comprehensive session navigation and token usage tracking. It's designed to create a readable log of your Claude interactions with rich metadata and easy navigation.

## Key Features

- **Single File or Directory Processing**: Convert individual JSONL files or entire directories
- **Chronological Ordering**: All messages sorted by timestamp across sessions
- **Session Navigation**: Interactive table of contents with session summaries and quick navigation
- **Token Usage Tracking**: Display token consumption for individual messages and session totals
- **Timestamp Ranges**: Show first-to-last timestamp ranges for each session in navigation
- **Rich Message Types**: Support for user/assistant messages, tool use/results, thinking content, images
- **Date Range Filtering**: Filter messages by date range using natural language (e.g., "today", "yesterday", "last week")
- **Markdown Rendering**: Client-side markdown rendering with syntax highlighting
- **Floating Navigation**: Always-available back-to-top button for easy navigation
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

- `claude_code_log/parser.py` - Data extraction and parsing from JSONL files
- `claude_code_log/renderer.py` - HTML generation and template rendering
- `claude_code_log/converter.py` - High-level conversion orchestration
- `claude_code_log/cli.py` - Command-line interface
- `claude_code_log/models.py` - Pydantic models for transcript data structures
- `claude_code_log/templates/` - Jinja2 HTML templates
  - `transcript.html` - Main transcript viewer template
  - `index.html` - Project directory index template
- `pyproject.toml` - Project configuration with dependencies

## Development

The project uses:

- Python 3.12+
- Click for CLI interface
- Pydantic for data validation and parsing
- Jinja2 for HTML template rendering
- dateparser for natural language date parsing
- Standard library for JSON/HTML processing
- Client-side: marked.js for markdown rendering

## Development Commands

### Testing

Run tests with:

```bash
uv run pytest
```

### Test Coverage

Generate test coverage reports:

```bash
# Run tests with coverage
uv run pytest --cov=claude_code_log --cov-report=html --cov-report=term

# Generate HTML coverage report only
uv run pytest --cov=claude_code_log --cov-report=html

# View coverage in terminal
uv run pytest --cov=claude_code_log --cov-report=term-missing
```

HTML coverage reports are generated in `htmlcov/index.html`.

### Code Quality

- **Format code**: `ruff format`
- **Lint and fix**: `ruff check --fix`
- **Type checking**: `uv run pyright`

### Testing & Style Guide

- **Unit Tests**: See [test/README.md](test/README.md) for comprehensive testing documentation
- **Visual Style Guide**: `uv run python scripts/generate_style_guide.py`
- **Manual Testing**: Use representative test data in `test/test_data/`

Test with Claude transcript JSONL files typically found in `~/.claude/projects/` directories.

## Architecture Notes

### Data Models

The application uses Pydantic models to parse and validate transcript JSON data:

- **TranscriptEntry**: Union of UserTranscriptEntry, AssistantTranscriptEntry, SummaryTranscriptEntry
- **UsageInfo**: Token usage tracking (input_tokens, output_tokens, cache_creation_input_tokens, cache_read_input_tokens)
- **ContentItem**: Union of TextContent, ToolUseContent, ToolResultContent, ThinkingContent, ImageContent

### Template System

Uses Jinja2 templates for HTML generation:

- **Session Navigation**: Generates table of contents with timestamp ranges and token summaries
- **Message Rendering**: Handles different content types with appropriate formatting
- **Token Display**: Shows usage for individual assistant messages and session totals

### Token Usage Features

- **Individual Messages**: Assistant messages display token usage in header
- **Session Aggregation**: ToC shows total tokens consumed per session
- **Format**: "Input: X | Output: Y | Cache Creation: Z | Cache Read: W"
- **Data Source**: Extracted from AssistantMessage.usage field in JSONL

### Session Management

- **Session Detection**: Groups messages by sessionId field
- **Summary Attachment**: Links session summaries via leafUuid -> message UUID -> session ID mapping
- **Timestamp Tracking**: Records first and last timestamp for each session
- **Navigation**: Generates clickable ToC with session previews and metadata
