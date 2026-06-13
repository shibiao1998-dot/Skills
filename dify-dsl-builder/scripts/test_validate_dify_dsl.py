#!/usr/bin/env python3
"""Regression tests for Dify DSL validator guardrails."""

from __future__ import annotations

import unittest

import validate_dify_dsl


def make_dsl(mode: str, nodes: list[dict], edges: list[dict]) -> dict:
    return {
        "kind": "app",
        "version": "0.3.1",
        "app": {"mode": mode, "name": "Validator fixture"},
        "workflow": {
            "conversation_variables": [],
            "environment_variables": [],
            "features": {},
            "graph": {
                "nodes": nodes,
                "edges": edges,
            },
        },
    }


def node(node_id: str, node_type: str, title: str | None = None, **extra: object) -> dict:
    data = {"type": node_type, "title": title or node_type}
    data.update(extra)
    return {"id": node_id, "data": data}


def edge(source: str, target: str) -> dict:
    return {"source": source, "target": target}


class AigcCodeQualityTests(unittest.TestCase):
    def test_rejects_boolean_code_output_type_observed_runtime_failure(self) -> None:
        errors: list[str] = []
        validate_dify_dsl.validate_code_node(
            "normalize_music_request",
            {
                "type": "code",
                "title": "规范音乐生成参数",
                "code_language": "javascript",
                "code": "function main() { return {instrumental_bool: true}; }",
                "outputs": {
                    "instrumental_bool": {"children": None, "type": "boolean"},
                },
            },
            errors,
        )

        self.assertTrue(
            any("CodeNodeData outputs" in error and "boolean" in error for error in errors),
            errors,
        )

    def test_rejects_hard_throw_for_missing_planner_output(self) -> None:
        errors: list[str] = []
        validate_dify_dsl.validate_aigc_code_quality_node(
            "normalize_media_request",
            {
                "type": "code",
                "title": "规范媒体生成参数",
                "code_language": "javascript",
                "code": """
function main({planned_keyframe_prompt}) {
  const imagePrompt = String(planned_keyframe_prompt || '').trim();
  if (!imagePrompt) {
    throw new Error('keyframe_prompt is missing from planner output');
  }
  return {
    image_prompt: imagePrompt,
    diagnostics: JSON.stringify({status: 'success'}, null, 2)
  };
}
""",
            },
            errors,
        )

        self.assertTrue(
            any("must not hard-throw on missing planner output" in error for error in errors),
            errors,
        )


class AgentStrategyContractTests(unittest.TestCase):
    def test_rejects_agent_missing_function_calling_strategy(self) -> None:
        errors: list[str] = []
        validate_dify_dsl.validate_agent_node(
            "knowledge_agent",
            {
                "type": "agent",
                "title": "检索专家",
                "agent_parameters": {},
            },
            errors,
        )

        self.assertTrue(
            any("FunctionCalling" in error and "agent_strategy_label" in error for error in errors),
            errors,
        )

    def test_rejects_react_agent_strategy_for_generated_dsl(self) -> None:
        errors: list[str] = []
        validate_dify_dsl.validate_agent_node(
            "knowledge_agent",
            {
                "type": "agent",
                "title": "检索专家",
                "agent_strategy_label": "ReAct",
                "agent_strategy_name": "ReAct",
                "agent_strategy_provider_name": "langgenius/agent/agent",
                "agent_parameters": {},
            },
            errors,
        )

        self.assertTrue(
            any("ReAct" in error and "FunctionCalling" in error for error in errors),
            errors,
        )


class IterationTypeContractTests(unittest.TestCase):
    def test_rejects_string_iterator_for_object_array_source(self) -> None:
        errors: list[str] = []
        nodes = [
            {
                "id": "planner",
                "data": {
                    "type": "llm",
                    "title": "Planner",
                    "structured_output_enabled": True,
                    "structured_output": {
                        "schema": {
                            "type": "object",
                            "properties": {
                                "shot_package": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {"shot_id": {"type": "string"}},
                                        "required": ["shot_id"],
                                        "additionalProperties": False,
                                    },
                                }
                            },
                            "required": ["shot_package"],
                            "additionalProperties": False,
                        }
                    },
                },
            },
            {
                "id": "iter",
                "data": {
                    "type": "iteration",
                    "title": "遍历",
                    "iterator_selector": ["planner", "structured_output", "shot_package"],
                    "iterator_input_type": "string",
                },
            },
        ]

        validate_dify_dsl.validate_iteration_type_contract(nodes, errors)

        self.assertTrue(
            any("iterator_input_type 'string' is incompatible" in error for error in errors),
            errors,
        )

    def test_rejects_code_variable_string_for_iteration_object_item(self) -> None:
        errors: list[str] = []
        nodes = [
            {
                "id": "iter",
                "data": {
                    "type": "iteration",
                    "title": "遍历",
                    "iterator_input_type": "array[object]",
                },
            },
            {
                "id": "unpack",
                "data": {
                    "type": "code",
                    "title": "解包",
                    "variables": [
                        {
                            "value_selector": ["iter", "item"],
                            "value_type": "string",
                            "variable": "item",
                        }
                    ],
                },
            },
        ]

        validate_dify_dsl.validate_iteration_item_variable_type_contract(nodes, errors)

        self.assertTrue(
            any("selector type 'object'" in error and "value_type 'string'" in error for error in errors),
            errors,
        )


class StructuralValidatorTests(unittest.TestCase):
    def test_rejects_retired_3d_resource_node_type_dropped_by_aihub_canvas(self) -> None:
        data = make_dsl(
            "workflow",
            [
                node("start", "start", "Start"),
                node(
                    "model",
                    "3d-resource-generation",
                    "Generate 3D",
                    model_info={
                        "config_version": "v1",
                        "model_id": "tencent-hunyuan-3d-3.1-resource-pro",
                        "model_name": "混元生 3D（专业版）3.1",
                        "provider": "hunyuan",
                        "provider_name": "腾讯混元",
                    },
                    params={"prompt": {"type": "constant", "value": "stylized classroom globe"}},
                ),
                node(
                    "end",
                    "end",
                    "End",
                    outputs=[
                        {
                            "variable": "models",
                            "value_selector": ["model", "models"],
                            "value_type": "array[file]",
                        }
                    ],
                ),
            ],
            [edge("start", "model"), edge("model", "end")],
        )

        errors, _warnings = validate_dify_dsl.validate_dsl(data, aigc_quality=True)

        self.assertTrue(
            any("3d-resource-generation" in error and "model-3d-generation" in error for error in errors),
            errors,
        )

    def test_accepts_model_3d_generation_node_type(self) -> None:
        data = make_dsl(
            "workflow",
            [
                node("start", "start", "Start"),
                node(
                    "model",
                    "model-3d-generation",
                    "Generate 3D",
                    model_info={
                        "config_version": "v1",
                        "model_id": "hunyuan-3d-3.1-pro-text",
                        "model_name": "混元3D 3.1 专业版",
                        "provider": "hunyuan",
                        "provider_name": "腾讯混元",
                    },
                    params={
                        "EnablePBR": {"type": "constant", "value": False},
                        "FaceCount": {"type": "constant", "value": 500000},
                        "GenerateType": {"type": "constant", "value": "Normal"},
                        "Prompt": {"type": "constant", "value": "stylized classroom globe"},
                        "ResultFormat": {"type": "constant", "value": None},
                        "enable_cs_transfer": {"type": "constant", "value": True},
                    },
                ),
                node(
                    "end",
                    "end",
                    "End",
                    outputs=[
                        {
                            "variable": "models",
                            "value_selector": ["model", "models"],
                            "value_type": "array[file]",
                        }
                    ],
                ),
            ],
            [edge("start", "model"), edge("model", "end")],
        )

        errors, _warnings = validate_dify_dsl.validate_dsl(data, aigc_quality=True)

        self.assertFalse(
            any("model-3d-generation" in error or "3d-resource-generation" in error for error in errors),
            errors,
        )

    def test_rejects_model_3d_generation_unaccepted_output_selectors(self) -> None:
        data = make_dsl(
            "workflow",
            [
                node("start", "start", "Start"),
                node(
                    "model",
                    "model-3d-generation",
                    "Generate 3D",
                    model_info={
                        "config_version": "v1",
                        "model_id": "hunyuan-3d-3.1-pro-text",
                        "model_name": "混元3D 3.1 专业版",
                        "provider": "hunyuan",
                        "provider_name": "腾讯混元",
                    },
                    params={
                        "EnablePBR": {"type": "constant", "value": False},
                        "FaceCount": {"type": "constant", "value": 500000},
                        "GenerateType": {"type": "constant", "value": "Normal"},
                        "Prompt": {"type": "constant", "value": "stylized classroom globe"},
                        "ResultFormat": {"type": "constant", "value": None},
                        "enable_cs_transfer": {"type": "constant", "value": True},
                    },
                ),
                node(
                    "pack",
                    "code",
                    "Pack",
                    variables=[
                        {
                            "variable": "resources",
                            "value_selector": ["model", "resources"],
                            "value_type": "string",
                        }
                    ],
                    code="function main({resources}) { return {out: String(resources || '')}; }",
                    outputs={"out": {"type": "string", "children": None}},
                ),
                node(
                    "end",
                    "end",
                    "End",
                    outputs=[
                        {
                            "variable": "out",
                            "value_selector": ["pack", "out"],
                            "value_type": "string",
                        }
                    ],
                ),
            ],
            [edge("start", "model"), edge("model", "pack"), edge("pack", "end")],
        )

        errors, _warnings = validate_dify_dsl.validate_dsl(data, aigc_quality=True)

        self.assertTrue(
            any("model.resources" in error and "available outputs are ['models']" in error for error in errors),
            errors,
        )

    def test_rejects_aigc_selector_with_recent_import_metadata_failure(self) -> None:
        data = make_dsl(
            "workflow",
            [
                node("start", "start", "Start"),
                node(
                    "video",
                    "video-generation",
                    "Generate video",
                    model_info={
                        "config_version": "v1",
                        "model_id": "jimeng-3.5-pro-text2video",
                        "model_name": "即梦 3.5 Pro 文生视频",
                        "provider": "jimeng",
                        "provider_name": "即梦",
                    },
                    params={
                        "camerafixed": {"type": "constant", "value": False},
                        "duration": {"type": "constant", "value": 5},
                        "enable_cs_transfer": {"type": "constant", "value": True},
                        "generate_audio": {"type": "constant", "value": True},
                        "prompt": {"type": "constant", "value": "short production video"},
                        "ratio": {"type": "constant", "value": "adaptive"},
                        "resolution": {"type": "constant", "value": "720p"},
                        "return_last_frame": {"type": "constant", "value": False},
                        "seed": {"type": "constant", "value": -1},
                        "watermark": {"type": "constant", "value": False},
                    },
                ),
                node(
                    "end",
                    "end",
                    "End",
                    outputs=[
                        {
                            "variable": "videos",
                            "value_selector": ["video", "videos"],
                            "value_type": "array[file]",
                        }
                    ],
                ),
            ],
            [edge("start", "video"), edge("video", "end")],
        )

        errors, _warnings = validate_dify_dsl.validate_dsl(data, aigc_quality=True)

        self.assertTrue(
            any("not production-safe for direct DSL generation" in error for error in errors),
            errors,
        )

    def test_rejects_aigc_catalog_alias_when_mapped_selector_is_not_safe(self) -> None:
        data = make_dsl(
            "workflow",
            [
                node("start", "start", "Start"),
                node(
                    "video",
                    "video-generation",
                    "Generate video",
                    model_info={
                        "config_version": "v1",
                        "model_id": "jimeng-3.5-pro",
                        "model_name": "即梦 3.5 Pro 文生视频",
                        "provider": "jimeng",
                        "provider_name": "即梦",
                    },
                    params={
                        "camerafixed": {"type": "constant", "value": False},
                        "duration": {"type": "constant", "value": 5},
                        "enable_cs_transfer": {"type": "constant", "value": True},
                        "generate_audio": {"type": "constant", "value": True},
                        "prompt": {"type": "constant", "value": "short production video"},
                        "ratio": {"type": "constant", "value": "adaptive"},
                        "resolution": {"type": "constant", "value": "720p"},
                        "return_last_frame": {"type": "constant", "value": False},
                        "seed": {"type": "constant", "value": -1},
                        "watermark": {"type": "constant", "value": False},
                    },
                ),
                node(
                    "end",
                    "end",
                    "End",
                    outputs=[
                        {
                            "variable": "videos",
                            "value_selector": ["video", "videos"],
                            "value_type": "array[file]",
                        }
                    ],
                ),
            ],
            [edge("start", "video"), edge("video", "end")],
        )

        errors, _warnings = validate_dify_dsl.validate_dsl(data, aigc_quality=True)

        self.assertTrue(
            any(
                "maps to canvas component selector id 'jimeng-3.5-pro-text2video'" in error
                and "not production-safe" in error
                for error in errors
            ),
            errors,
        )

    def test_accepts_saved_canvas_exported_video_selector(self) -> None:
        data = make_dsl(
            "workflow",
            [
                node("start", "start", "Start"),
                node(
                    "video",
                    "video-generation",
                    "Generate video",
                    model_info={
                        "config_version": "v1",
                        "model_id": "jimeng-seedance-1.5-pro-text2video",
                        "model_name": "即梦 3.5 Pro 文生视频",
                        "provider": "jimeng",
                        "provider_name": "即梦",
                    },
                    params={
                        "camera_fixed": {"type": "constant", "value": False},
                        "duration": {"type": "constant", "value": "5"},
                        "enable_cs_transfer": {"type": "constant", "value": True},
                        "generate_audio": {"type": "constant", "value": True},
                        "prompt": {"type": "constant", "value": "short production video"},
                        "ratio": {"type": "constant", "value": "adaptive"},
                        "resolution": {"type": "constant", "value": "720p"},
                        "return_last_frame": {"type": "constant", "value": False},
                        "seed": {"type": "constant", "value": -1},
                        "watermark": {"type": "constant", "value": False},
                    },
                ),
                node(
                    "end",
                    "end",
                    "End",
                    outputs=[
                        {
                            "variable": "videos",
                            "value_selector": ["video", "videos"],
                            "value_type": "array[file]",
                        }
                    ],
                ),
            ],
            [edge("start", "video"), edge("video", "end")],
        )

        errors, _warnings = validate_dify_dsl.validate_dsl(data, aigc_quality=True)

        self.assertFalse(
            any("video-generation" in error or "AIGC component" in error for error in errors),
            errors,
        )

    def test_rejects_video_runtime_params_bound_as_variables(self) -> None:
        data = make_dsl(
            "workflow",
            [
                node(
                    "start",
                    "start",
                    "Start",
                    variables=[
                        {"label": "duration", "required": False, "type": "text-input", "variable": "duration"},
                        {"label": "ratio", "required": False, "type": "text-input", "variable": "ratio"},
                        {"label": "resolution", "required": False, "type": "text-input", "variable": "resolution"},
                        {"label": "prompt", "required": False, "type": "paragraph", "variable": "prompt"},
                    ],
                ),
                node(
                    "video",
                    "video-generation",
                    "Generate video",
                    model_info={
                        "config_version": "v1",
                        "model_id": "jimeng-seedance-1.5-pro-text2video",
                        "model_name": "即梦 3.5 Pro 文生视频",
                        "provider": "jimeng",
                        "provider_name": "即梦",
                    },
                    params={
                        "camera_fixed": {"type": "constant", "value": False},
                        "duration": {"type": "variable", "value_selector": ["start", "duration"]},
                        "enable_cs_transfer": {"type": "constant", "value": True},
                        "generate_audio": {"type": "constant", "value": True},
                        "prompt": {"type": "variable", "value_selector": ["start", "prompt"]},
                        "ratio": {"type": "variable", "value_selector": ["start", "ratio"]},
                        "resolution": {"type": "variable", "value_selector": ["start", "resolution"]},
                        "return_last_frame": {"type": "constant", "value": False},
                        "seed": {"type": "constant", "value": -1},
                        "watermark": {"type": "constant", "value": False},
                    },
                ),
                node(
                    "end",
                    "end",
                    "End",
                    outputs=[
                        {
                            "variable": "videos",
                            "value_selector": ["video", "videos"],
                            "value_type": "array[file]",
                        }
                    ],
                ),
            ],
            [edge("start", "video"), edge("video", "end")],
        )

        errors, _warnings = validate_dify_dsl.validate_dsl(data, aigc_quality=True)

        self.assertTrue(
            any("duration" in error and "constant" in error and "variable" in error for error in errors),
            errors,
        )
        self.assertTrue(
            any("ratio" in error and "constant" in error and "variable" in error for error in errors),
            errors,
        )
        self.assertTrue(
            any("resolution" in error and "constant" in error and "variable" in error for error in errors),
            errors,
        )

    def test_rejects_jimeng_video_duration_outside_runtime_enum(self) -> None:
        data = make_dsl(
            "workflow",
            [
                node("start", "start", "Start"),
                node(
                    "video",
                    "video-generation",
                    "Generate video",
                    model_info={
                        "config_version": "v1",
                        "model_id": "jimeng-seedance-1.5-pro-text2video",
                        "model_name": "即梦 3.5 Pro 文生视频",
                        "provider": "jimeng",
                        "provider_name": "即梦",
                    },
                    params={
                        "camera_fixed": {"type": "constant", "value": False},
                        "duration": {"type": "constant", "value": "18"},
                        "enable_cs_transfer": {"type": "constant", "value": True},
                        "generate_audio": {"type": "constant", "value": True},
                        "prompt": {"type": "constant", "value": "short production video"},
                        "ratio": {"type": "constant", "value": "adaptive"},
                        "resolution": {"type": "constant", "value": "720p"},
                        "return_last_frame": {"type": "constant", "value": False},
                        "seed": {"type": "constant", "value": -1},
                        "watermark": {"type": "constant", "value": False},
                    },
                ),
                node(
                    "end",
                    "end",
                    "End",
                    outputs=[
                        {
                            "variable": "videos",
                            "value_selector": ["video", "videos"],
                            "value_type": "array[file]",
                        }
                    ],
                ),
            ],
            [edge("start", "video"), edge("video", "end")],
        )

        errors, _warnings = validate_dify_dsl.validate_dsl(data, aigc_quality=True)

        self.assertTrue(
            any("duration" in error and "'18'" in error and "allowed" in error for error in errors),
            errors,
        )

    def test_rejects_suno_vocal_gender_chinese_runtime_value(self) -> None:
        data = make_dsl(
            "workflow",
            [
                node("start", "start", "Start"),
                node(
                    "music",
                    "audio-generation",
                    "Generate music",
                    model_info={
                        "capability": "music_generate",
                        "config_version": "v1",
                        "model_id": "suno-v5-music_generate",
                        "model_name": "Suno V5",
                        "provider": "suno",
                        "provider_name": "Suno",
                    },
                    params={
                        "audioWeight": {"type": "constant", "value": 0.7},
                        "customMode": {"type": "constant", "value": True},
                        "enable_cs_transfer": {"type": "constant", "value": True},
                        "instrumental": {"type": "constant", "value": False},
                        "negativeTags": {"type": "constant", "value": "low quality"},
                        "promptDescription": {"type": "constant", "value": None},
                        "promptLyrics": {"type": "constant", "value": "demo lyrics"},
                        "style": {"type": "constant", "value": "pop"},
                        "styleWeight": {"type": "constant", "value": 0.9},
                        "title": {"type": "constant", "value": "demo"},
                        "vocalGender": {"type": "constant", "value": "男"},
                        "weirdnessConstraint": {"type": "constant", "value": 0.2},
                    },
                ),
                node(
                    "end",
                    "end",
                    "End",
                    outputs=[
                        {
                            "variable": "audios",
                            "value_selector": ["music", "audios"],
                            "value_type": "array[file]",
                        }
                    ],
                ),
            ],
            [edge("start", "music"), edge("music", "end")],
        )

        errors, _warnings = validate_dify_dsl.validate_dsl(data, aigc_quality=True)

        self.assertTrue(
            any("vocalGender" in error and "'男'" in error and "allowed" in error for error in errors),
            errors,
        )

    def test_rejects_media_param_bound_to_handoff_field(self) -> None:
        data = make_dsl(
            "workflow",
            [
                node(
                    "start",
                    "start",
                    "Start",
                    variables=[
                        {"label": "Brief", "required": True, "type": "paragraph", "variable": "brief"}
                    ],
                ),
                node(
                    "expert",
                    "code",
                    "Expert handoff",
                    code_language="javascript",
                    code="""
function main({brief}) {
  return {
    handoff: '请下游节点根据这个执行说明生成歌词，而不是歌词本身',
    promptLyrics: '真正的歌词内容'
  };
}
""",
                    outputs={
                        "handoff": {"type": "string"},
                        "promptLyrics": {"type": "string"},
                    },
                ),
                node(
                    "music",
                    "audio-generation",
                    "Generate music",
                    model_info={
                        "capability": "music_generate",
                        "config_version": "v1",
                        "model_id": "suno-v5-music_generate",
                        "model_name": "Suno V5",
                        "provider": "suno",
                        "provider_name": "Suno",
                    },
                    params={
                        "audioWeight": {"type": "constant", "value": 0.7},
                        "customMode": {"type": "constant", "value": True},
                        "enable_cs_transfer": {"type": "constant", "value": True},
                        "instrumental": {"type": "constant", "value": False},
                        "negativeTags": {"type": "constant", "value": "low quality"},
                        "promptDescription": {"type": "constant", "value": None},
                        "promptLyrics": {"type": "variable", "value_selector": ["expert", "handoff"]},
                        "style": {"type": "constant", "value": "pop"},
                        "styleWeight": {"type": "constant", "value": 0.9},
                        "title": {"type": "constant", "value": "demo"},
                        "vocalGender": {"type": "constant", "value": ""},
                        "weirdnessConstraint": {"type": "constant", "value": 0.2},
                    },
                ),
                node(
                    "end",
                    "end",
                    "End",
                    outputs=[
                        {
                            "variable": "audios",
                            "value_selector": ["music", "audios"],
                            "value_type": "array[file]",
                        }
                    ],
                ),
            ],
            [edge("start", "expert"), edge("expert", "music"), edge("music", "end")],
        )

        errors, _warnings = validate_dify_dsl.validate_dsl(data, aigc_quality=True)

        self.assertTrue(
            any("promptLyrics" in error and "handoff" in error for error in errors),
            errors,
        )

    def test_rejects_workflow_backed_aigc_tool_in_default_main_path(self) -> None:
        data = make_dsl(
            "workflow",
            [
                node("start", "start", "Start"),
                node(
                    "video_tool",
                    "tool",
                    "Dreamina video tool",
                    provider_id="41d6c1fa-5cd4-460d-9f6d-65d728614438",
                    provider_type="workflow",
                    tool_name="dreamina_image_generate_video_3_5_pro",
                    tool_node_version="2",
                    tool_configurations={},
                    tool_parameters={},
                    params={
                        "duration": "",
                        "image_asset_id": "",
                        "prompt": "",
                        "ratio": "",
                        "resolution": "",
                    },
                    outputs=[{"variable": "video_url"}],
                ),
                node(
                    "end",
                    "end",
                    "End",
                    outputs=[
                        {
                            "variable": "video_url",
                            "value_selector": ["video_tool", "video_url"],
                            "value_type": "string",
                        }
                    ],
                ),
            ],
            [edge("start", "video_tool"), edge("video_tool", "end")],
        )

        errors, _warnings = validate_dify_dsl.validate_dsl(data, aigc_quality=True)

        self.assertTrue(
            any("workflow-backed AIGC tool" in error and "video-generation" in error for error in errors),
            errors,
        )

    def test_rejects_image_generation_inside_iteration_as_video_main_path_blocker(self) -> None:
        data = make_dsl(
            "workflow",
            [
                node("start", "start", "Start"),
                node(
                    "shot_loop",
                    "iteration",
                    "分镜循环",
                    start_node_id="loop_start",
                    iterator_selector=["start", "shots"],
                    iterator_input_type="array[string]",
                    output_selector=["video", "videos"],
                ),
                node(
                    "loop_start",
                    "iteration-start",
                    "Loop Start",
                    isInIteration=True,
                    iteration_id="shot_loop",
                ),
                node(
                    "keyframe",
                    "image-generation",
                    "分镜关键帧",
                    isInIteration=True,
                    iteration_id="shot_loop",
                    model_info={
                        "config_version": "v1",
                        "model_id": "gpt-image-2-t2i",
                        "model_name": "GPT Image 2.0 文生图",
                        "provider": "openai",
                        "provider_name": "OpenAI",
                    },
                    params={
                        "background": {"type": "constant", "value": "opaque"},
                        "enable_cs_transfer": {"type": "constant", "value": True},
                        "n": {"type": "constant", "value": 1},
                        "output_compression": {"type": "constant", "value": 100},
                        "output_format": {"type": "constant", "value": "png"},
                        "prompt": {"type": "constant", "value": "keyframe"},
                        "quality": {"type": "constant", "value": "high"},
                        "size": {"type": "constant", "value": "1024x1536"},
                    },
                ),
                node(
                    "video",
                    "video-generation",
                    "生成视频",
                    isInIteration=True,
                    iteration_id="shot_loop",
                    model_info={
                        "config_version": "v1",
                        "model_id": "jimeng-seedance-1.5-pro-text2video",
                        "model_name": "即梦 3.5 Pro 文生视频",
                        "provider": "jimeng",
                        "provider_name": "即梦",
                    },
                    params={
                        "camera_fixed": {"type": "constant", "value": False},
                        "duration": {"type": "constant", "value": "12"},
                        "enable_cs_transfer": {"type": "constant", "value": True},
                        "generate_audio": {"type": "constant", "value": True},
                        "prompt": {"type": "constant", "value": "shot video"},
                        "ratio": {"type": "constant", "value": "9:16"},
                        "resolution": {"type": "constant", "value": "720p"},
                        "return_last_frame": {"type": "constant", "value": False},
                        "seed": {"type": "constant", "value": -1},
                        "watermark": {"type": "constant", "value": False},
                    },
                ),
                node(
                    "end",
                    "end",
                    "End",
                    outputs=[
                        {
                            "variable": "videos",
                            "value_selector": ["shot_loop", "output"],
                            "value_type": "array[file]",
                        }
                    ],
                ),
            ],
            [
                edge("start", "shot_loop"),
                {"source": "loop_start", "target": "keyframe", "data": {"sourceType": "iteration-start", "targetType": "image-generation", "isInIteration": True, "iteration_id": "shot_loop"}},
                {"source": "keyframe", "target": "video", "data": {"sourceType": "image-generation", "targetType": "video-generation", "isInIteration": True, "iteration_id": "shot_loop"}},
                edge("shot_loop", "end"),
            ],
        )

        errors, _warnings = validate_dify_dsl.validate_dsl(data, aigc_quality=True)

        self.assertTrue(
            any("image-generation" in error and "blocking" in error and "video-generation" in error for error in errors),
            errors,
        )

    def test_rejects_asr_model_list_id_after_canvas_export_evidence(self) -> None:
        data = make_dsl(
            "workflow",
            [
                node("start", "start", "Start"),
                node(
                    "asr",
                    "speech-recognition",
                    "Recognize speech",
                    model_info={
                        "config_version": "v1",
                        "model_id": "volc.seedasr.auc",
                        "model_name": "Doubao Seed ASR",
                        "provider": "doubao",
                        "provider_name": "豆包",
                    },
                    params={
                        "audio_format": {"type": "constant", "value": "mp3"},
                        "audio_input_type": {"type": "constant", "value": "url"},
                        "audio_url": {"type": "constant", "value": "https://example.com/audio.mp3"},
                        "language": {"type": "constant", "value": "auto"},
                    },
                ),
                node(
                    "end",
                    "end",
                    "End",
                    outputs=[
                        {
                            "variable": "text",
                            "value_selector": ["asr", "text"],
                            "value_type": "string",
                        }
                    ],
                ),
            ],
            [edge("start", "asr"), edge("asr", "end")],
        )

        errors, _warnings = validate_dify_dsl.validate_dsl(data, aigc_quality=True)

        self.assertTrue(
            any("doubao-asr-speech2text" in error and "not production-safe" in error for error in errors),
            errors,
        )

    def test_accepts_saved_canvas_exported_asr_selector(self) -> None:
        data = make_dsl(
            "workflow",
            [
                node("start", "start", "Start"),
                node(
                    "asr",
                    "speech-recognition",
                    "Recognize speech",
                    model_info={
                        "config_version": "v1",
                        "model_id": "doubao-asr-speech2text",
                        "model_name": "豆包语音识别",
                        "provider": "doubao",
                        "provider_name": "豆包",
                    },
                    params={
                        "audio_file": {"type": "constant", "value": None},
                        "audio_format": {"type": "constant", "value": "mp3"},
                        "audio_source": {"type": "constant", "value": "url"},
                        "audio_url": {"type": "constant", "value": "https://example.com/audio.mp3"},
                        "language": {"type": "constant", "value": ""},
                    },
                ),
                node(
                    "end",
                    "end",
                    "End",
                    outputs=[
                        {
                            "variable": "text",
                            "value_selector": ["asr", "text"],
                            "value_type": "string",
                        }
                    ],
                ),
            ],
            [edge("start", "asr"), edge("asr", "end")],
        )

        errors, _warnings = validate_dify_dsl.validate_dsl(data, aigc_quality=True)

        self.assertFalse(
            any("speech-recognition" in error or "AIGC component" in error for error in errors),
            errors,
        )

    def test_rejects_stale_aigc_diagnostics_selector(self) -> None:
        data = make_dsl(
            "workflow",
            [
                node("start", "start", "Start"),
                node(
                    "normalize",
                    "code",
                    "Normalize diagnostics",
                    code_language="javascript",
                    code="""
function main() {
  const diagnostics = {
    status: 'success',
    selected_model: 'jimeng-3.5-pro-text2video',
    selected_model_note: 'stale selector id jimeng-3.5-pro-text2video'
  };
  return {
    video_prompt: 'short production video',
    diagnostics: JSON.stringify(diagnostics, null, 2)
  };
}
""",
                    outputs={
                        "video_prompt": {"type": "string"},
                        "diagnostics": {"type": "string"},
                    },
                ),
                node(
                    "video",
                    "video-generation",
                    "Generate video",
                    model_info={
                        "config_version": "v1",
                        "model_id": "jimeng-seedance-1.5-pro-text2video",
                        "model_name": "即梦 3.5 Pro 文生视频",
                        "provider": "jimeng",
                        "provider_name": "即梦",
                    },
                    params={
                        "camera_fixed": {"type": "constant", "value": False},
                        "duration": {"type": "constant", "value": "5"},
                        "enable_cs_transfer": {"type": "constant", "value": True},
                        "generate_audio": {"type": "constant", "value": True},
                        "prompt": {"type": "variable", "value_selector": ["normalize", "video_prompt"]},
                        "ratio": {"type": "constant", "value": "adaptive"},
                        "resolution": {"type": "constant", "value": "720p"},
                        "return_last_frame": {"type": "constant", "value": False},
                        "seed": {"type": "constant", "value": -1},
                        "watermark": {"type": "constant", "value": False},
                    },
                ),
                node(
                    "end",
                    "end",
                    "End",
                    outputs=[
                        {
                            "variable": "videos",
                            "value_selector": ["video", "videos"],
                            "value_type": "array[file]",
                        }
                    ],
                ),
            ],
            [edge("start", "normalize"), edge("normalize", "video"), edge("video", "end")],
        )

        errors, _warnings = validate_dify_dsl.validate_dsl(data, aigc_quality=True)

        self.assertTrue(
            any("AIGC diagnostics mention stale" in error for error in errors),
            errors,
        )

    def test_rejects_tool_node_missing_tool_configurations(self) -> None:
        data = make_dsl(
            "workflow",
            [
                node("start", "start", "Start"),
                node(
                    "tool_1",
                    "tool",
                    "Missing tool configurations",
                    provider_id="test-provider",
                    tool_name="test_tool",
                    tool_parameters={},
                    outputs=[{"variable": "text"}],
                ),
                node(
                    "end",
                    "end",
                    "End",
                    outputs=[
                        {
                            "variable": "result",
                            "value_selector": ["tool_1", "text"],
                            "value_type": "string",
                        }
                    ],
                ),
            ],
            [edge("start", "tool_1"), edge("tool_1", "end")],
        )

        errors, _warnings = validate_dify_dsl.validate_dsl(data)

        self.assertTrue(any("tool_configurations" in error for error in errors), errors)

    def test_rejects_structured_output_reference_without_enabled_metadata(self) -> None:
        data = make_dsl(
            "workflow",
            [
                node(
                    "start",
                    "start",
                    "Start",
                    variables=[
                        {
                            "label": "Query",
                            "required": True,
                            "type": "text-input",
                            "variable": "query",
                        }
                    ],
                ),
                node("planner", "llm", "Planner"),
                node(
                    "normalize",
                    "code",
                    "Normalize",
                    code_language="python",
                    code="def main(result):\n    return {'result': result}\n",
                    variables=[
                        {
                            "variable": "result",
                            "value_selector": ["planner", "structured_output", "result"],
                            "value_type": "string",
                        }
                    ],
                    outputs={"result": {"type": "string"}},
                ),
                node(
                    "end",
                    "end",
                    "End",
                    outputs=[
                        {
                            "variable": "result",
                            "value_selector": ["normalize", "result"],
                            "value_type": "string",
                        }
                    ],
                ),
            ],
            [edge("start", "planner"), edge("planner", "normalize"), edge("normalize", "end")],
        )

        errors, _warnings = validate_dify_dsl.validate_dsl(data)

        self.assertTrue(
            any("structured_output_enabled: true" in error for error in errors),
            errors,
        )

    def test_rejects_code_node_selecting_whole_llm_structured_output_object(self) -> None:
        data = make_dsl(
            "workflow",
            [
                node(
                    "start",
                    "start",
                    "Start",
                    variables=[
                        {
                            "label": "Query",
                            "required": True,
                            "type": "text-input",
                            "variable": "query",
                        }
                    ],
                ),
                node(
                    "planner",
                    "llm",
                    "Planner",
                    structured_output_enabled=True,
                    structured_output={
                        "schema": {
                            "type": "object",
                            "properties": {"result": {"type": "string"}},
                            "required": ["result"],
                            "additionalProperties": False,
                        }
                    },
                ),
                node(
                    "normalize",
                    "code",
                    "Normalize",
                    code_language="python",
                    code="def main(result):\n    return {'result': result}\n",
                    variables=[
                        {
                            "variable": "result",
                            "value_selector": ["planner", "structured_output"],
                            "value_type": "object",
                        }
                    ],
                    outputs={"result": {"type": "object"}},
                ),
                node(
                    "end",
                    "end",
                    "End",
                    outputs=[
                        {
                            "variable": "result",
                            "value_selector": ["normalize", "result"],
                            "value_type": "object",
                        }
                    ],
                ),
            ],
            [edge("start", "planner"), edge("planner", "normalize"), edge("normalize", "end")],
        )

        errors, _warnings = validate_dify_dsl.validate_dsl(data)

        self.assertTrue(any("selects whole LLM structured_output" in error for error in errors), errors)

    def test_rejects_query_variable_selector_missing_source_node(self) -> None:
        data = make_dsl(
            "workflow",
            [
                node("start", "start", "Start"),
                node(
                    "planner",
                    "llm",
                    "Planner",
                    query_variable_selector=["missing_node", "query"],
                ),
                node(
                    "end",
                    "end",
                    "End",
                    outputs=[
                        {
                            "variable": "result",
                            "value_selector": ["planner", "text"],
                            "value_type": "string",
                        }
                    ],
                ),
            ],
            [edge("start", "planner"), edge("planner", "end")],
        )

        errors, _warnings = validate_dify_dsl.validate_dsl(data)

        self.assertTrue(any("missing variable source node" in error for error in errors), errors)

    def test_rejects_missing_llm_structured_output_field(self) -> None:
        data = make_dsl(
            "workflow",
            [
                node("start", "start", "Start"),
                node(
                    "planner",
                    "llm",
                    "Planner",
                    structured_output_enabled=True,
                    structured_output={
                        "schema": {
                            "type": "object",
                            "properties": {"result": {"type": "string"}},
                            "required": ["result"],
                            "additionalProperties": False,
                        }
                    },
                ),
                node(
                    "normalize",
                    "code",
                    "Normalize",
                    code_language="python",
                    code="def main(missing_field):\n    return {'missing_field': missing_field}\n",
                    variables=[
                        {
                            "variable": "missing_field",
                            "value_selector": ["planner", "structured_output", "missing_field"],
                            "value_type": "string",
                        }
                    ],
                    outputs={"missing_field": {"type": "string"}},
                ),
                node(
                    "end",
                    "end",
                    "End",
                    outputs=[
                        {
                            "variable": "result",
                            "value_selector": ["normalize", "missing_field"],
                            "value_type": "string",
                        }
                    ],
                ),
            ],
            [edge("start", "planner"), edge("planner", "normalize"), edge("normalize", "end")],
        )

        errors, _warnings = validate_dify_dsl.validate_dsl(data)

        self.assertTrue(any("missing structured_output field" in error for error in errors), errors)

    def test_rejects_workflow_with_answer_final_node(self) -> None:
        data = make_dsl(
            "workflow",
            [
                node("start", "start", "Start"),
                node(
                    "end",
                    "end",
                    "End",
                    outputs=[
                        {
                            "variable": "result",
                            "value_selector": ["start", "query"],
                            "value_type": "string",
                        }
                    ],
                ),
                node("answer", "answer", "Answer", answer="{{#start.query#}}"),
            ],
            [edge("start", "end"), edge("end", "answer")],
        )

        errors, _warnings = validate_dify_dsl.validate_dsl(data)

        self.assertTrue(any("workflow mode must not include an answer node" in error for error in errors), errors)

    def test_rejects_advanced_chat_with_end_final_node(self) -> None:
        data = make_dsl(
            "advanced-chat",
            [
                node("start", "start", "Start"),
                node("answer", "answer", "Answer", answer="{{#sys.query#}}"),
                node(
                    "end",
                    "end",
                    "End",
                    outputs=[
                        {
                            "variable": "result",
                            "value_selector": ["start", "query"],
                            "value_type": "string",
                        }
                    ],
                ),
            ],
            [edge("start", "answer"), edge("answer", "end")],
        )

        errors, _warnings = validate_dify_dsl.validate_dsl(data)

        self.assertTrue(any("advanced-chat mode must not include an end node" in error for error in errors), errors)


if __name__ == "__main__":
    unittest.main()
