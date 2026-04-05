#!/usr/bin/env python3
"""
Unit Tests for GitHub Stats Workflow Scripts
=============================================
Tests for get_github_stats.py, compare_l5.py, and update_readme.py

Run with:
    python -m pytest test_stats.py -v
    python -m unittest test_stats -v

Author: Jesse Niesen / Liv Hana SI
Version: 2.0.0
"""

import unittest
import json
import os
import sys
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone

# Import modules to test
from get_github_stats import (
    get_month_date_range,
    get_ytd_date_range,
    get_previous_month_date_range,
    build_graphql_query,
    fetch_github_stats,
    fetch_ytd_stats,
    fetch_previous_month_stats,
)
from compare_l5 import (
    calculate_multiplier,
    compare_to_l5,
    generate_markdown_table,
    generate_full_output,
    generate_ytd_banner,
    generate_archive_section,
    L5_BENCHMARKS,
)
from update_readme import (
    has_markers,
    find_insertion_point,
    update_readme_content,
    update_ytd_content,
    update_archive_content,
    update_section_content,
    START_MARKER,
    END_MARKER,
    YTD_START_MARKER,
    YTD_END_MARKER,
    YTD_MARKER_PATTERN,
    ARCHIVE_START_MARKER,
    ARCHIVE_END_MARKER,
    ARCHIVE_MARKER_PATTERN,
)


# ═══════════════════════════════════════════════════════════════════════════════
# Sample data for reuse across tests
# ═══════════════════════════════════════════════════════════════════════════════

SAMPLE_STATS = {
    "username": "reggieanddro",
    "month": "April",
    "year": 2026,
    "day_of_month": 5,
    "days_in_month": 30,
    "total_contributions": 750,
    "commits": 680,
    "pull_requests": 15,
    "issues": 5,
    "reviews": 8,
    "days_active": 5,
    "daily_avg": 150.0,
    "projected_month": 4500,
    "peak_day": {"date": "2026-04-03", "count": 210},
    "daily_breakdown": [
        {"date": "2026-04-01", "count": 120},
        {"date": "2026-04-02", "count": 145},
        {"date": "2026-04-03", "count": 210},
        {"date": "2026-04-04", "count": 155},
        {"date": "2026-04-05", "count": 120},
    ],
    "repo_count": 30,
    "fetched_at": "2026-04-05T10:20:00+00:00",
    # YTD fields
    "ytd_total": 13500,
    "ytd_commits": 12000,
    "ytd_daily_avg": 142.1,
    "ytd_day_of_year": 95,
    "ytd_streak_current": 45,
    "ytd_year": 2026,
    # Previous month fields
    "prev_month_name": "March",
    "prev_month_year": 2026,
    "prev_month_total": 4200,
    "prev_month_commits": 3800,
    "prev_month_daily_avg": 135.5,
    "prev_month_days_active": 31,
    "prev_month_days_in_month": 31,
    "prev_month_peak_day": {"date": "2026-03-15", "count": 250},
}

MOCK_GRAPHQL_RESPONSE = {
    "data": {
        "user": {
            "contributionsCollection": {
                "totalCommitContributions": 100,
                "totalPullRequestContributions": 10,
                "totalIssueContributions": 5,
                "totalPullRequestReviewContributions": 8,
                "restrictedContributionsCount": 50,
                "contributionCalendar": {
                    "totalContributions": 150,
                    "weeks": [
                        {
                            "contributionDays": [
                                {"date": "2026-04-01", "contributionCount": 50},
                                {"date": "2026-04-02", "contributionCount": 60},
                                {"date": "2026-04-03", "contributionCount": 40},
                            ]
                        }
                    ]
                }
            },
            "repositories": {"totalCount": 25}
        }
    }
}


def _mock_urlopen(response_data):
    """Helper to create a mock urlopen context manager."""
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps(response_data).encode()
    mock_response.__enter__ = lambda s: s
    mock_response.__exit__ = MagicMock(return_value=False)
    return mock_response


class TestGetGitHubStats(unittest.TestCase):
    """Tests for get_github_stats.py"""

    def test_get_month_date_range(self):
        """Test that date range calculation returns valid dates"""
        start, end, day, days_in_month = get_month_date_range()

        self.assertIn("T", start)
        self.assertIn("T", end)
        self.assertGreater(day, 0)
        self.assertLessEqual(day, 31)
        self.assertGreaterEqual(days_in_month, 28)
        self.assertLessEqual(days_in_month, 31)

    def test_get_ytd_date_range(self):
        """Test YTD date range returns Jan 1 to now"""
        year_start, today, day_of_year = get_ytd_date_range()

        self.assertIn("-01-01", year_start)
        self.assertIn("T", today)
        self.assertGreater(day_of_year, 0)
        self.assertLessEqual(day_of_year, 366)

    def test_get_previous_month_date_range(self):
        """Test previous month date range calculation"""
        prev_start, prev_end, month_name, days = get_previous_month_date_range()

        self.assertIn("T", prev_start)
        self.assertIn("T", prev_end)
        self.assertIsInstance(month_name, str)
        self.assertGreater(len(month_name), 0)
        self.assertGreaterEqual(days, 28)
        self.assertLessEqual(days, 31)

    def test_build_graphql_query(self):
        """Test GraphQL query generation"""
        query = build_graphql_query(
            "testuser",
            "2026-02-01T00:00:00+00:00",
            "2026-02-03T12:00:00+00:00"
        )

        self.assertIn("testuser", query)
        self.assertIn("totalCommitContributions", query)
        self.assertIn("contributionCalendar", query)
        self.assertIn("totalContributions", query)
        self.assertIn("2026-02-01", query)

    @patch('get_github_stats.urllib.request.urlopen')
    def test_fetch_github_stats_success(self, mock_urlopen):
        """Test successful API response parsing"""
        mock_urlopen.return_value = _mock_urlopen(MOCK_GRAPHQL_RESPONSE)

        stats = fetch_github_stats("fake_token", "testuser")

        self.assertEqual(stats["username"], "testuser")
        self.assertEqual(stats["total_contributions"], 150)
        self.assertEqual(stats["commits"], 150)  # 100 + 50 restricted
        self.assertEqual(stats["pull_requests"], 10)
        self.assertEqual(stats["repo_count"], 25)

    @patch('get_github_stats.urllib.request.urlopen')
    def test_fetch_github_stats_user_not_found(self, mock_urlopen):
        """Test handling of user not found error"""
        mock_urlopen.return_value = _mock_urlopen({"data": {"user": None}})

        with self.assertRaises(ValueError) as ctx:
            fetch_github_stats("fake_token", "nonexistent")

        self.assertIn("not found", str(ctx.exception))

    @patch('get_github_stats.urllib.request.urlopen')
    def test_fetch_ytd_stats_success(self, mock_urlopen):
        """Test YTD stats fetch with streak calculation"""
        # Response with 3 consecutive active days
        ytd_response = {
            "data": {
                "user": {
                    "contributionsCollection": {
                        "totalCommitContributions": 500,
                        "totalPullRequestContributions": 20,
                        "totalIssueContributions": 10,
                        "totalPullRequestReviewContributions": 15,
                        "restrictedContributionsCount": 200,
                        "contributionCalendar": {
                            "totalContributions": 800,
                            "weeks": [
                                {
                                    "contributionDays": [
                                        {"date": "2026-04-03", "contributionCount": 100},
                                        {"date": "2026-04-04", "contributionCount": 150},
                                        {"date": "2026-04-05", "contributionCount": 120},
                                    ]
                                }
                            ]
                        }
                    },
                    "repositories": {"totalCount": 30}
                }
            }
        }
        mock_urlopen.return_value = _mock_urlopen(ytd_response)

        ytd = fetch_ytd_stats("fake_token", "testuser")

        self.assertEqual(ytd["ytd_total"], 800)
        self.assertEqual(ytd["ytd_commits"], 700)  # 500 + 200
        self.assertGreater(ytd["ytd_daily_avg"], 0)
        self.assertEqual(ytd["ytd_streak_current"], 3)  # 3 consecutive days

    @patch('get_github_stats.urllib.request.urlopen')
    def test_fetch_ytd_stats_streak_with_gap(self, mock_urlopen):
        """Test streak calculation with a zero-day gap"""
        response = {
            "data": {
                "user": {
                    "contributionsCollection": {
                        "totalCommitContributions": 100,
                        "totalPullRequestContributions": 5,
                        "totalIssueContributions": 2,
                        "totalPullRequestReviewContributions": 3,
                        "restrictedContributionsCount": 50,
                        "contributionCalendar": {
                            "totalContributions": 200,
                            "weeks": [
                                {
                                    "contributionDays": [
                                        {"date": "2026-04-01", "contributionCount": 50},
                                        {"date": "2026-04-02", "contributionCount": 0},
                                        {"date": "2026-04-03", "contributionCount": 80},
                                        {"date": "2026-04-04", "contributionCount": 70},
                                    ]
                                }
                            ]
                        }
                    },
                    "repositories": {"totalCount": 20}
                }
            }
        }
        mock_urlopen.return_value = _mock_urlopen(response)

        ytd = fetch_ytd_stats("fake_token", "testuser")

        # Streak should be 2 (04 and 03 are active, 02 breaks it)
        self.assertEqual(ytd["ytd_streak_current"], 2)

    @patch('get_github_stats.urllib.request.urlopen')
    def test_fetch_previous_month_stats_success(self, mock_urlopen):
        """Test previous month stats fetch"""
        mock_urlopen.return_value = _mock_urlopen(MOCK_GRAPHQL_RESPONSE)

        prev = fetch_previous_month_stats("fake_token", "testuser")

        self.assertIn("prev_month_name", prev)
        self.assertEqual(prev["prev_month_total"], 150)
        self.assertEqual(prev["prev_month_commits"], 150)
        self.assertGreater(prev["prev_month_days_active"], 0)


class TestCompareL5(unittest.TestCase):
    """Tests for compare_l5.py"""

    def test_calculate_multiplier(self):
        """Test multiplier calculation"""
        mult_min, mult_max = calculate_multiplier(80, 40, 80)
        self.assertEqual(mult_min, 1.0)
        self.assertEqual(mult_max, 2.0)

        mult_min, mult_max = calculate_multiplier(160, 40, 80)
        self.assertEqual(mult_min, 2.0)
        self.assertEqual(mult_max, 4.0)

        mult_min, mult_max = calculate_multiplier(0, 40, 80)
        self.assertEqual(mult_min, 0.0)
        self.assertEqual(mult_max, 0.0)

    def test_calculate_multiplier_zero_benchmark(self):
        """Test handling of zero benchmark values"""
        mult_min, mult_max = calculate_multiplier(100, 0, 0)
        self.assertEqual(mult_min, 0.0)
        self.assertEqual(mult_max, 0.0)

    def test_compare_to_l5(self):
        """Test L5 comparison with sample data"""
        stats = {
            "total_contributions": 275,
            "commits": 200,
            "daily_avg": 91.7,
            "days_active": 3,
            "pull_requests": 15,
            "day_of_month": 3,
            "projected_month": 2567
        }

        result = compare_to_l5(stats)

        self.assertIn("comparisons", result)
        self.assertGreater(len(result["comparisons"]), 0)
        self.assertIn("overall_multiplier", result)
        self.assertIsInstance(result["overall_multiplier"], float)
        self.assertIn("Worklytics", result["benchmark_source"])

    def test_compare_to_l5_high_performer(self):
        """Test that high performers show 'above' status"""
        stats = {
            "total_contributions": 1000,
            "commits": 800,
            "daily_avg": 100,
            "days_active": 30,
            "pull_requests": 50,
            "day_of_month": 10,
            "projected_month": 3000
        }

        result = compare_to_l5(stats)

        self.assertEqual(result["overall_status"], "above")
        self.assertGreater(result["overall_multiplier"], 1.0)

    def test_generate_markdown_table(self):
        """Test markdown table generation"""
        comparison = compare_to_l5(SAMPLE_STATS)
        markdown = generate_markdown_table(SAMPLE_STATS, comparison)

        self.assertIn("April 2026", markdown)
        self.assertIn("Live Stats", markdown)
        self.assertIn("| Metric |", markdown)
        self.assertIn("Google L5", markdown)
        self.assertIn("210", markdown)  # peak day
        self.assertIn("Daily Breakdown", markdown)

    def test_generate_markdown_table_with_streak(self):
        """Test markdown includes streak when present"""
        comparison = compare_to_l5(SAMPLE_STATS)
        markdown = generate_markdown_table(SAMPLE_STATS, comparison)

        self.assertIn("Current Streak", markdown)
        self.assertIn("45", markdown)

    def test_generate_markdown_table_with_mom(self):
        """Test markdown includes MoM trend when prev month data present"""
        comparison = compare_to_l5(SAMPLE_STATS)
        markdown = generate_markdown_table(SAMPLE_STATS, comparison)

        self.assertIn("MoM Trend", markdown)
        self.assertIn("March", markdown)

    def test_generate_markdown_table_ct_timezone(self):
        """Test that timestamp uses CT timezone"""
        comparison = compare_to_l5(SAMPLE_STATS)
        markdown = generate_markdown_table(SAMPLE_STATS, comparison)

        self.assertIn("CT", markdown)
        self.assertNotIn("UTC", markdown)

    def test_generate_full_output_with_error(self):
        """Test full output generation with error stats"""
        error_stats = {
            "error": "User not found",
            "username": "testuser"
        }

        result = generate_full_output(error_stats)

        self.assertIn("error", result)
        self.assertIn("Failed to fetch", result["markdown"])

    def test_generate_ytd_banner(self):
        """Test YTD banner generation"""
        banner = generate_ytd_banner(SAMPLE_STATS)

        self.assertIn("2026 Year-to-Date", banner)
        self.assertIn("142.1", banner)  # daily avg
        self.assertIn("13,500", banner)  # YTD total
        self.assertIn("Day 95", banner)
        self.assertIn("45-day streak", banner)
        self.assertIn("annualized vs L5", banner)

    def test_generate_ytd_banner_no_data(self):
        """Test YTD banner with minimal data"""
        minimal = {"ytd_total": 0, "ytd_daily_avg": 0, "ytd_streak_current": 0}
        banner = generate_ytd_banner(minimal)

        self.assertIn("Year-to-Date", banner)
        self.assertIn("0 YTD", banner)

    def test_generate_archive_section(self):
        """Test archive section generation"""
        archive = generate_archive_section(SAMPLE_STATS)

        self.assertIn("March 2026", archive)
        self.assertIn("4,200", archive)  # total
        self.assertIn("<details>", archive)
        self.assertIn("</details>", archive)
        self.assertIn("135.5", archive)  # daily avg
        self.assertIn("250", archive)  # peak day count

    def test_generate_archive_section_no_data(self):
        """Test archive section returns empty when no prev month data"""
        minimal = {"prev_month_name": "", "prev_month_total": 0}
        archive = generate_archive_section(minimal)

        self.assertEqual(archive, "")

    def test_generate_archive_section_partial_data(self):
        """Test archive with data but no peak"""
        partial = {
            "prev_month_name": "February",
            "prev_month_year": 2026,
            "prev_month_total": 3000,
            "prev_month_commits": 2500,
            "prev_month_daily_avg": 107.1,
            "prev_month_days_active": 28,
            "prev_month_days_in_month": 28,
            "prev_month_peak_day": {},
        }
        archive = generate_archive_section(partial)

        self.assertIn("February 2026", archive)
        self.assertIn("3,000", archive)


class TestUpdateReadme(unittest.TestCase):
    """Tests for update_readme.py"""

    def test_has_markers_present(self):
        """Test marker detection when present"""
        content = f"""
# README

{START_MARKER}
Old stats here
{END_MARKER}

More content
"""
        self.assertTrue(has_markers(content))

    def test_has_markers_missing(self):
        """Test marker detection when missing"""
        content = "# README\n\nNo markers here"
        self.assertFalse(has_markers(content))

    def test_has_markers_partial(self):
        """Test marker detection with only one marker"""
        content = f"# README\n\n{START_MARKER}\n\nNo end marker"
        self.assertFalse(has_markers(content))

    def test_find_insertion_point_with_divider(self):
        """Test insertion point after divider"""
        content = "# Title\n\n---\n\nContent here"
        point = find_insertion_point(content)

        self.assertIsNotNone(point)
        # Insertion point is right after "---" — remaining content starts with newlines
        self.assertIn("Content", content[point:])

    def test_find_insertion_point_no_divider(self):
        """Test insertion point after heading when no divider"""
        content = "# Title\n\nContent here"
        point = find_insertion_point(content)

        self.assertIsNotNone(point)

    def test_find_insertion_point_with_markers(self):
        """Test that None is returned when markers exist"""
        content = f"{START_MARKER}\nstuff\n{END_MARKER}"
        point = find_insertion_point(content)
        self.assertIsNone(point)

    def test_update_readme_content_replace(self):
        """Test replacing existing stats section"""
        original = f"""# README

{START_MARKER}
Old stats
{END_MARKER}

Footer
"""
        new_markdown = "New amazing stats!"

        updated, was_updated = update_readme_content(original, new_markdown)

        self.assertTrue(was_updated)
        self.assertIn("New amazing stats!", updated)
        self.assertNotIn("Old stats", updated)
        self.assertIn("Footer", updated)

    def test_update_readme_content_insert(self):
        """Test inserting stats when markers don't exist"""
        original = "# README\n\n---\n\nContent"
        new_markdown = "Brand new stats!"

        updated, was_updated = update_readme_content(original, new_markdown)

        self.assertTrue(was_updated)
        self.assertIn("Brand new stats!", updated)
        self.assertIn(START_MARKER, updated)
        self.assertIn(END_MARKER, updated)

    def test_update_readme_content_no_change(self):
        """Test that identical content returns no change"""
        markdown = "Same stats"
        original = f"""# README

{START_MARKER}
{markdown}
{END_MARKER}
"""

        updated, was_updated = update_readme_content(original, markdown)

        self.assertFalse(was_updated)

    def test_update_ytd_content(self):
        """Test YTD section update"""
        original = f"""# README

{YTD_START_MARKER}
Old YTD
{YTD_END_MARKER}

{START_MARKER}
Stats
{END_MARKER}
"""
        new_ytd = "### 2026 Year-to-Date\n142.1 per day"

        updated, was_updated = update_ytd_content(original, new_ytd)

        self.assertTrue(was_updated)
        self.assertIn("142.1 per day", updated)
        self.assertNotIn("Old YTD", updated)
        # Stats section should be preserved
        self.assertIn("Stats", updated)

    def test_update_ytd_content_no_markers(self):
        """Test YTD update skips when markers not present"""
        original = "# README\n\nNo markers"
        updated, was_updated = update_ytd_content(original, "YTD content")

        self.assertFalse(was_updated)
        self.assertEqual(updated, original)

    def test_update_archive_content(self):
        """Test archive section update"""
        original = f"""# README

{ARCHIVE_START_MARKER}
Old archive
{ARCHIVE_END_MARKER}
"""
        new_archive = "<details><summary>March 2026</summary>Content</details>"

        updated, was_updated = update_archive_content(original, new_archive)

        self.assertTrue(was_updated)
        self.assertIn("March 2026", updated)
        self.assertNotIn("Old archive", updated)

    def test_update_archive_content_no_markers(self):
        """Test archive update skips when markers not present"""
        original = "# README\n\nNo markers"
        updated, was_updated = update_archive_content(original, "Archive content")

        self.assertFalse(was_updated)

    def test_multiple_section_updates(self):
        """Test updating all sections in sequence"""
        original = f"""# README

{YTD_START_MARKER}
Old YTD
{YTD_END_MARKER}

{START_MARKER}
Old stats
{END_MARKER}

{ARCHIVE_START_MARKER}
Old archive
{ARCHIVE_END_MARKER}
"""
        # Update stats
        content, _ = update_readme_content(original, "New stats")
        # Update YTD
        content, _ = update_ytd_content(content, "New YTD")
        # Update archive
        content, _ = update_archive_content(content, "New archive")

        self.assertIn("New stats", content)
        self.assertIn("New YTD", content)
        self.assertIn("New archive", content)
        self.assertNotIn("Old stats", content)
        self.assertNotIn("Old YTD", content)
        self.assertNotIn("Old archive", content)


class TestL5Benchmarks(unittest.TestCase):
    """Tests for L5 benchmark constants"""

    def test_benchmarks_structure(self):
        """Test that benchmarks have required structure"""
        required_keys = ["min", "max", "description"]

        for metric, data in L5_BENCHMARKS.items():
            for key in required_keys:
                self.assertIn(key, data, f"Missing {key} in {metric}")

    def test_benchmarks_valid_ranges(self):
        """Test that benchmark min < max"""
        for metric, data in L5_BENCHMARKS.items():
            self.assertLess(
                data["min"], data["max"],
                f"Invalid range for {metric}: {data['min']} >= {data['max']}"
            )

    def test_commits_benchmark_values(self):
        """Test specific commits benchmark (from Worklytics 2025)"""
        commits = L5_BENCHMARKS["commits_per_month"]
        self.assertEqual(commits["min"], 40)
        self.assertEqual(commits["max"], 80)


if __name__ == "__main__":
    unittest.main(verbosity=2)
