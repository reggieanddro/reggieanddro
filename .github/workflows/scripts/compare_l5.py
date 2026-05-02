#!/usr/bin/env python3
"""
Google L5 Benchmark Comparison - Daily README Auto-Update
==========================================================
Compares GitHub contribution statistics against Google L5 engineer benchmarks.

Benchmarks Source: 2025 Worklytics Software Engineering Productivity Report
https://www.worklytics.co/resources/software-engineering-productivity-benchmarks-2025-good-scores

Usage:
    echo '{"total_contributions": 275, ...}' | python compare_l5.py
    python compare_l5.py --stats '{"total_contributions": 275, ...}'

Output:
    JSON object with comparison results and formatted markdown table

Author: Jesse Niesen / Liv Hana SI
Version: 1.0.0
"""

import os
import sys
import json
import argparse
import logging
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from collections import defaultdict
from typing import Dict, Any, List, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# GOOGLE L5 BENCHMARKS (Source: 2025 Worklytics)
# ═══════════════════════════════════════════════════════════════════════════════

L5_BENCHMARKS = {
    "commits_per_month": {
        "min": 40,
        "max": 80,
        "description": "Commits per month"
    },
    "contributions_per_day": {
        "min": 2,
        "max": 4,
        "description": "Contributions per day"
    },
    "prs_per_month": {
        "min": 5,
        "max": 15,
        "description": "Pull requests per month"
    },
    "days_active_per_month": {
        "min": 18,
        "max": 22,
        "description": "Active days per month"
    },
    "files_changed_per_month": {
        "min": 50,
        "max": 100,
        "description": "Files changed per month"
    },
    "lines_per_month": {
        "min": 125,
        "max": 185,
        "description": "Net lines shipped per month"
    }
}


def calculate_multiplier(value: float, benchmark_min: int, benchmark_max: int) -> Tuple[float, float]:
    """
    Calculate multiplier range compared to benchmark.

    Args:
        value: Actual value
        benchmark_min: Minimum benchmark value
        benchmark_max: Maximum benchmark value

    Returns:
        Tuple of (multiplier_vs_max, multiplier_vs_min)
    """
    if benchmark_max == 0 or benchmark_min == 0:
        return (0.0, 0.0)

    mult_min = round(value / benchmark_max, 1)  # vs max (conservative)
    mult_max = round(value / benchmark_min, 1)  # vs min (generous)

    return (mult_min, mult_max)


def compare_to_l5(stats: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compare GitHub stats against Google L5 benchmarks.

    Args:
        stats: Dictionary containing GitHub statistics

    Returns:
        Dictionary with comparison results
    """
    comparisons = []

    # Total contributions vs commits benchmark (most comparable)
    total = stats.get("total_contributions", 0)
    private_included_events = stats.get("private_included_events", stats.get("commits", 0))
    daily_avg = stats.get("daily_avg", 0)
    days_active = stats.get("days_active", 0)
    prs = stats.get("pull_requests", 0)
    day_of_month = stats.get("day_of_month", 1)
    projected = stats.get("projected_month", 0)

    # GitHub contribution calendar attribution comparison. This is an
    # activity-rhythm comparison for the GitHub vanity graph, not a productivity
    # equivalence claim and not a complete operating-work ledger.
    commit_mult = calculate_multiplier(total, L5_BENCHMARKS["commits_per_month"]["min"],
                                        L5_BENCHMARKS["commits_per_month"]["max"])
    comparisons.append({
        "metric": "GitHub Profile-Attributed Events",
        "value": total,
        "benchmark": f"{L5_BENCHMARKS['commits_per_month']['min']}-{L5_BENCHMARKS['commits_per_month']['max']}/mo profile-attribution benchmark",
        "multiplier_min": commit_mult[0],
        "multiplier_max": commit_mult[1],
        "status": "above" if commit_mult[0] >= 1.0 else "below"
    })

    # Private/restricted GitHub events are not typed by GitHub. Keep them visible
    # for transparency, but never compare them as "commits".
    comparisons.append({
        "metric": "Private/Restricted Profile Events",
        "value": private_included_events,
        "benchmark": "GitHub does not expose event type",
        "multiplier_min": None,
        "multiplier_max": None,
        "status": "context"
    })

    # Daily average
    daily_mult = calculate_multiplier(daily_avg, L5_BENCHMARKS["contributions_per_day"]["min"],
                                       L5_BENCHMARKS["contributions_per_day"]["max"])
    comparisons.append({
        "metric": "Daily Average",
        "value": daily_avg,
        "benchmark": f"{L5_BENCHMARKS['contributions_per_day']['min']}-{L5_BENCHMARKS['contributions_per_day']['max']}/day",
        "multiplier_min": daily_mult[0],
        "multiplier_max": daily_mult[1],
        "status": "above" if daily_mult[0] >= 1.0 else "below"
    })

    # Days active (scaled to 30-day month)
    scaled_days_active = round(days_active / max(day_of_month, 1) * 30, 1)
    days_mult = calculate_multiplier(scaled_days_active, L5_BENCHMARKS["days_active_per_month"]["min"],
                                      L5_BENCHMARKS["days_active_per_month"]["max"])
    comparisons.append({
        "metric": "Days Active (rate)",
        "value": f"{days_active}/{day_of_month}",
        "benchmark": f"{L5_BENCHMARKS['days_active_per_month']['min']}-{L5_BENCHMARKS['days_active_per_month']['max']}/mo",
        "multiplier_min": days_mult[0],
        "multiplier_max": days_mult[1],
        "status": "above" if days_mult[0] >= 1.0 else "below"
    })

    # Projected month
    proj_mult = calculate_multiplier(projected, L5_BENCHMARKS["commits_per_month"]["min"],
                                      L5_BENCHMARKS["commits_per_month"]["max"])
    comparisons.append({
        "metric": "Projected Month",
        "value": f"~{projected:,}",
        "benchmark": f"{L5_BENCHMARKS['commits_per_month']['min']}-{L5_BENCHMARKS['commits_per_month']['max']}/mo",
        "multiplier_min": proj_mult[0],
        "multiplier_max": proj_mult[1],
        "status": "above" if proj_mult[0] >= 1.0 else "below"
    })

    # Overall assessment
    multiplier_rows = [c for c in comparisons if c["multiplier_min"] is not None]
    avg_multiplier = sum(c["multiplier_min"] for c in multiplier_rows) / len(multiplier_rows)
    overall_status = "above" if avg_multiplier >= 1.0 else "below"

    return {
        "comparisons": comparisons,
        "overall_multiplier": round(avg_multiplier, 1),
        "overall_status": overall_status,
        "benchmark_source": "2025 Worklytics Software Engineering Productivity Benchmarks",
        "benchmark_url": "https://www.worklytics.co/resources/software-engineering-productivity-benchmarks-2025-good-scores",
        "compared_at": datetime.now(timezone.utc).isoformat()
    }


def _coverage_label(stats: Dict[str, Any]) -> str:
    months = stats.get("all_months") or []
    if not months:
        return "current runtime window"
    return f"{months[0].get('month_key')} through {months[-1].get('month_key')}"


def _current_operational_month(stats: Dict[str, Any]) -> Dict[str, Any]:
    month_key = f"{int(stats.get('year', datetime.now(timezone.utc).year)):04d}-{datetime.now(timezone.utc).month:02d}"
    operational = stats.get("operational_activity") or {}
    for row in operational.get("months", []):
        if row.get("month_key") == month_key:
            return row
    return {}


def generate_markdown_table(stats: Dict[str, Any], comparison: Dict[str, Any]) -> str:
    """
    Generate the top README proof block.

    CEO directive 2026-05-02: GitHub vanity attribution is not the
    lead signal. Lead with operational dark-factory output and mission proof.
    """
    ct_tz = ZoneInfo("America/Chicago")
    now_ct = datetime.now(ct_tz)
    tx_time = now_ct.strftime("%A, %B %d, %Y at %-I:%M %p CT")
    operational = stats.get("operational_activity") or {}
    totals = operational.get("totals") or {}
    current_month = _current_operational_month(stats)
    op_commits = int(totals.get("commits", 0) or 0)
    bot_agent = int(totals.get("bot_or_agent_commits", 0) or 0)
    trailers = int(totals.get("author_agent_trailers", 0) or 0)
    current_commits = int(current_month.get("commits", 0) or 0)
    current_agent = int(current_month.get("bot_or_agent_commits", 0) or 0)
    error_count = int(operational.get("error_count", 0) or 0)
    repos = ", ".join(operational.get("repos", [])) or "configured live repos"
    coverage = _coverage_label(stats)

    lines = [
        "### Dark Factory Live Output",
        "",
        f"> **Auto-updated:** {tx_time}",
        f"> **Coverage:** {coverage}",
        "",
        "| Mission metric | Live count | Why it matters |",
        "|----------------|------------|----------------|",
        f"| Operational repo commits | {_format_int(op_commits)} | Real default-branch work shipped across the live factory repos |",
        f"| Bot/agent operational commits | {_format_int(bot_agent)} | Delegated dark-factory execution by bots and agent identities |",
        f"| Commit-trailer receipts | {_format_int(trailers)} | Auditable `author-agent:` provenance where present |",
        f"| Current-month operational commits | {_format_int(current_commits)} | This month's actual factory motion |",
        f"| Current-month bot/agent commits | {_format_int(current_agent)} | Current autonomous execution share |",
        "",
        f"**Operational repos:** {repos}.",
        "",
        "**CEO intent signal:** build Liv Hana as a dark factory for regulated-industry AI assurance, prove it through Reggie & Dro, and scale toward the Unicorn Race with revenue, compliance, security, and runtime receipts.",
    ]

    if error_count:
        lines.append(f"**Data caveat:** {error_count} repo-month fetches were unavailable. The factory must keep `PROFILE_PAT`/`OPERATIONAL_GITHUB_TOKEN` live to preserve full private-repo coverage.")

    lines.extend([
        "",
        "_Truth note: this block intentionally ignores GitHub vanity contribution-graph attribution. It reports operational commit output from GitHub's commits API. Profile graph numbers are not a CEO success metric._",
    ])

    return "\n".join(lines)


def generate_ytd_banner(stats: Dict[str, Any]) -> str:
    """
    Generate a dynamic YTD banner for <!-- YTD_START/END --> markers.

    Args:
        stats: Dictionary containing YTD statistics

    Returns:
        Formatted markdown string for YTD section
    """
    ytd_total = stats.get("ytd_total", 0)
    ytd_daily_avg = stats.get("ytd_daily_avg", 0)
    ytd_streak = stats.get("ytd_streak_current", 0)
    ytd_commits = stats.get("ytd_commits", 0)
    year = stats.get("ytd_year", datetime.now(timezone.utc).year)
    day_of_year = stats.get("ytd_day_of_year", 1)

    # L5 benchmark: 40-80 commits/month = ~480-960/year
    l5_yearly_max = 80 * 12
    ytd_mult = round(ytd_total / max(l5_yearly_max, 1), 1) if ytd_total > 0 else 0

    lines = [
        f"### 🏆 {year} Year-to-Date",
        "",
        f"> **{ytd_daily_avg} Profile-Attributed Events/Day · {ytd_total:,} YTD · Day {day_of_year}**",
        f"> {ytd_commits:,} private/restricted profile events · {ytd_streak}-day streak · **{ytd_mult}x** annualized profile-attribution ratio vs L5 max ({l5_yearly_max:,}/yr)",
    ]

    return "\n".join(lines)


def generate_archive_section(stats: Dict[str, Any]) -> str:
    """
    Generate auto-archive section for previous month in a collapsible block.

    Args:
        stats: Dictionary containing previous month statistics

    Returns:
        Formatted markdown string for archive section
    """
    prev_name = stats.get("prev_month_name", "")
    prev_year = stats.get("prev_month_year", "")
    prev_total = stats.get("prev_month_total", 0)
    prev_commits = stats.get("prev_month_commits", 0)
    prev_daily = stats.get("prev_month_daily_avg", 0)
    prev_active = stats.get("prev_month_days_active", 0)
    prev_days = stats.get("prev_month_days_in_month", 30)
    prev_peak = stats.get("prev_month_peak_day", {})

    if not prev_name or prev_total == 0:
        return ""

    # L5 multiplier for previous month
    l5_max = 80
    mult = round(prev_total / max(l5_max, 1), 1)

    peak_str = ""
    if prev_peak.get("count", 0) > 0:
        peak_date = prev_peak.get("date", "").split("-")[-1]
        peak_str = f" · Peak: {prev_peak['count']} on day {peak_date}"

    lines = [
        "<details>",
        f"<summary>📁 {prev_name} {prev_year} Archive ({prev_total:,} contributions, {mult}x L5)</summary>",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| GitHub Profile-Attributed Events | {prev_total:,} |",
        f"| Private/Restricted Profile Events | {prev_commits:,} |",
        f"| Daily Average | {prev_daily} |",
        f"| Days Active | {prev_active}/{prev_days} |",
        f"| vs L5 Max | **{mult}x** |",
    ]

    if peak_str:
        lines.append(f"| Peak Day | {prev_peak.get('count', 0)} contributions (day {prev_peak.get('date', '').split('-')[-1]}) |")

    lines.extend([
        "",
        "</details>",
    ])

    return "\n".join(lines)


def _format_int(value: Any) -> str:
    try:
        return f"{int(value):,}"
    except (TypeError, ValueError):
        return "0"


def _daily_bar(count: int, max_count: int) -> str:
    if max_count <= 0:
        return "░" * 20
    bar_len = int((count / max_count) * 20)
    return "█" * bar_len + "░" * (20 - bar_len)


def generate_all_months_ledger(stats: Dict[str, Any]) -> str:
    """
    Generate an operational-only dark-factory ledger.

    CEO directive 2026-05-02: remove profile-event vanity stats from the
    public surface. Keep the machine focused on operational output.
    """
    operational = stats.get("operational_activity") or {}
    op_months = [row for row in operational.get("months", []) if row.get("month_key")]
    ct_tz = ZoneInfo("America/Chicago")
    now_ct = datetime.now(ct_tz)
    updated = now_ct.strftime("%A, %B %d, %Y at %-I:%M %p CT")
    if not op_months:
        return "\n".join([
            "## Dark Factory Operational Ledger",
            "",
            f"**Auto-updated:** {updated}",
            "",
            "Operational commit ledger is temporarily unavailable. Check CI token access to configured repos.",
        ])

    by_year: Dict[int, List[Dict[str, Any]]] = defaultdict(list)
    for row in op_months:
        by_year[int(row["year"])].append(row)

    total_operational = sum(int(row.get("commits", 0)) for row in op_months)
    total_bot_agent = sum(int(row.get("bot_or_agent_commits", 0)) for row in op_months)
    total_trailers = sum(int(row.get("author_agent_trailers", 0)) for row in op_months)
    coverage_start = min(row["month_key"] for row in op_months)
    coverage_end = max(row["month_key"] for row in op_months)
    repos = ", ".join(operational.get("repos", [])) or "not configured"
    op_error_count = int(operational.get("error_count", 0) or 0)

    lines = [
        "## Dark Factory Operational Ledger",
        "",
        f"**Auto-updated:** {updated}",
        f"**Coverage:** {coverage_start} through {coverage_end}",
        "",
        "| Output lane | Count | What it proves |",
        "|-------------|-------|----------------|",
        f"| Operational repo commits | {_format_int(total_operational)} | Real default-branch work shipped across live factory repos |",
        f"| Bot/agent operational commits | {_format_int(total_bot_agent)} | Delegated dark-factory work executed by automation and agent identities |",
        f"| `author-agent:` trailer receipts | {_format_int(total_trailers)} | Auditable agent provenance where enforced |",
        "",
        f"**Operational repos:** {repos}. Source: {operational.get('source', 'GitHub REST commits API')}.",
    ]

    if op_error_count:
        lines.append(f"**Data caveat:** {op_error_count} repo-month fetches were unavailable. Fix token access before trusting this as complete.")

    lines.extend([
        "",
        "| Year | Operational commits | Bot/agent commits | Trailer receipts |",
        "|------|---------------------|------------------|------------------|",
    ])
    for year in sorted(by_year):
        rows = by_year[year]
        op_sum = sum(int(row.get("commits", 0)) for row in rows)
        agent_sum = sum(int(row.get("bot_or_agent_commits", 0)) for row in rows)
        trailer_sum = sum(int(row.get("author_agent_trailers", 0)) for row in rows)
        lines.append(f"| {year} | {_format_int(op_sum)} | {_format_int(agent_sum)} | {_format_int(trailer_sum)} |")

    lines.append("")
    for year in sorted(by_year, reverse=True):
        rows = sorted(by_year[year], key=lambda item: item["month_number"])
        op_sum = sum(int(row.get("commits", 0)) for row in rows)
        agent_sum = sum(int(row.get("bot_or_agent_commits", 0)) for row in rows)
        lines.extend([
            "<details>",
            f"<summary><strong>{year}</strong> — {_format_int(op_sum)} operational commits · {_format_int(agent_sum)} bot/agent commits</summary>",
            "",
            "| Month | Operational commits | Bot/agent commits | Trailer receipts |",
            "|-------|---------------------|------------------|------------------|",
        ])
        for row in rows:
            lines.append(
                f"| {row['month']} | {_format_int(row.get('commits', 0))} | "
                f"{_format_int(row.get('bot_or_agent_commits', 0))} | "
                f"{_format_int(row.get('author_agent_trailers', 0))} |"
            )
        lines.extend(["", "</details>", ""])

    lines.append("### Monthly Operational Receipts")
    lines.append("")
    for row in sorted(op_months, key=lambda item: item["month_key"], reverse=True):
        repo_rows = []
        for repo in row.get("repos", []):
            if repo.get("error"):
                repo_rows.append(f"| `{repo.get('repo')}` | unavailable | {repo.get('error')} |")
            else:
                top_authors = ", ".join(
                    f"{author['name']} ({author['commits']})"
                    for author in repo.get("top_authors", [])[:3]
                ) or "none"
                repo_rows.append(f"| `{repo.get('repo')}` | {_format_int(repo.get('commits', 0))} | {top_authors} |")

        lines.extend([
            "<details>",
            f"<summary><strong>{row['month']} {row['year']}</strong> — {_format_int(row.get('commits', 0))} operational commits</summary>",
            "",
            "| Metric | Value |",
            "|--------|-------|",
            f"| Operational repo commits | {_format_int(row.get('commits', 0))} |",
            f"| Bot/agent operational commits | {_format_int(row.get('bot_or_agent_commits', 0))} |",
            f"| `author-agent:` trailer receipts | {_format_int(row.get('author_agent_trailers', 0))} |",
            "",
            "| Operational repo | Commits | Top authors |",
            "|------------------|---------|-------------|",
            *(repo_rows or ["| unavailable | 0 | no configured repo data |"]),
            "",
            "</details>",
            "",
        ])

    lines.append("_Truth note: operational commits are real default-branch repo commits from configured factory repos. GitHub vanity graph attribution is intentionally not used as a success metric._")
    return "\n".join(lines)


def generate_full_output(stats: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate full output including comparison and markdown.

    Args:
        stats: GitHub statistics

    Returns:
        Complete output dictionary
    """
    if "error" in stats:
        return {
            "error": stats["error"],
            "markdown": f"⚠️ Failed to fetch stats: {stats['error']}",
            "generated_at": datetime.now(timezone.utc).isoformat()
        }

    comparison = compare_to_l5(stats)
    markdown = generate_markdown_table(stats, comparison)

    return {
        "stats": stats,
        "comparison": comparison,
        "markdown": markdown,
        "generated_at": datetime.now(timezone.utc).isoformat()
    }


def main() -> int:
    """
    Main entry point for the script.

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    parser = argparse.ArgumentParser(description="Compare GitHub stats to L5 benchmarks")
    parser.add_argument("--stats", type=str, help="JSON string of GitHub stats")
    parser.add_argument("--markdown-only", action="store_true",
                        help="Output only the markdown table")
    parser.add_argument("--ytd-only", action="store_true",
                        help="Output only the YTD banner markdown")
    parser.add_argument("--archive-only", action="store_true",
                        help="Output only the archive section markdown")
    parser.add_argument("--ledger-only", action="store_true",
                        help="Output only the all-month stats ledger markdown")
    args = parser.parse_args()

    try:
        # Read stats from argument, stdin, or GITHUB_STATS env var
        if args.stats:
            stats = json.loads(args.stats)
        elif not sys.stdin.isatty():
            stats = json.load(sys.stdin)
        elif os.environ.get("GITHUB_STATS"):
            stats = json.loads(os.environ["GITHUB_STATS"])
        else:
            logger.error("No stats provided. Use --stats, stdin, or GITHUB_STATS env var")
            return 1

        if args.ytd_only:
            print(generate_ytd_banner(stats))
        elif args.ledger_only:
            print(generate_all_months_ledger(stats))
        elif args.archive_only:
            print(generate_archive_section(stats))
        elif args.markdown_only:
            output = generate_full_output(stats)
            print(output["markdown"])
        else:
            output = generate_full_output(stats)
            print(json.dumps(output, indent=2))

        return 0

    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON input: {e}")
        return 1
    except Exception as e:
        logger.error(f"Comparison failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
