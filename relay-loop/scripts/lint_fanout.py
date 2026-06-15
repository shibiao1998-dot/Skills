#!/usr/bin/env python3
"""Lint a relay-loop fan-out split note before dispatch.

The Goal linter validates one executor contract. This linter validates the
commander harness around multiple contracts: whether fan-out is bounded, whether
each baton has its own files and evidence path, and whether the commander has a
real synthesis plan before starting parallel work.

Usage:
    python3 lint_fanout.py <split-note-file> [<split-note-file> ...]

Exit codes: 0 = clean, 1 = problems found, 2 = bad invocation.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


REQUIRED_SECTIONS = [
    ("Fan-out decision", [r"Fan-out decision", r"Parallel decision", r"并行决策"]),
    ("Shared objective", [r"Shared objective", r"共同目标"]),
    ("Truth sources", [r"Truth sources?", r"真相源?"]),
    ("Shared constraints", [r"Shared constraints?", r"共同约束"]),
    ("Synthesis plan", [r"Synthesis plan", r"合成计划"]),
    ("Verification plan", [r"Verification plan", r"验证计划"]),
    ("Dispatch checklist", [r"Dispatch checklist", r"派发检查清单"]),
]

FANOUT_SECTIONS = [
    ("Sub-batons", [r"Sub-batons?", r"Batons?", r"子任务", r"子棒"]),
    ("Collision rules", [r"Collision rules?", r"冲突规则"]),
]

SINGLE_SECTIONS = [
    ("Single-baton rationale", [r"Single-baton rationale", r"Single baton rationale", r"单棒理由"]),
]

BATON_FIELDS = [
    ("Type", [r"Type", r"类型"]),
    ("Goal file", [r"Goal file", r"Goal path", r"目标文件"]),
    ("Handoff file", [r"Handoff file", r"Handoff path", r"交接文件"]),
    ("Log file", [r"Log file", r"Log path", r"日志文件"]),
    ("Ownership", [r"Ownership", r"Owner scope", r"负责范围"]),
    ("Allowed write surface", [r"Allowed write surface", r"Allowed writes?", r"允许写入"]),
    ("Forbidden write surface", [r"Forbidden write surface", r"Forbidden writes?", r"禁止写入"]),
    ("Verification surface", [r"Verification surface", r"Verification", r"验证面"]),
    ("Stop when", [r"Stop when", r"完成条件", r"停止条件"]),
    ("Pause if", [r"Pause if", r"暂停条件", r"阻塞条件"]),
]

PLACEHOLDER_PATTERNS = [
    r"\{\{[^}]+\}\}",
    r"\[[A-Z][A-Z0-9 _/\-]{2,}\](?!\()",
    r"\bTBD\b",
    r"\bTODO\b",
    r"待补充",
    r"待定",
]

DANGEROUS_VAGUE_PATTERNS = [
    r"as many agents as needed",
    r"spawn agents as needed",
    r"parallelize everything",
    r"let them coordinate",
    r"edit anything",
    r"change whatever",
    r"随便派",
    r"尽可能多.*agent",
    r"让.*自己协调",
    r"随便改",
]

SYNTHESIS_EVIDENCE_PATTERNS = [
    r"\b(compare|merge|choose|integrate|synthesi[sz]e|rerun|verify|evidence|Handoff)\b",
    r"(比较|合成|整合|选择|复验|验证|证据|交接)",
]

VERIFICATION_EVIDENCE_PATTERNS = [
    r"\b(lint_goal|lint_handoff|test|pytest|npm|pnpm|yarn|make|curl|browser|screenshot|artifact|evidence|Handoff)\b",
    r"(测试|构建|检查|验证|截图|证据|交接|日志)",
]


def _header_regex(keyword: str) -> str:
    return rf"(?:#{{1,6}}\s*)?{keyword}[^\n:：]*[:：]?"


def _section_present(text: str, keywords: list[str]) -> bool:
    return any(
        re.search(rf"^\s*{_header_regex(kw)}", text, flags=re.MULTILINE | re.IGNORECASE)
        for kw in keywords
    )


def _section_body(text: str, keywords: list[str]) -> str:
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if any(re.match(rf"^\s*{_header_regex(kw)}\s*$", line, flags=re.IGNORECASE) for kw in keywords):
            body: list[str] = []
            for nxt in lines[i + 1:]:
                if re.match(r"^\s*#{1,6}\s+", nxt):
                    break
                if nxt.strip():
                    body.append(nxt.strip())
            return "\n".join(body).strip()
    return ""


def _contains_any(text: str, patterns: list[str]) -> bool:
    return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns)


def _mode(text: str) -> str | None:
    decision = _section_body(text, [r"Fan-out decision", r"Parallel decision", r"并行决策"])
    match = re.search(r"\bMode\s*[:：]\s*(FANOUT|SINGLE|EXPLORE_FIRST)\b", decision, flags=re.IGNORECASE)
    if match:
        return match.group(1).upper()
    return None


def _baton_blocks(text: str) -> list[tuple[str, str]]:
    lines = text.splitlines()
    blocks: list[tuple[str, list[str]]] = []
    current_title: str | None = None
    current_body: list[str] = []

    for line in lines:
        match = re.match(r"^\s*#{3,6}\s+(Baton\s+.+|Sub-baton\s+.+|子任务\s+.+|子棒\s+.+)$", line, flags=re.IGNORECASE)
        if match:
            if current_title is not None:
                blocks.append((current_title, current_body))
            current_title = match.group(1).strip()
            current_body = []
            continue
        if current_title is not None:
            if re.match(r"^\s*#{1,2}\s+", line):
                blocks.append((current_title, current_body))
                current_title = None
                current_body = []
            else:
                current_body.append(line)

    if current_title is not None:
        blocks.append((current_title, current_body))

    return [(title, "\n".join(body).strip()) for title, body in blocks]


def _field(block: str, keywords: list[str]) -> str:
    for line in block.splitlines():
        for keyword in keywords:
            match = re.match(rf"^\s*(?:[-*]\s*)?{keyword}\s*[:：]\s*(.+)$", line, flags=re.IGNORECASE)
            if match:
                return match.group(1).strip()
    return ""


def _is_read_only(block: str) -> bool:
    value = _field(block, [r"Type", r"类型"]).lower()
    allowed = _field(block, [r"Allowed write surface", r"Allowed writes?", r"允许写入"]).lower()
    return "read-only" in value or "read only" in value or "none" in allowed or "read-only" in allowed


def _write_surfaces(block: str) -> list[str]:
    allowed = _field(block, [r"Allowed write surface", r"Allowed writes?", r"允许写入"])
    if _is_read_only(block):
        return []
    parts = re.split(r"[;,，、]", allowed)
    surfaces: list[str] = []
    for raw in parts:
        item = raw.strip().strip("`")
        if not item:
            continue
        lowered = item.lower()
        if lowered in {"none", "n/a", "na", "read-only analysis", "read only analysis"}:
            continue
        surfaces.append(item)
    return surfaces


def lint_text(text: str, source: str) -> list[str]:
    errors: list[str] = []

    if not re.search(r"^#\s*Relay Fan-out Split Note\b|^#\s*Relay 并行拆分记录", text, flags=re.MULTILINE | re.IGNORECASE):
        errors.append(f"{source}: missing `Relay Fan-out Split Note` title")

    for name, keywords in REQUIRED_SECTIONS:
        if not _section_present(text, keywords):
            errors.append(f"{source}: missing required section `{name}`")

    mode = _mode(text)
    if mode is None:
        errors.append(f"{source}: Fan-out decision must include `Mode: FANOUT`, `Mode: SINGLE`, or `Mode: EXPLORE_FIRST`")

    if mode in {"FANOUT", "EXPLORE_FIRST"}:
        for name, keywords in FANOUT_SECTIONS:
            if not _section_present(text, keywords):
                errors.append(f"{source}: missing required fan-out section `{name}`")
    if mode == "SINGLE":
        for name, keywords in SINGLE_SECTIONS:
            if not _section_present(text, keywords):
                errors.append(f"{source}: missing required single-baton section `{name}`")

    for pattern in PLACEHOLDER_PATTERNS:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            errors.append(f"{source}: unresolved placeholder `{match.group(0)}` matched `{pattern}`")

    for pattern in DANGEROUS_VAGUE_PATTERNS:
        if re.search(pattern, text, flags=re.IGNORECASE):
            errors.append(f"{source}: vague/unbounded fan-out instruction matched `{pattern}`")

    synthesis = _section_body(text, [r"Synthesis plan", r"合成计划"])
    if synthesis and not _contains_any(synthesis, SYNTHESIS_EVIDENCE_PATTERNS):
        errors.append(f"{source}: Synthesis plan must name compare/merge/choose logic and evidence")

    verification = _section_body(text, [r"Verification plan", r"验证计划"])
    if verification and not _contains_any(verification, VERIFICATION_EVIDENCE_PATTERNS):
        errors.append(f"{source}: Verification plan must name concrete checks, linters, commands, artifacts, or evidence")

    batons = _baton_blocks(text)
    if mode in {"FANOUT", "EXPLORE_FIRST"} and len(batons) < 2:
        errors.append(f"{source}: {mode} split note must define at least two baton blocks")

    seen_goal_files: dict[str, str] = {}
    seen_handoff_files: dict[str, str] = {}
    seen_log_files: dict[str, str] = {}
    write_owner: dict[str, str] = {}

    for title, block in batons:
        for name, keywords in BATON_FIELDS:
            value = _field(block, keywords)
            if not value:
                errors.append(f"{source}: `{title}` missing baton field `{name}`")
            elif len(value) < 4:
                errors.append(f"{source}: `{title}` field `{name}` is too thin")

        baton_type = _field(block, [r"Type", r"类型"])
        if baton_type and not re.search(r"read-only|read only|exploration|implementation|verification|review", baton_type, flags=re.IGNORECASE):
            errors.append(f"{source}: `{title}` Type should be read-only exploration, implementation, verification, or review")

        allowed = _field(block, [r"Allowed write surface", r"Allowed writes?", r"允许写入"])
        if re.search(r"\b(anything|everything|whole repo|entire repo|all files|unbounded)\b|随便|全部", allowed, flags=re.IGNORECASE):
            errors.append(f"{source}: `{title}` has unbounded allowed write surface")

        for field_name, table, keywords in [
            ("Goal file", seen_goal_files, [r"Goal file", r"Goal path", r"目标文件"]),
            ("Handoff file", seen_handoff_files, [r"Handoff file", r"Handoff path", r"交接文件"]),
            ("Log file", seen_log_files, [r"Log file", r"Log path", r"日志文件"]),
        ]:
            value = _field(block, keywords)
            if not value:
                continue
            if value in table:
                errors.append(f"{source}: `{title}` duplicates {field_name} `{value}` already used by `{table[value]}`")
            table[value] = title

        for surface in _write_surfaces(block):
            if surface in write_owner:
                errors.append(
                    f"{source}: duplicate implementation write surface `{surface}` in `{title}` and `{write_owner[surface]}`"
                )
            write_owner[surface] = title

    return errors


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("Usage: lint_fanout.py <split-note-file> [<split-note-file> ...]", file=sys.stderr)
        return 2

    all_errors: list[str] = []
    for raw_path in argv[1:]:
        path = Path(raw_path)
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            all_errors.append(f"{path}: cannot read file: {exc}")
            continue
        all_errors.extend(lint_text(text, str(path)))

    if all_errors:
        for error in all_errors:
            print(error, file=sys.stderr)
        print(f"\n{len(all_errors)} problem(s) found.", file=sys.stderr)
        return 1

    print("Fan-out split-note lint passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
