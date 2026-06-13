#!/usr/bin/env python3
"""Regression tests for the native 3D generation fixture."""

from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

import yaml


SKILL_DIR = Path(__file__).resolve().parents[1]
FIXTURE = SKILL_DIR / "assets" / "fixtures" / "aigc-3d-resource-workflow.yml"
FINGERPRINTS = SKILL_DIR / "references" / "ndhy-aigc-component-fingerprints.json"


class Aigc3DGenerationFixtureTests(unittest.TestCase):
    def test_3d_component_fingerprint_uses_aihub_renderable_node_type(self) -> None:
        fingerprints = json.loads(FINGERPRINTS.read_text(encoding="utf-8"))

        self.assertIn("model-3d-generation", fingerprints["components"])
        self.assertNotIn("3d-resource-generation", fingerprints["components"])
        self.assertEqual(
            fingerprints["components"]["model-3d-generation"]["node_type"],
            "model-3d-generation",
        )

    def test_3d_fixture_uses_native_model_3d_generation_type(self) -> None:
        data = yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))
        nodes = data["workflow"]["graph"]["nodes"]
        node_types = {node["data"]["type"] for node in nodes}
        serialized = json.dumps(data, ensure_ascii=False)

        self.assertIn("model-3d-generation", node_types)
        self.assertNotIn("3d-resource-generation", node_types)
        self.assertNotIn("tool", node_types)
        self.assertIn("hunyuan-3d-3.1-pro-text", serialized)
        self.assertIn("Prompt", serialized)
        self.assertIn("GenerateType", serialized)
        self.assertNotIn("tencent-hunyuan-3d-3.1-resource-pro", serialized)

    def test_3d_fixture_edge_types_match_renderable_node_type(self) -> None:
        data = yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))
        edges = data["workflow"]["graph"]["edges"]
        edge_blob = json.dumps(edges, ensure_ascii=False)

        self.assertIn("model-3d-generation", edge_blob)
        self.assertNotIn("3d-resource-generation", edge_blob)

    def test_3d_downstream_uses_only_aihub_valid_model_output(self) -> None:
        data = yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))
        nodes = data["workflow"]["graph"]["nodes"]
        normalize_output = next(node for node in nodes if node["id"] == "normalize_3d_output")
        variables = {
            tuple(variable["value_selector"]): variable["value_type"]
            for variable in normalize_output["data"]["variables"]
        }

        self.assertEqual(variables[("generate_3d_asset", "models")], "array[file]")
        self.assertNotIn(("generate_3d_asset", "resources"), variables)
        self.assertNotIn(("generate_3d_asset", "files"), variables)

    def test_3d_fixture_passes_static_and_aigc_quality_validation(self) -> None:
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
