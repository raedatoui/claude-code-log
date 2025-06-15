# Default is to list commands
default:
  @just --list

gen:
    uv run claude-code-log

test:
    uv run pytest

format:
    uv run ruff format

lint:
    uv run ruff check --fix

typecheck:
    uv run pyright

build:
    uv build

publish:
    uv publish