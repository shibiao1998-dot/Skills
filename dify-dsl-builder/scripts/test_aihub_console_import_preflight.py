#!/usr/bin/env python3
"""Tests for AI Hub console import preflight reporting."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import verify_aihub_console_import as console_import


class AihubConsoleImportPreflightTests(unittest.TestCase):
    def test_masks_console_token_and_hashes_yaml_content(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            dsl_path = Path(tmp_dir) / "demo.yml"
            dsl_text = "app:\n  name: Demo\n  mode: workflow\nworkflow:\n  graph:\n    nodes: []\n    edges: []\n"
            dsl_path.write_text(dsl_text, encoding="utf-8")

            report = console_import.build_yaml_content_import_report(
                yaml_path=dsl_path,
                console_token="console-token-secret-123456",
                base_url=console_import.PROD_CONSOLE_API_BASE_URL,
            )

        serialized = json.dumps(report, ensure_ascii=False, sort_keys=True)
        self.assertEqual(report["classification"], "console_import_ready")
        self.assertEqual(report["request_preview"]["method"], "POST")
        self.assertEqual(report["request_preview"]["path"], "/apps/imports")
        self.assertEqual(report["body_preview"]["mode"], "yaml-content")
        self.assertEqual(report["body_preview"]["yaml_bytes"], len(dsl_text.encode("utf-8")))
        self.assertNotIn("console-token-secret-123456", serialized)
        self.assertNotIn("mode: workflow", serialized)

    def test_missing_console_token_is_environment_preflight(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            dsl_path = Path(tmp_dir) / "demo.yml"
            dsl_path.write_text("app:\n  mode: workflow\n", encoding="utf-8")

            report = console_import.build_yaml_content_import_report(
                yaml_path=dsl_path,
                console_token="",
                base_url=console_import.PROD_CONSOLE_API_BASE_URL,
            )

        self.assertEqual(report["classification"], "environment_preflight")
        self.assertIn("console_token", report["missing_fields"])

    def test_url_import_requires_http_url(self) -> None:
        report = console_import.build_yaml_url_import_report(
            yaml_url="file:///tmp/demo.yml",
            console_token="console-token-secret-123456",
            base_url=console_import.PROD_CONSOLE_API_BASE_URL,
        )

        self.assertEqual(report["classification"], "environment_preflight")
        self.assertIn("yaml_url", report["missing_fields"])

    def test_execute_import_masks_failed_http_response(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            dsl_path = Path(tmp_dir) / "demo.yml"
            dsl_path.write_text("app:\n  mode: workflow\n", encoding="utf-8")

            def fake_transport(request: console_import.ImportRequest) -> console_import.ImportResponse:
                self.assertIn("Bearer ", request.headers["Authorization"])
                self.assertIn("yaml_content", request.body)
                return console_import.ImportResponse(
                    status=401,
                    text='{"code":"unauthorized","message":"Invalid token"}',
                )

            report = console_import.execute_yaml_content_import(
                yaml_path=dsl_path,
                console_token="console-token-secret-123456",
                base_url=console_import.PROD_CONSOLE_API_BASE_URL,
                transport=fake_transport,
            )

        serialized = json.dumps(report, ensure_ascii=False, sort_keys=True)
        self.assertEqual(report["classification"], "console_import_failed")
        self.assertEqual(report["http_status"], 401)
        self.assertNotIn("console-token-secret-123456", serialized)
        self.assertNotIn("mode: workflow", serialized)

    def test_skill_declares_console_import_diagnostic(self) -> None:
        skill_dir = Path(__file__).resolve().parents[1]
        skill_text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
        reference_text = (skill_dir / "references" / "capability-aihub-api-validation.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("scripts/verify_aihub_console_import.py", skill_text)
        self.assertIn("console import", reference_text.lower())


if __name__ == "__main__":
    unittest.main()
