#!/usr/bin/env python3
"""
GitHub Stats Fetcher - Daily README Auto-Update
================================================
Fetches contribution statistics from GitHub GraphQL API for the current month
AND year-to-date totals for the dynamic subtitle.

Usage:
    python get_github_stats.py [username]

Environment:
    GITHUB_TOKEN: GitHub Personal Access Token (required)
    GITHUB_USERNAME: Target username (optional, can be passed as arg)

Output:
    JSON object with contribution statistics to stdout

Author: Jesse Niesen / Liv Hana SI
Version: 2.0.0
"""

import os
import sys
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any
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


def get_date_ranges() -> dict:
    """
    Calculate date ranges for current month and year-to-date.
    """
    now = datetime.now(timezone.utc)
    year = now.year
    month = now.month
    day = now.day

    month_start = datetime(year, month, 1, tzinfo=timezone.utc)
    year_start = datetime(year, 1, 1, tzinfo=timezone.utc)

    if month == 12:
        next_month = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
    else:
        next_month = datetime(year, month + 1, 1, tzinfo=timezone.utc)
    days_in_month = (next_month - month_start).days

    ytd_days = (now - year_start).days + 1

    return {
        "month_start": month_start.isoformat(),
        "year_start": year_start.isoformat(),
        "today": now.isoformat(),
        "day_of_month": day,
        "days_in_month": days_in_month,
        "ytd_days": ytd_days,
    }


def build_graphql_query(username: str, month_start: str, year_start: str, today: str) -> str:
    """
    Build GraphQL query fetching both monthly and YTD stats via aliases.
    """
    return f"""{{
  user(login: "{username}") {{
    monthly: contributionsCollection(from: "{month_start}", to: "{today}") {{
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
    ytd: contributionsCollection(from: "{year_start}", to: "{today}") {{
      contributionCalendar {{
        totalContributions
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
    Returns monthly stats + YTD totals.
    """
    dates = get_date_ranges()

    query = build_graphql_query(
        username,
        dates["month_start"],
        dates["year_start"],
        dates["today"]
    )

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "User-Agent": "readme-stats-bot/2.0"
    }

    data = json.dumps({"query": query}).encode("utf-8")

    request = urllib.request.Request(
        GITHUB_GRAPHQL_URL,
        data=data,
        headers=headers,
        method="POST"
    )

    logger.info(f"Fetching stats for {username} (month: {dates['month_start'][:10]}, ytd: {dates['year_start'][:10]})")

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

    if "errors" in result:
        error_msg = result["errors"][0].get("message", "Unknown error")
        logger.error(f"GraphQL error: {error_msg}")
        raise ValueError(f"GraphQL error: {error_msg}")

    user = result.get("data", {}).get("user")
    if not user:
        raise ValueError(f"User '{username}' not found")

    # Monthly stats
    contrib = user["monthly"]
    calendar = contrib["contributionCalendar"]

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

    total_contributions = calendar["totalContributions"]
    commits = contrib["totalCommitContributions"] + contrib["restrictedContributionsCount"]
    daily_avg = round(total_contributions / max(dates["day_of_month"], 1), 1)
    projected_month = round(daily_avg * dates["days_in_month"])

    # YTD stats
    ytd_total = user["ytd"]["contributionCalendar"]["totalContributions"]
    ytd_daily_avg = round(ytd_total / max(dates["ytd_days"], 1), 1)

    stats = {
        "username": username,
        "month": datetime.now(timezone.utc).strftime("%B"),
        "year": datetime.now(timezone.utc).year,
        "day_of_month": dates["day_of_month"],
        "days_in_month": dates["days_in_month"],
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
        # YTD fields
        "ytd_total": ytd_total,
        "ytd_daily_avg": ytd_daily_avg,
        "ytd_days": dates["ytd_days"],
        "fetched_at": datetime.now(timezone.utc).isoformat()
    }

    logger.info(f"Stats fetched: {total_contributions} monthly, {ytd_total} YTD ({ytd_daily_avg}/day)")

    return stats


def main() -> int:
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        logger.error("GITHUB_TOKEN environment variable is required")
        return 1

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
        error_output = {
            "error": str(e),
            "username": username,
            "fetched_at": datetime.now(timezone.utc).isoformat()
        }
        print(json.dumps(error_output, indent=2))
        return 1


if __name__ == "__main__":
    sys.exit(main())
