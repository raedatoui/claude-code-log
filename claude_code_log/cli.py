#!/usr/bin/env python3
"""CLI interface for claude-code-log."""

import sys
from pathlib import Path
from typing import Optional

import click

from .converter import convert_jsonl_to_html, process_projects_hierarchy


def convert_project_path_to_claude_dir(input_path: Path) -> Path:
    """Convert a project path to the corresponding directory in ~/.claude/projects/."""
    # Get the real path to resolve any symlinks
    real_path = input_path.resolve()

    # Convert the path to the expected format: replace slashes with hyphens
    path_parts = real_path.parts
    if path_parts[0] == "/":
        path_parts = path_parts[1:]  # Remove leading slash

    # Join with hyphens instead of slashes, prepend with dash
    claude_project_name = "-" + "-".join(path_parts)

    # Construct the path in ~/.claude/projects/
    claude_projects_dir = Path.home() / ".claude" / "projects" / claude_project_name

    return claude_projects_dir


@click.command()
@click.argument("input_path", type=click.Path(path_type=Path), required=False)
@click.option(
    "-o",
    "--output",
    type=click.Path(path_type=Path),
    help="Output HTML file path (default: input file with .html extension or combined_transcripts.html for directories)",
)
@click.option(
    "--open-browser",
    is_flag=True,
    help="Open the generated HTML file in the default browser",
)
@click.option(
    "--from-date",
    type=str,
    help='Filter messages from this date/time (e.g., "2 hours ago", "yesterday", "2025-06-08")',
)
@click.option(
    "--to-date",
    type=str,
    help='Filter messages up to this date/time (e.g., "1 hour ago", "today", "2025-06-08 15:00")',
)
@click.option(
    "--all-projects",
    is_flag=True,
    help="Process all projects in ~/.claude/projects/ hierarchy and create linked HTML files",
)
def main(
    input_path: Optional[Path],
    output: Optional[Path],
    open_browser: bool,
    from_date: Optional[str],
    to_date: Optional[str],
    all_projects: bool,
) -> None:
    """Convert Claude transcript JSONL files to HTML.

    INPUT_PATH: Path to a Claude transcript JSONL file, directory containing JSONL files, or project path to convert. If not provided, defaults to ~/.claude/projects/ and --all-projects is used.
    """
    try:
        # Handle default case - process all projects hierarchy if no input path and --all-projects flag
        if input_path is None:
            input_path = Path.home() / ".claude" / "projects"
            all_projects = True

        # Handle --all-projects flag or default behavior
        if all_projects:
            if not input_path.exists():
                raise FileNotFoundError(f"Projects directory not found: {input_path}")

            click.echo(f"Processing all projects in {input_path}...")
            output_path = process_projects_hierarchy(input_path, from_date, to_date)

            # Count processed projects
            project_count = len(
                [
                    d
                    for d in input_path.iterdir()
                    if d.is_dir() and list(d.glob("*.jsonl"))
                ]
            )
            click.echo(
                f"Successfully processed {project_count} projects and created index at {output_path}"
            )

            if open_browser:
                click.launch(str(output_path))
            return

        # Original single file/directory processing logic
        should_convert = False

        if not input_path.exists():
            # Path doesn't exist, try conversion
            should_convert = True
        elif input_path.is_dir():
            # Path exists and is a directory, check if it has JSONL files
            jsonl_files = list(input_path.glob("*.jsonl"))
            if len(jsonl_files) == 0:
                # No JSONL files found, try conversion
                should_convert = True

        if should_convert:
            claude_path = convert_project_path_to_claude_dir(input_path)
            if claude_path.exists():
                click.echo(f"Converting project path {input_path} to {claude_path}")
                input_path = claude_path
            elif not input_path.exists():
                # Original path doesn't exist and conversion failed
                raise FileNotFoundError(
                    f"Neither {input_path} nor {claude_path} exists"
                )

        output_path = convert_jsonl_to_html(input_path, output, from_date, to_date)
        if input_path.is_file():
            click.echo(f"Successfully converted {input_path} to {output_path}")
        else:
            jsonl_count = len(list(input_path.glob("*.jsonl")))
            click.echo(
                f"Successfully combined {jsonl_count} transcript files from {input_path} to {output_path}"
            )

        if open_browser:
            click.launch(str(output_path))

    except FileNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error converting file: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
