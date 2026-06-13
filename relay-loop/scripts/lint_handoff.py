#!/usr/bin/env python3
"""Lint a relay-loop Handoff before the commander trusts it.

The Goal linter keeps the executor's contract tight before dispatch. This Handoff
linter guards the other side of the loop: a returned baton must be verifiable,
re-runnable, and capable of turning failures into regression protection.

Usage:
    python3 lint_handoff.py <handoff-file> [<handoff-file> ...]

Exit codes: 0 = clean, 1 = problems found, 2 = bad invocation.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


REQUIRED_SECTIONS = [
    ("Part A", [r"Part A", r"must-read", r"必读"]),
    ("Part B", [r"Part B", r"full record", r"完整记录"]),
    ("Status", [r"Status", r"状态"]),
    ("Acceptance", [r"Acceptance", r"验收"]),
    ("What I did NOT verify", [r"What I did NOT verify", r"未验证", r"没有验证"]),
    ("Deliverables", [r"Deliverables", r"交付物"]),
    ("How to re-verify", [r"How to re-verify", r"重新验证", r"复验"]),
    ("Next baton", [r"Next baton", r"下一棒", r"下一轮"]),
]

DIAGNOSTIC_FIELDS = [
    ("failure observed", [r"failure observed", r"observed failure", r"失败现象"]),
    ("causal chain", [r"causal chain", r"因果链"]),
    ("root cause hypothesis", [r"root cause", r"根因"]),
    ("exact fix surface", [r"exact fix surface", r"fix surface", r"修复面"]),
    ("rerun command", [r"rerun command", r"复放命令", r"重新运行命令"]),
]

REPRO_FIELDS = [
    ("original input", [r"original input", r"原始输入"]),
    ("command to reproduce", [r"command to reproduce", r"reproduce command", r"复现命令"]),
    ("environment/config", [r"environment", r"config", r"环境", r"配置"]),
    ("failing signal", [r"failing signal", r"失败信号"]),
    ("trace/log/evidence", [r"trace", r"log", r"evidence", r"日志", r"证据"]),
]

REGRESSION_FIELDS = [
    ("test/check added", [r"test/check added", r"test added", r"check added", r"新增测试", r"新增检查"]),
    ("locked failure", [r"locked failure", r"锁定失败", r"回归"]),
]

SECRET_PATTERNS = [
    (r"Bearer\s+[A-Za-z0-9._\-]{16,}", "looks like a real bearer token"),
    (r"\bsk-[A-Za-z0-9]{16,}\b", "looks like an API secret key (sk-...)"),
    (r"\b(?:AKIA|ASIA)[A-Z0-9]{12,}\b", "looks like an AWS access key id"),
    (r"-----BEGIN (?:[A-Z ]+ )?PRIVATE KEY-----", "contains a private key block"),
    (
        r"(?i)\b(password|passwd|secret|sign[_-]?key|api[_-]?key|access[_-]?token|client[_-]?secret)\b\s*[:=]\s*['\"]?(?!\$|\{\{)[A-Za-z0-9/+._\-]{8,}",
        "looks like a hardcoded credential value (use $ENV_VAR instead)",
    ),
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


def _status(text: str) -> str | None:
    body = _section_body(text, [r"Status", r"状态"])
    match = re.search(r"\b(READY|PARTIAL|BLOCKED)\b", body, flags=re.IGNORECASE)
    if match:
        return match.group(1).upper()
    return None


def _part_a_body(text: str) -> str:
    return _section_body(text, [r"Part A", r"must-read", r"必读"])


def lint_text(text: str, source: str) -> list[str]:
    errors: list[str] = []

    if not re.search(r"^#\s*Handoff\b|^#\s*交接", text, flags=re.MULTILINE | re.IGNORECASE):
        errors.append(f"{source}: missing Handoff title")

    for name, keywords in REQUIRED_SECTIONS:
        if not _section_present(text, keywords):
            errors.append(f"{source}: missing required section `{name}`")

    status = _status(text)
    if status is None:
        errors.append(f"{source}: Status must be one of READY, PARTIAL, or BLOCKED")

    part_a = _part_a_body(text)
    if len(part_a.encode("utf-8")) > 1800:
        errors.append(f"{source}: Part A must stay small enough to inline into the next Goal (<=1800 bytes)")
    for label in ["build on", "base", "no-go zones", "traps"]:
        if label not in part_a.lower():
            errors.append(f"{source}: Part A should include `{label}`")

    negative = _section_body(text, [r"What I did NOT verify", r"未验证", r"没有验证"])
    if len(negative) < 30:
        errors.append(f"{source}: `What I did NOT verify` must include concrete negative evidence")
    if not re.search(r"NOT verified|not verified|未验证|没有验证|not exercised|未覆盖", negative, flags=re.IGNORECASE):
        errors.append(f"{source}: negative evidence should explicitly mark unverified or not-exercised paths")

    reverification = _section_body(text, [r"How to re-verify", r"重新验证", r"复验"])
    if not re.search(r"`[^`]+`|\b(pytest|npm|pnpm|yarn|make|curl|python|go test|cargo test|browser|screenshot)\b", reverification, flags=re.IGNORECASE):
        errors.append(f"{source}: How to re-verify must include concrete commands or evidence pointers")

    if status == "READY":
        acceptance = _section_body(text, [r"Acceptance", r"验收"])
        if "[done]" not in acceptance.lower():
            errors.append(f"{source}: READY Handoff must mark completed acceptance items with `[done]`")

        if not _section_present(text, [r"Diagnostic repair record", r"诊断修复记录"]):
            errors.append(f"{source}: READY Handoff must include `Diagnostic repair record`")
        diagnostic = _section_body(text, [r"Diagnostic repair record", r"诊断修复记录"])
        for name, patterns in DIAGNOSTIC_FIELDS:
            if not _contains_any(diagnostic, patterns):
                errors.append(f"{source}: Diagnostic repair record missing `{name}`")

        if not _section_present(text, [r"Repro Capsule", r"复放胶囊", r"复现胶囊"]):
            errors.append(f"{source}: READY Handoff must include `Repro Capsule`")
        repro = _section_body(text, [r"Repro Capsule", r"复放胶囊", r"复现胶囊"])
        for name, patterns in REPRO_FIELDS:
            if not _contains_any(repro, patterns):
                errors.append(f"{source}: Repro Capsule missing `{name}`")

        if not _section_present(text, [r"Regression lock", r"回归锁定"]):
            errors.append(f"{source}: READY Handoff must include `Regression lock`")
        regression = _section_body(text, [r"Regression lock", r"回归锁定"])
        for name, patterns in REGRESSION_FIELDS:
            if not _contains_any(regression, patterns):
                errors.append(f"{source}: Regression lock missing `{name}`")
        if not re.search(r"\bn/a\b|not automated|manual|人工|`[^`]+`|::", regression, flags=re.IGNORECASE):
            errors.append(f"{source}: Regression lock must name an automated check or explain why only manual verification is possible")

    if status in {"PARTIAL", "BLOCKED"}:
        if not re.search(r"needs human action|human action|need[s]? from (the )?human|人工|需要.*(人工|人类|审批|凭证|推送)", text, flags=re.IGNORECASE):
            errors.append(f"{source}: {status} Handoff must state the exact human action needed")

    if re.search(r"\{\{[^}]+\}\}|\bTBD\b|\bTODO\b|待补充|待定", text, flags=re.IGNORECASE):
        errors.append(f"{source}: unresolved placeholder found")

    for pattern, why in SECRET_PATTERNS:
        if re.search(pattern, text):
            errors.append(f"{source}: possible leaked secret - {why}")

    return errors


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("Usage: lint_handoff.py <handoff-file> [<handoff-file> ...]", file=sys.stderr)
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

    print("Handoff lint passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
