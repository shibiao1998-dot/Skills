#!/usr/bin/env python3
"""Suggest vNext Dify DSL Builder references for a request."""

from __future__ import annotations

import argparse
import json
import re
from typing import Any


BASE_REFERENCES = [
    "references/core-design-principles.md",
]

CAPABILITY_RULES = [
    (
        ("workflow", "chatflow", "对话", "多轮", "api", "批处理"),
        "references/capability-workflow-chatflow-architecture.md",
    ),
    (
        ("节点", "分支", "变量", "iteration", "loop", "answer", "end"),
        "references/capability-dify-node-composition.md",
    ),
    (
        ("prompt", "提示词", "专家", "文案", "脚本", "质量"),
        "references/capability-domain-expert-generation.md",
    ),
    (
        ("拆解", "分镜", "审核", "校验", "结构化", "多阶段"),
        "references/capability-dimension-aware-decomposition.md",
    ),
    (
        ("schema", "json", "code", "变量", "selector", "字段"),
        "references/capability-code-schema-variable-contracts.md",
    ),
    (
        ("ai hub", "aihub", "内部工具", "provider", "模型", "权限"),
        "references/capability-aihub-compatibility.md",
    ),
    (
        ("aigc", "图片", "视频", "音频", "3d", "成语", "故事", "短视频"),
        "references/capability-aigc-production-lines.md",
    ),
    (
        ("aigc", "图片", "图像", "视频", "音频", "歌曲", "音乐", "语音", "识别", "3d", "模型", "短视频"),
        "references/capability-aihub-native-aigc-components.md",
    ),
    (
        ("验证", "导入", "运行", "qa", "验收", "交付"),
        "references/capability-validation-delivery.md",
    ),
]

FAILURE_RULES = [
    (("打不开", "白屏", "client-side exception", "画布", "canvas"), "references/failure-canvas-rendering.md"),
    (("code node", "代码节点", "syntaxerror", "exit status", "runtime"), "references/failure-runtime-code-node.md"),
    (("tool_configurations", "tool node", "工具节点", "provider"), "references/failure-tool-node-shape.md"),
    (("一次问", "太多问题", "提前生成", "交互", "澄清"), "references/failure-generated-interaction.md"),
]


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def add_matches(text: str, rules: list[tuple[tuple[str, ...], str]], refs: list[str]) -> None:
    for terms, ref in rules:
        if any(term.lower() in text for term in terms) and ref not in refs:
            refs.append(ref)


def classify_journey(text: str) -> str:
    if any(term in text for term in ("旧 dsl", "旧dsl", "导入错误", "运行失败", "报错", "修复", "迭代", "反馈")):
        return "references/journey-repair-iteration.md"
    return "references/journey-new-build.md"


def select_references(request: str) -> dict[str, Any]:
    text = normalize(request)
    refs = list(BASE_REFERENCES)
    journey = classify_journey(text)
    refs.append(journey)
    add_matches(text, CAPABILITY_RULES, refs)
    add_matches(text, FAILURE_RULES, refs)
    if "references/capability-validation-delivery.md" not in refs:
        refs.append("references/capability-validation-delivery.md")
    return {
        "journey": "repair_iteration" if "repair" in journey else "new_build",
        "references": refs,
        "notes": [
            "Use these as progressive-disclosure references only.",
            "Do not expose internal process labels to the user.",
            "Ask at most one user-facing clarification question per turn.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Print JSON output.")
    parser.add_argument("request", nargs="*", help="Natural-language request.")
    args = parser.parse_args()
    request = " ".join(args.request)
    result = select_references(request)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        for ref in result["references"]:
            print(ref)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
