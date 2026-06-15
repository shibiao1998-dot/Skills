#!/usr/bin/env python3
"""Lint an assembled relay-loop Goal contract before dispatch.

Catches the failure modes that make a memoryless executor waste a baton:
missing contract elements, unfilled {{placeholders}}, vague verification,
unbounded retries, a missing truth-source reference, a pause list with no real
escalation trigger, a stop condition that forgets the handoff, and — importantly —
anything that looks like a leaked secret.

Usage:
    python3 lint_goal.py <goal-file> [<goal-file> ...]

Exit codes: 0 = clean, 1 = problems found, 2 = bad invocation.

Placeholders use {{double-brace}} on purpose: that way the linter can flag the ones
you forgot to fill without tripping over legitimate <...> in content (generics,
<branch> notation). Element headers may carry a parenthetical note before the colon
(e.g. "Verification (concrete evidence only):"). Markers are accepted in English or
Chinese so the Goal body can be written in either working language; the command
token stays /goal.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# Each element: a human name + the keyword alternatives that head its section.
# The colon (and any "(note)" before it) is matched by the helpers, not here.
REQUIRED_ELEMENTS = [
    ("outcome anchor (truth sources)", [r"Truth sources?", r"真相源?", r"Task"]),
    ("verification", [r"Verification", r"验证"]),
    ("constraints", [r"Constraints", r"约束"]),
    ("boundaries", [r"Boundaries", r"边界"]),
    ("iteration policy", [r"Iteration(?: policy)?", r"迭代策略?"]),
    ("stop when", [r"Stop when", r"完成条件", r"停止条件"]),
    ("pause if", [r"Pause if", r"暂停条件", r"阻塞条件"]),
]

# Unfilled placeholders. {{...}} is ours; the rest are common stray markers.
# The bracketed pattern catches copied prompt templates like [THING] while avoiding
# normal Markdown links such as [docs](path).
PLACEHOLDER_PATTERNS = [
    r"\{\{[^}]+\}\}",
    r"\[[A-Z][A-Z0-9 _/\-]{2,}\](?!\()",
    r"\bTBD\b",
    r"\bTODO\b",
    r"待补充",
    r"待定",
]

# Verification must name something concrete, not "make sure it works".
VERIFICATION_EVIDENCE_PATTERNS = [
    r"\b(run|start|open|test|build|lint|typecheck|verify|inspect|capture|screenshot|log|artifact|file|url|api|endpoint|curl|query|browser|migrat|assert)\w*",
    r"(运行|启动|打开|测试|构建|检查|验证|读取|截图|日志|产物|文件|链接|接口|查询|浏览器|断言|迁移|证据)",
]

# Banned vague instructions — they remove the brakes from an autonomous run.
DANGEROUS_VAGUE_PATTERNS = [
    r"make sure it works",
    r"edit anything",
    r"change whatever",
    r"keep trying",
    r"try again until",
    r"until it (looks|seems|feels) (good|right|ok)",
    r"随便改",
    r"随意修改",
    r"一直尝试",
    r"直到满意",
    r"看起来不错就行",
    r"感觉可以",
]

# Pause-if must contain at least one real escalation trigger.
PAUSE_TRIGGER_PATTERNS = [
    r"\b(credential|secret|token|password|network|push|remote|production|prod|destructive|delete|drop|migration|payment|deploy|human|owner|decision|approval|conflict|block)\w*",
    r"(凭证|密钥|账号|联网|推送|远端|生产|破坏性|删除|迁移|支付|发布|部署|人工|决策|审批|冲突|阻塞)",
]

# Things that look like REAL secrets. $ENV_VAR placeholders and {{...}} are exempt.
SECRET_PATTERNS = [
    (r"Bearer\s+[A-Za-z0-9._\-]{16,}", "looks like a real bearer token"),
    (r"\bsk-[A-Za-z0-9]{16,}\b", "looks like an API secret key (sk-...)"),
    (r"\b(?:AKIA|ASIA)[A-Z0-9]{12,}\b", "looks like an AWS access key id"),
    (r"-----BEGIN (?:[A-Z ]+ )?PRIVATE KEY-----", "contains a private key block"),
    (r"(?i)\b(password|passwd|secret|sign[_-]?key|api[_-]?key|access[_-]?token|client[_-]?secret)\b\s*[:=]\s*['\"]?(?!\$|\{\{)[A-Za-z0-9/+._\-]{8,}", "looks like a hardcoded credential value (use $ENV_VAR instead)"),
]


def _header_regex(keyword: str) -> str:
    # keyword, then an optional "(note)" qualifier, then the colon.
    return rf"(?:[-*]\s*)?{keyword}[^\n:：]*[:：]"


def section_present(text: str, keywords: list[str]) -> bool:
    return any(
        re.search(rf"^\s*{_header_regex(kw)}", text, flags=re.MULTILINE | re.IGNORECASE)
        for kw in keywords
    )


def _is_any_header(line: str) -> bool:
    for _, keywords in REQUIRED_ELEMENTS:
        for kw in keywords:
            if re.match(rf"^\s*{_header_regex(kw)}", line, flags=re.IGNORECASE):
                return True
    return False


def section_body(text: str, keywords: list[str]) -> str | None:
    """Return a section's content: the header line's tail plus following non-blank
    lines, stopping at a blank line or the next element header."""
    lines = text.splitlines()
    for i, line in enumerate(lines):
        for kw in keywords:
            match = re.match(rf"^\s*{_header_regex(kw)}\s*(.*)$", line, flags=re.IGNORECASE)
            if match:
                parts: list[str] = []
                if match.group(1).strip():
                    parts.append(match.group(1).strip())
                for nxt in lines[i + 1:]:
                    if not nxt.strip() or _is_any_header(nxt):
                        break
                    parts.append(nxt.strip())
                return " ".join(parts).strip()
    return None


def lint_text(text: str, source: str) -> list[str]:
    errors: list[str] = []

    # Command token must be present and must be /goal, not a localized alias.
    if re.search(r"^\s*/目标\b", text, flags=re.MULTILINE):
        errors.append(f"{source}: use `/goal`, not `/目标`, as the command token")
    if not re.search(r"/goal\b", text):
        errors.append(f"{source}: missing the `/goal` command token")

    # All seven elements must be present.
    for name, keywords in REQUIRED_ELEMENTS:
        if not section_present(text, keywords):
            errors.append(f"{source}: missing required element `{name}`")

    # No unfilled placeholders.
    for pattern in PLACEHOLDER_PATTERNS:
        match = re.search(pattern, text)
        if match:
            errors.append(
                f"{source}: unresolved placeholder `{match.group(0)}` matched `{pattern}`"
            )

    # No brake-removing vague instructions.
    for pattern in DANGEROUS_VAGUE_PATTERNS:
        if re.search(pattern, text, flags=re.IGNORECASE):
            errors.append(f"{source}: vague/unbounded instruction matched `{pattern}`")

    # Outcome must be substantial enough to be actionable.
    goal_line = next(
        (ln.strip() for ln in text.splitlines() if ln.strip().startswith("/goal")), ""
    )
    if goal_line and len(goal_line.removeprefix("/goal").strip()) < 20:
        errors.append(f"{source}: /goal outcome is too short to be actionable (>=20 chars)")

    # Verification must name concrete evidence.
    verification = section_body(text, REQUIRED_ELEMENTS[1][1])
    if verification and not any(
        re.search(p, verification, flags=re.IGNORECASE) for p in VERIFICATION_EVIDENCE_PATTERNS
    ):
        errors.append(f"{source}: verification should name concrete evidence (commands, tests, logs, screenshots, endpoints, artifacts)")

    # Thin sections usually mean the contract wasn't really filled in.
    for name, keywords in REQUIRED_ELEMENTS[1:]:
        content = section_body(text, keywords)
        if content is not None and len(content) < 12:
            errors.append(f"{source}: `{name}` content is too thin")

    # Pause-if must list at least one real escalation trigger.
    pause = section_body(text, REQUIRED_ELEMENTS[6][1])
    if pause is not None and not any(
        re.search(p, pause, flags=re.IGNORECASE) for p in PAUSE_TRIGGER_PATTERNS
    ):
        errors.append(f"{source}: pause-if lists no real escalation trigger (credentials, network/push, production, destructive, human decision, conflict)")

    # Stop-when must require producing a handoff (the baton).
    if not re.search(r"hand[\s\-]?off|交接|接力棒", text, flags=re.IGNORECASE):
        errors.append(f"{source}: stop-when must require producing a Handoff (none mentioned)")

    # Secret scan — the leak gate.
    for pattern, why in SECRET_PATTERNS:
        if re.search(pattern, text):
            errors.append(f"{source}: possible leaked secret — {why}")

    return errors


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("Usage: lint_goal.py <goal-file> [<goal-file> ...]", file=sys.stderr)
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

    print("Goal contract lint passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
