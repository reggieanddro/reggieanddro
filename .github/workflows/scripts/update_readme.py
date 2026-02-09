#!/usr/bin/env python3
"""
README Updater - Daily README Auto-Update
==========================================
Updates README.md with generated statistics between markers.
Supports two marker pairs:
  - STATS_START/STATS_END for the monthly stats table
  - YTD_START/YTD_END for the dynamic YTD subtitle

Usage:
    python update_readme.py --readme README.md
    echo "markdown content" | python update_readme.py --readme README.md

Author: Jesse Niesen / Liv Hana SI
Version: 2.0.0
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

# Stats marker patterns
STATS_START = "<!-- STATS_START -->"
STATS_END = "<!-- STATS_END -->"
STATS_PATTERN = re.compile(
    rf"{re.escape(STATS_START)}.*?{re.escape(STATS_END)}",
    re.DOTALL
)

# YTD subtitle marker patterns
YTD_START = "<!-- YTD_START -->"
YTD_END = "<!-- YTD_END -->"
YTD_PATTERN = re.compile(
    rf"{re.escape(YTD_START)}.*?{re.escape(YTD_END)}",
    re.DOTALL
)


def read_readme(path: str) -> str:
    logger.info(f"Reading README from: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def write_readme(path: str, content: str) -> None:
    logger.info(f"Writing README to: {path}")
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def update_section(content: str, start_marker: str, end_marker: str,
                   pattern: re.Pattern, new_content: str) -> Tuple[str, bool]:
    """
    Replace content between marker pairs.

    Returns:
        Tuple of (updated_content, was_updated)
    """
    if start_marker not in content or end_marker not in content:
        logger.warning(f"Markers not found: {start_marker} / {end_marker}")
        return content, False

    new_section = f"{start_marker}\n{new_content}\n{end_marker}"
    updated = pattern.sub(new_section, content)
    was_updated = updated != content

    if was_updated:
        logger.info(f"Replaced section between {start_marker}")
    else:
        logger.info(f"No changes in {start_marker} section")

    return updated, was_updated


def find_insertion_point(content: str) -> Optional[int]:
    """Find a suitable insertion point if stats markers are missing."""
    if STATS_START in content and STATS_END in content:
        return None

    divider_match = re.search(r"^---\s*$", content, re.MULTILINE)
    if divider_match:
        return divider_match.end()

    heading_match = re.search(r"^#{1,3}\s+.+$", content, re.MULTILINE)
    if heading_match:
        newline_after = content.find("\n", heading_match.end())
        return newline_after + 1 if newline_after != -1 else heading_match.end()

    return 0


def update_readme_content(readme_content: str, stats_markdown: str,
                          ytd_subtitle: str = "") -> Tuple[str, bool]:
    """
    Update README content with new statistics and optional YTD subtitle.
    """
    any_updated = False

    # Update stats section
    if STATS_START in readme_content and STATS_END in readme_content:
        readme_content, updated = update_section(
            readme_content, STATS_START, STATS_END, STATS_PATTERN, stats_markdown
        )
        any_updated = any_updated or updated
    else:
        insertion_point = find_insertion_point(readme_content)
        if insertion_point is not None:
            new_section = f"{STATS_START}\n{stats_markdown}\n{STATS_END}"
            readme_content = (
                readme_content[:insertion_point] +
                "\n" + new_section + "\n\n" +
                readme_content[insertion_point:]
            )
            any_updated = True
            logger.info(f"Inserted new stats section at position {insertion_point}")

    # Update YTD subtitle section (if markers exist and subtitle provided)
    if ytd_subtitle and YTD_START in readme_content and YTD_END in readme_content:
        readme_content, updated = update_section(
            readme_content, YTD_START, YTD_END, YTD_PATTERN, ytd_subtitle
        )
        any_updated = any_updated or updated

    return readme_content, any_updated


def main() -> int:
    parser = argparse.ArgumentParser(description="Update README with stats")
    parser.add_argument("--readme", type=str, default="README.md",
                        help="Path to README file")
    parser.add_argument("--markdown", type=str,
                        help="Markdown content to insert (stats table)")
    parser.add_argument("--ytd-subtitle", type=str, default="",
                        help="YTD subtitle line to insert")
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

        ytd_subtitle = args.ytd_subtitle or os.environ.get("YTD_SUBTITLE", "")

        try:
            readme_content = read_readme(args.readme)
        except FileNotFoundError:
            logger.error(f"README file not found: {args.readme}")
            return 1

        updated_content, was_updated = update_readme_content(
            readme_content, markdown, ytd_subtitle
        )

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
