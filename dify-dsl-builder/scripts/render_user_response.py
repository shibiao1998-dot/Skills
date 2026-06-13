#!/usr/bin/env python3
"""Render a concise user-facing response from a vNext interaction payload."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


FORBIDDEN_WAITING_SNIPPETS = (
    "失败策略",
    "缺失依赖",
    "缺失组件",
    "缺少组件",
    "停止并提示",
    "直接停止",
    "允许降级",
    "是否降级",
    "朗诵配乐",
    "素材包",
    "音视频合成/拼接",
    "有没有可用",
    "有没有组件",
    "有没有工具",
)


def load_payload(path: Path | None) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8") if path else sys.stdin.read()
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"invalid JSON payload: {exc}") from exc
    if not isinstance(payload, dict):
        raise SystemExit("payload must be a JSON object")
    return payload


def assert_waiting_response_safe(payload: dict[str, Any], text: str) -> None:
    if payload.get("decision") == "generated":
        return
    if payload.get("response_type") == "narrow_repair_confirmation":
        return
    missing = [token for token in ("我的推荐", "A.", "B.") if token not in text]
    if missing:
        raise SystemExit(f"unsafe waiting response: missing recommended choice token(s): {', '.join(missing)}")
    forbidden = [snippet for snippet in FORBIDDEN_WAITING_SNIPPETS if snippet in text]
    if forbidden:
        raise SystemExit(f"unsafe waiting response: contains forbidden engineering contingency text: {', '.join(forbidden)}")


def render_response(payload: dict[str, Any]) -> str:
    if payload.get("decision") == "generated":
        delivery = payload.get("user_delivery")
        if isinstance(delivery, dict):
            readme = str(delivery.get("readme") or "").strip()
            dsl = str(delivery.get("dsl") or "").strip()
            lines = ["我已经生成本版工作流文件。"]
            if readme:
                lines.append(f"README：{readme}")
            if dsl:
                lines.append(f"DSL：{dsl}")
            lines.append("建议先按首测路径跑一个小样例，再把结果反馈给我继续迭代。")
            return "\n".join(lines).strip() + "\n"
        return "我已经生成本版工作流文件。\n"

    message = str(payload.get("message") or "").strip()
    if message:
        rendered = message + "\n"
        assert_waiting_response_safe(payload, rendered)
        return rendered

    context = str(payload.get("context") or "").strip()
    question = str(payload.get("recommended_next_question") or "").strip()
    hint = str(payload.get("answer_hint") or "你可以直接用一句话回答。").strip()
    blocks = [part for part in (context, question, hint) if part]
    if not blocks:
        return "我还缺少下一步要确认的问题，请先检查上游返回的响应内容。\n"
    rendered = "\n\n".join(blocks).strip() + "\n"
    assert_waiting_response_safe(payload, rendered)
    return rendered


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--payload", type=Path, help="JSON payload path. Defaults to stdin.")
    args = parser.parse_args(argv)

    sys.stdout.write(render_response(load_payload(args.payload)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
