#!/usr/bin/env python3
"""Classify one Dify DSL Builder user turn and produce a vNext response payload.

This helper intentionally stops before writing a DSL unless a higher-level agent
has already completed final alignment and invokes generation itself. The active
path here is interaction-safe: one user-facing question or one final confirmation
message, with engineering details kept out of the response.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


EXPECTATION_SENTENCE = "你可以直接回复 A 或 B，也可以用一句话修正。"


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())


def contains_any(text: str, terms: tuple[str, ...]) -> bool:
    lower = text.lower()
    return any(term.lower() in lower for term in terms)


def is_aigc_media_request(text: str) -> bool:
    return contains_any(
        text,
        (
            "aigc",
            "图片",
            "图像",
            "视频",
            "短视频",
            "mv",
            "3d",
            "模型",
            "音频",
            "语音",
            "识别",
            "歌曲",
            "音乐",
            "tts",
        ),
    )


def is_source_quality_gate(text: str) -> bool:
    has_source_evidence = contains_any(
        text,
        (
            "可信作者",
            "朝代",
            "原文",
            "来源链接",
            "公开来源",
            "可靠来源",
            "证据",
            "出处",
        ),
    )
    has_missing_condition = contains_any(
        text,
        (
            "找不到",
            "无法找到",
            "未找到",
            "没有找到",
            "未检索到",
            "证据不足",
        ),
    )
    has_no_fabrication_gate = contains_any(
        text,
        (
            "不继续生成",
            "不能继续生成",
            "停止生成",
            "不要编造",
            "不编造",
        ),
    )
    return has_source_evidence and has_missing_condition and has_no_fabrication_gate


def project_slug(requirement: str, explicit_slug: str | None = None) -> str:
    if explicit_slug:
        return explicit_slug
    if "成语" in requirement and "视频" in requirement:
        return "idiom-story-video"
    if contains_any(requirement, ("旧 dsl", "旧DSL", "导入错误", "tool_configurations")):
        return "dsl-repair"
    cleaned = re.sub(r"[^a-z0-9]+", "-", requirement.lower()).strip("-")
    return cleaned[:48].strip("-") or "dify-dsl-project"


def ask_payload(
    *,
    response_type: str,
    context: str,
    question: str,
    hint: str,
    slug: str,
) -> dict[str, Any]:
    return {
        "decision": "not_ready",
        "response_type": response_type,
        "project_slug": slug,
        "context": context,
        "recommended_next_question": question,
        "answer_hint": hint,
    }


def message_payload(
    *,
    response_type: str,
    message: str,
    slug: str,
) -> dict[str, Any]:
    return {
        "decision": "not_ready",
        "response_type": response_type,
        "project_slug": slug,
        "message": message,
    }


def classify_turn(
    requirement: str,
    *,
    slug: str,
    existing_dsl: Path | None = None,
    requirement_doc: Path | None = None,
    feedback: str | None = None,
    narrow_repair: bool = False,
) -> dict[str, Any]:
    text = normalize(requirement)
    has_uploaded_doc = requirement_doc is not None or contains_any(
        text,
        ("上传", "需求文档", "写清楚的需求"),
    )
    if "生成文档" in text or "文档生成" in text:
        has_uploaded_doc = requirement_doc is not None
    has_old_dsl = existing_dsl is not None or contains_any(
        text,
        ("旧 dsl", "旧DSL", "已有 dsl", "已有DSL", "导入后报", "导入错误"),
    )
    mechanical_repair = narrow_repair or (
        has_old_dsl
        and contains_any(text, ("只修", "不改业务逻辑", "tool_configurations", "missing"))
    )
    asks_to_generate = contains_any(
        text,
        (
            "已完成澄清",
            "请求生成",
            "可以生成",
            "开始生成",
            "直接生成",
            "按这个方案生成",
            "请生成",
            "生成 dsl",
            "生成DSL",
        ),
    )
    if contains_any(text, ("继续生成",)) and not contains_any(text, ("不继续生成", "不能继续生成", "先不要继续生成")):
        asks_to_generate = True
    if contains_any(text, ("不继续生成", "不能继续生成", "先不要生成", "不要生成")) and not is_source_quality_gate(text):
        asks_to_generate = False

    if mechanical_repair:
        return message_payload(
            response_type="narrow_repair_confirmation",
            slug=slug,
            message=(
                "我会先定位这个导入错误，只修 tool_configurations 缺失这一类结构问题，"
                "保持原输入输出和业务逻辑不变，并按窄修复处理。"
            ),
        )

    if feedback:
        return ask_payload(
            response_type="runtime_feedback_boundary",
            slug=slug,
            context="我已经记录这次运行反馈，会先把问题收敛到最影响你使用的方向。",
            question="这次优先把它修到稳定跑通，还是先把生成结果调到更符合预期？",
            hint=(
                "我的推荐：A. 先修稳定跑通，确保视频链接、状态和诊断能正确返回。"
                " B. 先调结果质量，让内容、风格和呈现更接近你想要的效果。"
                f"{EXPECTATION_SENTENCE}"
            ),
        )

    if has_uploaded_doc:
        return message_payload(
            response_type="uploaded_document_boundary",
            slug=slug,
            message=(
                "我先确认这份文档就是本次生成范围：目标、输入输出和好结果都以文档为准，"
                "暂时不额外扩展需求。我的推荐：A. 按这份文档边界继续；"
                f"B. 先补充文档里没有写清楚的业务边界。{EXPECTATION_SENTENCE}"
            ),
        )

    if has_old_dsl:
        return message_payload(
            response_type="preserve_first_confirmation",
            slug=slug,
            message=(
                "我会先定位旧 DSL 的失败阶段，并默认保持原输入输出不变；"
                "只有确认会影响导入或运行的结构问题才改。"
                "我的推荐：A. 保留原业务语义，只修导入或运行问题。"
                " B. 允许我在保留目标的前提下重新整理流程。"
                f"{EXPECTATION_SENTENCE}"
            ),
        )

    if asks_to_generate:
        if is_aigc_media_request(text):
            source_quality = ""
            if contains_any(text, ("联网", "检索", "公开来源", "原文", "校验", "来源")):
                source_quality = (
                    "联网检索和原文校验会作为前置质量检查；找不到可靠来源时，"
                    "工作流会返回清楚诊断，不编造出处。"
                )
            audio_role = "歌曲音频" if contains_any(text, ("歌曲", "音乐", "mv")) else "音频内容"
            return message_payload(
                response_type="final_alignment",
                slug=slug,
                message=(
                    source_quality +
                    f"我会默认用 AI Hub 原生 AIGC 节点来实现：音频生成负责{audio_role}，"
                    "视频生成负责 MV 片段，必要时用图像生成补首帧；LLM 和 Code 节点只负责"
                    "歌词、分镜、参数整理、质量检查和输出包装。我的推荐：A. 直接按原生节点方案生成；"
                    f"B. 只有你明确要保留既有生产线时再告诉我调整方向。{EXPECTATION_SENTENCE}"
                ),
            )
        return message_payload(
            response_type="final_alignment",
            slug=slug,
            message=(
                "我会把这个工作流拆成输入理解、内容生成、结构化输出和第一次运行验证四段，"
                "先确认这些维度都对齐，再进入文件生成。我的推荐：A. 按这个拆法生成；"
                f"B. 先调整目标或输出边界。{EXPECTATION_SENTENCE}"
            ),
        )

    if is_aigc_media_request(text) and contains_any(text, ("联网", "检索", "公开来源", "原文", "校验", "来源")):
        return ask_payload(
            response_type="source_checked_aigc_outcome_question",
            slug=slug,
            context=(
                "我会把来源校验、歌曲音频和 MV 完整作品当成目标，技术可行性放到首测里验证。"
            ),
            question="这个完整作品优先用于哪类使用场景？",
            hint=(
                "我的推荐：A. 面向短视频发布，优先完整可播放和传播效果。"
                " B. 面向内部审核或选题验证，优先来源证据、歌词和分镜完整。"
                f"{EXPECTATION_SENTENCE}"
            ),
        )

    if "成语" in text and "视频" in text:
        return ask_payload(
            response_type="outcome_first_question",
            slug=slug,
            context="我先按结果效果来收口，不急着决定节点和模型。",
            question="这个成语故事短视频主要面向哪类目标用户？",
            hint=(
                "我的推荐：A. 小学生，用 30 秒短视频帮助理解来源和寓意。"
                " B. 家长/老师，用作课堂展示或亲子讲解。"
                f"{EXPECTATION_SENTENCE}"
            ),
        )

    return ask_payload(
        response_type="outcome_first_question",
        slug=slug,
        context="我先确认会影响结果质量的一件事，清楚后再继续设计工作流。",
        question="这个工作流最希望帮哪类使用者完成什么结果？",
        hint=(
            "我的推荐：A. 面向一线业务人员，快速产出可直接使用的内容或素材。"
            " B. 面向产品/运营人员，生成可复用、可迭代的任务工作流。"
            f"{EXPECTATION_SENTENCE}"
        ),
    )


def generate_project(
    requirement: str,
    project_dir: Path,
    slug: str | None = None,
    *,
    existing_dsl: Path | None = None,
    requirement_doc: Path | None = None,
    feedback: str | None = None,
    external_evidence_summary: str | None = None,
    narrow_repair: bool = False,
    **_ignored_compatibility_flags: Any,
) -> dict[str, Any]:
    del external_evidence_summary
    normalized = normalize(requirement)
    resolved_slug = project_slug(normalized, slug)
    project_dir.mkdir(parents=True, exist_ok=True)
    return classify_turn(
        normalized,
        slug=resolved_slug,
        existing_dsl=existing_dsl,
        requirement_doc=requirement_doc,
        feedback=feedback,
        narrow_repair=narrow_repair,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Print raw JSON payload.")
    parser.add_argument("--project-dir", type=Path, required=True)
    parser.add_argument("--slug")
    parser.add_argument("--existing-dsl", type=Path)
    parser.add_argument("--requirement-doc", type=Path)
    parser.add_argument("--feedback")
    parser.add_argument("--narrow-repair", action="store_true")
    parser.add_argument("text", nargs="*", help="User turn text. Reads stdin when omitted.")
    args = parser.parse_args(argv)

    requirement = " ".join(args.text) if args.text else sys.stdin.read()
    payload = generate_project(
        requirement,
        args.project_dir,
        args.slug,
        existing_dsl=args.existing_dsl,
        requirement_doc=args.requirement_doc,
        feedback=args.feedback,
        narrow_repair=args.narrow_repair,
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload.get("decision") == "generated" else 3


if __name__ == "__main__":
    raise SystemExit(main())
