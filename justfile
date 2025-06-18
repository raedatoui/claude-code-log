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

# Release a new version - e.g. `just release-prep 0.2.5`
release-prep version:
    #!/usr/bin/env bash
    set -euo pipefail
    
    echo "🚀 Starting release process for version {{version}}"
    
    if [[ -n $(git status --porcelain) ]]; then
        echo "❌ Error: There are uncommitted changes. Please commit or stash them first."
        git status --short
        exit 1
    fi
    
    echo "✅ Git working directory is clean"
    
    echo "📝 Updating version in pyproject.toml to {{version}}"
    sed -i '' 's/^version = ".*"/version = "{{version}}"/' pyproject.toml
    
    echo "🔄 Running uv sync to update lock file"
    uv sync
    
    LAST_TAG=$(git tag --sort=-version:refname | head -n 1 || echo "")
    echo "📋 Generating changelog from tag $LAST_TAG to HEAD"
    COMMIT_RANGE="$LAST_TAG..HEAD"
    
    echo "📝 Updating CHANGELOG.md"
    TEMP_CHANGELOG=$(mktemp)
    NEW_ENTRY=$(mktemp)
    
    # Create the new changelog entry
    {
        echo "## [{{version}}] - $(date +%Y-%m-%d)"
        echo ""
        echo "### Changed"
        echo ""
        
        # Add commit messages since last tag
        if [[ -n "$COMMIT_RANGE" ]]; then
            git log --pretty=format:"- %s" "$COMMIT_RANGE" | sed 's/^- /- **/' | sed 's/$/**/' || true
        else
            git log --pretty=format:"- %s" | sed 's/^- /- **/' | sed 's/$/**/' || true
        fi
        echo ""
    } > "$NEW_ENTRY"
    
    # Insert new entry after the header (after line 7)
    {
        head -n 7 CHANGELOG.md
        echo ""
        cat "$NEW_ENTRY"
        echo ""
        tail -n +8 CHANGELOG.md
    } > "$TEMP_CHANGELOG"
    
    mv "$TEMP_CHANGELOG" CHANGELOG.md
    rm "$NEW_ENTRY"
    
    echo "💾 Committing version bump and changelog"
    git add pyproject.toml uv.lock CHANGELOG.md
    git commit -m "Release {{version}}"
    
    echo "🏷️  Creating tag {{version}}"
    git tag "{{version}}" -m "Release {{version}}"
    
    echo "🎉 Release {{version}} created successfully!"
    echo "📦 You can now run 'just release-push' to publish to PyPI"

release-push:
    #!/usr/bin/env bash
    set -euo pipefail

    LAST_TAG=$(git tag --sort=-version:refname | head -n 1 || echo "")
    
    echo "📦 Build and publish package $LAST_TAG"
    just build
    just publish

    echo "⬆️  Pushing commit to origin"
    git push origin main

    echo "🏷️  Pushing tag $LAST_TAG"
    git push origin $LAST_TAG

copy-example:
    rsync ~/.claude/projects/-Users-dain-workspace-claude-code-log/combined_transcripts.html ./docs/claude-code-log-transcript.html

regen-all: render-test-data style-guide gen copy-example