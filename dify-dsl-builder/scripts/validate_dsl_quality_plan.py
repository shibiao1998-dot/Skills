#!/usr/bin/env python3
"""Validate that a DSL quality plan is deep enough to drive quality prompts."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


SECTION_NAMES = (
    "Discovery Brief",
    "Reference Mapping",
    "Node Quality Plan",
    "Runtime QA Plan",
)

DISCOVERY_MARKERS = {
    "real_user_goal": ("real_user_goal", "真实目标", "用户真正", "核心目标"),
    "target_user_and_use_context": ("target_user", "use_context", "目标用户", "使用场景"),
    "good_result_example": ("good_result_example", "好结果", "强结果", "优秀结果"),
    "bad_result_example": ("bad_result_example", "坏结果", "糟糕结果", "失败结果"),
    "domain_constraints_and_boundaries": ("domain_constraints", "boundaries", "约束", "边界"),
    "iteration_feedback_signal": ("iteration_feedback", "反馈", "迭代", "failure_classification"),
}

REFERENCE_MARKERS = {
    "sample": ("sample:", "reference:", "evidence:", "样本", "参考", "证据", ".yml", ".md"),
    "borrow": ("borrow:", "借鉴", "复用", "borrow"),
    "avoid": ("avoid:", "不复制", "不借", "avoid", "旧任务残留"),
}

NODE_FIELDS = {
    "role": ("role:", "角色", "你是"),
    "task": ("task:", "任务", "负责"),
    "input_interpretation": ("input_interpretation:", "输入解释", "输入理解"),
    "output_contract": ("output_contract:", "输出契约", "输出字段", "json schema"),
    "quality_criteria": ("quality_criteria:", "质量标准", "验收标准"),
    "constraints": ("constraints:", "约束", "不得", "不能"),
    "diagnostics": ("diagnostics:", "诊断", "decision_trace", "quality_checklist"),
    "downstream_use": ("downstream_use:", "下游", "后续节点"),
}

RUNTIME_MARKERS = {
    "representative_inputs": ("representative_inputs:", "代表性输入", "测试输入"),
    "expected_output_fields": ("expected_output_fields:", "期望输出", "输出字段"),
    "quality_checks": ("quality_checks:", "质量检查", "验收检查"),
    "failure_classification": ("failure_classification:", "失败分类", "故障分类"),
    "validation_commands": ("validation_commands:", "validate_dify_dsl.py", "--prompt-quality"),
}


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def split_sections(text: str) -> dict[str, str]:
    sections: dict[str, str] = {}
    current: str | None = None
    chunks: list[str] = []
    section_pattern = re.compile(r"^\s{0,3}#{1,4}\s+(.+?)\s*$")
    for line in text.splitlines():
        match = section_pattern.match(line.lstrip())
        if match:
            title = match.group(1).strip()
            matched_section = next((name for name in SECTION_NAMES if name.lower() in title.lower()), None)
            if matched_section:
                if current:
                    sections[current] = "\n".join(chunks).strip()
                current = matched_section
                chunks = []
                continue
        if current:
            chunks.append(line)
    if current:
        sections[current] = "\n".join(chunks).strip()
    return sections


def missing_markers(content: str, markers: dict[str, tuple[str, ...]]) -> list[str]:
    lowered = normalize(content)
    return [
        name
        for name, options in markers.items()
        if not any(option.lower() in lowered for option in options)
    ]


def split_blocks(content: str, marker: str) -> list[str]:
    blocks: list[list[str]] = []
    current: list[str] = []
    marker_pattern = re.compile(rf"^\s*(?:[-*]\s*)?{re.escape(marker)}\s*[:：]", re.IGNORECASE)
    for line in content.splitlines():
        if marker_pattern.match(line):
            if current:
                blocks.append(current)
            current = [line]
            continue
        if current:
            current.append(line)
    if current:
        blocks.append(current)
    return ["\n".join(block).strip() for block in blocks]


def validate_text(text: str) -> list[str]:
    errors: list[str] = []
    sections = split_sections(text)
    for section_name in SECTION_NAMES:
        content = sections.get(section_name, "")
        if len(normalize(content)) < 180:
            errors.append(f"{section_name}: section is too shallow to guide DSL generation")

    discovery_missing = missing_markers(sections.get("Discovery Brief", ""), DISCOVERY_MARKERS)
    if discovery_missing:
        errors.append(f"Discovery Brief: missing evidence {discovery_missing}")

    reference_content = sections.get("Reference Mapping", "")
    reference_missing = missing_markers(reference_content, REFERENCE_MARKERS)
    if reference_missing:
        errors.append(f"Reference Mapping: missing fields {reference_missing}")
    reference_blocks = split_blocks(reference_content, "sample")
    if len(reference_blocks) < 2:
        errors.append("Reference Mapping: must map at least 2 concrete portable references or evidence records")
    for index, block in enumerate(reference_blocks, start=1):
        block_missing = missing_markers(block, REFERENCE_MARKERS)
        if block_missing:
            errors.append(f"Reference Mapping: mapping {index} missing fields {block_missing}")

    node_content = sections.get("Node Quality Plan", "")
    node_missing = missing_markers(node_content, NODE_FIELDS)
    if node_missing:
        errors.append(f"Node Quality Plan: missing fields {node_missing}")
    node_blocks = split_blocks(node_content, "node")
    if not node_blocks:
        errors.append("Node Quality Plan: must define at least one major LLM or Agent node")
    for index, block in enumerate(node_blocks, start=1):
        block_missing = missing_markers(block, NODE_FIELDS)
        if block_missing:
            errors.append(f"Node Quality Plan: node {index} missing fields {block_missing}")

    runtime_missing = missing_markers(sections.get("Runtime QA Plan", ""), RUNTIME_MARKERS)
    if runtime_missing:
        errors.append(f"Runtime QA Plan: missing fields {runtime_missing}")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path, help="Markdown or text plan file to validate")
    args = parser.parse_args()

    errors = validate_text(args.path.read_text(encoding="utf-8"))
    if errors:
        print(f"DSL quality plan validation failed: {args.path}")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"OK: {args.path} passed DSL quality plan validation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
