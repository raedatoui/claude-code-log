#!/usr/bin/env python3
"""CLI interface for claude-logbook."""

import sys
from pathlib import Path
from typing import Optional

import click

from .converter import convert_jsonl_to_html


@click.command()
@click.argument('input_path', type=click.Path(exists=True, path_type=Path))
@click.option(
    '-o', '--output', 
    type=click.Path(path_type=Path),
    help='Output HTML file path (default: input file with .html extension or combined_transcripts.html for directories)'
)
@click.option(
    '--open-browser', 
    is_flag=True,
    help='Open the generated HTML file in the default browser'
)
def main(input_path: Path, output: Optional[Path], open_browser: bool) -> None:
    """Convert Claude transcript JSONL files to HTML.
    
    INPUT_PATH: Path to a Claude transcript JSONL file or directory containing JSONL files
    """
    try:
        output_path = convert_jsonl_to_html(input_path, output)
        if input_path.is_file():
            click.echo(f"Successfully converted {input_path} to {output_path}")
        else:
            jsonl_count = len(list(input_path.glob("*.jsonl")))
            click.echo(f"Successfully combined {jsonl_count} transcript files from {input_path} to {output_path}")
        
        if open_browser:
            click.launch(str(output_path))
            
    except FileNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error converting file: {e}", err=True)
        sys.exit(1)


if __name__ == '__main__':
    main()