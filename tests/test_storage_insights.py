"""
test_storage_insights.py - Unit Tests for storage_insights.py
============================================================
Tests Pandas aggregation, Plotly chart generation, and CSV/JSON export utilities.
"""

import json
import sys
import unittest
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go

sys.path.insert(0, str(Path(__file__).parent.parent))

from storage_insights import (
    create_category_donut_chart,
    create_extension_bar_chart,
    create_largest_files_chart,
    export_report_to_json,
    export_scan_to_csv,
    files_to_dataframe,
    get_category_summary,
    get_extension_summary,
    get_largest_files,
    get_largest_folders,
)


class TestStorageInsights(unittest.TestCase):
    def setUp(self):
        # Sample synthetic file records
        self.sample_files = [
            {
                "path": "C:/demo/photo1.jpg",
                "filename": "photo1.jpg",
                "extension": ".jpg",
                "size_bytes": 204800,  # 200 KB
                "size_human": "200.00 KB",
                "category": "Images",
                "directory": "C:/demo",
                "modified_time": "2026-10-20 10:00:00",
                "modified_timestamp": 1792480800.0,
            },
            {
                "path": "C:/demo/photo2.jpg",
                "filename": "photo2.jpg",
                "extension": ".jpg",
                "size_bytes": 307200,  # 300 KB
                "size_human": "300.00 KB",
                "category": "Images",
                "directory": "C:/demo",
                "modified_time": "2026-10-20 11:00:00",
                "modified_timestamp": 1792484400.0,
            },
            {
                "path": "C:/demo/docs/report.pdf",
                "filename": "report.pdf",
                "extension": ".pdf",
                "size_bytes": 1048576,  # 1 MB
                "size_human": "1.00 MB",
                "category": "Documents",
                "directory": "C:/demo/docs",
                "modified_time": "2026-10-20 12:00:00",
                "modified_timestamp": 1792488000.0,
            },
            {
                "path": "C:/demo/code/script.py",
                "filename": "script.py",
                "extension": ".py",
                "size_bytes": 4096,  # 4 KB
                "size_human": "4.00 KB",
                "category": "Code",
                "directory": "C:/demo/code",
                "modified_time": "2026-10-20 13:00:00",
                "modified_timestamp": 1792491600.0,
            },
        ]
        self.df = files_to_dataframe(self.sample_files)

    def test_files_to_dataframe(self):
        """Verify DataFrame creation and numeric typing."""
        df = self.df
        self.assertFalse(df.empty)
        self.assertEqual(len(df), 4)
        self.assertIn("filename", df.columns)
        self.assertIn("size_bytes", df.columns)
        self.assertTrue(pd.api.types.is_numeric_dtype(df["size_bytes"]))

        # Empty files list handling
        empty_df = files_to_dataframe([])
        self.assertTrue(empty_df.empty)

    def test_category_summary(self):
        """Verify grouping by category, percentage calculation, and sorting."""
        summary = get_category_summary(self.df)
        self.assertEqual(len(summary), 3)  # Images, Documents, Code
        self.assertIn("Category", summary.columns)
        self.assertIn("% of Storage", summary.columns)

        # Largest category by storage is Documents (1 MB)
        self.assertEqual(summary.iloc[0]["Category"], "Documents")
        self.assertEqual(summary.iloc[0]["Files"], 1)

        # Total % should sum to approximately 100%
        total_pct = summary["% of Storage"].sum()
        self.assertAlmostEqual(total_pct, 100.0, delta=0.5)

    def test_extension_summary(self):
        """Verify extension aggregation."""
        ext_sum = get_extension_summary(self.df, top_n=5)
        self.assertEqual(len(ext_sum), 3)  # .pdf, .jpg, .py
        self.assertEqual(ext_sum.iloc[0]["Extension"], ".pdf")

    def test_largest_files_and_folders(self):
        """Verify ranking of largest individual files and folders."""
        largest_files = get_largest_files(self.df, top_n=2)
        self.assertEqual(len(largest_files), 2)
        self.assertEqual(largest_files.iloc[0]["filename"], "report.pdf")

        largest_folders = get_largest_folders(self.df, top_n=2)
        self.assertEqual(len(largest_folders), 2)
        # C:/demo/docs has 1 MB
        self.assertEqual(largest_folders.iloc[0]["Directory"], "C:/demo/docs")

    def test_plotly_chart_generation(self):
        """Verify Plotly charts are constructed as valid figure objects."""
        cat_summary = get_category_summary(self.df)
        ext_summary = get_extension_summary(self.df)
        largest = get_largest_files(self.df)

        fig_donut = create_category_donut_chart(cat_summary)
        self.assertIsInstance(fig_donut, go.Figure)

        fig_bar = create_extension_bar_chart(ext_summary)
        self.assertIsInstance(fig_bar, go.Figure)

        fig_largest = create_largest_files_chart(largest)
        self.assertIsInstance(fig_largest, go.Figure)

    def test_export_utilities(self):
        """Verify CSV and JSON report export formatting."""
        # CSV Export
        csv_str = export_scan_to_csv(self.sample_files)
        self.assertIn("photo1.jpg", csv_str)
        self.assertIn("report.pdf", csv_str)

        # JSON Export
        scan_summary = {
            "folder_path": "C:/demo",
            "total_files": 4,
            "total_size_bytes": 1564072,
            "total_size_human": "1.49 MB",
            "scanned_at": "2026-10-20 14:00:00",
            "errors": [],
        }
        json_str = export_report_to_json(scan_summary)
        parsed = json.loads(json_str)

        self.assertEqual(parsed["report_type"], "ClearSpace Storage & Declutter Report")
        self.assertEqual(parsed["scan_summary"]["total_files"], 4)
        self.assertIn("category_summary", parsed)
        self.assertIn("duplicate_summary", parsed)


if __name__ == "__main__":
    unittest.main()
