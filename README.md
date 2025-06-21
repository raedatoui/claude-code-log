# Claude Code Log

A Python CLI tool that converts Claude Code transcript JSONL files into readable HTML format.

[claude_code_log.webm](https://github.com/user-attachments/assets/12d94faf-6901-4429-b4e6-ea5f102d0c1c)

## Project Overview

📋 **[View Changelog](CHANGELOG.md)** - See what's new in each release

This tool generates clean, minimalist HTML pages showing user prompts and assistant responses chronologically. It's designed to create a readable log of your Claude Code interactions with support for both individual files and entire project hierarchies.

[See example log (generated from real usage on this project).](https://daaain.github.io/claude-code-log/claude-code-log-transcript.html)

## Quickstart

TL;DR: run the command below and browse the pages generated from your entire Claude Code archives:

```sh
uvx claude-code-log --open-browser
```

## Key Features

- **Project Hierarchy Processing**: Process entire `~/.claude/projects/` directory with linked index page
- **Single File or Directory Processing**: Convert individual JSONL files or specific directories
- **Chronological Ordering**: All messages sorted by timestamp across sessions
- **Session Demarcation**: Clear visual separators between different transcript sessions
- **Date Range Filtering**: Filter messages by date range using natural language (e.g., "today", "yesterday", "last week")
- **Summary Support**: Display summary messages matched with corresponding sessions
- **System Command Visibility**: Show system commands (like `init`) in expandable details
- **Markdown Rendering**: Automatic markdown rendering in assistant message content
- **Project Navigation**: Master index page with project statistics and quick navigation
- **Space-Efficient Layout**: Compact design optimized for content density
- **CLI Interface**: Simple command-line tool using Click

## Usage

### Default Behavior (Process All Projects)

```bash
# Process all projects in ~/.claude/projects/ (default behavior)
claude-code-log

# Explicitly process all projects
claude-code-log --all-projects

# Process all projects and open in browser
claude-code-log --open-browser

# Process all projects with date filtering
claude-code-log --from-date "yesterday" --to-date "today"
claude-code-log --from-date "last week"
```

This creates:

- `~/.claude/projects/index.html` - Master index with project cards and statistics
- `~/.claude/projects/project-name/combined_transcripts.html` - Individual project pages

### Single File or Directory Processing

```bash
# Single file
claude-code-log transcript.jsonl

# Specific directory
claude-code-log /path/to/transcript/directory

# Custom output location
claude-code-log /path/to/directory -o combined_transcripts.html

# Open in browser after conversion
claude-code-log /path/to/directory --open-browser

# Filter by date range (supports natural language)
claude-code-log /path/to/directory --from-date "yesterday" --to-date "today"
claude-code-log /path/to/directory --from-date "3 days ago" --to-date "yesterday"
```

## File Structure

- `claude_code_log/parser.py` - Data extraction and parsing from JSONL files
- `claude_code_log/renderer.py` - HTML generation and template rendering
- `claude_code_log/converter.py` - High-level conversion orchestration
- `claude_code_log/cli.py` - Command-line interface with project discovery
- `claude_code_log/models.py` - Pydantic models for transcript data structures
- `claude_code_log/templates/` - Jinja2 HTML templates
  - `transcript.html` - Main transcript viewer template
  - `index.html` - Project directory index template
- `pyproject.toml` - Project configuration with dependencies

## Development

The project uses:

- Python 3.12+ with uv package management
- Click for CLI interface and argument parsing
- Pydantic for robust data modeling and validation
- dateparser for natural language date parsing
- Standard library for JSON/HTML processing
- Minimal dependencies for portability
- mistune for quick Markdown rendering

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

**Comprehensive Testing & Style Guide**: The project includes extensive testing infrastructure and visual documentation. See [test/README.md](test/README.md) for details on:

- **Unit Tests**: Template rendering, message type handling, edge cases
- **Test Coverage**: 78%+ coverage across all modules with detailed reporting
- **Visual Style Guide**: Interactive documentation showing all message types
- **Representative Test Data**: Real-world JSONL samples for development
- **Style Guide Generation**: Create visual documentation with `uv run python scripts/generate_style_guide.py`

### Code Quality

- **Format code**: `ruff format`
- **Lint and fix**: `ruff check --fix`
- **Type checking**: `uv run pyright`

### All Commands

- **Test**: `uv run pytest`
- **Test with Coverage**: `uv run pytest --cov=claude_code_log --cov-report=html`
- **Format**: `ruff format`
- **Lint**: `ruff check --fix`
- **Type Check**: `uv run pyright`
- **Generate Style Guide**: `uv run python scripts/generate_style_guide.py`

Test with Claude transcript JSONL files typically found in `~/.claude/projects/` directories.

## Project Hierarchy Output

When processing all projects, the tool generates:

```sh
~/.claude/projects/
├── index.html                    # Master index with project cards
├── project1/
│   └── combined_transcripts.html # Individual project page
├── project2/
│   └── combined_transcripts.html
└── ...
```

### Index Page Features

- **Project Cards**: Each project shown as a clickable card with statistics
- **Summary Statistics**: Total projects, transcript files, and message counts
- **Recent Activity**: Projects sorted by last modification date
- **Quick Navigation**: One-click access to any project's detailed transcript
- **Clean URLs**: Readable project names converted from directory names

## Message Types Supported

- **User Messages**: Regular user inputs and prompts
- **Assistant Messages**: Claude's responses (when not filtered)
- **Summary Messages**: Session summaries with special formatting
- **System Commands**: Commands like `init` shown in expandable details
- **Tool Use**: Tool invocations and results with proper formatting

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
- **Tool Interactions**: Tool use and results displayed in collapsible sections

## Installation

Install using pip:

```bash
pip install claude-code-log
```

Or install from source:

```bash
git clone https://github.com/your-username/claude-code-log.git
cd claude-code-log
uv sync
uv run claude-code-log
```

## TODO

- **In-page Filtering**: Client-side filtering and search
- **Timeline view**: Show interaction on a timeline to get a better idea on timings and parallel calls - maybe Timeline.js optionally generated runtime?
- document what questions does this library help answering
- filter out system message from beginning of convo to prevent from being shown on session navigation instead of user's first prompt
- integrate claude-trace request logs if present?
- use Anthropic's own types: <https://github.com/anthropics/anthropic-sdk-python/tree/main/src/anthropic/types> – can these be used to generate Pydantic classes though?
- Shortcut / command to resume a specific conversation by session ID $ claude --resume 550e8400-e29b-41d4-a716-446655440000?
- Split up transcripts by jsonl files (too) as the combined ones can get quite big and add navigation to the top level
- Localised number formatting and timezone adjustment runtime? For this we'd need to make Jinja template variables more granular
- get `cwd` from logs to be able to render the proper path for titles
- handle `"isSidechain":true` for sub-agent Tasks
- convert images to WebP as screenshots are often huge PNGs – this might be time consuming to keep redoing (so would also need some caching) and need heavy dependencies with compilation (unless there are fast pure Python conversation libraries? Or WASM?)
- add special formatting for built-in tools: Bash, Glob, Grep, LS, exit_plan_mode, Read, Edit, MultiEdit, Write, NotebookRead, NotebookEdit, WebFetch, TodoRead, TodoWrite, WebSearch
