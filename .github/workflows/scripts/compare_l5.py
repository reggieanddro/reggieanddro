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
    # activity-rhythm comparison for the profile graph, not a productivity
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


def generate_markdown_table(stats: Dict[str, Any], comparison: Dict[str, Any]) -> str:
    """
    Generate a formatted markdown table for the README.

    Args:
        stats: GitHub statistics
        comparison: L5 comparison results

    Returns:
        Formatted markdown string
    """
    month = stats.get("month", "Unknown")
    year = stats.get("year", 2026)
    day = stats.get("day_of_month", 1)
    days_in_month = stats.get("days_in_month", 30)
    peak = stats.get("peak_day", {})

    # Format timestamp for Texas time (CT)
    ct_tz = ZoneInfo("America/Chicago")
    now_ct = datetime.now(ct_tz)
    tx_time = now_ct.strftime("%A, %B %d, %Y at %-I:%M %p CT")

    lines = [
        f"### 📊 {month} {year} Live Stats (Solo, No CS Degree)",
        "",
        f"> **🤖 Auto-Updated:** {tx_time}",
        f"> **📅 Day {day} of {days_in_month}**"
    ]

    if peak.get("count", 0) > 0:
        peak_day_num = peak.get("date", "").split("-")[-1] if peak.get("date") else "?"
        lines.append(f" | **🔥 Peak Day:** {peak_day_num} with {peak['count']} contributions")

    lines.extend(["", "| Metric | Value | Activity benchmark | Ratio |",
                  "|--------|-------|----------------------|------------|"])

    for comp in comparison["comparisons"]:
        value = comp["value"]
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            value = f"{value:,}" if isinstance(value, int) else f"{value}"
        if comp["multiplier_min"] is None:
            mult_str = "context only"
        else:
            mult_str = f"**{comp['multiplier_min']}-{comp['multiplier_max']}x**"
        lines.append(f"| **{comp['metric']}** | {value} | {comp['benchmark']} | {mult_str} |")

    # Daily breakdown (collapsible)
    daily = stats.get("daily_breakdown", [])
    if daily:
        lines.extend([
            "",
            "<details>",
            "<summary>📈 Daily Breakdown (Click to expand)</summary>",
            "",
            "```"
        ])

        max_count = max((d["count"] for d in daily), default=1)
        for d in daily:
            bar_len = int((d["count"] / max(max_count, 1)) * 20)
            bar = "█" * bar_len + "░" * (20 - bar_len)
            day_num = d["date"].split("-")[-1]
            lines.append(f"{day_num}: {bar} {d['count']}")

        lines.extend([
            "```",
            "",
            "</details>"
        ])

    # Streak + Month-over-Month trend
    streak = stats.get("ytd_streak_current", 0)
    prev_total = stats.get("prev_month_total", 0)
    prev_name = stats.get("prev_month_name", "")
    total_contributions = stats.get("total_contributions", 0)
    if streak > 0:
        lines.append(f"\n🔥 **Current Streak:** {streak} consecutive days with contributions")
    if prev_total > 0 and total_contributions > 0:
        # MoM comparison (projected vs actual prev)
        projected = stats.get("projected_month", 0)
        if projected > 0 and prev_total > 0:
            mom_pct = round(((projected - prev_total) / prev_total) * 100, 1)
            trend = "📈" if mom_pct > 0 else "📉"
            sign = "+" if mom_pct > 0 else ""
            lines.append(f"{trend} **Projected MoM Activity Trend:** {sign}{mom_pct}% vs {prev_name} ({prev_total:,} actual → ~{projected:,} projected)")

    # Source
    lines.extend([
        "",
        f"**Source:** [GitHub GraphQL API](https://docs.github.com/graphql) (live) • [{comparison['benchmark_source']}]({comparison['benchmark_url']})",
        "",
        "_Truth note: GitHub profile-attributed events include private/restricted activity. They are profile graph signals, not deployable commit counts, complete operating-work ledgers, or productivity equivalence claims. Bot/alternate-author commits can be real work while showing as zero on the personal contribution calendar._"
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
    Generate permanent all-month stats ledger with profile and operational lanes.

    The profile lane is GitHub contribution-calendar attribution. The operational
    lane is real default-branch repo commit activity from configured repositories.
    """
    months = stats.get("all_months") or []
    operational = stats.get("operational_activity") or {}
    op_months = {
        row.get("month_key"): row
        for row in operational.get("months", [])
        if row.get("month_key")
    }
    ct_tz = ZoneInfo("America/Chicago")
    now_ct = datetime.now(ct_tz)
    updated = now_ct.strftime("%A, %B %d, %Y at %-I:%M %p CT")

    if not months:
        return "\n".join([
            "## Current & Historical Stats Ledger",
            "",
            f"**Auto-updated:** {updated}",
            "",
            "All-month GitHub profile stats are temporarily unavailable. The live-month section above remains the fallback source.",
        ])

    by_year: Dict[int, List[Dict[str, Any]]] = defaultdict(list)
    for row in months:
        by_year[int(row["year"])].append(row)

    total_profile = sum(int(row.get("profile_events", 0)) for row in months)
    total_private = sum(int(row.get("private_restricted_events", 0)) for row in months)
    total_operational = sum(int(row.get("commits", 0)) for row in op_months.values())
    total_bot_agent = sum(int(row.get("bot_or_agent_commits", 0)) for row in op_months.values())
    coverage_start = months[0]["month_key"]
    coverage_end = months[-1]["month_key"]
    repos = ", ".join(operational.get("repos", [])) or "not configured"
    op_error_count = int(operational.get("error_count", 0) or 0)

    lines = [
        "## Current & Historical Stats Ledger",
        "",
        f"**Auto-updated:** {updated}",
        f"**Coverage:** {coverage_start} through {coverage_end}",
        "",
        "| Lane | Count | What it means |",
        "|------|-------|---------------|",
        f"| GitHub profile-attributed events | {_format_int(total_profile)} | What GitHub credits to `@{stats.get('username', 'reggieanddro')}` under contribution-calendar rules |",
        f"| Private/restricted profile events | {_format_int(total_private)} | GitHub-verified private/restricted profile events without public type disclosure |",
        f"| Operational repo commits | {_format_int(total_operational)} | Real default-branch commits across configured repos, regardless of whether GitHub credits the personal graph |",
        f"| Bot/agent operational commits | {_format_int(total_bot_agent)} | Operational commits by bots or agent author identities |",
        "",
        f"**Operational repos:** {repos}. Source: {operational.get('source', 'GitHub REST commits API')}.",
    ]

    if op_error_count:
        lines.append(f"**Operational caveat:** {op_error_count} repo-month fetches were unavailable, usually because the workflow token cannot read a private repo. Configure `PROFILE_PAT`/`OPERATIONAL_GITHUB_TOKEN` to close this gap.")

    year_rows = []
    for year in sorted(by_year):
        rows = by_year[year]
        profile_sum = sum(int(row.get("profile_events", 0)) for row in rows)
        private_sum = sum(int(row.get("private_restricted_events", 0)) for row in rows)
        active_sum = sum(int(row.get("days_active", 0)) for row in rows)
        op_sum = sum(int(op_months.get(row["month_key"], {}).get("commits", 0)) for row in rows)
        agent_sum = sum(int(op_months.get(row["month_key"], {}).get("bot_or_agent_commits", 0)) for row in rows)
        year_rows.append(f"| {year} | {_format_int(profile_sum)} | {_format_int(private_sum)} | {active_sum} | {_format_int(op_sum)} | {_format_int(agent_sum)} |")

    lines.extend([
        "",
        "| Year | Profile-attributed events | Private/restricted profile events | Active profile days | Operational commits | Bot/agent commits |",
        "|------|---------------------------|-----------------------------------|---------------------|---------------------|------------------|",
        *year_rows,
        "",
    ])

    for year in sorted(by_year, reverse=True):
        rows = sorted(by_year[year], key=lambda item: item["month_number"])
        profile_sum = sum(int(row.get("profile_events", 0)) for row in rows)
        op_sum = sum(int(op_months.get(row["month_key"], {}).get("commits", 0)) for row in rows)
        lines.extend([
            "<details>",
            f"<summary><strong>{year}</strong> — {_format_int(profile_sum)} profile events · {_format_int(op_sum)} operational commits</summary>",
            "",
            "| Month | Profile events | Private/restricted | Active days | Operational commits | Bot/agent commits |",
            "|-------|----------------|--------------------|-------------|---------------------|------------------|",
        ])
        for row in rows:
            op = op_months.get(row["month_key"], {})
            lines.append(
                f"| {row['month']} | {_format_int(row.get('profile_events', 0))} | "
                f"{_format_int(row.get('private_restricted_events', 0))} | "
                f"{row.get('days_active', 0)}/{row.get('days_elapsed', row.get('days_in_month', 0))} | "
                f"{_format_int(op.get('commits', 0))} | {_format_int(op.get('bot_or_agent_commits', 0))} |"
            )
        lines.extend(["", "</details>", ""])

    lines.append("### Monthly Drop-Down Receipts")
    lines.append("")

    for row in sorted(months, key=lambda item: item["month_key"], reverse=True):
        op = op_months.get(row["month_key"], {})
        daily = row.get("daily_breakdown") or []
        max_count = max((int(day.get("count", 0)) for day in daily), default=0)
        repo_rows = []
        for repo in op.get("repos", []):
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
            f"<summary><strong>{row['month']} {row['year']}</strong> — "
            f"{_format_int(row.get('profile_events', 0))} profile events · "
            f"{_format_int(op.get('commits', 0))} operational commits</summary>",
            "",
            "| Metric | Value |",
            "|--------|-------|",
            f"| GitHub profile-attributed events | {_format_int(row.get('profile_events', 0))} |",
            f"| Private/restricted profile events | {_format_int(row.get('private_restricted_events', 0))} |",
            f"| Public typed profile events | {_format_int(row.get('public_typed_events', 0))} |",
            f"| Profile active days | {row.get('days_active', 0)}/{row.get('days_elapsed', row.get('days_in_month', 0))} |",
            f"| Profile daily average | {row.get('daily_avg', 0)} |",
            f"| Operational repo commits | {_format_int(op.get('commits', 0))} |",
            f"| Bot/agent operational commits | {_format_int(op.get('bot_or_agent_commits', 0))} |",
            "",
            "| Operational repo | Commits | Top authors |",
            "|------------------|---------|-------------|",
            *(repo_rows or ["| unavailable | 0 | no configured repo data |"]),
            "",
        ])

        if daily:
            lines.extend([
                "| Day | Profile activity bar | Events |",
                "|-----|----------------------|--------|",
            ])
            for day in daily:
                count = int(day.get("count", 0))
                day_num = str(day.get("date", "")).split("-")[-1]
                lines.append(f"| {day_num} | {_daily_bar(count, max_count)} | {_format_int(count)} |")
            lines.append("")

        lines.extend(["</details>", ""])

    lines.append("_Truth note: profile-attributed events are GitHub contribution-calendar signals. Operational commits are real default-branch repo commits. Both are useful; neither alone is the full truth._")
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
