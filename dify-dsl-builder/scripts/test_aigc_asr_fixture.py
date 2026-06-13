#!/usr/bin/env python3
"""Regression tests for the native speech-recognition fixture."""

from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

import yaml


SKILL_DIR = Path(__file__).resolve().parents[1]
FIXTURE = SKILL_DIR / "assets" / "fixtures" / "aigc-speech-recognition-workflow.yml"
FINGERPRINTS = SKILL_DIR / "references" / "ndhy-aigc-component-fingerprints.json"


class AigcSpeechRecognitionFixtureTests(unittest.TestCase):
    def test_asr_component_fingerprint_uses_exported_canvas_selector(self) -> None:
        fingerprints = json.loads(FINGERPRINTS.read_text(encoding="utf-8"))
        speech_shapes = fingerprints["components"]["speech-recognition"]["model_param_shapes"]

        self.assertIn("doubao-asr-speech2text", speech_shapes)
        self.assertEqual(
            fingerprints["components"]["speech-recognition"]["alias_to_model_id"]["volc.seedasr.auc"],
            "doubao-asr-speech2text",
        )

    def test_asr_fixture_uses_native_speech_recognition_not_model_list_id(self) -> None:
        data = yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))
        nodes = data["workflow"]["graph"]["nodes"]
        node_types = {node["data"]["type"] for node in nodes}
        serialized = json.dumps(data, ensure_ascii=False)

        self.assertIn("speech-recognition", node_types)
        self.assertNotIn("tool", node_types)
        self.assertIn("doubao-asr-speech2text", serialized)
        self.assertNotIn("volc.seedasr.auc", serialized)

    def test_asr_fixture_uses_ui_exported_param_contract(self) -> None:
        data = yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))
        nodes = {node["id"]: node for node in data["workflow"]["graph"]["nodes"]}
        recognizer = nodes["recognize_audio"]["data"]

        self.assertEqual(
            recognizer["model_info"],
            {
                "config_version": "v1",
                "model_id": "doubao-asr-speech2text",
                "model_name": "豆包语音识别",
                "provider": "doubao",
                "provider_name": "豆包",
            },
        )
        self.assertEqual(recognizer["params"]["audio_source"], {"type": "constant", "value": "url"})
        self.assertEqual(recognizer["params"]["audio_file"], {"type": "constant", "value": None})
        self.assertEqual(recognizer["params"]["audio_format"], {"type": "constant", "value": "mp3"})
        self.assertEqual(recognizer["params"]["language"], {"type": "constant", "value": ""})
        self.assertEqual(
            recognizer["params"]["audio_url"],
            {"type": "variable", "value_selector": ["normalize_asr_request", "audio_url"]},
        )
        self.assertNotIn("audio_input_type", recognizer["params"])

    def test_asr_fixture_passes_static_and_aigc_quality_validation(self) -> None:
        result = subprocess.run(
            [
                "python3",
                str(SKILL_DIR / "scripts" / "validate_dify_dsl.py"),
                str(FIXTURE),
                "--model-quality",
                "--aigc-quality",
                "--strict-schema",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
