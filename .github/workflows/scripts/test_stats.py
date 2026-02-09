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
    get_date_ranges,
    build_graphql_query,
    fetch_github_stats,
)
from compare_l5 import (
    calculate_multiplier,
    compare_to_l5,
    generate_markdown_table,
    generate_ytd_subtitle,
    generate_full_output,
    green,
    green_bold,
    L5_BENCHMARKS,
)
from update_readme import (
    find_insertion_point,
    update_readme_content,
    STATS_START,
    STATS_END,
    YTD_START,
    YTD_END,
)


class TestGetGitHubStats(unittest.TestCase):
    """Tests for get_github_stats.py"""

    def test_get_date_ranges(self):
        """Test that date range calculation returns valid dates"""
        ranges = get_date_ranges()

        self.assertIn("T", ranges["month_start"])
        self.assertIn("T", ranges["year_start"])
        self.assertIn("T", ranges["today"])

        self.assertGreater(ranges["day_of_month"], 0)
        self.assertLessEqual(ranges["day_of_month"], 31)

        self.assertGreaterEqual(ranges["days_in_month"], 28)
        self.assertLessEqual(ranges["days_in_month"], 31)

        self.assertGreater(ranges["ytd_days"], 0)
        self.assertLessEqual(ranges["ytd_days"], 366)

    def test_build_graphql_query(self):
        """Test GraphQL query generation with monthly + YTD aliases"""
        query = build_graphql_query(
            "testuser",
            "2026-02-01T00:00:00+00:00",
            "2026-01-01T00:00:00+00:00",
            "2026-02-03T12:00:00+00:00"
        )

        self.assertIn("testuser", query)
        self.assertIn("monthly:", query)
        self.assertIn("ytd:", query)
        self.assertIn("totalCommitContributions", query)
        self.assertIn("contributionCalendar", query)
        self.assertIn("2026-02-01", query)
        self.assertIn("2026-01-01", query)

    @patch('get_github_stats.urllib.request.urlopen')
    def test_fetch_github_stats_success(self, mock_urlopen):
        """Test successful API response parsing"""
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "data": {
                "user": {
                    "monthly": {
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
                                        {"date": "2026-02-01", "contributionCount": 50},
                                        {"date": "2026-02-02", "contributionCount": 60},
                                        {"date": "2026-02-03", "contributionCount": 40},
                                    ]
                                }
                            ]
                        }
                    },
                    "ytd": {
                        "contributionCalendar": {
                            "totalContributions": 2500
                        }
                    },
                    "repositories": {"totalCount": 25}
                }
            }
        }).encode()
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        stats = fetch_github_stats("fake_token", "testuser")

        self.assertEqual(stats["username"], "testuser")
        self.assertEqual(stats["total_contributions"], 150)
        self.assertEqual(stats["commits"], 150)  # 100 + 50 restricted
        self.assertEqual(stats["pull_requests"], 10)
        self.assertEqual(stats["repo_count"], 25)
        self.assertEqual(stats["ytd_total"], 2500)
        self.assertIn("ytd_daily_avg", stats)

    @patch('get_github_stats.urllib.request.urlopen')
    def test_fetch_github_stats_user_not_found(self, mock_urlopen):
        """Test handling of user not found error"""
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "data": {"user": None}
        }).encode()
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        with self.assertRaises(ValueError) as ctx:
            fetch_github_stats("fake_token", "nonexistent")

        self.assertIn("not found", str(ctx.exception))


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

    def test_green_wrapper(self):
        """Test green LaTeX color wrapper"""
        result = green("hello")
        self.assertIn("#0ab123", result)
        self.assertIn("textsf", result)
        self.assertIn("hello", result)

    def test_green_bold_wrapper(self):
        """Test green bold LaTeX color wrapper"""
        result = green_bold("hello")
        self.assertIn("#0ab123", result)
        self.assertIn("textbf", result)
        self.assertIn("hello", result)

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
        self.assertIn("benchmark_source", result)
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
        """Test markdown table generation with green colors"""
        stats = {
            "month": "February",
            "year": 2026,
            "day_of_month": 3,
            "days_in_month": 28,
            "total_contributions": 275,
            "commits": 200,
            "daily_avg": 91.7,
            "peak_day": {"date": "2026-02-02", "count": 132},
            "daily_breakdown": [
                {"date": "2026-02-01", "count": 41},
                {"date": "2026-02-02", "count": 132},
                {"date": "2026-02-03", "count": 102},
            ]
        }
        comparison = compare_to_l5(stats)
        markdown = generate_markdown_table(stats, comparison)

        self.assertIn("February 2026", markdown)
        self.assertIn("Live Stats", markdown)
        self.assertIn("#0ab123", markdown)
        self.assertIn("Google L5", markdown)
        self.assertIn("132", markdown)
        self.assertIn("Daily Breakdown", markdown)

    def test_generate_ytd_subtitle(self):
        """Test YTD subtitle generation"""
        stats = {
            "ytd_daily_avg": 62.4,
            "ytd_total": 2497,
            "year": 2026
        }
        subtitle = generate_ytd_subtitle(stats)

        self.assertIn("$$", subtitle)
        self.assertIn("#0ab123", subtitle)
        self.assertIn("62.4", subtitle)
        self.assertIn("2{,}497", subtitle)
        self.assertIn("Liv Hanna S.I.", subtitle)

    def test_generate_full_output_with_error(self):
        """Test full output generation with error stats"""
        error_stats = {"error": "User not found", "username": "testuser"}
        result = generate_full_output(error_stats)

        self.assertIn("error", result)
        self.assertIn("Failed to fetch", result["markdown"])
        self.assertEqual(result["ytd_subtitle"], "")

    def test_generate_full_output_success(self):
        """Test full output includes ytd_subtitle"""
        stats = {
            "total_contributions": 275,
            "commits": 200,
            "daily_avg": 91.7,
            "days_active": 3,
            "day_of_month": 3,
            "projected_month": 2567,
            "month": "February",
            "year": 2026,
            "days_in_month": 28,
            "peak_day": {"date": "2026-02-02", "count": 132},
            "daily_breakdown": [],
            "ytd_total": 2500,
            "ytd_daily_avg": 62.5,
        }
        result = generate_full_output(stats)

        self.assertIn("markdown", result)
        self.assertIn("ytd_subtitle", result)
        self.assertIn("$$", result["ytd_subtitle"])


class TestUpdateReadme(unittest.TestCase):
    """Tests for update_readme.py"""

    def test_markers_defined(self):
        """Test that all marker constants are defined"""
        self.assertIn("STATS_START", STATS_START)
        self.assertIn("STATS_END", STATS_END)
        self.assertIn("YTD_START", YTD_START)
        self.assertIn("YTD_END", YTD_END)

    def test_find_insertion_point_with_divider(self):
        """Test insertion point after divider"""
        content = "# Title\n\n---\n\nContent here"
        point = find_insertion_point(content)

        self.assertIsNotNone(point)
        self.assertEqual(content[point:point+7], "\n\nConte")

    def test_find_insertion_point_no_divider(self):
        """Test insertion point after heading when no divider"""
        content = "# Title\n\nContent here"
        point = find_insertion_point(content)
        self.assertIsNotNone(point)

    def test_find_insertion_point_with_markers(self):
        """Test that None is returned when markers exist"""
        content = f"{STATS_START}\nstuff\n{STATS_END}"
        point = find_insertion_point(content)
        self.assertIsNone(point)

    def test_update_readme_content_replace(self):
        """Test replacing existing stats section"""
        original = f"# README\n\n{STATS_START}\nOld stats\n{STATS_END}\n\nFooter\n"
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
        self.assertIn(STATS_START, updated)
        self.assertIn(STATS_END, updated)

    def test_update_readme_content_no_change(self):
        """Test that identical content returns no change"""
        markdown = "Same stats"
        original = f"# README\n\n{STATS_START}\n{markdown}\n{STATS_END}\n"

        updated, was_updated = update_readme_content(original, markdown)
        self.assertFalse(was_updated)

    def test_update_readme_content_with_ytd(self):
        """Test updating both stats and YTD subtitle"""
        original = (
            f"# Title\n{YTD_START}\nOld subtitle\n{YTD_END}\n"
            f"{STATS_START}\nOld stats\n{STATS_END}\n"
        )
        updated, was_updated = update_readme_content(
            original, "New stats", r"$${\color{#0ab123}\textsf{New subtitle}}$$"
        )

        self.assertTrue(was_updated)
        self.assertIn("New stats", updated)
        self.assertIn("New subtitle", updated)
        self.assertNotIn("Old stats", updated)
        self.assertNotIn("Old subtitle", updated)

    def test_update_readme_backslash_in_content(self):
        """Test that backslashes in LaTeX content don't break regex"""
        original = f"{STATS_START}\nold\n{STATS_END}"
        new_md = r"$\color{#0ab123}{\textsf{hello \cdot world}}$"

        updated, was_updated = update_readme_content(original, new_md)
        self.assertTrue(was_updated)
        self.assertIn(r"\cdot", updated)


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
