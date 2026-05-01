#!/usr/bin/env python3
"""
GitHub Stats Fetcher - Daily README Auto-Update
================================================
Fetches contribution statistics from GitHub GraphQL API for the current month.

Usage:
    python get_github_stats.py [username]

Environment:
    GITHUB_TOKEN: GitHub Personal Access Token (required)
    GITHUB_USERNAME: Target username (optional, can be passed as arg)

Output:
    JSON object with contribution statistics to stdout

Author: Jesse Niesen / Liv Hana SI
Version: 1.0.0
"""

import os
import sys
import json
import calendar
import logging
from datetime import datetime, timezone, timedelta
from collections import Counter
from typing import Dict, Any, Optional, List
import urllib.request
import urllib.error
import urllib.parse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Constants
GITHUB_GRAPHQL_URL = "https://api.github.com/graphql"
GITHUB_REST_URL = "https://api.github.com"
DEFAULT_USERNAME = "reggieanddro"
DEFAULT_STATS_START_YEAR = 2025
DEFAULT_OPERATIONAL_REPOS = [
    "RND-Technology/LivHana-SoT",
    "reggieanddro/reggieanddro",
]


def get_month_date_range() -> tuple[str, str, int, int]:
    """
    Calculate the date range for the current month.

    Returns:
        Tuple of (month_start_iso, today_iso, day_of_month, days_in_month)
    """
    now = datetime.now(timezone.utc)
    year = now.year
    month = now.month
    day = now.day

    # First day of current month
    month_start = datetime(year, month, 1, tzinfo=timezone.utc)

    # Calculate days in month
    if month == 12:
        next_month = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
    else:
        next_month = datetime(year, month + 1, 1, tzinfo=timezone.utc)
    days_in_month = (next_month - month_start).days

    return (
        month_start.isoformat(),
        now.isoformat(),
        day,
        days_in_month
    )


def get_ytd_date_range() -> tuple[str, str, int]:
    """
    Calculate YTD date range: Jan 1 to now.

    Returns:
        Tuple of (year_start_iso, today_iso, day_of_year)
    """
    now = datetime.now(timezone.utc)
    year_start = datetime(now.year, 1, 1, tzinfo=timezone.utc)
    day_of_year = (now - year_start).days + 1
    return (year_start.isoformat(), now.isoformat(), day_of_year)


def get_previous_month_date_range() -> tuple[str, str, str, int]:
    """
    Calculate date range for the previous month.

    Returns:
        Tuple of (prev_month_start_iso, prev_month_end_iso, month_name, days_in_prev_month)
    """
    now = datetime.now(timezone.utc)
    # First day of current month
    first_of_current = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
    # Last day of previous month = day before first of current
    prev_month_end = first_of_current - timedelta(days=1)
    prev_month_start = datetime(prev_month_end.year, prev_month_end.month, 1, tzinfo=timezone.utc)
    days_in_prev = (first_of_current - prev_month_start).days
    month_name = prev_month_start.strftime("%B")
    return (prev_month_start.isoformat(), first_of_current.isoformat(), month_name, days_in_prev)


def get_stats_start_year() -> int:
    """Return configured first year for historical stats."""
    raw = os.environ.get("STATS_START_YEAR", str(DEFAULT_STATS_START_YEAR)).strip()
    try:
        year = int(raw)
    except ValueError:
        logger.warning("Invalid STATS_START_YEAR=%r; using %s", raw, DEFAULT_STATS_START_YEAR)
        year = DEFAULT_STATS_START_YEAR
    return max(2008, min(year, datetime.now(timezone.utc).year))


def iter_month_ranges(start_year: Optional[int] = None) -> List[Dict[str, Any]]:
    """Return month ranges from January of start_year through now."""
    now = datetime.now(timezone.utc)
    start_year = start_year or get_stats_start_year()
    ranges = []
    for year in range(start_year, now.year + 1):
        last_month = now.month if year == now.year else 12
        for month in range(1, last_month + 1):
            start = datetime(year, month, 1, tzinfo=timezone.utc)
            if year == now.year and month == now.month:
                end = now
                days_elapsed = now.day
            else:
                if month == 12:
                    end = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
                else:
                    end = datetime(year, month + 1, 1, tzinfo=timezone.utc)
                days_elapsed = calendar.monthrange(year, month)[1]
            ranges.append({
                "year": year,
                "month": month,
                "month_name": start.strftime("%B"),
                "month_key": f"{year}-{month:02d}",
                "start": start.isoformat(),
                "end": end.isoformat(),
                "days_in_month": calendar.monthrange(year, month)[1],
                "days_elapsed": days_elapsed,
                "is_current_month": year == now.year and month == now.month,
            })
    return ranges


def build_graphql_query(username: str, from_date: str, to_date: str) -> str:
    """
    Build the GraphQL query for fetching contribution statistics.

    Args:
        username: GitHub username
        from_date: Start date in ISO format
        to_date: End date in ISO format

    Returns:
        GraphQL query string
    """
    return f"""{{
  user(login: "{username}") {{
    contributionsCollection(from: "{from_date}", to: "{to_date}") {{
      totalCommitContributions
      totalPullRequestContributions
      totalIssueContributions
      totalPullRequestReviewContributions
      restrictedContributionsCount
      contributionCalendar {{
        totalContributions
        weeks {{
          contributionDays {{
            date
            contributionCount
          }}
        }}
      }}
    }}
    repositories(first: 1, ownerAffiliations: OWNER) {{
      totalCount
    }}
  }}
}}"""


def fetch_github_stats(token: str, username: str) -> Dict[str, Any]:
    """
    Fetch GitHub contribution statistics via GraphQL API.

    Args:
        token: GitHub Personal Access Token
        username: GitHub username to fetch stats for

    Returns:
        Dictionary containing contribution statistics

    Raises:
        ValueError: If API returns an error
        urllib.error.URLError: If network request fails
    """
    month_start, today, day_of_month, days_in_month = get_month_date_range()

    query = build_graphql_query(username, month_start, today)

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "User-Agent": "readme-stats-bot/1.0"
    }

    data = json.dumps({"query": query}).encode("utf-8")

    request = urllib.request.Request(
        GITHUB_GRAPHQL_URL,
        data=data,
        headers=headers,
        method="POST"
    )

    logger.info(f"Fetching stats for {username} from {month_start[:10]} to {today[:10]}")

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8") if e.fp else "No details"
        logger.error(f"GitHub API error {e.code}: {error_body}")
        raise ValueError(f"GitHub API returned {e.code}: {error_body}")
    except urllib.error.URLError as e:
        logger.error(f"Network error: {e.reason}")
        raise

    # Check for GraphQL errors
    if "errors" in result:
        error_msg = result["errors"][0].get("message", "Unknown error")
        logger.error(f"GraphQL error: {error_msg}")
        raise ValueError(f"GraphQL error: {error_msg}")

    user = result.get("data", {}).get("user")
    if not user:
        raise ValueError(f"User '{username}' not found")

    contrib = user["contributionsCollection"]
    calendar = contrib["contributionCalendar"]

    # Extract daily breakdown for current month
    daily_breakdown = []
    days_active = 0
    peak_day = {"date": "", "count": 0}
    current_month = datetime.now(timezone.utc).month

    for week in calendar["weeks"]:
        for day in week["contributionDays"]:
            day_month = int(day["date"].split("-")[1])
            if day_month == current_month:
                daily_breakdown.append({
                    "date": day["date"],
                    "count": day["contributionCount"]
                })
                if day["contributionCount"] > 0:
                    days_active += 1
                if day["contributionCount"] > peak_day["count"]:
                    peak_day = {"date": day["date"], "count": day["contributionCount"]}

    # Calculate derived metrics
    total_contributions = calendar["totalContributions"]
    restricted_events = contrib["restrictedContributionsCount"]
    visible_typed_events = (
        contrib["totalCommitContributions"]
        + contrib["totalPullRequestContributions"]
        + contrib["totalIssueContributions"]
        + contrib["totalPullRequestReviewContributions"]
    )
    # GitHub exposes private work as "restricted contributions" without type.
    # Do not label this as commits: it is verified activity, not deployable commit count.
    private_included_events = contrib["totalCommitContributions"] + restricted_events
    daily_avg = round(total_contributions / max(day_of_month, 1), 1)
    projected_month = round(daily_avg * days_in_month)

    stats = {
        "username": username,
        "month": datetime.now(timezone.utc).strftime("%B"),
        "year": datetime.now(timezone.utc).year,
        "day_of_month": day_of_month,
        "days_in_month": days_in_month,
        "total_contributions": total_contributions,
        "commits": private_included_events,
        "private_included_events": private_included_events,
        "restricted_contributions": restricted_events,
        "visible_typed_events": visible_typed_events,
        "pull_requests": contrib["totalPullRequestContributions"],
        "issues": contrib["totalIssueContributions"],
        "reviews": contrib["totalPullRequestReviewContributions"],
        "days_active": days_active,
        "daily_avg": daily_avg,
        "projected_month": projected_month,
        "peak_day": peak_day,
        "daily_breakdown": daily_breakdown,
        "repo_count": user["repositories"]["totalCount"],
        "fetched_at": datetime.now(timezone.utc).isoformat()
    }

    logger.info(
        "Stats fetched: %s contribution events, %s private/restricted events",
        total_contributions,
        private_included_events,
    )

    return stats


def fetch_ytd_stats(token: str, username: str) -> Dict[str, Any]:
    """
    Fetch YTD contribution statistics via GraphQL API.

    Args:
        token: GitHub Personal Access Token
        username: GitHub username

    Returns:
        Dictionary containing YTD statistics
    """
    year_start, today, day_of_year = get_ytd_date_range()
    query = build_graphql_query(username, year_start, today)

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "User-Agent": "readme-stats-bot/2.0"
    }

    data = json.dumps({"query": query}).encode("utf-8")
    request = urllib.request.Request(
        GITHUB_GRAPHQL_URL, data=data, headers=headers, method="POST"
    )

    logger.info(f"Fetching YTD stats for {username} ({year_start[:10]} to {today[:10]})")

    with urllib.request.urlopen(request, timeout=30) as response:
        result = json.loads(response.read().decode("utf-8"))

    if "errors" in result:
        raise ValueError(f"GraphQL error: {result['errors'][0].get('message', 'Unknown')}")

    user = result.get("data", {}).get("user")
    if not user:
        raise ValueError(f"User '{username}' not found")

    contrib = user["contributionsCollection"]
    calendar = contrib["contributionCalendar"]

    ytd_total = calendar["totalContributions"]
    ytd_commits = contrib["totalCommitContributions"] + contrib["restrictedContributionsCount"]
    ytd_daily_avg = round(ytd_total / max(day_of_year, 1), 1)

    # Walk contribution days backwards to find current streak
    all_days = []
    for week in calendar["weeks"]:
        for day in week["contributionDays"]:
            all_days.append(day)

    # Sort by date descending
    all_days.sort(key=lambda d: d["date"], reverse=True)

    streak = 0
    for day in all_days:
        if day["contributionCount"] > 0:
            streak += 1
        else:
            break

    return {
        "ytd_total": ytd_total,
        "ytd_commits": ytd_commits,
        "ytd_daily_avg": ytd_daily_avg,
        "ytd_day_of_year": day_of_year,
        "ytd_streak_current": streak,
        "ytd_year": datetime.now(timezone.utc).year,
    }


def fetch_previous_month_stats(token: str, username: str) -> Dict[str, Any]:
    """
    Fetch previous month contribution statistics.

    Args:
        token: GitHub Personal Access Token
        username: GitHub username

    Returns:
        Dictionary containing previous month statistics
    """
    prev_start, prev_end, month_name, days_in_prev = get_previous_month_date_range()
    query = build_graphql_query(username, prev_start, prev_end)

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "User-Agent": "readme-stats-bot/2.0"
    }

    data = json.dumps({"query": query}).encode("utf-8")
    request = urllib.request.Request(
        GITHUB_GRAPHQL_URL, data=data, headers=headers, method="POST"
    )

    logger.info(f"Fetching previous month stats ({month_name})")

    with urllib.request.urlopen(request, timeout=30) as response:
        result = json.loads(response.read().decode("utf-8"))

    if "errors" in result:
        raise ValueError(f"GraphQL error: {result['errors'][0].get('message', 'Unknown')}")

    user = result.get("data", {}).get("user")
    if not user:
        raise ValueError(f"User '{username}' not found")

    contrib = user["contributionsCollection"]
    calendar = contrib["contributionCalendar"]

    total = calendar["totalContributions"]
    commits = contrib["totalCommitContributions"] + contrib["restrictedContributionsCount"]
    daily_avg = round(total / max(days_in_prev, 1), 1)

    # Count active days
    days_active = 0
    peak_day = {"date": "", "count": 0}
    for week in calendar["weeks"]:
        for day in week["contributionDays"]:
            if day["contributionCount"] > 0:
                days_active += 1
            if day["contributionCount"] > peak_day["count"]:
                peak_day = {"date": day["date"], "count": day["contributionCount"]}

    return {
        "prev_month_name": month_name,
        "prev_month_year": datetime.now(timezone.utc).year if datetime.now(timezone.utc).month > 1 else datetime.now(timezone.utc).year - 1,
        "prev_month_total": total,
        "prev_month_commits": commits,
        "prev_month_daily_avg": daily_avg,
        "prev_month_days_active": days_active,
        "prev_month_days_in_month": days_in_prev,
        "prev_month_peak_day": peak_day,
    }


def _graphql_contributions(token: str, username: str, start: str, end: str) -> Dict[str, Any]:
    """Fetch a contributionCollection window from GitHub GraphQL."""
    query = build_graphql_query(username, start, end)
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "User-Agent": "readme-stats-bot/3.0"
    }
    data = json.dumps({"query": query}).encode("utf-8")
    request = urllib.request.Request(
        GITHUB_GRAPHQL_URL, data=data, headers=headers, method="POST"
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        result = json.loads(response.read().decode("utf-8"))
    if "errors" in result:
        raise ValueError(f"GraphQL error: {result['errors'][0].get('message', 'Unknown')}")
    user = result.get("data", {}).get("user")
    if not user:
        raise ValueError(f"User '{username}' not found")
    return user["contributionsCollection"]


def _profile_month_from_collection(month_meta: Dict[str, Any], contrib: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize one GraphQL contributionCollection response into a month row."""
    calendar_data = contrib["contributionCalendar"]
    daily_breakdown = []
    days_active = 0
    peak_day = {"date": "", "count": 0}
    target_month = month_meta["month"]

    for week in calendar_data["weeks"]:
        for day in week["contributionDays"]:
            day_month = int(day["date"].split("-")[1])
            if day_month != target_month:
                continue
            daily_breakdown.append({
                "date": day["date"],
                "count": day["contributionCount"]
            })
            if day["contributionCount"] > 0:
                days_active += 1
            if day["contributionCount"] > peak_day["count"]:
                peak_day = {"date": day["date"], "count": day["contributionCount"]}

    total = calendar_data["totalContributions"]
    restricted = contrib["restrictedContributionsCount"]
    typed = (
        contrib["totalCommitContributions"]
        + contrib["totalPullRequestContributions"]
        + contrib["totalIssueContributions"]
        + contrib["totalPullRequestReviewContributions"]
    )

    return {
        "month_key": month_meta["month_key"],
        "month": month_meta["month_name"],
        "month_number": month_meta["month"],
        "year": month_meta["year"],
        "days_in_month": month_meta["days_in_month"],
        "days_elapsed": month_meta["days_elapsed"],
        "is_current_month": month_meta["is_current_month"],
        "profile_events": total,
        "private_restricted_events": restricted,
        "public_typed_events": typed,
        "commit_events": contrib["totalCommitContributions"],
        "pull_request_events": contrib["totalPullRequestContributions"],
        "issue_events": contrib["totalIssueContributions"],
        "review_events": contrib["totalPullRequestReviewContributions"],
        "days_active": days_active,
        "daily_avg": round(total / max(month_meta["days_elapsed"], 1), 1),
        "projected_month": round((total / max(month_meta["days_elapsed"], 1)) * month_meta["days_in_month"]),
        "peak_day": peak_day,
        "daily_breakdown": daily_breakdown,
    }


def fetch_all_month_profile_stats(token: str, username: str) -> List[Dict[str, Any]]:
    """Fetch profile-attributed stats for every month in the configured range."""
    months = []
    for month_meta in iter_month_ranges():
        logger.info("Fetching profile month %s", month_meta["month_key"])
        contrib = _graphql_contributions(token, username, month_meta["start"], month_meta["end"])
        months.append(_profile_month_from_collection(month_meta, contrib))
    return months


def get_operational_repos() -> List[str]:
    """Return comma-delimited operational repos to count as real repo activity."""
    raw = os.environ.get("OPERATIONAL_REPOS", "").strip()
    if not raw:
        return DEFAULT_OPERATIONAL_REPOS
    repos = [repo.strip() for repo in raw.split(",") if repo.strip()]
    return repos or DEFAULT_OPERATIONAL_REPOS


def _parse_next_link(link_header: Optional[str]) -> Optional[str]:
    if not link_header:
        return None
    for part in link_header.split(","):
        section = part.strip()
        if 'rel="next"' not in section:
            continue
        if section.startswith("<") and ">" in section:
            return section[1:section.index(">")]
    return None


def _github_rest_get(token: str, url: str) -> tuple[list, Optional[str]]:
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "readme-operational-stats/1.0",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    request = urllib.request.Request(url, headers=headers, method="GET")
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))
        return payload, _parse_next_link(response.headers.get("Link"))


def _count_repo_commits_for_month(token: str, repo: str, month_meta: Dict[str, Any]) -> Dict[str, Any]:
    """Count default-branch commits for a repo in a month via GitHub REST."""
    params = urllib.parse.urlencode({
        "since": month_meta["start"],
        "until": month_meta["end"],
        "per_page": 100,
    })
    url = f"{GITHUB_REST_URL}/repos/{repo}/commits?{params}"
    commits = 0
    bot_or_agent_commits = 0
    author_counts: Counter[str] = Counter()
    author_agent_trailers = 0

    try:
        while url:
            payload, next_url = _github_rest_get(token, url)
            for item in payload:
                commits += 1
                commit = item.get("commit") or {}
                author = commit.get("author") or {}
                github_author = item.get("author") or {}
                name = author.get("name") or github_author.get("login") or "unknown"
                email = author.get("email") or ""
                login = github_author.get("login") or ""
                message = commit.get("message") or ""
                author_counts[name] += 1

                lowered = f"{name} {email} {login}".lower()
                is_bot = "[bot]" in lowered or "bot" in lowered or "github-actions" in lowered
                is_agent = "author-agent:" in message.lower() or "anthropic" in lowered or name.lower() in {"claude", "cursor"}
                if is_bot or is_agent:
                    bot_or_agent_commits += 1
                if "author-agent:" in message.lower():
                    author_agent_trailers += 1
            url = next_url
    except urllib.error.HTTPError as e:
        return {
            "repo": repo,
            "commits": 0,
            "bot_or_agent_commits": 0,
            "author_agent_trailers": 0,
            "top_authors": [],
            "error": f"HTTP {e.code}",
        }
    except Exception as e:
        return {
            "repo": repo,
            "commits": 0,
            "bot_or_agent_commits": 0,
            "author_agent_trailers": 0,
            "top_authors": [],
            "error": str(e),
        }

    return {
        "repo": repo,
        "commits": commits,
        "bot_or_agent_commits": bot_or_agent_commits,
        "author_agent_trailers": author_agent_trailers,
        "top_authors": [{"name": name, "commits": count} for name, count in author_counts.most_common(5)],
    }


def fetch_operational_activity(token: str) -> Dict[str, Any]:
    """Fetch real default-branch repo activity by month across configured repos."""
    repos = get_operational_repos()
    months = []
    totals = {
        "commits": 0,
        "bot_or_agent_commits": 0,
        "author_agent_trailers": 0,
    }
    errors = []

    for month_meta in iter_month_ranges():
        repo_rows = []
        month_totals = {
            "month_key": month_meta["month_key"],
            "month": month_meta["month_name"],
            "month_number": month_meta["month"],
            "year": month_meta["year"],
            "commits": 0,
            "bot_or_agent_commits": 0,
            "author_agent_trailers": 0,
            "repos": [],
        }
        for repo in repos:
            row = _count_repo_commits_for_month(token, repo, month_meta)
            repo_rows.append(row)
            if row.get("error"):
                errors.append({"month_key": month_meta["month_key"], "repo": repo, "error": row["error"]})
                continue
            month_totals["commits"] += row["commits"]
            month_totals["bot_or_agent_commits"] += row["bot_or_agent_commits"]
            month_totals["author_agent_trailers"] += row["author_agent_trailers"]

        month_totals["repos"] = repo_rows
        for key in totals:
            totals[key] += month_totals[key]
        months.append(month_totals)

    return {
        "source": "GitHub REST commits API, default branch per repo",
        "repos": repos,
        "months": months,
        "totals": totals,
        "errors": errors[:25],
        "error_count": len(errors),
    }


def main() -> int:
    """
    Main entry point for the script.

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    # Get configuration
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        logger.error("GITHUB_TOKEN environment variable is required")
        return 1

    # Username from args or environment
    username = (
        sys.argv[1] if len(sys.argv) > 1
        else os.environ.get("GITHUB_USERNAME", DEFAULT_USERNAME)
    )

    try:
        stats = fetch_github_stats(token, username)

        # Fetch YTD stats (new keys merged into stats dict)
        try:
            ytd = fetch_ytd_stats(token, username)
            stats.update(ytd)
        except Exception as e:
            logger.warning(f"YTD fetch failed (non-fatal): {e}")

        # Fetch previous month stats
        try:
            prev = fetch_previous_month_stats(token, username)
            stats.update(prev)
        except Exception as e:
            logger.warning(f"Previous month fetch failed (non-fatal): {e}")

        # Fetch all-month profile-attributed stats for permanent ledger.
        try:
            stats["all_months"] = fetch_all_month_profile_stats(token, username)
        except Exception as e:
            logger.warning(f"All-month profile stats fetch failed (non-fatal): {e}")
            stats["all_months_error"] = str(e)

        # Fetch operational repo activity. Use a broader PAT when configured,
        # because the default profile-repo GITHUB_TOKEN cannot read private SoT repos.
        try:
            operational_token = os.environ.get("OPERATIONAL_GITHUB_TOKEN") or token
            stats["operational_activity"] = fetch_operational_activity(operational_token)
        except Exception as e:
            logger.warning(f"Operational activity fetch failed (non-fatal): {e}")
            stats["operational_activity_error"] = str(e)

        print(json.dumps(stats, indent=2))
        return 0
    except Exception as e:
        logger.error(f"Failed to fetch stats: {e}")
        # Output minimal error JSON for downstream handling
        error_output = {
            "error": str(e),
            "username": username,
            "fetched_at": datetime.now(timezone.utc).isoformat()
        }
        print(json.dumps(error_output, indent=2))
        return 1


if __name__ == "__main__":
    sys.exit(main())
