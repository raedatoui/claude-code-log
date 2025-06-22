# Changelog

All notable changes to claude-code-log will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).


## [0.2.8] - 2025-06-23

### Changed

- **Implement filtering by message type in transcripts**


## [0.2.7] - 2025-06-21

### Changed

- **Unwrap messages to not have double boxes**


## [0.2.6] - 2025-06-20

### Changed

- **Token usage stats and usage time intervals on top level index page + make time consistently UTC**
- **Fix example transcript link + exclude dirs from package**


## [0.2.5] - 2025-06-18

### Changed

- **Tiny Justfile fixes**
- **Create docs.yml**
- **Improve expandable details handling + open/close all button + just render short ones + add example**
- **Remove unnecessary line in error message**
- **Script release process**

## [0.2.4] - 2025-06-18

### Changed

- **More error handling**: Add better error reporting with line numbers and render fallbacks

## [0.2.3] - 2025-06-16

### Changed

- **Error handling**: Add more detailed error handling

## [0.2.2] - 2025-06-16

### Changed

- **Static Markdown**: Render Markdown in Python to make it easier to test and not require Javascipt
- **Visual Design**: Make it nicer to look at

## [0.2.1] - 2025-06-15

### Added

- **Table of Contents & Session Navigation**: Added comprehensive session navigation system
  - Interactive table of contents with session summaries and quick navigation
  - Timestamp ranges showing first-to-last timestamp for each session
  - Session-based organization with clickable navigation links
  - Floating "back to top" button for easy navigation

- **Token Usage Tracking**: Complete token consumption display and tracking
  - Individual assistant messages show token usage in headers
  - Session-level token aggregation in table of contents
  - Detailed breakdown: Input, Output, Cache Creation, Cache Read tokens
  - Data extracted from AssistantMessage.usage field in JSONL files

- **Enhanced Content Support**: Expanded message type and content handling
  - **Tool Use Rendering**: Proper display of tool invocations and results
  - **Thinking Content**: Support for Claude's internal thinking processes
  - **Image Handling**: Display of pasted images in transcript conversations
  - **Todo List Rendering**: Support for structured todo lists in messages

- **Project Hierarchy Processing**: Complete project management system
  - Process entire `~/.claude/projects/` directory by default
  - Master index page with project cards and statistics
  - Linked navigation between index and individual project pages
  - Project statistics including file counts and recent activity

- **Improved User Experience**: Enhanced interface and navigation
  - Chronological ordering of all messages across sessions
  - Session demarcation with clear visual separators
  - Always-visible scroll-to-top button
  - Space-efficient, content-dense layout design

### Changed

- **Default Behavior**: Changed default mode to process all projects instead of requiring explicit input
  - `claude-code-log` now processes `~/.claude/projects/` by default
  - Added `--all-projects` flag for explicit project processing
  - Maintained backward compatibility for single file/directory processing

- **Output Structure**: Restructured HTML output for better organization
  - Session-based navigation replaces simple chronological listing
  - Enhanced template system with comprehensive session metadata
  - Improved visual hierarchy with table of contents integration

- **Data Models**: Expanded Pydantic models for richer data representation
  - Enhanced TranscriptEntry with proper content type handling
  - Added UsageInfo model for token usage tracking
  - Improved ContentItem unions for diverse content types

### Technical

- **Template System**: Major improvements to Jinja2 template architecture
  - New session navigation template components
  - Token usage display templates
  - Enhanced message rendering with rich content support
  - Responsive design improvements

- **Testing Infrastructure**: Comprehensive test coverage expansion
  - Increased test coverage to 78%+ across all modules
  - Added visual style guide generation
  - Representative test data based on real transcript files
  - Extensive test documentation in test/README.md

- **Code Quality**: Significant refactoring and quality improvements
  - Complete Pydantic migration with proper error handling
  - Improved type hints and function documentation
  - Enhanced CLI interface with better argument parsing
  - Comprehensive linting and formatting standards

### Fixed

- **Data Processing**: Improved robustness of transcript processing
  - Better handling of malformed or incomplete JSONL entries
  - More reliable session detection and grouping
  - Enhanced error handling for edge cases in data parsing
  - Fixed HTML escaping issues in message content

- **Template Rendering**: Resolved template and rendering issues
  - Fixed session summary attachment logic
  - Improved timestamp handling and formatting
  - Better handling of mixed content types in templates
  - Resolved CSS and styling inconsistencies

## [0.1.0]

### Added

- **Summary Message Support**: Added support for `summary` type messages in JSONL transcripts
  - Summary messages are displayed with green styling and "Summary:" prefix
  - Includes special CSS class `.summary` for custom styling
  
- **System Command Visibility**: System commands (like `init`) are now shown instead of being filtered out
  - Commands appear in expandable `<details>` elements
  - Shows command name in the summary (e.g., "Command: init")
  - Full command content is revealed when expanded
  - Uses orange styling with `.system` CSS class
  
- **Markdown Rendering Support**: Automatic client-side markdown rendering
  - Uses marked.js ESM module loaded from CDN
  - Supports GitHub Flavored Markdown (GFM)
  - Renders headers, emphasis, code blocks, lists, links, and images
  - Preserves existing HTML content when present
  
- **Enhanced CSS Styling**: New styles for better visual organization
  - Added styles for `.summary` messages (green theme)
  - Added styles for `.system` messages (orange theme)  
  - Added styles for `<details>` elements with proper spacing and cursor behavior
  - Improved overall visual hierarchy

### Changed

- **System Message Filtering**: Modified system message handling logic
  - System messages with `<command-name>` tags are no longer filtered out
  - Added `extract_command_name()` function to parse command names
  - Updated `is_system_message()` function to handle command messages differently
  - Other system messages (stdout, caveats) are still filtered as before

- **Message Type Support**: Extended message type handling in `load_transcript()`
  - Now accepts `"summary"` type in addition to `"user"` and `"assistant"`
  - Updated message processing logic to handle different content structures

### Technical

- **Dependencies**: No new Python dependencies added
  - marked.js is loaded via CDN for client-side rendering
  - Maintains existing minimal dependency approach
  
- **Testing**: Added comprehensive test coverage
  - New test file `test_new_features.py` with tests for:
    - Summary message type support
    - System command message handling  
    - Markdown script inclusion
    - System message filtering behavior
  - Tests use anonymized fixtures based on real transcript data

- **Code Quality**: Improved type hints and function documentation
  - Added proper docstrings for new functions
  - Enhanced error handling for edge cases
  - Maintained backward compatibility with existing functionality

### Fixed

- **Message Processing**: Improved robustness of message content extraction
  - Better handling of mixed content types in transcript files
  - More reliable text extraction from complex message structures

## Previous Versions

Earlier versions focused on basic JSONL to HTML conversion with session demarcation and date filtering capabilities.
