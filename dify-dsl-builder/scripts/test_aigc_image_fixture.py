#!/usr/bin/env python3
"""Regression tests for bundled native image-generation fixture behavior."""

from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

import yaml


SKILL_DIR = Path(__file__).resolve().parents[1]
IMAGE_FIXTURE = SKILL_DIR / "assets" / "fixtures" / "aigc-image-asset-workflow.yml"


def node_by_title(title: str) -> dict:
    data = yaml.safe_load(IMAGE_FIXTURE.read_text(encoding="utf-8"))
    for node in data["workflow"]["graph"]["nodes"]:
        if node.get("data", {}).get("title") == title:
            return node
    raise AssertionError(f"node not found: {title}")


def run_js_main(code: str, payload: dict) -> dict:
    harness = "\n".join(
        [
            code,
            f"const result = main({json.dumps(payload, ensure_ascii=False)});",
            "console.log(JSON.stringify(result));",
        ]
    )
    result = subprocess.run(
        ["node", "-e", harness],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise AssertionError(result.stderr or result.stdout)
    return json.loads(result.stdout)


class AigcImageFixtureTests(unittest.TestCase):
    def test_infers_landscape_size_from_business_brief_when_explicit_size_is_empty(self) -> None:
        code = node_by_title("规范图像生成参数")["data"]["code"]

        result = run_js_main(
            code,
            {
                "planned_image_prompt": "Bright science classroom cover, water cycle diagram.",
                "planned_size": "auto",
                "planned_output_format": "png",
                "planned_image_count": 1,
                "planned_background": "auto",
                "planned_quality_notes": "clear, readable",
                "planned_quality_checklist": "water cycle elements visible",
                "image_brief": "为小学三年级科学课生成一张 16:9 封面图，适合课堂投屏。",
                "output_use": "课堂课件封面",
                "aspect_size": "",
                "image_count": "",
                "output_format": "",
            },
        )

        diagnostics = json.loads(result["diagnostics"])
        self.assertEqual(result["size"], "1536x1024")
        self.assertEqual(diagnostics["size"], "1536x1024")
        self.assertEqual(diagnostics["size_source"], "brief_inferred")


if __name__ == "__main__":
    unittest.main()
