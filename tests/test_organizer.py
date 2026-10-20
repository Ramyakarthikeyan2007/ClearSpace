"""
test_organizer.py - Unit Tests for organizer.py & safety.py
==========================================================
Tests organization planning, collision avoidance, dry-run safety, and execution.
"""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from organizer import (
    execute_organization_plan,
    generate_organization_plan,
)
from safety import (
    get_safe_destination,
    safe_delete_file,
    safe_move_file,
    validate_move_path,
)
from scanner import scan_folder


class TestOrganizer(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

        # Source files
        self.src_dir = self.root / "Source"
        self.src_dir.mkdir()
        (self.src_dir / "subfolder").mkdir()

        self.img1 = self.src_dir / "sunset.jpg"
        self.img1.write_bytes(b"JPG_DATA_1")

        self.doc1 = self.src_dir / "resume.pdf"
        self.doc1.write_bytes(b"PDF_DATA_1")

        # Second file with same name in subfolder
        self.doc2 = self.src_dir / "subfolder" / "resume.pdf"
        self.doc2.write_bytes(b"PDF_DATA_2_DIFFERENT")

        self.code1 = self.src_dir / "app.py"
        self.code1.write_text("print(1)", encoding="utf-8")

        self.dest_dir = self.root / "Target_Organized"

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_collision_avoidance_renaming(self):
        """Verify get_safe_destination appends numerical indices without overwriting."""
        self.dest_dir.mkdir(parents=True, exist_ok=True)
        sample = self.dest_dir / "report.docx"
        sample.write_text("existing", encoding="utf-8")

        # Next destination should be report (1).docx
        dest_1 = get_safe_destination(self.dest_dir, "report.docx")
        self.assertEqual(dest_1.name, "report (1).docx")

        # If report (1).docx also exists, it should be report (2).docx
        dest_1.write_text("first collision", encoding="utf-8")
        dest_2 = get_safe_destination(self.dest_dir, "report.docx")
        self.assertEqual(dest_2.name, "report (2).docx")

    def test_organization_plan_preview(self):
        """Verify organization plan previews correct destinations and detects name collisions."""
        scan_res = scan_folder(str(self.src_dir))
        plan = generate_organization_plan(
            files=scan_res["files"],
            target_base_dir=self.dest_dir,
            selected_categories=["Images", "Documents", "Code"],
        )

        self.assertTrue(plan["is_valid"])
        self.assertEqual(plan["total_active_moves"], 4)

        # Both doc1 and doc2 are named 'resume.pdf' -> collision avoidance must trigger!
        doc_moves = [m for m in plan["active_moves"] if m["category"] == "Documents"]
        self.assertEqual(len(doc_moves), 2)

        # One should be resume.pdf and the other resume (1).pdf
        dest_names = {m["target_filename"] for m in doc_moves}
        self.assertIn("resume.pdf", dest_names)
        self.assertIn("resume (1).pdf", dest_names)
        self.assertEqual(plan["collisions_avoided"], 1)

    def test_dry_run_does_not_modify_disk(self):
        """Verify dry-run mode strictly prevents any changes to the disk."""
        scan_res = scan_folder(str(self.src_dir))
        plan = generate_organization_plan(
            files=scan_res["files"],
            target_base_dir=self.dest_dir,
        )

        # Execute in dry-run mode
        exec_res = execute_organization_plan(plan, dry_run=True)
        self.assertTrue(exec_res["dry_run"])
        self.assertEqual(exec_res["success_count"], 4)

        # Verify target directory was NOT created and source files still exist intact
        self.assertTrue(self.img1.exists())
        self.assertTrue(self.doc1.exists())
        self.assertTrue(self.doc2.exists())
        self.assertTrue(self.code1.exists())
        self.assertFalse(self.dest_dir.exists())

    def test_live_organization_execution(self):
        """Verify live execution successfully moves files into categorized folders."""
        scan_res = scan_folder(str(self.src_dir))
        plan = generate_organization_plan(
            files=scan_res["files"],
            target_base_dir=self.dest_dir,
        )

        exec_res = execute_organization_plan(plan, dry_run=False)
        self.assertFalse(exec_res["dry_run"])
        self.assertEqual(exec_res["success_count"], 4)
        self.assertEqual(exec_res["error_count"], 0)

        # Check organized destinations
        organized_img = self.dest_dir / "Images" / "sunset.jpg"
        organized_code = self.dest_dir / "Code" / "app.py"
        organized_doc1 = self.dest_dir / "Documents" / "resume.pdf"
        organized_doc2 = self.dest_dir / "Documents" / "resume (1).pdf"

        self.assertTrue(organized_img.exists())
        self.assertTrue(organized_code.exists())
        self.assertTrue(organized_doc1.exists())
        self.assertTrue(organized_doc2.exists())

        # Original files should no longer be at original locations
        self.assertFalse(self.img1.exists())
        self.assertFalse(self.code1.exists())

    def test_validate_move_path_boundaries(self):
        """Verify path traversal outside authorized base folder is rejected."""
        safe_src = self.root / "file.txt"
        safe_src.write_text("test")

        unauthorized_dst = self.root.parent / "Forbidden"

        is_valid, reason = validate_move_path(safe_src, unauthorized_dst, allowed_base_dir=self.root)
        self.assertFalse(is_valid)
        self.assertIn("outside the authorized", reason.lower())


if __name__ == "__main__":
    unittest.main()
