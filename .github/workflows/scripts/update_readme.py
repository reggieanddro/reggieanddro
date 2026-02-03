#!/usr/bin/env python3
"""
README Updater - Daily README Auto-Update
==========================================
Updates README.md with generated statistics between markers.

Usage:
    python update_readme.py --markdown "..." --readme README.md
    echo "markdown content" | python update_readme.py --readme README.md

Markers:
    <!-- STATS_START -->
    <!-- STATS_END -->

Author: Jesse Niesen / Liv Hana SI
Version: 1.0.0
"""

import os
import sys
import re
import argparse
import logging
from typing import Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Marker patterns
START_MARKER = "<!-- STATS_START -->"
END_MARKER = "<!-- STATS_END -->"
MARKER_PATTERN = re.compile(
    rf"{re.escape(START_MARKER)}.*?{re.escape(END_MARKER)}",
    re.DOTALL
)


def read_readme(path: str) -> str:
    """
    Read the README file content.

    Args:
        path: Path to README file

    Returns:
        File content as string

    Raises:
        FileNotFoundError: If file doesn't exist
        IOError: If file can't be read
    """
    logger.info(f"Reading README from: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def write_readme(path: str, content: str) -> None:
    """
    Write content to README file.

    Args:
        path: Path to README file
        content: New file content

    Raises:
        IOError: If file can't be written
    """
    logger.info(f"Writing README to: {path}")
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def has_markers(content: str) -> bool:
    """
    Check if README contains the required markers.

    Args:
        content: README content

    Returns:
        True if both markers are present
    """
    return START_MARKER in content and END_MARKER in content


def find_insertion_point(content: str) -> Optional[int]:
    """
    Find a suitable insertion point if markers are missing.

    Strategy:
    1. After the first "---" divider
    2. After the first heading
    3. At the beginning of the file

    Args:
        content: README content

    Returns:
        Index for insertion, or None if markers exist
    """
    if has_markers(content):
        return None

    # Try after first divider
    divider_match = re.search(r"^---\s*$", content, re.MULTILINE)
    if divider_match:
        return divider_match.end()

    # Try after first heading
    heading_match = re.search(r"^#{1,3}\s+.+$", content, re.MULTILINE)
    if heading_match:
        # Find end of line after heading
        newline_after = content.find("\n", heading_match.end())
        return newline_after + 1 if newline_after != -1 else heading_match.end()

    # Default: beginning of file
    return 0


def update_readme_content(readme_content: str, markdown: str) -> Tuple[str, bool]:
    """
    Update README content with new statistics.

    Args:
        readme_content: Current README content
        markdown: New markdown content to insert

    Returns:
        Tuple of (updated_content, was_updated)
    """
    new_section = f"{START_MARKER}\n{markdown}\n{END_MARKER}"

    if has_markers(readme_content):
        # Replace existing content between markers
        updated = MARKER_PATTERN.sub(new_section, readme_content)
        was_updated = updated != readme_content
        logger.info("Replaced existing stats section" if was_updated else "No changes detected")
        return updated, was_updated
    else:
        # Insert at suitable location
        insertion_point = find_insertion_point(readme_content)
        if insertion_point is not None:
            updated = (
                readme_content[:insertion_point] +
                "\n" + new_section + "\n\n" +
                readme_content[insertion_point:]
            )
            logger.info(f"Inserted new stats section at position {insertion_point}")
            return updated, True
        else:
            # This shouldn't happen, but handle it
            logger.warning("Could not find insertion point, prepending to file")
            return new_section + "\n\n" + readme_content, True


def main() -> int:
    """
    Main entry point for the script.

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    parser = argparse.ArgumentParser(description="Update README with stats")
    parser.add_argument("--readme", type=str, default="README.md",
                        help="Path to README file")
    parser.add_argument("--markdown", type=str,
                        help="Markdown content to insert")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print result without writing file")
    args = parser.parse_args()

    try:
        # Get markdown content
        if args.markdown:
            markdown = args.markdown
        elif not sys.stdin.isatty():
            markdown = sys.stdin.read()
        elif os.environ.get("STATS_MARKDOWN"):
            markdown = os.environ["STATS_MARKDOWN"]
        else:
            logger.error("No markdown provided. Use --markdown, stdin, or STATS_MARKDOWN env var")
            return 1

        # Read current README
        try:
            readme_content = read_readme(args.readme)
        except FileNotFoundError:
            logger.error(f"README file not found: {args.readme}")
            return 1

        # Update content
        updated_content, was_updated = update_readme_content(readme_content, markdown)

        if args.dry_run:
            print("=== DRY RUN - Would write: ===")
            print(updated_content)
            return 0

        if was_updated:
            write_readme(args.readme, updated_content)
            logger.info("README updated successfully")
        else:
            logger.info("No changes needed")

        return 0

    except Exception as e:
        logger.error(f"Failed to update README: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
