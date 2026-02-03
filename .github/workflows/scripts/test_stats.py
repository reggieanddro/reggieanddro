#!/usr/bin/env python3
"""
Unit Tests for GitHub Stats Workflow Scripts
=============================================
Tests for get_github_stats.py, compare_l5.py, and update_readme.py

Run with:
    python -m pytest test_stats.py -v
    python -m unittest test_stats -v

Author: Jesse Niesen / Liv Hana SI
Version: 1.0.0
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
    build_graphql_query,
    fetch_github_stats,
)
from compare_l5 import (
    calculate_multiplier,
    compare_to_l5,
    generate_markdown_table,
    generate_full_output,
    L5_BENCHMARKS,
)
from update_readme import (
    has_markers,
    find_insertion_point,
    update_readme_content,
    START_MARKER,
    END_MARKER,
)


class TestGetGitHubStats(unittest.TestCase):
    """Tests for get_github_stats.py"""

    def test_get_month_date_range(self):
        """Test that date range calculation returns valid dates"""
        start, end, day, days_in_month = get_month_date_range()

        # Should return ISO format strings
        self.assertIn("T", start)
        self.assertIn("T", end)

        # Day should be positive
        self.assertGreater(day, 0)
        self.assertLessEqual(day, 31)

        # Days in month should be 28-31
        self.assertGreaterEqual(days_in_month, 28)
        self.assertLessEqual(days_in_month, 31)

    def test_build_graphql_query(self):
        """Test GraphQL query generation"""
        query = build_graphql_query(
            "testuser",
            "2026-02-01T00:00:00+00:00",
            "2026-02-03T12:00:00+00:00"
        )

        # Should contain username
        self.assertIn("testuser", query)

        # Should contain contribution fields
        self.assertIn("totalCommitContributions", query)
        self.assertIn("contributionCalendar", query)
        self.assertIn("totalContributions", query)

        # Should contain date range
        self.assertIn("2026-02-01", query)

    @patch('get_github_stats.urllib.request.urlopen')
    def test_fetch_github_stats_success(self, mock_urlopen):
        """Test successful API response parsing"""
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
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
                                        {"date": "2026-02-01", "contributionCount": 50},
                                        {"date": "2026-02-02", "contributionCount": 60},
                                        {"date": "2026-02-03", "contributionCount": 40},
                                    ]
                                }
                            ]
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
        # Exactly at max benchmark
        mult_min, mult_max = calculate_multiplier(80, 40, 80)
        self.assertEqual(mult_min, 1.0)
        self.assertEqual(mult_max, 2.0)

        # Double the max benchmark
        mult_min, mult_max = calculate_multiplier(160, 40, 80)
        self.assertEqual(mult_min, 2.0)
        self.assertEqual(mult_max, 4.0)

        # Zero value
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

        # Should have comparisons
        self.assertIn("comparisons", result)
        self.assertGreater(len(result["comparisons"]), 0)

        # Should have overall multiplier
        self.assertIn("overall_multiplier", result)
        self.assertIsInstance(result["overall_multiplier"], float)

        # Should have benchmark source
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

        # Overall should be above
        self.assertEqual(result["overall_status"], "above")
        self.assertGreater(result["overall_multiplier"], 1.0)

    def test_generate_markdown_table(self):
        """Test markdown table generation"""
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

        # Should contain header
        self.assertIn("February 2026", markdown)
        self.assertIn("Live Stats", markdown)

        # Should contain table
        self.assertIn("| Metric |", markdown)
        self.assertIn("Google L5", markdown)

        # Should contain peak day
        self.assertIn("132", markdown)

        # Should contain daily breakdown
        self.assertIn("Daily Breakdown", markdown)

    def test_generate_full_output_with_error(self):
        """Test full output generation with error stats"""
        error_stats = {
            "error": "User not found",
            "username": "testuser"
        }

        result = generate_full_output(error_stats)

        self.assertIn("error", result)
        self.assertIn("Failed to fetch", result["markdown"])


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
        self.assertEqual(content[point:point+7], "\n\nConte")

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
