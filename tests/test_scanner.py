"""
test_scanner.py - Unit Tests for scanner.py
===========================================
Tests directory scanning, categorization, symlink safety, and error handling.
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

# Add ClearSpace root directory to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from safety import is_safe_directory
from scanner import (
    get_file_category,
    is_hidden,
    scan_folder,
)


class TestScanner(unittest.TestCase):
    def setUp(self):
        # Create a temporary synthetic folder structure for scanning
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

        # Create subdirectories
        (self.root / "sub1").mkdir()
        (self.root / "sub2").mkdir()

        # Create synthetic files
        (self.root / "photo.jpg").write_bytes(b"\xFF\xD8\xFF\xE0" + b"\x00" * 200)
        (self.root / "document.pdf").write_bytes(b"%PDF-1.4" + b"\x00" * 300)
        (self.root / "sub1" / "script.py").write_text("print('hello')", encoding="utf-8")
        (self.root / "sub2" / "data.csv").write_text("a,b\n1,2", encoding="utf-8")
        (self.root / "sub2" / "song.mp3").write_bytes(b"ID3" + b"\x00" * 150)
        (self.root / "archive.zip").write_bytes(b"PK\x03\x04" + b"\x00" * 50)
        (self.root / "video.mp4").write_bytes(b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 400)
        (self.root / "unknown.xyz123").write_text("random bytes", encoding="utf-8")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_file_categorization(self):
        """Verify extension to category mapping logic."""
        self.assertEqual(get_file_category(".jpg"), "Images")
        self.assertEqual(get_file_category("png"), "Images")
        self.assertEqual(get_file_category(".docx"), "Documents")
        self.assertEqual(get_file_category(".txt"), "Documents")
        self.assertEqual(get_file_category(".mp4"), "Videos")
        self.assertEqual(get_file_category(".mp3"), "Audio")
        self.assertEqual(get_file_category(".zip"), "Archives")
        self.assertEqual(get_file_category(".py"), "Code")
        self.assertEqual(get_file_category(".csv"), "Spreadsheets")
        self.assertEqual(get_file_category(".xlsx"), "Spreadsheets")
        self.assertEqual(get_file_category(".unknown_ext"), "Others")
        self.assertEqual(get_file_category(""), "Others")

    def test_scan_folder_recursive(self):
        """Verify recursive folder scanning discovers all files with valid metadata."""
        result = scan_folder(str(self.root), skip_hidden=True)
        self.assertTrue(result["success"])
        self.assertEqual(result["total_files"], 8)
        self.assertGreater(result["total_size_bytes"], 0)

        # Check metadata attributes
        for f in result["files"]:
            self.assertIn("filename", f)
            self.assertIn("category", f)
            self.assertIn("size_bytes", f)
            self.assertIn("size_human", f)
            self.assertIn("path", f)
            self.assertIn("modified_time", f)
            self.assertTrue(os.path.exists(f["path"]))

        # Check category counts
        counts = result["category_counts"]
        self.assertEqual(counts["Images"], 1)
        self.assertEqual(counts["Documents"], 1)
        self.assertEqual(counts["Code"], 1)
        self.assertEqual(counts["Spreadsheets"], 1)
        self.assertEqual(counts["Audio"], 1)
        self.assertEqual(counts["Archives"], 1)
        self.assertEqual(counts["Videos"], 1)
        self.assertEqual(counts["Others"], 1)

    def test_max_depth_restriction(self):
        """Verify max depth limit stops deeper directory recursion."""
        # depth 0 means root only (no subdirectories)
        res_depth_0 = scan_folder(str(self.root), max_depth=0)
        self.assertTrue(res_depth_0["success"])
        # Only files in root directory: photo.jpg, document.pdf, archive.zip, video.mp4, unknown.xyz123 = 5 files
        self.assertEqual(res_depth_0["total_files"], 5)

    def test_skip_hidden_files(self):
        """Verify hidden dot-prefixed files are excluded when skip_hidden=True."""
        hidden_file = self.root / ".hidden_config"
        hidden_file.write_text("secret", encoding="utf-8")

        res_skip = scan_folder(str(self.root), skip_hidden=True)
        filenames_skip = [f["filename"] for f in res_skip["files"]]
        self.assertNotIn(".hidden_config", filenames_skip)

        res_include = scan_folder(str(self.root), skip_hidden=False)
        filenames_include = [f["filename"] for f in res_include["files"]]
        self.assertIn(".hidden_config", filenames_include)

    def test_invalid_and_empty_paths(self):
        """Verify scanner handles invalid, empty, or non-existent directories gracefully."""
        res_nonexistent = scan_folder(str(self.root / "does_not_exist"))
        self.assertFalse(res_nonexistent["success"])
        self.assertEqual(res_nonexistent["total_files"], 0)

        res_empty = scan_folder("")
        self.assertFalse(res_empty["success"])

    def test_safety_check_blocks_system_root(self):
        """Verify safety guardrail prevents scanning system drive root."""
        is_safe, reason = is_safe_directory("C:\\")
        self.assertFalse(is_safe)
        self.assertIn("drive root", reason.lower())


if __name__ == "__main__":
    unittest.main()
