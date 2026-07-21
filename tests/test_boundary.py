import importlib.util
import json
import stat
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("verify_boundary", ROOT / "scripts" / "verify_boundary.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class BoundaryTests(unittest.TestCase):
    def setUp(self):
        self.boundary = json.loads((ROOT / "BOUNDARY.json").read_text(encoding="utf-8"))

    def test_live_repository_matches_immutable_boundary(self):
        stats = MODULE.verify(ROOT)
        self.assertEqual(stats["zipArchives"], 74)
        self.assertEqual(stats["zipEntries"], 1593)

    def test_deployable_boundary_is_rejected(self):
        changed = dict(self.boundary, deployableApplication=True)
        with self.assertRaises(MODULE.BoundaryError):
            MODULE.validate_boundary(changed)

    def test_removed_governance_gate_is_rejected(self):
        changed = dict(self.boundary, unresolved=["accountable-owner"])
        with self.assertRaises(MODULE.BoundaryError):
            MODULE.validate_boundary(changed)

    def test_traversal_archive_member_is_rejected(self):
        with self.assertRaises(MODULE.BoundaryError):
            MODULE.safe_archive_member("../../outside", 0, 0)

    def test_windows_absolute_archive_member_is_rejected(self):
        with self.assertRaises(MODULE.BoundaryError):
            MODULE.safe_archive_member("C:\\outside.txt", 0, 0)

    def test_symlink_archive_member_is_rejected(self):
        with self.assertRaises(MODULE.BoundaryError):
            MODULE.safe_archive_member("link", stat.S_IFLNK << 16, 0)

    def test_nested_archive_member_is_rejected(self):
        with self.assertRaises(MODULE.BoundaryError):
            MODULE.safe_archive_member("payload/second.zip", 0, 0)

    def test_regular_archive_member_is_allowed(self):
        MODULE.safe_archive_member("lesson/index.html", stat.S_IFREG << 16, 0)


if __name__ == "__main__":
    unittest.main()
