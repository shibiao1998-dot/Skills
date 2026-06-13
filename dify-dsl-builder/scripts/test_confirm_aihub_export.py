#!/usr/bin/env python3
"""Regression tests for confirming AI Hub DSL exports saved through Chrome."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path

import confirm_aihub_export


class ConfirmAihubExportTests(unittest.TestCase):
    def test_selects_newest_matching_yaml_and_hashes_it(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            old_file = root / "E2E-test (1).yml"
            new_file = root / "E2E-test (2).yml"
            ignored = root / "notes.txt"

            old_file.write_text("app: old\n", encoding="utf-8")
            new_content = "app: newest\n"
            new_file.write_text(new_content, encoding="utf-8")
            ignored.write_text("not yaml\n", encoding="utf-8")
            os.utime(old_file, (1000, 1000))
            os.utime(new_file, (2000, 2000))

            report = confirm_aihub_export.confirm_export(
                [root],
                name_contains=["E2E-test"],
            )

            self.assertEqual(report["path"], str(new_file))
            self.assertEqual(report["matched_count"], 2)
            self.assertEqual(
                report["sha256"],
                hashlib.sha256(new_content.encode("utf-8")).hexdigest(),
            )
            self.assertEqual(report["size_bytes"], len(new_content.encode("utf-8")))

    def test_json_output_is_stable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            export_file = root / "workflow.yml"
            export_file.write_text("kind: app\n", encoding="utf-8")

            exit_code, output = confirm_aihub_export.run_cli(
                ["--dir", str(root), "--json"],
            )

            self.assertEqual(exit_code, 0, output)
            payload = json.loads(output)
            self.assertEqual(payload["path"], str(export_file))
            self.assertEqual(payload["matched_count"], 1)

    def test_returns_clear_failure_when_no_yaml_exists(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            exit_code, output = confirm_aihub_export.run_cli(["--dir", tmp])

            self.assertEqual(exit_code, 2)
            self.assertIn("No exported DSL YAML found", output)


if __name__ == "__main__":
    unittest.main()
