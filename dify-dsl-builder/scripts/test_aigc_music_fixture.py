#!/usr/bin/env python3
"""Regression tests for the native music audio fixture."""

from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml


SKILL_DIR = Path(__file__).resolve().parents[1]
FIXTURE = SKILL_DIR / "assets" / "fixtures" / "aigc-music-audio-workflow.yml"
FINGERPRINTS = SKILL_DIR / "references" / "ndhy-aigc-component-fingerprints.json"


class AigcMusicAudioFixtureTests(unittest.TestCase):
    def test_suno_component_fingerprint_has_matching_native_fixture(self) -> None:
        fingerprints = json.loads(FINGERPRINTS.read_text(encoding="utf-8"))
        audio_shapes = fingerprints["components"]["audio-generation"]["model_param_shapes"]
        self.assertIn("suno-v5-music_generate", audio_shapes)
        self.assertTrue(
            FIXTURE.exists(),
            "suno-v5-music_generate fingerprint must ship a matching native fixture",
        )

    def test_music_fixture_uses_native_audio_generation_not_packaged_tool(self) -> None:
        data = yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))
        nodes = data["workflow"]["graph"]["nodes"]
        node_types = {node["data"]["type"] for node in nodes}
        self.assertIn("audio-generation", node_types)
        self.assertNotIn("tool", node_types)
        serialized = json.dumps(data, ensure_ascii=False)
        self.assertIn("suno-v5-music_generate", serialized)
        self.assertNotIn("model_id: suno-v5\n", FIXTURE.read_text(encoding="utf-8"))
        self.assertNotIn("suno_instrumental_tool", serialized)

    def test_music_fixture_uses_ui_valid_music_selector_and_runtime_safe_switch(self) -> None:
        data = yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))
        nodes = {node["id"]: node for node in data["workflow"]["graph"]["nodes"]}
        normalizer = nodes["normalize_music_request"]["data"]
        generator = nodes["generate_music_audio"]["data"]

        self.assertEqual(
            generator["model_info"],
            {
                "capability": "music_generate",
                "config_version": "v1",
                "model_id": "suno-v5-music_generate",
                "model_name": "Suno V5",
                "provider": "suno",
                "provider_name": "Suno",
            },
        )
        self.assertNotIn("instrumental_bool", normalizer["outputs"])
        self.assertFalse(
            any(spec.get("type") == "boolean" for spec in normalizer["outputs"].values()),
            "AI Hub runtime rejects CodeNodeData outputs.*.type: boolean",
        )
        self.assertEqual(
            generator["params"]["instrumental"],
            {"type": "constant", "value": True},
        )
        self.assertEqual(generator["params"]["customMode"], {"type": "constant", "value": True})
        self.assertIn("promptLyrics", generator["params"])
        self.assertIn("promptDescription", generator["params"])
        self.assertEqual(generator["params"]["vocalGender"], {"type": "constant", "value": ""})

    def test_music_normalizer_respects_suno_negative_tag_limit(self) -> None:
        data = yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))
        nodes = {node["id"]: node for node in data["workflow"]["graph"]["nodes"]}
        code = nodes["normalize_music_request"]["data"]["code"]
        script = (
            code
            + "\nconst result = main({"
            + "music_brief:'小学科学水循环课堂导入背景音乐',"
            + "planned_negative_tags:'"
            + ("low quality noisy distorted excessive reverb off key bad mix " * 20)
            + "'"
            + "});\nconsole.log(JSON.stringify(result));\n"
        )
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".js", delete=False) as f:
            f.write(script)
            script_path = Path(f.name)
        try:
            result = subprocess.run(
                ["node", str(script_path)],
                check=False,
                capture_output=True,
                text=True,
            )
        finally:
            script_path.unlink(missing_ok=True)

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertLessEqual(len(payload["negativeTags"]), 200)

    def test_music_normalizer_maps_vocal_gender_to_runtime_enum(self) -> None:
        data = yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))
        nodes = {node["id"]: node for node in data["workflow"]["graph"]["nodes"]}
        code = nodes["normalize_music_request"]["data"]["code"]
        script = (
            code
            + "\nconst male = main({music_brief:'国风歌曲', vocal_gender:'男', instrumental_mode:'false'});"
            + "\nconst female = main({music_brief:'国风歌曲', vocal_gender:'女', instrumental_mode:'false'});"
            + "\nconst instrumental = main({music_brief:'纯音乐BGM', vocal_gender:'女', instrumental_mode:'true'});"
            + "\nconsole.log(JSON.stringify({male: male.vocalGender, female: female.vocalGender, instrumental: instrumental.vocalGender}));\n"
        )
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".js", delete=False) as f:
            f.write(script)
            script_path = Path(f.name)
        try:
            result = subprocess.run(
                ["node", str(script_path)],
                check=False,
                capture_output=True,
                text=True,
            )
        finally:
            script_path.unlink(missing_ok=True)

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload, {"male": "m", "female": "f", "instrumental": ""})

    def test_music_fixture_passes_static_and_aigc_quality_validation(self) -> None:
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
