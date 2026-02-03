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
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional
import urllib.request
import urllib.error

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Constants
GITHUB_GRAPHQL_URL = "https://api.github.com/graphql"
DEFAULT_USERNAME = "reggieanddro"


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
    commits = contrib["totalCommitContributions"] + contrib["restrictedContributionsCount"]
    daily_avg = round(total_contributions / max(day_of_month, 1), 1)
    projected_month = round(daily_avg * days_in_month)

    stats = {
        "username": username,
        "month": datetime.now(timezone.utc).strftime("%B"),
        "year": datetime.now(timezone.utc).year,
        "day_of_month": day_of_month,
        "days_in_month": days_in_month,
        "total_contributions": total_contributions,
        "commits": commits,
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

    logger.info(f"Stats fetched: {total_contributions} contributions, {commits} commits")

    return stats


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
