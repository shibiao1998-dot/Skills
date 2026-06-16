#!/usr/bin/env python3
"""Lint an assembled relay-loop Goal contract before dispatch.

Catches the failure modes that make a memoryless executor waste a baton:
missing contract elements, unfilled {{placeholders}}, vague verification,
unbounded retries, a missing truth-source reference, a missing anti-gaming clause,
a green-class ("until green") Goal that doesn't also forbid rewriting the check
command or exit criteria, a failure-driven Goal that forgets to require a red-first
regression check, a pause list with no real escalation trigger, a stop condition
that forgets the handoff, an
autonomy-mode Goal that hasn't mechanically earned its unattended gate, and —
importantly — anything that looks like a leaked secret.

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
    ("outcome anchor (truth sources)", [r"Truth sources?", r"真相源?"]),
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

# Anti-gaming / integrity clause must be present (Goodhart's-law defense): the Goal
# must tell the executor it may not fake green by weakening or deleting the checks.
# Match the SEMANTICS — a "don't fake it" verb near a tests/checks/green object — not a
# literal label, so a substantive clause in any wording or language passes, while a bare
# mention of the word "anti-gaming" does not.
ANTIGAMING_FORBID = (
    r"delet|remov|skip|disabl|weaken|loosen|comment[\s-]?out|mock|stub|"
    + r"hard[\s-]?cod|fake|fabricat|swallow|suppress|"
    + r"删除|移除|跳过|禁用|弱化|放松|注释|硬编码|伪造|造假|吞掉|屏蔽"
)
ANTIGAMING_OBJECT = r"test|assert|check|green|coverage|测试|断言|检查|绿|覆盖"
ANTIGAMING_RE = re.compile(
    rf"(?:{ANTIGAMING_FORBID})[\s\S]{{0,60}}(?:{ANTIGAMING_OBJECT})"
    + rf"|(?:{ANTIGAMING_OBJECT})[\s\S]{{0,60}}(?:{ANTIGAMING_FORBID})",
    flags=re.IGNORECASE,
)

# Green-class Goals — the "until green" / "make the checks pass" family (CI-until-green,
# fix-the-build). They are the ones most tempted to reach green by rewriting the verifier
# itself, not just weakening a test, so they must carry an extra guardrail. Narrow on
# purpose: an ordinary "tests are green" completion signal must NOT trip this.
GREEN_CLASS_PATTERNS = [
    r"\buntil\b[\s\S]{0,40}\bgreen\b",
    r"\b(?:keep|make|drive|get|turn|stay|remain|bring|push)\b[\s\S]{0,40}\bgreen\b",
    r"\buntil\b[\s\S]{0,40}\b(?:pass|passes|passing)\b",
    r"\b(?:all|required|every)\b[\s\S]{0,25}\bchecks?\b[\s\S]{0,25}\b(?:pass|passes|green)\b",
    r"\bCI\b[\s\S]{0,25}\bgreen\b",
    r"(?:直到|保持|让|使)[\s\S]{0,20}(?:通过|变绿|为绿|全绿)",
]

# The guardrail a green-class Goal must carry beyond "don't weaken tests": it must forbid
# rewriting the verifier itself — the check command, the exit/stop criteria, or the
# acceptance gate. Same forbid-verb-near-object shape as ANTIGAMING_RE.
CHECK_TAMPER_FORBID = (
    r"modif|rewrit|rewrote|chang|alter|relax|loosen|adjust|edit|swap|replac|disabl|bypass|weaken|"
    + r"改写|修改|更改|放松|放宽|绕过|篡改|削弱"
)
CHECK_TAMPER_OBJECT = (
    r"check command|exit (?:condition|criteri)|stop[\s-]?when|pass(?:ing)? condition|"
    + r"acceptance (?:criteri|condition|gate)|the gate\b|exit code|"
    + r"检查命令|退出条件|完成条件|停止条件|验收(?:标准|条件)|通过条件"
)
CHECK_TAMPER_RE = re.compile(
    rf"(?:{CHECK_TAMPER_FORBID})[\s\S]{{0,60}}(?:{CHECK_TAMPER_OBJECT})"
    + rf"|(?:{CHECK_TAMPER_OBJECT})[\s\S]{{0,60}}(?:{CHECK_TAMPER_FORBID})",
    flags=re.IGNORECASE,
)

# Signals that a Goal is failure-driven (bugfix / bad-trace work). Narrow on purpose:
# generic words like "regression" or "failing input" must NOT trip it, and these are
# matched only against the commander-authored Verification / Stop-when sections (never
# the boilerplate brief / Handoff template, which mention "Repro Capsule" generically).
FAILURE_DRIVEN_PATTERNS = [
    r"repro capsule",
    r"regression lock",
    r"bad trace",
    r"original failing input",
    r"reproduces? the (?:original )?fail",
    r"复现胶囊",
    r"复放胶囊",
    r"回归锁",
    r"坏轨迹",
]

# A failure-driven Goal must require the regression check to fail BEFORE the fix —
# otherwise a passing test proves nothing about the bug it claims to guard.
RED_FIRST_PATTERNS = [
    r"fails? before",
    r"red before",
    r"before the fix",
    r"先失败",
    r"先红",
    r"修复前.*失败",
]

# Autonomy tier: a Goal may declare it is eligible to run unattended on a heartbeat.
# When it does, the gate stops being prose self-attestation and must be mechanically
# earned (see references/autonomy-heartbeat.md): a machine-verifiable Stop-when, a
# named independent verifier, and a recorded human sign-off (autonomy is granted, never
# self-granted).
AUTONOMOUS_MODE_RE = re.compile(
    r"^\s*(?:#{1,6}\s*|[-*]\s*)?(?:Mode|Autonomy|模式)\s*[:：]\s*(?:AUTONOMOUS|autonomous|自治|无人值守)\b"
    + r"|^\s*(?:#{1,6}\s*|[-*]\s*)?自治模式\s*[:：]",
    flags=re.MULTILINE | re.IGNORECASE,
)

# Taste / judgment words an unattended Stop-when must NOT rely on — they need a human.
TASTE_PATTERNS = [
    r"looks?\s+(?:good|right|fine|nice|polished|clean|native|professional)",
    r"seems?\s+(?:good|right|fine|ok|okay|reasonable)",
    r"feels?\s+(?:good|right|native)",
    r"\b(?:polished|good enough|clean enough|looks native|production-quality)\b",
    r"(?:好看|美观|像样|自然|差不多|感觉(?:对|不错|可以|良好))",
]

# An autonomous Goal must name the independent verifier that gates its advance.
INDEPENDENT_VERIFIER_PATTERNS = [
    r"independent verifier",
    r"verifier baton",
    r"独立验证",
    r"独立校验",
]

# An autonomous Goal must record the human sign-off that granted autonomy.
AUTONOMY_SIGNOFF_PATTERNS = [
    r"sign(?:ed)?[\s-]?off\b",
    r"human[\s-]?(?:grant|approv|authoriz)",
    r"eligibility checklist",
    r"签字",
    r"签核",
    r"人工(?:授权|批准|签)",
    r"授权自治",
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
    for name, keywords in REQUIRED_ELEMENTS:
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

    # Anti-gaming clause must be present — without it the executor may optimize the
    # verifier instead of the outcome (delete failing tests, weaken assertions). Match
    # the semantics anywhere in the Goal, not a literal label.
    if not ANTIGAMING_RE.search(text):
        errors.append(f"{source}: missing an anti-gaming/integrity clause (forbid deleting, skipping, or weakening tests/assertions to fake a green result)")

    # Green-class Goals (the "until green" / make-the-checks-pass family) can be gamed by
    # rewriting the check command or exit criteria themselves — a vector the general
    # anti-gaming clause (aimed at tests/assertions) need not cover. When the Goal's
    # outcome / verification / stop-when is about reaching or keeping green, require an
    # explicit guardrail against tampering with the check / exit criteria. The green-class
    # signal is scoped to commander-authored sections so boilerplate doesn't trip it; the
    # guardrail itself may appear anywhere in the Goal.
    green_blob = " ".join(
        body for body in (
            goal_line,
            section_body(text, REQUIRED_ELEMENTS[1][1]),
            section_body(text, REQUIRED_ELEMENTS[5][1]),
        ) if body
    )
    if any(re.search(p, green_blob, flags=re.IGNORECASE) for p in GREEN_CLASS_PATTERNS) and not CHECK_TAMPER_RE.search(text):
        errors.append(f"{source}: green-class ('until green' / make-the-checks-pass) Goal must also forbid modifying the check command or exit/stop criteria to force a pass — not only weakening tests")

    # Failure-driven Goals must require red-first. Look only in the commander-authored
    # Verification + Stop-when sections, so the boilerplate brief / Handoff template
    # (which mention "Repro Capsule" generically) don't misclassify a feature Goal.
    fd_text = " ".join(
        body for body in (
            section_body(text, REQUIRED_ELEMENTS[1][1]),
            section_body(text, REQUIRED_ELEMENTS[5][1]),
        ) if body
    )
    if any(re.search(p, fd_text, flags=re.IGNORECASE) for p in FAILURE_DRIVEN_PATTERNS) and not any(
        re.search(p, fd_text, flags=re.IGNORECASE) for p in RED_FIRST_PATTERNS
    ):
        errors.append(f"{source}: failure-driven Goal must require the regression check to fail before the fix (red-first), not just pass after")

    # Autonomy gate: a Goal that declares it may run unattended (`Mode: AUTONOMOUS`)
    # must mechanically earn it, not just assert it — see references/autonomy-heartbeat.md.
    # Otherwise "earned by verifiability" is prose the same agent can tick off for itself.
    if AUTONOMOUS_MODE_RE.search(text):
        stop_when = section_body(text, REQUIRED_ELEMENTS[5][1]) or ""
        if not any(re.search(p, stop_when, flags=re.IGNORECASE) for p in VERIFICATION_EVIDENCE_PATTERNS):
            errors.append(f"{source}: autonomous Goal's Stop-when must be machine-verifiable (name commands/checks/exit codes, not prose)")
        for pattern in TASTE_PATTERNS:
            match = re.search(pattern, stop_when, flags=re.IGNORECASE)
            if match:
                errors.append(f"{source}: autonomous Goal's Stop-when relies on a taste/judgment word (`{match.group(0)}`) — unattended acceptance must be machine-checkable, not a human eye")
                break
        if not any(re.search(p, text, flags=re.IGNORECASE) for p in INDEPENDENT_VERIFIER_PATTERNS):
            errors.append(f"{source}: autonomous Goal must name the independent verifier baton that gates its advance (different model, refute template)")
        if not any(re.search(p, text, flags=re.IGNORECASE) for p in AUTONOMY_SIGNOFF_PATTERNS):
            errors.append(f"{source}: autonomous Goal must record the human sign-off that granted autonomy (autonomy is granted, never self-granted)")

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
