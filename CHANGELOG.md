# Changelog

All notable changes to claude-code-log will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
