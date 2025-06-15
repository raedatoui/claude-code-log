# Claude Code Log Testing & Style Guide

This directory contains comprehensive testing infrastructure and visual documentation for the Claude Code Log template system.

## Test Data (`test_data/`)

Representative JSONL files covering all message types and edge cases:

**Note**: After the module split, import paths have changed:
- `from claude_code_log.parser import load_transcript, extract_text_content`
- `from claude_code_log.renderer import generate_html, format_timestamp`
- `from claude_code_log.converter import convert_jsonl_to_html`

### `representative_messages.jsonl`
A comprehensive conversation demonstrating:
- User and assistant messages
- Tool use and tool results (success cases)
- Markdown formatting and code blocks
- Summary messages
- Multiple message interactions

### `edge_cases.jsonl`
Edge cases and special scenarios:
- Complex markdown formatting
- Very long text content
- Tool errors and error handling
- System command messages
- Command output parsing
- Special characters and Unicode
- HTML escaping scenarios

### `session_b.jsonl`
Additional session for testing multi-session handling:
- Different source file content
- Session divider behavior
- Cross-session message ordering

## Template Tests (`test_template_rendering.py`)

Comprehensive unit tests that verify:

### Core Functionality
- ✅ Basic HTML structure generation
- ✅ All message types render correctly
- ✅ Session divider logic (only first session shown)
- ✅ Multi-session content combining
- ✅ Empty file handling

### Message Type Coverage
- ✅ User messages with markdown
- ✅ Assistant responses
- ✅ Tool use and tool results
- ✅ Error handling for failed tools
- ✅ System command messages
- ✅ Command output parsing
- ✅ Summary messages

### Formatting & Safety
- ✅ Timestamp formatting
- ✅ CSS class application
- ✅ HTML escaping for security
- ✅ Unicode and special character support
- ✅ JavaScript markdown setup

### Template Systems
- ✅ Transcript template (individual conversations)
- ✅ Index template (project listings)
- ✅ Project summary statistics
- ✅ Date range filtering display

## Visual Style Guide (`../scripts/generate_style_guide.py`)

Generates comprehensive visual documentation:

### Generated Files
- **Main Index** (`index.html`) - Overview and navigation
- **Transcript Guide** (`transcript_style_guide.html`) - All message types
- **Index Guide** (`index_style_guide.html`) - Project listing examples

### Coverage
The style guide demonstrates:
- 📝 **Message Types**: User, assistant, system, summary
- 🛠️ **Tool Interactions**: Usage, results, errors
- 📏 **Text Handling**: Long content, wrapping, formatting
- 🌍 **Unicode Support**: Special characters, emojis, international text
- ⚙️ **System Messages**: Commands, outputs, parsing
- 🎨 **Visual Design**: Typography, colors, spacing, responsive layout

### Usage
```bash
# Generate style guides
uv run python scripts/generate_style_guide.py

# Open in browser
open scripts/style_guide_output/index.html
```

## Running Tests

### Unit Tests
```bash
# Run all tests
uv run pytest -v

# Run all template tests
uv run pytest test/test_template_rendering.py -v

# Run specific test
uv run pytest test/test_template_rendering.py::TestTemplateRendering::test_representative_messages_render -v

# Run tests with coverage
uv run pytest --cov=claude_code_log --cov-report=term-missing -v
```

### Test Coverage

Generate detailed coverage reports:

```bash
# Run tests with coverage and HTML report
uv run pytest --cov=claude_code_log --cov-report=html --cov-report=term

# View coverage by module
uv run pytest --cov=claude_code_log --cov-report=term-missing

# Open HTML coverage report
open htmlcov/index.html
```

Current coverage: **78%+** across all modules:
- `parser.py`: 81% - Data extraction and parsing
- `renderer.py`: 86% - HTML generation and formatting  
- `converter.py`: 52% - High-level orchestration
- `models.py`: 89% - Pydantic data models

### Manual Testing
```bash
# Test with representative data
uv run python -c "
from claude_code_log.converter import convert_jsonl_to_html
from pathlib import Path
html_file = convert_jsonl_to_html(Path('test/test_data/representative_messages.jsonl'))
print(f'Generated: {html_file}')
"

# Test multi-session handling
uv run python -c "
from claude_code_log.converter import convert_jsonl_to_html
from pathlib import Path
html_file = convert_jsonl_to_html(Path('test/test_data/'))
print(f'Generated: {html_file}')
"
```

## Development Workflow

When modifying templates:

1. **Make Changes** to `claude_code_log/templates/`
2. **Run Tests** to verify functionality
3. **Generate Style Guide** to check visual output
4. **Review in Browser** to ensure design consistency

## File Structure

```
test/
├── README.md                     # This file
├── test_data/                    # Representative JSONL samples
│   ├── representative_messages.jsonl
│   ├── edge_cases.jsonl
│   └── session_b.jsonl
├── test_template_rendering.py    # Template rendering tests
├── test_template_data.py         # Template data structure tests
├── test_template_utils.py        # Utility function tests
├── test_message_filtering.py     # Message filtering tests
├── test_date_filtering.py        # Date filtering tests
└── test_*.py                     # Additional test modules

scripts/
├── generate_style_guide.py       # Visual documentation generator
└── style_guide_output/           # Generated style guides
    ├── index.html
    ├── transcript_style_guide.html
    └── index_style_guide.html

htmlcov/                          # Coverage reports
├── index.html                    # Main coverage report
└── *.html                        # Per-module coverage details
```

## Benefits

This testing infrastructure provides:

- **Regression Prevention**: Catch template breaking changes
- **Coverage Tracking**: 78%+ test coverage with detailed reporting
- **Module Testing**: Focused tests for parser, renderer, and converter modules
- **Visual Documentation**: See how all message types render
- **Development Reference**: Example data for testing new features
- **Quality Assurance**: Verify edge cases and error handling
- **Design Consistency**: Maintain visual standards across updates

The combination of unit tests, coverage tracking, and visual style guides ensures both functional correctness and design quality across the modular codebase.