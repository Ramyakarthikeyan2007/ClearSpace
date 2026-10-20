"""
test_duplicates.py - Unit Tests for duplicate_finder.py
======================================================
Tests SHA-256 hashing, duplicate grouping, keep recommendations, and savings calculations.
"""

import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from duplicate_finder import (
    apply_keep_strategy,
    calculate_selected_savings,
    compute_sha256,
    find_duplicates,
)
from scanner import scan_folder


class TestDuplicateFinder(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

        (self.root / "folder1").mkdir()
        (self.root / "folder2").mkdir()

        # Synthetic duplicate contents
        self.content_a = b"Identical duplicate data content for group A!" * 20
        self.content_b = b"Distinct duplicate data content for group B!" * 15
        self.content_unique = b"Completely unique data file!" * 10

        # Group 1: 3 identical files
        self.file_a1 = self.root / "doc_original.txt"
        self.file_a2 = self.root / "folder1" / "doc_copy.txt"
        self.file_a3 = self.root / "folder2" / "doc_backup.txt"

        self.file_a1.write_bytes(self.content_a)
        time.sleep(0.01)
        self.file_a2.write_bytes(self.content_a)
        time.sleep(0.01)
        self.file_a3.write_bytes(self.content_a)

        # Group 2: 2 identical files
        self.file_b1 = self.root / "image1.png"
        self.file_b2 = self.root / "folder1" / "image2.png"
        self.file_b1.write_bytes(self.content_b)
        self.file_b2.write_bytes(self.content_b)

        # Unique file
        self.file_unique = self.root / "unique.txt"
        self.file_unique.write_bytes(self.content_unique)

        # 0-byte file (should not be counted as duplicate waste)
        self.file_empty1 = self.root / "empty1.txt"
        self.file_empty2 = self.root / "empty2.txt"
        self.file_empty1.write_bytes(b"")
        self.file_empty2.write_bytes(b"")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_compute_sha256(self):
        """Verify SHA-256 generates identical hashes for identical content and distinct for different."""
        hash_a1 = compute_sha256(str(self.file_a1))
        hash_a2 = compute_sha256(str(self.file_a2))
        hash_b1 = compute_sha256(str(self.file_b1))

        self.assertIsNotNone(hash_a1)
        self.assertEqual(hash_a1, hash_a2)
        self.assertNotEqual(hash_a1, hash_b1)

    def test_find_duplicates(self):
        """Verify grouping of identical files and accurate savings calculation."""
        scan_res = scan_folder(str(self.root), skip_hidden=True)
        dup_res = find_duplicates(scan_res["files"])

        # Should find 2 duplicate groups (Group A with 3 files, Group B with 2 files)
        self.assertEqual(dup_res["total_groups"], 2)

        # Redundant files = (3-1) + (2-1) = 3 redundant files
        self.assertEqual(dup_res["total_redundant_files"], 3)

        # Expected total savings = 2 * len(content_a) + 1 * len(content_b)
        expected_savings = 2 * len(self.content_a) + 1 * len(self.content_b)
        self.assertEqual(dup_res["total_savings_bytes"], expected_savings)

        # Groups should be sorted by potential savings descending
        groups = dup_res["groups"]
        self.assertGreaterEqual(groups[0]["potential_savings_bytes"], groups[1]["potential_savings_bytes"])

    def test_apply_keep_strategy(self):
        """Verify keep strategies mark exactly one file as recommended keep."""
        scan_res = scan_folder(str(self.root), skip_hidden=True)
        dup_res = find_duplicates(scan_res["files"])
        group_a = next(g for g in dup_res["groups"] if g["file_count"] == 3)

        # Strategy: keep_oldest
        files_oldest = apply_keep_strategy(group_a, "keep_oldest")
        kept = [f for f in files_oldest if f["is_recommended_keep"]]
        self.assertEqual(len(kept), 1)
        # Oldest file should be file_a1
        self.assertEqual(kept[0]["path"], str(self.file_a1.resolve()))

        # Strategy: keep_newest
        files_newest = apply_keep_strategy(group_a, "keep_newest")
        kept_newest = [f for f in files_newest if f["is_recommended_keep"]]
        self.assertEqual(len(kept_newest), 1)
        self.assertEqual(kept_newest[0]["path"], str(self.file_a3.resolve()))

        # Strategy: keep_shortest_path
        files_shortest = apply_keep_strategy(group_a, "keep_shortest_path")
        kept_shortest = [f for f in files_shortest if f["is_recommended_keep"]]
        self.assertEqual(len(kept_shortest), 1)
        # file_a1 is in root, which has shorter path than folder1 / folder2
        self.assertEqual(kept_shortest[0]["path"], str(self.file_a1.resolve()))

    def test_calculate_selected_savings_protects_original(self):
        """
        Verify safety rule: If user selects ALL files in a group,
        at least one copy is protected and NOT deleted.
        """
        scan_res = scan_folder(str(self.root), skip_hidden=True)
        dup_res = find_duplicates(scan_res["files"])
        groups = dup_res["groups"]

        # Malicious / Accidental scenario: Select EVERY copy of group A for deletion
        all_group_a_paths = {str(self.file_a1.resolve()), str(self.file_a2.resolve()), str(self.file_a3.resolve())}

        audit = calculate_selected_savings(groups, all_group_a_paths)

        # Should protect 1 file from deletion
        self.assertEqual(len(audit["protected_files"]), 1)
        self.assertEqual(len(audit["files_to_remove"]), 2)
        self.assertEqual(audit["actual_savings_bytes"], 2 * len(self.content_a))


if __name__ == "__main__":
    unittest.main()
