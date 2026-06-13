#!/usr/bin/env python3
"""Tests for AI Hub API preflight reporting."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import verify_aihub_api_preflight as preflight


class AihubApiPreflightTests(unittest.TestCase):
    def test_masks_loaded_credentials_in_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            token_path = Path(tmp_dir) / "bts.txt"
            token_path.write_text("secret-token-1234567890\n", encoding="utf-8")

            report = preflight.build_preflight_report(
                auth_mode="bts",
                auth_value=preflight.load_text_file(token_path),
                bot_id="bot-1234567890",
                user_id="779988",
                sdp_app_id=preflight.DEFAULT_SDP_APP_ID,
                base_url=preflight.PROD_API_BASE_URL,
                endpoint="/v1/workflows/run",
            )

        serialized = json.dumps(report, ensure_ascii=False, sort_keys=True)
        self.assertNotIn("secret-token-1234567890", serialized)
        self.assertNotIn("bot-1234567890", serialized)
        self.assertEqual(report["classification"], "api_validation_ready")
        self.assertEqual(report["headers_preview"]["Authorization"].split(" ", 1)[0], "BTS")
        self.assertEqual(report["headers_preview"]["Content-Type"], "application/json")

    def test_missing_runtime_identity_is_environment_preflight(self) -> None:
        report = preflight.build_preflight_report(
            auth_mode="api-key",
            auth_value="sk-local-secret",
            bot_id="",
            user_id="",
            sdp_app_id=preflight.DEFAULT_SDP_APP_ID,
            base_url=preflight.PROD_API_BASE_URL,
            endpoint="/v1/workflows/run",
        )

        self.assertEqual(report["classification"], "environment_preflight")
        self.assertIn("bot_id", report["missing_fields"])
        self.assertIn("user_id", report["missing_fields"])
        self.assertNotIn("sk-local-secret", json.dumps(report, ensure_ascii=False))

    def test_skill_declares_api_validation_contract(self) -> None:
        skill_dir = Path(__file__).resolve().parents[1]
        skill_text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
        reference_path = skill_dir / "references" / "capability-aihub-api-validation.md"

        self.assertIn("scripts/verify_aihub_api_preflight.py", skill_text)
        self.assertIn("references/capability-aihub-api-validation.md", skill_text)
        self.assertTrue(reference_path.is_file())


if __name__ == "__main__":
    unittest.main()
