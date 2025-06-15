# Claude Code Log

A Python CLI tool that converts Claude transcript JSONL files into readable HTML format.

## Project Overview

This tool processes Claude Code transcript files (stored as JSONL) and generates clean, minimalist HTML pages showing user prompts chronologically. It's designed to create a readable log of your Claude interactions with support for both individual files and entire project hierarchies.

## Key Features

- **Project Hierarchy Processing**: Process entire `~/.claude/projects/` directory with linked index page
- **Single File or Directory Processing**: Convert individual JSONL files or specific directories
- **Chronological Ordering**: All messages sorted by timestamp across sessions
- **Session Demarcation**: Clear visual separators between different transcript sessions
- **User-Focused**: Shows only user messages by default (assistant responses filtered out)
- **Date Range Filtering**: Filter messages by date range using natural language (e.g., "today", "yesterday", "last week")
- **Summary Support**: Display summary messages with highlighted formatting
- **System Command Visibility**: Show system commands (like `init`) in expandable details
- **Markdown Rendering**: Automatic markdown rendering in message content using marked.js
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

- `claude_code_log/converter.py` - Core conversion logic and hierarchy processing
- `claude_code_log/cli.py` - Command-line interface with project discovery
- `claude_code_log/models.py` - Pydantic models for transcript parsing
- `pyproject.toml` - Project configuration with dependencies

## Development

The project uses:

- Python 3.12+ with uv package management
- Click for CLI interface and argument parsing
- Pydantic for robust data modeling and validation
- dateparser for natural language date parsing
- Standard library for JSON/HTML processing
- Minimal dependencies for portability
- marked.js (CDN) for client-side markdown rendering

## Development Commands

### Testing

Run tests with:

```bash
uv run pytest
```

**Comprehensive Testing & Style Guide**: The project includes extensive testing infrastructure and visual documentation. See [test/README.md](test/README.md) for details on:

- **Unit Tests**: Template rendering, message type handling, edge cases
- **Visual Style Guide**: Interactive documentation showing all message types
- **Representative Test Data**: Real-world JSONL samples for development
- **Style Guide Generation**: Create visual documentation with `uv run python scripts/generate_style_guide.py`

### Code Quality

- **Format code**: `ruff format`
- **Lint and fix**: `ruff check --fix`
- **Type checking**: `uv run pyright`

### All Commands

- **Test**: `uv run pytest`
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

Install using pip (coming soon to PyPI):

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

- ✅ **Project Hierarchy Processing**: Process entire `~/.claude/projects/` with linked navigation
- ✅ **Master Index Page**: Project cards with statistics and quick navigation
- **Enhanced UI**: Make it look even nicer with improved styling
- **GitHub Action CI**: Automated testing and deployment
- ✅ **Template Refactoring**: Move HTML templates into separate files (use Jinja or similar)
- Handle thinking tokens
- Handle pasted images (and text?)
- **Tool Use Preview**: Show first few lines of tool use and other collapsed details
- **Rich Metadata**: Render timestamps, durations, token usage, etc.
- **Session Navigation**: Navigation between sessions within page
- **In-page Filtering**: Client-side filtering and search
- **PyPI Publishing**: Push to PyPI with secure token
- **TodoWrite Rendering**: Render TodoWrite as actual todo list with checkboxes
