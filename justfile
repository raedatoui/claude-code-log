# Default is to list commands
default:
  @just --list

gen:
    uv run claude-code-log

test:
    uv run pytest

test-cov:
    uv run pytest --cov=claude_code_log --cov-report=xml --cov-report=html --cov-report=term

format:
    uv run ruff format

lint:
    uv run ruff check --fix

typecheck:
    uv run pyright

ci: format test lint typecheck 

build:
    rm dist/*
    uv build

publish:
    uv publish

# Render all test data to HTML for visual testing
render-test-data:
    #!/usr/bin/env bash
    echo "🔄 Rendering test data files..."
    
    # Create output directory for rendered test data
    mkdir -p test_output
    
    # Find all .jsonl files in test/test_data directory
    find test/test_data -name "*.jsonl" -type f | while read -r jsonl_file; do
        filename=$(basename "$jsonl_file" .jsonl)
        echo "  📄 Rendering: $filename.jsonl"
        
        # Generate HTML output
        uv run claude-code-log "$jsonl_file" -o "test_output/${filename}.html"
        
        if [ $? -eq 0 ]; then
            echo "  ✅ Created: test_output/${filename}.html"
        else
            echo "  ❌ Failed to render: $filename.jsonl"
        fi
    done
    
    echo "🎉 Test data rendering complete! Check test_output/ directory"
    echo "💡 Open HTML files in browser to review output"

style-guide:
    uv run python scripts/generate_style_guide.py