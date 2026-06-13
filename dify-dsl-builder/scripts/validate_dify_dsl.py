#!/usr/bin/env python3
"""Static checks for Dify app DSL YAML files.

This is intentionally conservative. It catches common generation mistakes before
the user tries to import the file into Dify, but it is not a replacement for a
live import test against the target Dify instance.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import shutil
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any

try:
    import yaml
except Exception as exc:  # pragma: no cover
    print(f"PyYAML is required: {exc}", file=sys.stderr)
    sys.exit(2)


UNSUPPORTED_SCHEMA_KEYS = {"$ref", "oneOf", "anyOf", "allOf", "if", "then", "else"}
VALID_APP_MODES = {"workflow", "advanced-chat"}
AIGC_NODE_TYPES = {
    "image-generation",
    "video-generation",
    "audio-generation",
    "speech-recognition",
    "3d-generation",
    "model-3d-generation",
}
AIGC_NODE_COMPATIBLE_MODEL_TYPES = {
    "speech-recognition": {"speech-recognition", "audio-generation"},
    "model-3d-generation": {"3d-generation", "3d-resource-generation"},
}
RETIRED_AIGC_NODE_TYPE_REPLACEMENTS = {
    "3d-resource-generation": "model-3d-generation",
}
RETIRED_MODEL_REPLACEMENTS: dict[str, str] = {
    "tencent-hunyuan-3d-3.1-resource-pro": "hunyuan-3d-3.1-pro-text",
}
LOW_QUALITY_LLM_DEFAULTS = {"gpt-4o-mini", "openai-gpt-4o-mini"}
QUALITY_FIRST_LLM_MODELS = {
    "gpt-5.5-2026-04-24",
    "gpt-5.4-2026-03-05",
    "claude-opus-4-7",
    "claude-opus-4-6",
    "claude-sonnet-4-6",
    "gemini-3.1-pro-preview",
    "gemini-3-pro-preview",
    "qwen3-max-2025-09-23",
    "kimi-k2-5-260127",
    "deepseek-v3.2-1201",
}
ECONOMY_LLM_MARKERS = (
    "mini",
    "lite",
    "flash",
    "turbo",
    "fast",
    "低时延",
    "高并发",
    "成本敏感",
    "轻量",
)
OBSERVED_AIGC_TOOL_SHAPES = {
    "seedream_i2i_t2i_tool": {
        "provider_id": "22632cc7-732a-4b68-94e7-5be7e1b48ba9",
        "params": {
            "prompt",
            "images",
            "model",
            "size",
            "custom_size",
            "max_images",
            "sequential_image_generation",
            "watermark",
        },
    },
    "dreamina_image_generate_video_3_5_pro": {
        "provider_id": "41d6c1fa-5cd4-460d-9f6d-65d728614438",
        "params": {
            "prompt",
            "image",
            "duration",
            "ratio",
            "resolution",
            "seed",
            "generate_audio",
            "return_last_frame",
            "watermark",
            "camerafixed",
        },
    },
    "aic_infinite_talk": {
        "provider_id": "a7215485-9f16-44fa-a8ee-c9825e8e9ddf",
        "params": {
            "upload_image_url",
            "upload_audio_url",
            "prompt",
            "width",
            "height",
            "fps",
            "num_frams",
        },
    },
    "aic_lip_sync_seedance2_15sec": {
        "provider_id": "e9b0ceef-81cf-499a-809b-edfe8159ae2b",
        "params": {"image_file", "image_url", "tts_file", "tts_url", "tts_text"},
    },
    "aic_resource_storage": {
        "provider_id": "8e9ef31b-83d5-4a5a-a717-1e7d86250a62",
        "params": {"url", "type", "isCs", "isCdn"},
    },
    "volc_diaobo_videoconcat": {
        "provider_id": "e5d9c6cd-a06f-4b0f-9d42-09fa0f79b13b",
        "params": {"video_params", "audio_params", "subtitle_params", "width", "height", "is_web_project"},
    },
    "suno_instrumental_tool": {
        "provider_id": "b7eea029-31a8-4190-b08c-da1b21dffda3",
        "params": {
            "prompt",
            "style",
            "title",
            "model",
            "instrumental",
            "negativeTags",
            "audioWeight",
            "styleWeight",
            "vocalGender",
            "weirdnessConstraint",
        },
    },
    "doubao_seed_tts_1_0": {
        "provider_id": "2405d153-9a5e-4285-8732-ac68bb7e902a",
        "params": {
            "text",
            "speaker",
            "audio_params_format",
            "audio_params_speech_rate",
            "enable_language_detector",
            "disable_markdown_filter",
        },
    },
    "aic_aigc_gen_actor_v2": {
        "provider_id": "93c73102-c21f-4f33-84fa-98932da1d480",
        "params": {
            "content",
            "artistic_style",
            "image_discription",
            "images",
            "images2",
            "all_actors",
            "save_to_db",
        },
    },
    "aic_jianying_draft": {
        "provider_id": "db719041-7cc2-40c1-9278-38810f5d2c49",
        "params": {"script", "video_aspect", "video_width", "video_height"},
    },
}
GENERIC_AIGC_HTTP_PHRASES = (
    "video generation service",
    "image generation api",
    "3d generation endpoint",
    "短视频生成服务",
    "视频生成服务",
    "图像生成接口",
    "图片生成接口",
    "3d生成接口",
    "3D生成接口",
)
MEDIA_GENERATION_KEYWORDS = (
    "video generation",
    "image generation",
    "3d generation",
    "generate video",
    "generate image",
    "video job",
    "image job",
    "视频生成",
    "短视频",
    "图像生成",
    "图片生成",
    "文生视频",
    "图生视频",
    "文生图",
    "图生图",
    "3d",
    "3D",
)
PLACEHOLDER_URL_MARKERS = (
    "example.com",
    "placeholder",
    "todo",
    "待填写",
    "your-",
    "<",
    "未配置",
)
PROMPT_PLACEHOLDER_MARKERS = (
    "todo",
    "placeholder",
    "待填写",
    "your-",
    "xxx",
    "示例内容",
)
PRODUCTION_PROMPT_MIN_CHARS = 320
PRODUCTION_PROMPT_COVERAGE = {
    "role": ("你是", "role", "专家", "资深", "designer", "architect"),
    "task": ("任务", "目标", "负责", "需要", "task", "goal"),
    "input_interpretation": ("输入", "变量", "{{#", "input", "context"),
    "output_contract": ("输出", "返回", "契约", "字段", "json", "schema", "output"),
    "quality_criteria": ("质量", "标准", "检查", "验收", "criteria", "quality"),
    "constraints": ("约束", "边界", "不得", "不能", "不要", "禁止", "风险", "constraints", "risks"),
    "iteration_signal": ("迭代", "反馈", "diagnostics", "diagnostic", "quality_checklist", "decision_trace"),
}
NO_OFFLINE_DATE_VALUES = {"", "-", "暂无计划", "暂无数据", "none", "null"}
ENV_REFERENCE_PATTERN = re.compile(r"\{\{#env\.([A-Za-z_][A-Za-z0-9_]*)#\}\}")
VARIABLE_INTERPOLATION_PATTERN = re.compile(r"\{\{#([^{}#]+)#\}\}")
SELECTOR_KEYS = {
    "value_selector",
    "variable_selector",
    "iterator_selector",
    "output_selector",
    "query_variable_selector",
}
PSEUDO_SELECTOR_SOURCES = {"env", "sys", "conversation"}
DIRECT_NODE_OUTPUTS = {
    "image-generation": {"images"},
    "video-generation": {"videos"},
    "audio-generation": {"audios"},
    "speech-recognition": {"text", "utterances", "duration"},
    "3d-generation": {"files", "models", "resources"},
    "model-3d-generation": {"models"},
}
DEFAULT_GENERATED_AGENT_STRATEGY = {
    "agent_strategy_label": "FunctionCalling",
    "agent_strategy_name": "function_calling",
    "agent_strategy_provider_name": "langgenius/agent/agent",
}
MEDIA_CONTENT_PARAM_NAMES = {
    "prompt",
    "promptLyrics",
    "promptDescription",
    "style",
    "title",
    "negativeTags",
    "text",
    "content",
    "lyrics",
    "image_prompt",
    "video_prompt",
    "audio_prompt",
}
PROCEDURAL_MEDIA_SOURCE_MARKERS = {
    "handoff",
    "diagnostic",
    "diagnostics",
    "instruction",
    "instructions",
    "execution_instruction",
    "quality_checklist",
    "risk",
    "risks",
}
OPTIONAL_ITERATION_ASSET_MARKERS = {
    "optional",
    "reference",
    "non-blocking",
    "nonblocking",
    "asset",
    "可选",
    "参考",
    "非阻塞",
    "素材",
}
VALID_CODE_OUTPUT_TYPES = {
    "string",
    "number",
    "object",
    "array[string]",
    "array[number]",
    "array[object]",
}
MODEL_LIST_PATH = (
    Path(__file__).resolve().parents[1]
    / "references"
    / "ndhy-ai-hub-model-list-2026-05-22.json"
)
TOOL_FINGERPRINTS_PATH = (
    Path(__file__).resolve().parents[1]
    / "references"
    / "ndhy-aigc-tool-fingerprints.json"
)
COMPONENT_FINGERPRINTS_PATH = (
    Path(__file__).resolve().parents[1]
    / "references"
    / "ndhy-aigc-component-fingerprints.json"
)


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError("YAML root must be a mapping")
    return data


def require_mapping(value: Any, label: str, errors: list[str]) -> dict[str, Any]:
    if not isinstance(value, dict):
        errors.append(f"{label} must be a mapping")
        return {}
    return value


def require_list(value: Any, label: str, errors: list[str]) -> list[Any]:
    if not isinstance(value, list):
        errors.append(f"{label} must be a list")
        return []
    return value


def find_schema_candidates(value: Any, path: str = "$") -> list[tuple[str, dict[str, Any]]]:
    found: list[tuple[str, dict[str, Any]]] = []
    if isinstance(value, dict):
        keys = set(value.keys())
        if {"type", "properties"} <= keys or {"json_schema", "schema"} & keys:
            if value.get("type") == "object" or "properties" in value:
                found.append((path, value))
                return found
        for key, child in value.items():
            found.extend(find_schema_candidates(child, f"{path}.{key}"))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(find_schema_candidates(child, f"{path}[{index}]"))
    return found


def validate_json_schema(
    schema: dict[str, Any],
    label: str,
    errors: list[str],
    warnings: list[str],
    *,
    strict_schema: bool,
) -> None:
    for key in schema:
        if key in UNSUPPORTED_SCHEMA_KEYS:
            message = f"{label}: unsupported JSON Schema keyword {key}"
            (errors if strict_schema else warnings).append(message)

    schema_type = schema.get("type")
    type_values = schema_type if isinstance(schema_type, list) else [schema_type]
    if "boolean" in type_values or "bool" in type_values:
        errors.append(f"{label}: boolean type is not allowed; use string enum ['true', 'false']")
    if schema_type == "null":
        message = f"{label}: null type is not supported by the strict Dify schema rules"
        (errors if strict_schema else warnings).append(message)
    if isinstance(schema_type, list):
        message = f"{label}: union type {schema_type!r} is import-observed but not strict-schema-safe"
        (errors if strict_schema else warnings).append(message)

    if schema_type == "object" or "properties" in schema:
        if schema.get("type") != "object":
            errors.append(f"{label}: object schema must set type: object")
        if not isinstance(schema.get("properties"), dict):
            errors.append(f"{label}: object schema must include properties mapping")
        if not isinstance(schema.get("required"), list):
            message = f"{label}: object schema should include required list"
            (errors if strict_schema else warnings).append(message)
        if schema.get("additionalProperties") is not False:
            message = f"{label}: object schema should set additionalProperties: false"
            (errors if strict_schema else warnings).append(message)

    if schema_type == "array" and "items" not in schema:
        errors.append(f"{label}: array schema must include items")

    for key, child in schema.items():
        if key in UNSUPPORTED_SCHEMA_KEYS and not strict_schema:
            continue
        if isinstance(child, dict):
            validate_json_schema(child, f"{label}.{key}", errors, warnings, strict_schema=strict_schema)
        elif isinstance(child, list):
            for index, item in enumerate(child):
                if isinstance(item, dict):
                    validate_json_schema(item, f"{label}.{key}[{index}]", errors, warnings, strict_schema=strict_schema)


def validate_code_node(node_id: str, node_data: dict[str, Any], errors: list[str]) -> None:
    """Catch syntax errors in Dify code nodes before import/runtime."""
    if node_data.get("type") != "code":
        return

    code = node_data.get("code")
    if not isinstance(code, str):
        errors.append(f"node {node_id} code node must include code string")
        return

    title = node_data.get("title") or node_id
    code_language = node_data.get("code_language")
    if code_language in (None, "", "python", "python3"):
        try:
            tree = ast.parse(code)
        except SyntaxError as exc:
            errors.append(
                f"node {node_id} ({title}) Python code SyntaxError at line {exc.lineno}: {exc.msg}"
            )
        else:
            has_main = any(
                isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
                and item.name == "main"
                for item in tree.body
            )
            if not has_main:
                errors.append(f"node {node_id} ({title}) code node missing main entrypoint")
    elif code_language in ("javascript", "js"):
        if not re.search(r"\b(?:async\s+)?function\s+main\s*\(", code):
            errors.append(f"node {node_id} ({title}) code node missing main entrypoint")
        node_bin = shutil.which("node")
        if node_bin:
            try:
                result = subprocess.run(
                    [node_bin, "--check"],
                    input=code,
                    text=True,
                    capture_output=True,
                    timeout=5,
                    check=False,
                )
            except Exception as exc:
                errors.append(f"node {node_id} ({title}) JavaScript code check failed: {exc}")
            else:
                if result.returncode != 0:
                    first_error = next(
                        (line.strip() for line in result.stderr.splitlines() if line.strip()),
                        "syntax check failed",
                    )
                    errors.append(
                        f"node {node_id} ({title}) JavaScript code SyntaxError: {first_error}"
                    )

    outputs = node_data.get("outputs")
    if outputs is not None and not isinstance(outputs, dict):
        errors.append(f"node {node_id} code outputs must be a mapping")
    elif isinstance(outputs, dict):
        for output_name, output_spec in outputs.items():
            if not isinstance(output_spec, dict) or not output_spec.get("type"):
                errors.append(f"node {node_id} code output {output_name!r} must include a type")
                continue
            output_type = output_spec.get("type")
            if output_type not in VALID_CODE_OUTPUT_TYPES:
                errors.append(
                    f"node {node_id} code output {output_name!r} type {output_type!r} is not "
                    "accepted by AI Hub CodeNodeData outputs; use one of "
                    f"{sorted(VALID_CODE_OUTPUT_TYPES)}"
                )


def validate_start_node(node_id: str, node_data: dict[str, Any], errors: list[str]) -> None:
    if node_data.get("type") != "start":
        return
    variables = node_data.get("variables")
    if variables is None:
        return
    if not isinstance(variables, list):
        errors.append(f"node {node_id} start variables must be a list")
        return
    for index, variable in enumerate(variables):
        if not isinstance(variable, dict):
            errors.append(f"node {node_id} start variable {index} must be a mapping")
            continue
        for key in ("label", "required", "type", "variable"):
            if key not in variable:
                errors.append(f"node {node_id} start variable {index} missing {key}")
        options = variable.get("options")
        if options is not None:
            if not isinstance(options, list):
                errors.append(f"node {node_id} start variable {index} options must be a list")
            else:
                for option_index, option in enumerate(options):
                    if not isinstance(option, str):
                        errors.append(
                            f"node {node_id} start variable {index} option {option_index} "
                            f"must be a string; quote colon ratios such as '16:9' in YAML"
                        )


def validate_end_node(node_id: str, node_data: dict[str, Any], errors: list[str], warnings: list[str]) -> None:
    if node_data.get("type") != "end":
        return
    outputs = node_data.get("outputs")
    if not isinstance(outputs, list):
        errors.append(f"node {node_id} end node must include outputs list")
        return
    if not outputs:
        warnings.append(
            f"node {node_id} end node has empty outputs list; this is observed for early-stop/failure branches"
        )
        return
    for index, output in enumerate(outputs):
        if not isinstance(output, dict):
            errors.append(f"node {node_id} end output {index} must be a mapping")
            continue
        for key in ("value_selector", "value_type", "variable"):
            if key not in output:
                errors.append(f"node {node_id} end output {index} missing {key}")


def validate_agent_node(node_id: str, node_data: dict[str, Any], errors: list[str]) -> None:
    if node_data.get("type") != "agent":
        return
    title = node_data.get("title") or node_id

    for field_name, expected_value in DEFAULT_GENERATED_AGENT_STRATEGY.items():
        actual_value = node_data.get(field_name)
        if actual_value != expected_value:
            actual_label = "missing" if actual_value is None else repr(actual_value)
            errors.append(
                f"node {node_id} ({title}) agent strategy {field_name} is {actual_label}; "
                f"generated AI Hub DSL must default to FunctionCalling with "
                f"{field_name}: {expected_value!r}. Do not default to ReAct unless "
                "the user explicitly asks for it or an existing runnable DSL proves it is required."
            )

    def walk(value: Any, path: str) -> None:
        if isinstance(value, dict):
            if value.get("type") == "variable":
                variable_value = value.get("value")
                if variable_value is None or str(variable_value).strip() == "":
                    errors.append(
                        f"node {node_id} ({title}) agent parameter {path} has empty variable value"
                    )
            for key, child in value.items():
                walk(child, f"{path}.{key}" if path else str(key))
        elif isinstance(value, list):
            for index, child in enumerate(value):
                walk(child, f"{path}[{index}]")

    agent_parameters = node_data.get("agent_parameters")
    if isinstance(agent_parameters, dict):
        walk(agent_parameters, "agent_parameters")


def llm_has_structured_output_metadata(node_data: dict[str, Any]) -> bool:
    structured_output = node_data.get("structured_output")
    return (
        node_data.get("structured_output_enabled") is True
        and isinstance(structured_output, dict)
        and isinstance(structured_output.get("schema"), dict)
    )


def validate_llm_structured_output_shape(
    node_id: str, node_data: dict[str, Any], errors: list[str]
) -> None:
    if node_data.get("type") != "llm" or node_data.get("structured_output_enabled") is not True:
        return
    structured_output = node_data.get("structured_output")
    title = node_data.get("title") or node_id
    if not isinstance(structured_output, dict):
        errors.append(f"node {node_id} ({title}) structured_output must be a mapping")
        return
    if not isinstance(structured_output.get("schema"), dict):
        errors.append(
            f"node {node_id} ({title}) structured_output.schema must contain the JSON Schema; "
            "the target Dify UI does not expose structured_output fields when the schema is "
            "stored directly under structured_output"
        )


def declared_node_outputs(node_data: dict[str, Any]) -> set[str] | None:
    node_type = node_data.get("type")
    if node_type == "start":
        variables = node_data.get("variables")
        if not isinstance(variables, list):
            return set()
        return {
            str(variable.get("variable"))
            for variable in variables
            if isinstance(variable, dict) and variable.get("variable")
        }
    if node_type == "code":
        outputs = node_data.get("outputs")
        return set(outputs.keys()) if isinstance(outputs, dict) else set()
    if node_type == "llm":
        outputs = {"text", "usage"}
        if llm_has_structured_output_metadata(node_data):
            outputs.add("structured_output")
        return outputs
    if node_type == "iteration":
        return {"item", "output"}
    if node_type == "tool":
        outputs = node_data.get("outputs")
        if not isinstance(outputs, list):
            return set()
        return {
            str(output.get("variable"))
            for output in outputs
            if isinstance(output, dict) and output.get("variable")
        }
    if isinstance(node_type, str) and node_type in DIRECT_NODE_OUTPUTS:
        return set(DIRECT_NODE_OUTPUTS[node_type])
    if isinstance(node_data.get("outputs"), dict):
        return set(node_data["outputs"].keys())
    return None


def collect_selector_references(value: Any, path: str = "$") -> list[tuple[str, list[str]]]:
    found: list[tuple[str, list[str]]] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else str(key)
            if key in SELECTOR_KEYS and isinstance(child, list) and len(child) >= 2:
                found.append((child_path, [str(part) for part in child]))
            if key == "value" and value.get("type") == "variable" and isinstance(child, list) and len(child) >= 2:
                found.append((child_path, [str(part) for part in child]))
            if isinstance(child, str):
                for match in VARIABLE_INTERPOLATION_PATTERN.finditer(child):
                    selector = [part for part in match.group(1).split(".") if part]
                    if len(selector) >= 2:
                        found.append((f"{child_path}:{match.group(0)}", selector))
            found.extend(collect_selector_references(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(collect_selector_references(child, f"{path}[{index}]"))
    return found


def validate_variable_references(nodes: list[Any], errors: list[str]) -> None:
    node_data_by_id: dict[str, dict[str, Any]] = {}
    output_catalog: dict[str, set[str] | None] = {}
    for node_any in nodes:
        if not isinstance(node_any, dict):
            continue
        node_id = node_any.get("id")
        node_data = node_any.get("data")
        if not isinstance(node_id, str) or not isinstance(node_data, dict):
            continue
        node_data_by_id[node_id] = node_data
        output_catalog[node_id] = declared_node_outputs(node_data)

    for node_any in nodes:
        if not isinstance(node_any, dict):
            continue
        node_id = node_any.get("id") or "<unknown>"
        node_data = node_any.get("data")
        if not isinstance(node_data, dict):
            continue
        reference_data = node_data
        if node_data.get("type") == "tool":
            reference_data = {
                key: value
                for key, value in node_data.items()
                if key != "outputs"
            }
        for path, selector in collect_selector_references(reference_data, f"node {node_id}.data"):
            source_id, variable_name = selector[0], selector[1]
            if source_id in PSEUDO_SELECTOR_SOURCES:
                continue
            source_data = node_data_by_id.get(source_id)
            if source_data is None:
                errors.append(f"{path} references missing variable source node {source_id!r}")
                continue
            if (
                source_data.get("type") == "llm"
                and variable_name == "structured_output"
                and not llm_has_structured_output_metadata(source_data)
            ):
                errors.append(
                    f"{path} references {source_id}.structured_output but source LLM lacks "
                    "structured_output_enabled: true and structured_output metadata; Dify UI will mark it invalid"
                )
                continue
            if (
                source_data.get("type") == "llm"
                and variable_name == "structured_output"
                and len(selector) > 2
            ):
                schema = (source_data.get("structured_output") or {}).get("schema")
                selected_schema = schema_at_selector_path(schema, [str(part) for part in selector[2:]])
                if selected_schema is None:
                    field_path = ".".join(str(part) for part in selector[2:])
                    errors.append(
                        f"{path} references missing structured_output field "
                        f"{source_id}.{field_path}"
                    )
                    continue
            if (
                node_data.get("type") == "code"
                and source_data.get("type") == "llm"
                and variable_name == "structured_output"
                and len(selector) == 2
            ):
                errors.append(
                    f"{path} selects whole LLM structured_output from {source_id}; "
                    "Dify UI can mark Code node inputs invalid, so select individual "
                    "structured_output fields instead"
                )
                continue
            available = output_catalog.get(source_id)
            if available is not None and variable_name not in available:
                errors.append(
                    f"{path} references unavailable variable {source_id}.{variable_name}; "
                    f"available outputs are {sorted(available)}"
                )


def numeric_position(value: Any) -> tuple[float, float] | None:
    if not isinstance(value, dict):
        return None
    x = value.get("x")
    y = value.get("y")
    if isinstance(x, (int, float)) and isinstance(y, (int, float)):
        return float(x), float(y)
    return None


def validate_parent_child_positions(nodes: list[Any], errors: list[str]) -> None:
    node_by_id = {
        node.get("id"): node
        for node in nodes
        if isinstance(node, dict) and isinstance(node.get("id"), str)
    }
    for node in nodes:
        if not isinstance(node, dict):
            continue
        node_id = node.get("id")
        parent_id = node.get("parentId")
        if not isinstance(node_id, str) or not isinstance(parent_id, str):
            continue
        parent = node_by_id.get(parent_id)
        if not isinstance(parent, dict):
            errors.append(f"node {node_id} parentId references missing node {parent_id!r}")
            continue
        parent_abs = numeric_position(parent.get("positionAbsolute")) or numeric_position(parent.get("position"))
        child_pos = numeric_position(node.get("position"))
        child_abs = numeric_position(node.get("positionAbsolute"))
        if parent_abs is None or child_pos is None or child_abs is None:
            continue
        expected = (parent_abs[0] + child_pos[0], parent_abs[1] + child_pos[1])
        if abs(child_abs[0] - expected[0]) > 1 or abs(child_abs[1] - expected[1]) > 1:
            errors.append(
                f"node {node_id} positionAbsolute {child_abs} does not match parent {parent_id} "
                f"positionAbsolute + position {expected}; Dify iteration canvas edges can render disconnected"
            )


def validate_iteration_graph_contract(nodes: list[Any], edges: list[Any], errors: list[str]) -> None:
    node_by_id = {
        node.get("id"): node
        for node in nodes
        if isinstance(node, dict) and isinstance(node.get("id"), str)
    }
    type_by_id = {
        node_id: node.get("data", {}).get("type")
        for node_id, node in node_by_id.items()
        if isinstance(node.get("data"), dict)
    }
    children_by_parent: dict[str, set[str]] = {}
    for node_id, node in node_by_id.items():
        parent_id = node.get("parentId")
        if isinstance(parent_id, str):
            children_by_parent.setdefault(parent_id, set()).add(str(node_id))

    for node_id, node in node_by_id.items():
        node_data = node.get("data")
        if not isinstance(node_data, dict) or node_data.get("type") != "iteration":
            continue
        start_node_id = node_data.get("start_node_id")
        children = children_by_parent.get(str(node_id), set())
        if not isinstance(start_node_id, str) or not start_node_id:
            errors.append(f"iteration {node_id} must set start_node_id")
            continue
        if start_node_id not in children:
            errors.append(f"iteration {node_id} start_node_id {start_node_id!r} is not a child node")
            continue
        start_data = node_by_id[start_node_id].get("data", {})
        if not isinstance(start_data, dict) or start_data.get("type") != "iteration-start":
            errors.append(f"iteration {node_id} start_node_id {start_node_id!r} must point to an iteration-start node")
        for child_id in sorted(children):
            child_data = node_by_id[child_id].get("data", {})
            if not isinstance(child_data, dict):
                continue
            if child_data.get("type") == "custom-note":
                continue
            if child_data.get("isInIteration") is not True or child_data.get("iteration_id") != node_id:
                errors.append(
                    f"iteration child node {child_id} must set data.isInIteration: true "
                    f"and data.iteration_id: {node_id!r}"
                )

        adjacency: dict[str, set[str]] = {child_id: set() for child_id in children}
        for index, edge_any in enumerate(edges):
            if not isinstance(edge_any, dict):
                continue
            source = edge_any.get("source")
            target = edge_any.get("target")
            if source not in children and target not in children:
                continue
            edge_data = edge_any.get("data")
            if source in children and target in children:
                if not isinstance(edge_data, dict) or edge_data.get("isInIteration") is not True:
                    errors.append(f"edges[{index}] inside iteration {node_id} must set data.isInIteration: true")
                elif edge_data.get("iteration_id") != node_id:
                    errors.append(f"edges[{index}] inside iteration {node_id} must set data.iteration_id: {node_id!r}")
                adjacency.setdefault(str(source), set()).add(str(target))

        if not adjacency.get(start_node_id):
            errors.append(f"iteration {node_id} has no outgoing edge from start_node_id {start_node_id!r}")

        reachable: set[str] = set()
        stack = [start_node_id]
        while stack:
            current = stack.pop()
            if current in reachable:
                continue
            reachable.add(current)
            stack.extend(sorted(adjacency.get(current, set()) - reachable))
        for child_id in sorted(children - reachable):
            if child_id != start_node_id and type_by_id.get(child_id) != "custom-note":
                errors.append(f"iteration {node_id} child node {child_id} is not reachable from start_node_id")

        output_selector = node_data.get("output_selector")
        if isinstance(output_selector, list) and output_selector:
            output_node_id = str(output_selector[0])
            if output_node_id not in children:
                errors.append(f"iteration {node_id} output_selector source {output_node_id!r} is not a child node")
            elif output_node_id not in reachable:
                errors.append(f"iteration {node_id} output_selector source {output_node_id!r} is not reachable")


def schema_to_dify_type(schema: Any) -> str | None:
    if not isinstance(schema, dict):
        return None
    schema_type = schema.get("type")
    if schema_type == "array":
        item_type = schema_to_dify_type(schema.get("items")) or "object"
        return f"array[{item_type}]"
    if schema_type in {"object", "string", "number", "file"}:
        return str(schema_type)
    return None


def schema_at_selector_path(schema: Any, path: list[str]) -> Any:
    current = schema
    for part in path:
        if not isinstance(current, dict):
            return None
        if current.get("type") == "array":
            current = current.get("items")
        properties = current.get("properties")
        if not isinstance(properties, dict) or part not in properties:
            return None
        current = properties[part]
    return current


def infer_selector_type(nodes: list[Any], selector: Any) -> str | None:
    if not isinstance(selector, list) or len(selector) < 2:
        return None
    source_id = str(selector[0])
    variable_name = str(selector[1])
    node_by_id = {
        node.get("id"): node
        for node in nodes
        if isinstance(node, dict) and isinstance(node.get("id"), str)
    }
    source = node_by_id.get(source_id)
    if not isinstance(source, dict):
        return None
    source_data = source.get("data")
    if not isinstance(source_data, dict):
        return None

    source_type = source_data.get("type")
    if source_type == "llm" and variable_name == "structured_output":
        schema = (source_data.get("structured_output") or {}).get("schema")
        if len(selector) == 2:
            return "object"
        selected_schema = schema_at_selector_path(schema, [str(part) for part in selector[2:]])
        return schema_to_dify_type(selected_schema)

    if source_type == "code":
        outputs = source_data.get("outputs")
        if isinstance(outputs, dict):
            output_spec = outputs.get(variable_name)
            if isinstance(output_spec, dict) and isinstance(output_spec.get("type"), str):
                return str(output_spec["type"])

    if source_type == "iteration":
        if variable_name == "output":
            output_type = source_data.get("output_type")
            return str(output_type) if isinstance(output_type, str) and output_type else None
        if variable_name == "item":
            iterator_type = source_data.get("iterator_input_type")
            if not isinstance(iterator_type, str) or not iterator_type:
                return None
            match = re.fullmatch(r"array\[(.+)\]", iterator_type)
            return match.group(1) if match else iterator_type

    if source_type == "start":
        variables = source_data.get("variables")
        if isinstance(variables, list):
            for variable in variables:
                if isinstance(variable, dict) and variable.get("variable") == variable_name:
                    var_type = variable.get("type")
                    if var_type == "file":
                        return "file"
                    return str(var_type) if isinstance(var_type, str) else None

    return None


def allowed_iteration_input_types(iterator_source_type: str) -> set[str]:
    if iterator_source_type == "array[object]":
        return {"object", "array[object]"}
    if iterator_source_type == "array[string]":
        return {"string", "array[string]"}
    if iterator_source_type == "array[number]":
        return {"number", "array[number]"}
    if iterator_source_type == "array[file]":
        return {"file", "array[file]"}
    return {iterator_source_type}


def validate_iteration_type_contract(nodes: list[Any], errors: list[str]) -> None:
    for node in nodes:
        if not isinstance(node, dict):
            continue
        node_id = node.get("id")
        node_data = node.get("data")
        if not isinstance(node_id, str) or not isinstance(node_data, dict):
            continue
        if node_data.get("type") != "iteration":
            continue
        iterator_selector = node_data.get("iterator_selector")
        iterator_source_type = infer_selector_type(nodes, iterator_selector)
        iterator_input_type = node_data.get("iterator_input_type")
        if not iterator_source_type or not isinstance(iterator_input_type, str):
            continue
        allowed = allowed_iteration_input_types(iterator_source_type)
        if iterator_input_type not in allowed:
            errors.append(
                f"iteration {node_id} iterator_input_type {iterator_input_type!r} is incompatible "
                f"with iterator_selector type {iterator_source_type!r}; use one of {sorted(allowed)}"
            )


def validate_iteration_item_variable_type_contract(nodes: list[Any], errors: list[str]) -> None:
    for node in nodes:
        if not isinstance(node, dict):
            continue
        node_id = node.get("id")
        node_data = node.get("data")
        if not isinstance(node_id, str) or not isinstance(node_data, dict):
            continue
        variables = node_data.get("variables")
        if not isinstance(variables, list):
            continue
        for index, variable in enumerate(variables):
            if not isinstance(variable, dict):
                continue
            selector = variable.get("value_selector")
            if not isinstance(selector, list) or len(selector) < 2 or str(selector[1]) != "item":
                continue
            selector_type = infer_selector_type(nodes, selector)
            value_type = variable.get("value_type")
            if (
                selector_type
                and isinstance(value_type, str)
                and value_type != selector_type
                and not (selector_type == "object" and value_type == "array[object]")
            ):
                errors.append(
                    f"node {node_id} variable {index} selects iteration item with selector type "
                    f"{selector_type!r} but declares value_type {value_type!r}; use {selector_type!r}"
                )


def node_iteration_id(node: dict[str, Any], node_data: dict[str, Any]) -> str | None:
    iteration_id = node_data.get("iteration_id")
    if isinstance(iteration_id, str) and iteration_id.strip():
        return iteration_id.strip()
    parent_id = node.get("parentId")
    if isinstance(parent_id, str) and parent_id.strip():
        return parent_id.strip()
    return None


def node_title_desc_text(node_data: dict[str, Any]) -> str:
    return f"{node_data.get('title', '')} {node_data.get('desc', '')}".lower()


def is_optional_iteration_asset(node_data: dict[str, Any]) -> bool:
    text = node_title_desc_text(node_data)
    return any(marker.lower() in text for marker in OPTIONAL_ITERATION_ASSET_MARKERS)


def validate_aigc_iteration_blocking_nodes(nodes: list[Any], errors: list[str]) -> None:
    video_iteration_ids: set[str] = set()
    has_video_generation = False
    image_nodes: list[tuple[str, str, dict[str, Any], str | None]] = []

    for node in nodes:
        if not isinstance(node, dict):
            continue
        node_id = node.get("id")
        node_data = node.get("data")
        if not isinstance(node_id, str) or not isinstance(node_data, dict):
            continue
        node_type = node_data.get("type")
        current_iteration_id = node_iteration_id(node, node_data)
        if node_type == "video-generation":
            has_video_generation = True
            if current_iteration_id:
                video_iteration_ids.add(current_iteration_id)
        if node_type == "image-generation" and current_iteration_id:
            image_nodes.append((node_id, str(node_data.get("title") or node_id), node_data, current_iteration_id))

    if not has_video_generation:
        return

    for node_id, title, node_data, current_iteration_id in image_nodes:
        if is_optional_iteration_asset(node_data):
            continue
        if video_iteration_ids and current_iteration_id not in video_iteration_ids:
            continue
        errors.append(
            f"node {node_id} ({title}) image-generation is inside iteration {current_iteration_id!r} "
            "and can become a blocking dependency before video-generation. For 45-60 second "
            "multi-shot videos, feed normalized storyboard prompts directly to native "
            "video-generation; move keyframe/three-view image generation to optional or "
            "reference branches unless the user explicitly asks for an image-gated pipeline."
        )


def normalize_model_version(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    normalized = value.strip()
    if normalized in {"", "-"}:
        return ""
    return normalized


def parse_date_prefix(value: Any) -> date | None:
    if not isinstance(value, str):
        return None
    value = value.strip()
    if not value or value.lower() in NO_OFFLINE_DATE_VALUES:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def load_model_catalog(errors: list[str]) -> dict[str, Any]:
    try:
        with MODEL_LIST_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as exc:
        errors.append(f"AIGC quality check cannot load model list {MODEL_LIST_PATH}: {exc}")
        return {}

    models = data.get("models")
    if not isinstance(models, list):
        errors.append(f"AIGC quality check model list {MODEL_LIST_PATH} must contain models list")
        return {}

    ids: set[str] = set()
    dsl_names: set[str] = set()
    id_to_dsl_name: dict[str, str] = {}
    id_to_display_name: dict[str, str] = {}
    id_to_provider: dict[str, str] = {}
    id_to_type: dict[str, str] = {}
    display_to_dsl_name: dict[str, str] = {}
    display_to_id: dict[str, str] = {}
    dsl_name_to_id: dict[str, str] = {}
    display_to_id_by_type: dict[str, dict[str, str]] = {}
    dsl_name_to_id_by_type: dict[str, dict[str, str]] = {}
    id_to_offline_date: dict[str, str] = {}
    id_to_need_apply: dict[str, bool] = {}
    snapshot_date = parse_date_prefix(data.get("fetched_at")) or date.today()

    for model in models:
        if not isinstance(model, dict):
            continue
        model_id = model.get("id")
        if not isinstance(model_id, str) or not model_id.strip():
            continue
        model_id = model_id.strip()
        version = normalize_model_version(model.get("version"))
        dsl_name = version or model_id
        ids.add(model_id)
        dsl_names.add(dsl_name)
        id_to_dsl_name[model_id] = dsl_name
        dsl_name_to_id.setdefault(dsl_name, model_id)
        model_type = model.get("type")
        if isinstance(model_type, str) and model_type.strip():
            model_type = model_type.strip()
            id_to_type[model_id] = model_type
            dsl_name_to_id_by_type.setdefault(model_type, {}).setdefault(dsl_name, model_id)
        provider = model.get("provider")
        if isinstance(provider, str) and provider.strip():
            id_to_provider[model_id] = provider.strip()
        offline_date = model.get("offlineDate")
        if isinstance(offline_date, str):
            id_to_offline_date[model_id] = offline_date.strip()
        is_need_apply = model.get("isNeedApply")
        if isinstance(is_need_apply, bool):
            id_to_need_apply[model_id] = is_need_apply
        display_name = model.get("name")
        if isinstance(display_name, str) and display_name.strip():
            display_name = display_name.strip()
            id_to_display_name[model_id] = display_name
            display_to_dsl_name.setdefault(display_name, dsl_name)
            display_to_id.setdefault(display_name, model_id)
            if isinstance(model_type, str) and model_type:
                display_to_id_by_type.setdefault(model_type, {}).setdefault(display_name, model_id)

    return {
        "ids": ids,
        "dsl_names": dsl_names,
        "id_to_dsl_name": id_to_dsl_name,
        "id_to_display_name": id_to_display_name,
        "id_to_provider": id_to_provider,
        "id_to_type": id_to_type,
        "display_to_dsl_name": display_to_dsl_name,
        "display_to_id": display_to_id,
        "dsl_name_to_id": dsl_name_to_id,
        "display_to_id_by_type": display_to_id_by_type,
        "dsl_name_to_id_by_type": dsl_name_to_id_by_type,
        "id_to_offline_date": id_to_offline_date,
        "id_to_need_apply": id_to_need_apply,
        "snapshot_date": snapshot_date,
    }


def _as_string_set(value: Any) -> set[str]:
    if isinstance(value, set):
        return {str(item) for item in value}
    if isinstance(value, (list, tuple)):
        return {str(item) for item in value}
    return set()


def load_observed_tool_shapes(errors: list[str]) -> dict[str, dict[str, Any]]:
    shapes: dict[str, dict[str, Any]] = {}
    for tool_name, expected in OBSERVED_AIGC_TOOL_SHAPES.items():
        params = _as_string_set(expected.get("params"))
        shapes[tool_name] = {
            "provider_id": expected.get("provider_id"),
            "provider_type": expected.get("provider_type", "workflow"),
            "tool_node_version": expected.get("tool_node_version"),
            "required_params": params,
            "required_tool_parameters": _as_string_set(
                expected.get("tool_parameters", params)
            ),
            "output_variables": _as_string_set(expected.get("outputs")),
        }

    try:
        with TOOL_FINGERPRINTS_PATH.open("r", encoding="utf-8") as f:
            catalog = json.load(f)
    except Exception as exc:
        errors.append(
            f"AIGC quality check cannot load tool fingerprints {TOOL_FINGERPRINTS_PATH}: {exc}"
        )
        return shapes

    tools = catalog.get("tools")
    if not isinstance(tools, dict):
        errors.append(f"AIGC tool fingerprint catalog {TOOL_FINGERPRINTS_PATH} must contain tools mapping")
        return shapes

    for tool_name, item in tools.items():
        if not isinstance(tool_name, str) or not isinstance(item, dict):
            continue
        provider_id = item.get("provider_id")
        provider_type = item.get("provider_type") or "workflow"
        shapes[tool_name] = {
            "provider_id": provider_id if isinstance(provider_id, str) else None,
            "provider_type": provider_type if isinstance(provider_type, str) else "workflow",
            "tool_node_version": str(item["tool_node_version"])
            if item.get("tool_node_version") is not None
            else None,
            "required_params": _as_string_set(item.get("required_params")),
            "required_tool_parameters": _as_string_set(item.get("required_tool_parameters")),
            "output_variables": _as_string_set(item.get("output_variables")),
        }

    return shapes


def load_observed_component_shapes(errors: list[str]) -> dict[str, dict[str, Any]]:
    try:
        with COMPONENT_FINGERPRINTS_PATH.open("r", encoding="utf-8") as f:
            catalog = json.load(f)
    except Exception as exc:
        errors.append(
            f"AIGC quality check cannot load component fingerprints "
            f"{COMPONENT_FINGERPRINTS_PATH}: {exc}"
        )
        return {}

    components = catalog.get("components")
    if not isinstance(components, dict):
        errors.append(
            f"AIGC component fingerprint catalog {COMPONENT_FINGERPRINTS_PATH} "
            "must contain components mapping"
        )
        return {}

    shapes: dict[str, dict[str, Any]] = {}
    for node_type, component in components.items():
        if not isinstance(node_type, str) or not isinstance(component, dict):
            continue
        model_shapes: dict[str, dict[str, Any]] = {}
        alias_to_model_id: dict[str, str] = {}
        raw_model_shapes = component.get("model_param_shapes")
        if isinstance(raw_model_shapes, dict):
            for model_id, model_shape in raw_model_shapes.items():
                if not isinstance(model_id, str) or not isinstance(model_shape, dict):
                    continue
                variants: list[set[str]] = []
                raw_variants = model_shape.get("accepted_param_variants")
                if isinstance(raw_variants, list):
                    for variant in raw_variants:
                        if isinstance(variant, dict):
                            params = _as_string_set(variant.get("required_params"))
                            if params:
                                variants.append(params)
                if not variants:
                    fallback_params = _as_string_set(model_shape.get("required_params"))
                    if fallback_params:
                        variants.append(fallback_params)
                model_shapes[model_id] = {
                    "required_params": _as_string_set(model_shape.get("required_params")),
                    "accepted_param_variants": variants,
                    "param_contracts": normalize_param_contracts(
                        model_shape.get("param_contracts")
                    ),
                    "model_names": _as_string_set(model_shape.get("model_names")),
                    "providers": _as_string_set(model_shape.get("providers")),
                    "observed_model_ids": _as_string_set(model_shape.get("observed_model_ids")),
                    "permission_status": str(model_shape.get("permission_status", "") or ""),
                    "replacement_selector": model_shape.get("replacement_selector"),
                    "replacement_model_name": model_shape.get("replacement_model_name"),
                }
                for alias in _as_string_set(model_shape.get("observed_model_ids")):
                    if alias and alias != model_id:
                        alias_to_model_id.setdefault(alias, model_id)
                for alias in _as_string_set(model_shape.get("model_names")):
                    if alias and alias != model_id:
                        alias_to_model_id.setdefault(alias, model_id)

        shapes[node_type] = {
            "minimum_required_params": _as_string_set(
                component.get("minimum_required_params")
            ),
            "model_param_shapes": model_shapes,
            "alias_to_model_id": alias_to_model_id,
        }

    return shapes


def normalize_param_contracts(raw_contracts: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(raw_contracts, dict):
        return {}
    contracts: dict[str, dict[str, Any]] = {}
    for param_name, raw_contract in raw_contracts.items():
        if not isinstance(param_name, str) or not isinstance(raw_contract, dict):
            continue
        contract: dict[str, Any] = {}
        binding_type = raw_contract.get("binding_type")
        if isinstance(binding_type, str) and binding_type.strip():
            contract["binding_type"] = binding_type.strip()
        value_type = raw_contract.get("value_type")
        if isinstance(value_type, str) and value_type.strip():
            contract["value_type"] = value_type.strip()
        allowed_values = raw_contract.get("allowed_values")
        if isinstance(allowed_values, list):
            contract["allowed_values"] = allowed_values
        normalizer = raw_contract.get("normalizer")
        if isinstance(normalizer, str) and normalizer.strip():
            contract["normalizer"] = normalizer.strip()
        if contract:
            contracts[param_name] = contract
    return contracts


def permission_status_blocks_direct_generation(permission_status: object) -> bool:
    return (
        isinstance(permission_status, str)
        and (
            permission_status.startswith("locked")
            or "metadata_failed" in permission_status
            or "metadata_load_failed" in permission_status
            or "target_import" in permission_status
        )
    )


def validate_model_identifier(
    value: str,
    label: str,
    errors: list[str],
    model_catalog: dict[str, Any],
) -> None:
    if value in RETIRED_MODEL_REPLACEMENTS:
        errors.append(
            f"{label} uses retired sample model id {value!r}; "
            f"use {RETIRED_MODEL_REPLACEMENTS[value]}"
        )
        return

    if not model_catalog:
        return

    ids: set[str] = model_catalog.get("ids", set())
    dsl_names: set[str] = model_catalog.get("dsl_names", set())
    id_to_dsl_name: dict[str, str] = model_catalog.get("id_to_dsl_name", {})
    id_to_display_name: dict[str, str] = model_catalog.get("id_to_display_name", {})
    display_to_dsl_name: dict[str, str] = model_catalog.get("display_to_dsl_name", {})

    if value in ids:
        append_model_availability_errors(value, value, label, errors, model_catalog)
        dsl_name = id_to_dsl_name.get(value, value)
        if dsl_name != value:
            display_name = id_to_display_name.get(value, value)
            errors.append(
                f"{label} uses AI Hub catalog id {value!r}; "
                f"use the string after 模型版本, {dsl_name!r}, from the model detail card for {display_name!r}"
            )
        return

    if value in dsl_names:
        model_id = model_catalog.get("dsl_name_to_id", {}).get(value)
        if isinstance(model_id, str):
            append_model_availability_errors(model_id, value, label, errors, model_catalog)
        return

    if value in display_to_dsl_name:
        model_id = model_catalog.get("display_to_id", {}).get(value)
        if isinstance(model_id, str):
            append_model_availability_errors(model_id, value, label, errors, model_catalog)
        dsl_name = display_to_dsl_name[value]
        errors.append(
            f"{label} uses AI Hub display name {value!r}; "
            f"use the string after 模型版本, {dsl_name!r}, from the model detail card"
        )
        return

    errors.append(
        f"{label} {value!r} is not a current AI Hub model version; "
        "open the model card and use the string after 模型版本, or the catalog id only when version is '-' or blank"
    )


def append_model_availability_errors(
    model_id: str,
    value: str,
    label: str,
    errors: list[str],
    model_catalog: dict[str, Any],
) -> None:
    id_to_offline_date: dict[str, str] = model_catalog.get("id_to_offline_date", {})
    offline_raw = id_to_offline_date.get(model_id, "")
    offline_date = parse_date_prefix(offline_raw)
    snapshot_date = model_catalog.get("snapshot_date")
    if not isinstance(snapshot_date, date):
        snapshot_date = date.today()
    if offline_date and offline_date <= snapshot_date:
        errors.append(
            f"{label} uses offline AI Hub model {value!r}; model-list offlineDate is "
            f"{offline_raw!r}. Use a current quality-first model such as "
            "'gpt-5.5-2026-04-24' or refresh the AI Hub model list before delivery."
        )

    id_to_need_apply: dict[str, bool] = model_catalog.get("id_to_need_apply", {})
    if id_to_need_apply.get(model_id) is True:
        errors.append(
            f"{label} uses AI Hub model {value!r} that requires AI Hub permission. "
            "Use a no-application quality-first model such as 'gpt-5.5-2026-04-24' "
            "unless the user explicitly confirms the target workspace already has permission."
        )


def model_catalog_haystack(value: str, model_catalog: dict[str, Any]) -> str:
    if not model_catalog:
        return value.lower()

    id_to_dsl_name: dict[str, str] = model_catalog.get("id_to_dsl_name", {})
    id_to_display_name: dict[str, str] = model_catalog.get("id_to_display_name", {})
    dsl_name_to_id: dict[str, str] = model_catalog.get("dsl_name_to_id", {})
    display_to_id: dict[str, str] = model_catalog.get("display_to_id", {})

    model_id = ""
    if value in id_to_dsl_name:
        model_id = value
    elif value in dsl_name_to_id:
        model_id = dsl_name_to_id[value]
    elif value in display_to_id:
        model_id = display_to_id[value]

    if not model_id:
        return value.lower()

    return " ".join(
        part
        for part in [
            value,
            model_id,
            id_to_dsl_name.get(model_id, ""),
            id_to_display_name.get(model_id, ""),
        ]
        if part
    ).lower()


def is_economy_llm_model(value: str, model_catalog: dict[str, Any]) -> bool:
    normalized = value.strip()
    if normalized in QUALITY_FIRST_LLM_MODELS:
        return False
    haystack = model_catalog_haystack(normalized, model_catalog)
    return any(marker in haystack for marker in ECONOMY_LLM_MARKERS)


def validate_aigc_component_model_info(
    model_info: dict[str, Any],
    node_type: str,
    label: str,
    errors: list[str],
    model_catalog: dict[str, Any],
    observed_component_shapes: dict[str, dict[str, Any]],
) -> str:
    model_id = model_info.get("model_id")
    if not isinstance(model_id, str) or not model_id.strip():
        errors.append(f"{label} must include model_info.model_id")
        return ""

    value = model_id.strip()
    component_shape = observed_component_shapes.get(node_type, {})
    model_shapes = component_shape.get("model_param_shapes", {})
    alias_to_model_id = component_shape.get("alias_to_model_id", {})
    if not isinstance(model_shapes, dict):
        model_shapes = {}
    if not isinstance(alias_to_model_id, dict):
        alias_to_model_id = {}

    if value in RETIRED_MODEL_REPLACEMENTS:
        errors.append(
            f"{label} uses stale or retired selector id {value!r}; "
            f"use {RETIRED_MODEL_REPLACEMENTS[value]!r} from the saved AI Hub canvas export"
        )
        return value

    if value in model_shapes:
        expected_shape = model_shapes.get(value)
        if isinstance(expected_shape, dict):
            permission_status = expected_shape.get("permission_status")
            permission_blocks_production = permission_status_blocks_direct_generation(permission_status)
            if permission_blocks_production:
                replacement_selector = expected_shape.get("replacement_selector")
                replacement_model_name = expected_shape.get("replacement_model_name")
                replacement_text = ""
                if isinstance(replacement_selector, str) and replacement_selector:
                    replacement_text = f"; use {replacement_selector!r}"
                    if isinstance(replacement_model_name, str) and replacement_model_name:
                        replacement_text += f" ({replacement_model_name})"
                errors.append(
                    f"{label} selector id {value!r} is not production-safe for direct DSL "
                    f"generation in the current AI Hub workspace ({permission_status})"
                    f"{replacement_text}. Refresh the component fingerprint from a saved "
                    "canvas export that re-imports and opens cleanly before delivery."
                )
            expected_names = expected_shape.get("model_names", set())
            actual_name = model_info.get("model_name")
            if (
                isinstance(expected_names, set)
                and expected_names
                and isinstance(actual_name, str)
                and actual_name.strip()
                and actual_name.strip() not in expected_names
            ):
                errors.append(
                    f"{label} model_info.model_name {actual_name!r} does not match observed "
                    f"AI Hub component name for selector id {value!r}: {sorted(expected_names)}"
                )
            expected_providers = expected_shape.get("providers", set())
            actual_provider = model_info.get("provider")
            if (
                isinstance(expected_providers, set)
                and expected_providers
                and isinstance(actual_provider, str)
                and actual_provider.strip()
                and actual_provider.strip() not in expected_providers
            ):
                errors.append(
                    f"{label} model_info.provider {actual_provider!r} does not match observed "
                    f"AI Hub component provider for selector id {value!r}: {sorted(expected_providers)}"
                )
        return value

    if value in alias_to_model_id:
        expected_id = alias_to_model_id[value]
        expected_shape = model_shapes.get(expected_id)
        if isinstance(expected_shape, dict):
            permission_status = expected_shape.get("permission_status")
            if permission_status_blocks_direct_generation(permission_status):
                errors.append(
                    f"{label} uses model-list catalog id, model version, or display value {value!r}; "
                    f"it maps to canvas component selector id {expected_id!r}, but that selector is "
                    f"not production-safe for direct DSL generation in the current AI Hub workspace "
                    f"({permission_status}). Refresh the component fingerprint from a saved canvas "
                    "export that re-imports and opens cleanly before delivery."
                )
                return value
        errors.append(
            f"{label} uses model-list catalog id, model version, or display value {value!r}; "
            f"direct AIGC component model_info.model_id must use the canvas component selector id "
            f"{expected_id!r} from the AI Hub node dropdown or runnable DSL fingerprint"
        )
        return value

    if not model_catalog:
        return value

    ids: set[str] = model_catalog.get("ids", set())
    dsl_names: set[str] = model_catalog.get("dsl_names", set())
    dsl_name_to_id: dict[str, str] = model_catalog.get("dsl_name_to_id", {})
    display_to_id: dict[str, str] = model_catalog.get("display_to_id", {})
    id_to_display_name: dict[str, str] = model_catalog.get("id_to_display_name", {})
    id_to_provider: dict[str, str] = model_catalog.get("id_to_provider", {})
    id_to_type: dict[str, str] = model_catalog.get("id_to_type", {})
    dsl_name_to_id_by_type: dict[str, dict[str, str]] = model_catalog.get("dsl_name_to_id_by_type", {})
    display_to_id_by_type: dict[str, dict[str, str]] = model_catalog.get("display_to_id_by_type", {})

    if value in ids:
        expected_id = alias_to_model_id.get(value)
        if expected_id:
            errors.append(
                f"{label} uses model-list catalog id {value!r}; direct AIGC component "
                f"model_info.model_id must use canvas component selector id {expected_id!r}"
            )
            return value
        expected_type = id_to_type.get(value)
        compatible_types = AIGC_NODE_COMPATIBLE_MODEL_TYPES.get(node_type, {node_type})
        if expected_type and expected_type not in compatible_types:
            errors.append(
                f"{label} model_info.model_id {value!r} is a current AI Hub {expected_type!r} model, "
                f"but this node is {node_type!r}; choose a current {node_type!r} selector id"
            )
            return value
        errors.append(
            f"{label} uses AI Hub model-list catalog id {value!r}, but this direct component "
            "has no observed canvas component fingerprint for that id; open the node's model "
            "selector in AI Hub and use the exact model_info.model_id from an export before delivery"
        )
        return value

    if value in dsl_names:
        catalog_id = dsl_name_to_id_by_type.get(node_type, {}).get(value) or dsl_name_to_id.get(value)
        expected_id = alias_to_model_id.get(value) or alias_to_model_id.get(catalog_id or "")
        errors.append(
            f"{label} uses AI Hub model version {value!r}; direct AIGC component "
            f"model_info.model_id must use the canvas component selector id {expected_id or catalog_id!r}"
        )
        return value

    if value in display_to_id:
        catalog_id = display_to_id_by_type.get(node_type, {}).get(value) or display_to_id[value]
        expected_id = alias_to_model_id.get(value) or alias_to_model_id.get(catalog_id)
        errors.append(
            f"{label} uses AI Hub display name {value!r}; direct AIGC component "
            f"model_info.model_id must use the canvas component selector id {expected_id or catalog_id!r}"
        )
        return value

    errors.append(
        f"{label} model_info.model_id {value!r} is not an observed AI Hub AIGC component selector id; "
        "use the exact id from the node dropdown/exported DSL fingerprint, not the public model-list display name"
    )
    return value


def allowed_param_binding_types(binding_type: str) -> set[str]:
    if binding_type == "constant":
        return {"constant"}
    if binding_type == "variable":
        return {"variable"}
    if binding_type == "constant_or_variable":
        return {"constant", "variable"}
    return set()


def value_matches_type(value: Any, value_type: str) -> bool:
    if value_type == "string":
        return isinstance(value, str)
    if value_type == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if value_type == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if value_type == "boolean":
        return isinstance(value, bool)
    if value_type == "null":
        return value is None
    if value_type == "string_or_integer":
        return isinstance(value, str) or (isinstance(value, int) and not isinstance(value, bool))
    if value_type == "scalar":
        return value is None or isinstance(value, (str, int, float, bool))
    return True


def value_matches_allowed(actual: Any, expected: Any) -> bool:
    if isinstance(expected, (int, float)) and not isinstance(expected, bool):
        return type(actual) is type(expected) and actual == expected
    return type(actual) is type(expected) and actual == expected


def validate_aigc_param_contracts(
    node_id: str,
    title: str,
    node_type: str,
    model_id: str,
    params: dict[str, Any],
    model_shape: dict[str, Any],
    errors: list[str],
) -> None:
    contracts = model_shape.get("param_contracts")
    if not isinstance(contracts, dict) or not contracts:
        return

    for param_name, contract in contracts.items():
        if not isinstance(param_name, str) or not isinstance(contract, dict):
            continue
        if param_name not in params:
            continue

        label = (
            f"node {node_id} ({title}) {node_type} model {model_id!r} "
            f"param {param_name}"
        )
        param_entry = params.get(param_name)
        if not isinstance(param_entry, dict):
            errors.append(f"{label} must be a mapping with type and value/value_selector")
            continue

        entry_type = param_entry.get("type")
        binding_type = contract.get("binding_type")
        if isinstance(binding_type, str):
            allowed_bindings = allowed_param_binding_types(binding_type)
            if allowed_bindings and entry_type not in allowed_bindings:
                normalizer = contract.get("normalizer")
                suffix = f"; normalizer: {normalizer}" if isinstance(normalizer, str) and normalizer else ""
                errors.append(
                    f"{label} binding type {entry_type!r} is invalid; expected "
                    f"{sorted(allowed_bindings)} according to model-level parameter contract"
                    f"{suffix}"
                )

        if entry_type != "constant":
            continue

        value = param_entry.get("value")
        value_type = contract.get("value_type")
        if isinstance(value_type, str) and value_type:
            if not value_matches_type(value, value_type):
                errors.append(
                    f"{label} constant value {value!r} has invalid runtime type; "
                    f"expected {value_type!r}"
                )

        allowed_values = contract.get("allowed_values")
        if isinstance(allowed_values, list) and allowed_values:
            if not any(value_matches_allowed(value, allowed) for allowed in allowed_values):
                normalizer = contract.get("normalizer")
                suffix = f"; normalizer: {normalizer}" if isinstance(normalizer, str) and normalizer else ""
                errors.append(
                    f"{label} constant value {value!r} is not allowed; allowed "
                    f"values are {allowed_values!r}{suffix}"
                )


def variable_param_selector(param_entry: Any) -> list[str] | None:
    if not isinstance(param_entry, dict) or param_entry.get("type") != "variable":
        return None
    for selector_key in ("value_selector", "value"):
        selector = param_entry.get(selector_key)
        if isinstance(selector, list) and len(selector) >= 2:
            return [str(part) for part in selector]
    return None


def validate_media_param_semantic_sources(
    node_id: str,
    title: str,
    node_type: str,
    params: dict[str, Any],
    errors: list[str],
) -> None:
    for param_name, param_entry in params.items():
        if str(param_name) not in MEDIA_CONTENT_PARAM_NAMES:
            continue
        selector = variable_param_selector(param_entry)
        if not selector:
            continue

        selector_text = ".".join(selector).lower()
        last_field = selector[-1].lower()
        matched_markers = sorted(
            marker
            for marker in PROCEDURAL_MEDIA_SOURCE_MARKERS
            if marker in selector_text or marker in last_field
        )
        if not matched_markers:
            continue

        errors.append(
            f"node {node_id} ({title}) {node_type} media param {param_name!r} "
            f"is bound to procedural selector {selector}; matched process fields "
            f"{matched_markers}. Media generation params must bind to dedicated "
            "content fields such as promptLyrics, prompt, style, title, or storyboard_prompt, "
            "not handoff/diagnostics/instruction fields."
        )


def is_placeholder_url(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return True
    lower = value.strip().lower()
    return any(marker.lower() in lower for marker in PLACEHOLDER_URL_MARKERS)


def has_media_generation_language(node_data: dict[str, Any]) -> bool:
    text_parts = [
        str(node_data.get("title", "")),
        str(node_data.get("desc", "")),
        str(node_data.get("url", "")),
    ]
    text = " ".join(text_parts).lower()
    return any(phrase.lower() in text for phrase in GENERIC_AIGC_HTTP_PHRASES) or any(
        keyword.lower() in text for keyword in MEDIA_GENERATION_KEYWORDS
    )


def has_generic_aigc_http_phrase(node_data: dict[str, Any]) -> bool:
    text_parts = [
        str(node_data.get("title", "")),
        str(node_data.get("desc", "")),
        str(node_data.get("url", "")),
    ]
    text = " ".join(text_parts).lower()
    return any(phrase.lower() in text for phrase in GENERIC_AIGC_HTTP_PHRASES)


def is_aigc_surface_node(node_data: dict[str, Any]) -> bool:
    node_type = node_data.get("type")
    if node_type in AIGC_NODE_TYPES:
        return True
    if node_type == "http-request" and has_media_generation_language(node_data):
        return True
    if node_type == "tool":
        tool_name = str(node_data.get("tool_name", ""))
        if tool_name in OBSERVED_AIGC_TOOL_SHAPES:
            return True
        return has_media_generation_language(node_data)
    return False


def graph_has_aigc_surface(nodes: list[Any]) -> bool:
    for node_any in nodes:
        if not isinstance(node_any, dict):
            continue
        node_data = node_any.get("data")
        if isinstance(node_data, dict) and is_aigc_surface_node(node_data):
            return True
    return False


def media_http_contract_issues(node_data: dict[str, Any]) -> list[str]:
    method = str(node_data.get("method", "")).strip().lower()
    issues: list[str] = []

    retry_config = node_data.get("retry_config")
    if not isinstance(retry_config, dict) or not retry_config.get("retry_enabled"):
        issues.append("retry_config")

    if method in {"post", "put", "patch"}:
        headers = node_data.get("headers")
        if not isinstance(headers, str) or not headers.strip():
            issues.append("headers/auth")
        elif "{{#env." not in headers and "authorization" not in headers.lower():
            issues.append("headers/auth")

        body = node_data.get("body")
        if not isinstance(body, dict) or body.get("type") in {None, "", "none"}:
            issues.append("request body")
        elif not body.get("data"):
            issues.append("request body")

    return issues


def is_allowed_aigc_support_http(node_data: dict[str, Any]) -> bool:
    method = str(node_data.get("method", "")).strip().lower()
    title_desc = f"{node_data.get('title', '')} {node_data.get('desc', '')}".lower()
    url = node_data.get("url")
    if not isinstance(url, str) or not url.strip() or is_placeholder_url(url):
        return False

    support_terms = (
        "下载",
        "获取",
        "转存",
        "upload",
        "download",
        "fetch",
        "file",
        "文件",
    )
    generation_terms = (
        "生成任务",
        "生成",
        "prompt",
        "job",
        "task",
        "视频",
        "图像",
        "图片",
        "音频",
        "3d",
        "3D",
    )
    if method == "get" and any(term.lower() in title_desc for term in support_terms):
        return True
    if any(term.lower() in title_desc for term in generation_terms):
        return False
    return not media_http_contract_issues(node_data)


def parse_llm_json_schema(schema_value: Any, label: str, errors: list[str]) -> dict[str, Any] | None:
    if isinstance(schema_value, dict):
        return schema_value
    if isinstance(schema_value, str):
        if not schema_value.strip():
            errors.append(f"{label} json_schema must not be empty")
            return None
        try:
            parsed = json.loads(schema_value)
        except json.JSONDecodeError as exc:
            errors.append(f"{label} json_schema is not valid JSON: {exc.msg}")
            return None
        if not isinstance(parsed, dict):
            errors.append(f"{label} json_schema must decode to an object schema")
            return None
        return parsed
    errors.append(f"{label} json_schema must be a JSON object or JSON string")
    return None


def prompt_template_text_by_role(prompt_template: Any) -> dict[str, str]:
    by_role: dict[str, list[str]] = {}
    if not isinstance(prompt_template, list):
        return {}
    for item in prompt_template:
        if not isinstance(item, dict):
            continue
        role = item.get("role")
        text = item.get("text")
        if isinstance(role, str) and isinstance(text, str):
            by_role.setdefault(role.strip().lower(), []).append(text)
    return {role: "\n".join(parts).strip() for role, parts in by_role.items()}


def collect_prompt_text_for_node(node_data: dict[str, Any]) -> str:
    chunks: list[str] = []
    role_text = prompt_template_text_by_role(node_data.get("prompt_template"))
    if role_text:
        chunks.extend(role_text.values())
    for key in (
        "instruction",
        "agent_strategy",
        "system_prompt",
        "prompt",
        "query",
        "desc",
    ):
        value = node_data.get(key)
        if isinstance(value, str):
            chunks.append(value)
    return "\n".join(chunk for chunk in chunks if chunk).strip()


def validate_production_prompt_quality_node(
    node_id: str,
    node_data: dict[str, Any],
    errors: list[str],
) -> None:
    if node_data.get("type") not in {"llm", "agent"}:
        return
    title = node_data.get("title") or node_id
    label = f"node {node_id} ({title}) prompt quality"
    prompt_text = collect_prompt_text_for_node(node_data)
    if not prompt_text:
        errors.append(f"{label}: missing prompt text")
        return

    if len(prompt_text) < PRODUCTION_PROMPT_MIN_CHARS:
        errors.append(
            f"{label}: prompt is too thin for production DSL quality "
            f"({len(prompt_text)} chars < {PRODUCTION_PROMPT_MIN_CHARS})"
        )

    lowered = prompt_text.lower()
    placeholders = [
        marker for marker in PROMPT_PLACEHOLDER_MARKERS if marker.lower() in lowered
    ]
    if placeholders:
        errors.append(f"{label}: prompt contains placeholder markers {placeholders}")

    missing = [
        coverage_name
        for coverage_name, markers in PRODUCTION_PROMPT_COVERAGE.items()
        if not any(marker.lower() in lowered for marker in markers)
    ]
    if missing:
        errors.append(
            f"{label}: missing required production prompt coverage {missing}; "
            "cover role, task, input interpretation, output contract, quality "
            "criteria, constraints, and iteration feedback signals"
        )


def validate_aigc_llm_prompt_quality_node(
    node_id: str,
    node_data: dict[str, Any],
    errors: list[str],
) -> None:
    if node_data.get("type") != "llm":
        return
    title = node_data.get("title") or node_id
    label = f"node {node_id} ({title}) AIGC LLM prompt quality"

    model = node_data.get("model")
    completion_params = model.get("completion_params") if isinstance(model, dict) else None
    if not isinstance(completion_params, dict):
        errors.append(f"{label}: model.completion_params must include response_format and json_schema")
        return
    if completion_params.get("response_format") != "json_schema":
        errors.append(f"{label}: response_format must be json_schema")
    if "json_schema" not in completion_params:
        errors.append(f"{label}: json_schema is required")
    else:
        schema = parse_llm_json_schema(completion_params.get("json_schema"), label, errors)
        if isinstance(schema, dict):
            validate_json_schema(schema, f"{label}.json_schema", errors, [], strict_schema=True)

    role_text = prompt_template_text_by_role(node_data.get("prompt_template"))
    if not role_text:
        errors.append(f"{label}: prompt_template must contain system and user prompts")
        return

    system_text = role_text.get("system", "")
    user_text = role_text.get("user", "")
    if not system_text:
        errors.append(f"{label}: missing system prompt")
    elif len(system_text) < 80:
        errors.append(f"{label}: system prompt is too thin for production AIGC planning")

    if not user_text:
        errors.append(f"{label}: missing user prompt")
    elif len(user_text) < 80:
        errors.append(f"{label}: user prompt is too thin for production AIGC planning")

    combined = f"{system_text}\n{user_text}".lower()
    placeholders = [
        marker for marker in PROMPT_PLACEHOLDER_MARKERS if marker.lower() in combined
    ]
    if placeholders:
        errors.append(f"{label}: prompt contains placeholder markers {placeholders}")
    if "json schema" not in combined and "json_schema" not in combined:
        errors.append(f"{label}: prompt must explicitly require JSON Schema output")
    if "{{#" not in user_text:
        errors.append(f"{label}: user prompt must reference input variables")


def validate_aigc_code_quality_node(
    node_id: str,
    node_data: dict[str, Any],
    errors: list[str],
) -> None:
    if node_data.get("type") != "code":
        return
    title = node_data.get("title") or node_id
    label = f"node {node_id} ({title}) AIGC code quality"
    code = node_data.get("code")
    if not isinstance(code, str):
        return

    stripped = code.strip()
    if len(stripped) < 120:
        errors.append(f"{label}: code is too thin for production AIGC normalization")

    lowered = stripped.lower()
    placeholders = [
        marker for marker in PROMPT_PLACEHOLDER_MARKERS if marker.lower() in lowered
    ]
    if placeholders:
        errors.append(f"{label}: code contains placeholder markers {placeholders}")

    lowered_compact = re.sub(r"\s+", " ", lowered)
    if "throw new error" in lowered_compact and "planner output" in lowered_compact:
        errors.append(
            f"{label}: code must not hard-throw on missing planner output; return "
            "status/diagnostics and safe fallback fields instead"
        )

    if "return {" in lowered and "get(" not in stripped and "json" not in lowered and len(stripped) < 240:
        errors.append(
            f"{label}: code appears to be pass-through logic; parse, validate, "
            "normalize, and return diagnostics/fallback fields instead"
        )


def walk_key_values(value: Any, path: str = "") -> list[tuple[str, str, str]]:
    found: list[tuple[str, str, str]] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else str(key)
            if isinstance(child, str):
                found.append((child_path, str(key), child))
            else:
                found.extend(walk_key_values(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(walk_key_values(child, f"{path}[{index}]"))
    return found


def collect_env_references(value: Any) -> set[str]:
    refs: set[str] = set()
    if isinstance(value, str):
        refs.update(ENV_REFERENCE_PATTERN.findall(value))
    elif isinstance(value, dict):
        for child in value.values():
            refs.update(collect_env_references(child))
    elif isinstance(value, list):
        for child in value:
            refs.update(collect_env_references(child))
    return refs


def declared_environment_variable_names(items: list[Any]) -> set[str]:
    names: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        if isinstance(name, str) and name.strip():
            names.add(name.strip())
        selector = item.get("selector")
        if (
            isinstance(selector, list)
            and len(selector) >= 2
            and selector[0] == "env"
            and isinstance(selector[1], str)
            and selector[1].strip()
        ):
            names.add(selector[1].strip())
    return names


def validate_aigc_quality_node(
    node_id: str,
    node_data: dict[str, Any],
    errors: list[str],
    model_catalog: dict[str, Any],
    observed_tool_shapes: dict[str, dict[str, Any]],
    observed_component_shapes: dict[str, dict[str, Any]],
    *,
    aigc_graph: bool,
) -> None:
    node_type = node_data.get("type")
    title = node_data.get("title") or node_id

    if node_type == "llm":
        validate_model_quality_node(node_id, node_data, errors, model_catalog)
        if aigc_graph:
            validate_aigc_llm_prompt_quality_node(node_id, node_data, errors)

    if node_type == "code" and aigc_graph:
        validate_aigc_code_quality_node(node_id, node_data, errors)

    if node_type == "http-request":
        if has_media_generation_language(node_data):
            if has_generic_aigc_http_phrase(node_data) or is_placeholder_url(node_data.get("url")):
                errors.append(
                    f"node {node_id} ({title}) is a generic AIGC HTTP placeholder; "
                    "use an observed AI Hub component/tool or provide a concrete endpoint/auth/body/parser contract"
                )
            else:
                contract_issues = media_http_contract_issues(node_data)
                if contract_issues:
                    errors.append(
                        f"node {node_id} ({title}) media HTTP generation node lacks a concrete "
                        f"HTTP contract: missing {contract_issues}; use an observed AI Hub "
                        "component/tool unless the exact endpoint/auth/body/status/parser contract is known"
                    )
        elif aigc_graph and not is_allowed_aigc_support_http(node_data):
            errors.append(
                f"node {node_id} ({title}) is an unsupported AIGC HTTP node; "
                "use an observed AI Hub component/tool for generation, or provide a concrete "
                "support HTTP contract with endpoint/auth/body/parser evidence"
            )

    if node_type in AIGC_NODE_TYPES:
        model_info = node_data.get("model_info")
        model_id_value = ""
        if not isinstance(model_info, dict):
            errors.append(f"node {node_id} ({title}) {node_type} must include model_info")
        else:
            model_id_value = validate_aigc_component_model_info(
                model_info,
                str(node_type),
                f"node {node_id} ({title}) {node_type}",
                errors,
                model_catalog,
                observed_component_shapes,
            )
        params = node_data.get("params")
        if not isinstance(params, dict):
            errors.append(f"node {node_id} ({title}) {node_type} must include params mapping")
        else:
            validate_media_param_semantic_sources(
                node_id,
                str(title),
                str(node_type),
                params,
                errors,
            )
            params_keys = set(params.keys())
            component_shape = observed_component_shapes.get(str(node_type), {})
            minimum_required = component_shape.get("minimum_required_params", set())
            missing_minimum = sorted(minimum_required - params_keys)
            if missing_minimum:
                errors.append(
                    f"node {node_id} ({title}) {node_type} missing minimum params keys: "
                    f"{missing_minimum}"
                )
            model_shapes = component_shape.get("model_param_shapes", {})
            expected_model_shape = model_shapes.get(model_id_value) if isinstance(model_shapes, dict) else None
            if isinstance(expected_model_shape, dict):
                variants = expected_model_shape.get("accepted_param_variants", [])
                if isinstance(variants, list) and variants:
                    if not any(set(variant) <= params_keys for variant in variants):
                        missing_by_variant = [
                            sorted(set(variant) - params_keys)
                            for variant in variants
                        ]
                        shortest_missing = min(missing_by_variant, key=len)
                        errors.append(
                            f"node {node_id} ({title}) {node_type} params do not match any "
                            f"observed parameter variant for model {model_id_value!r}; "
                            f"missing keys for closest variant: {shortest_missing}"
                        )
                validate_aigc_param_contracts(
                    node_id,
                    str(title),
                    str(node_type),
                    model_id_value,
                    params,
                    expected_model_shape,
                    errors,
                )

    if node_type == "tool":
        tool_name = node_data.get("tool_name")
        if isinstance(tool_name, str):
            expected_tool = observed_tool_shapes.get(tool_name)
            if isinstance(expected_tool, dict) and expected_tool.get("provider_type") == "workflow":
                errors.append(
                    f"node {node_id} ({title}) uses workflow-backed AIGC tool {tool_name!r}; "
                    "generated AIGC main chains must default to native AI Hub nodes "
                    "such as image-generation, video-generation, audio-generation, "
                    "model-3d-generation, or speech-recognition. Use workflow-backed "
                    "Tool nodes only when the user explicitly asks for them or provides "
                    "a runnable AI Hub export proving the runtime contract."
                )

    validate_observed_tool_node(node_id, node_data, errors, observed_tool_shapes)

    for path, key, value in walk_key_values(node_data):
        if key in {"model", "model_id"} and value in RETIRED_MODEL_REPLACEMENTS:
            validate_model_identifier(
                value,
                f"node {node_id} ({title}) {path}",
                errors,
                model_catalog,
            )


SELECTED_MODEL_VALUE_PATTERNS = (
    re.compile(r"\bselected_model\s*:\s*['\"]([^'\"]+)['\"]"),
    re.compile(r"['\"]selected_model['\"]\s*:\s*['\"]([^'\"]+)['\"]"),
)


def looks_like_machine_model_id(value: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{2,}", value))


def validate_aigc_diagnostic_model_alignment(
    nodes: list[Any],
    errors: list[str],
    observed_component_shapes: dict[str, dict[str, Any]],
) -> None:
    actual_component_ids: set[str] = set()
    for node_any in nodes:
        if not isinstance(node_any, dict):
            continue
        node_data = node_any.get("data")
        if not isinstance(node_data, dict) or node_data.get("type") not in AIGC_NODE_TYPES:
            continue
        model_info = node_data.get("model_info")
        if isinstance(model_info, dict):
            model_id = model_info.get("model_id")
            if isinstance(model_id, str) and model_id.strip():
                actual_component_ids.add(model_id.strip())

    if not actual_component_ids:
        return

    known_ids: set[str] = set()
    blocked_ids: set[str] = set()
    aliases: dict[str, str] = {}
    for component_shape in observed_component_shapes.values():
        if not isinstance(component_shape, dict):
            continue
        model_shapes = component_shape.get("model_param_shapes")
        if isinstance(model_shapes, dict):
            for model_id, model_shape in model_shapes.items():
                if not isinstance(model_id, str) or not isinstance(model_shape, dict):
                    continue
                known_ids.add(model_id)
                if permission_status_blocks_direct_generation(model_shape.get("permission_status")):
                    blocked_ids.add(model_id)
        alias_to_model_id = component_shape.get("alias_to_model_id")
        if isinstance(alias_to_model_id, dict):
            for alias, model_id in alias_to_model_id.items():
                if isinstance(alias, str) and isinstance(model_id, str):
                    aliases[alias] = model_id

    for node_any in nodes:
        if not isinstance(node_any, dict):
            continue
        node_id = str(node_any.get("id", ""))
        node_data = node_any.get("data")
        if not isinstance(node_data, dict) or node_data.get("type") != "code":
            continue
        code = node_data.get("code")
        if not isinstance(code, str) or not code.strip():
            continue

        title = node_data.get("title") or node_id
        stale_mentions: set[str] = set()

        for pattern in SELECTED_MODEL_VALUE_PATTERNS:
            for match in pattern.findall(code):
                candidate = match.strip()
                if not looks_like_machine_model_id(candidate):
                    continue
                mapped = aliases.get(candidate, candidate)
                if mapped in known_ids and mapped not in actual_component_ids:
                    stale_mentions.add(candidate)

        for blocked_id in blocked_ids:
            if blocked_id not in actual_component_ids and blocked_id in code:
                stale_mentions.add(blocked_id)

        for retired_id, replacement_id in RETIRED_MODEL_REPLACEMENTS.items():
            if replacement_id in actual_component_ids and retired_id in code:
                stale_mentions.add(retired_id)

        if stale_mentions:
            errors.append(
                f"node {node_id} ({title}) AIGC diagnostics mention stale or non-active "
                f"component selector ids {sorted(stale_mentions)} while native AIGC nodes "
                f"use {sorted(actual_component_ids)}; keep selected_model, selected_model_note, "
                "diagnostics_json, and asset metadata aligned with the actual exported node selector"
            )


def validate_observed_tool_node(
    node_id: str,
    node_data: dict[str, Any],
    errors: list[str],
    observed_tool_shapes: dict[str, dict[str, Any]],
) -> None:
    if node_data.get("type") != "tool":
        return
    title = node_data.get("title") or node_id
    tool_name = node_data.get("tool_name")
    if not isinstance(tool_name, str) or tool_name not in observed_tool_shapes:
        return

    expected = observed_tool_shapes[tool_name]
    expected_provider_type = expected.get("provider_type") or "workflow"
    expected_provider_id = expected.get("provider_id")
    expected_version = expected.get("tool_node_version")
    if node_data.get("provider_type") != expected_provider_type:
        errors.append(
            f"node {node_id} ({title}) tool {tool_name!r} must keep provider_type "
            f"{expected_provider_type!r}"
        )
    if expected_provider_id and node_data.get("provider_id") != expected_provider_id:
        errors.append(
            f"node {node_id} ({title}) tool {tool_name!r} must keep provider_id "
            f"{expected_provider_id!r} from bundled AI Hub workflow export fingerprints"
        )
    if expected_version and str(node_data.get("tool_node_version", "")) != expected_version:
        errors.append(
            f"node {node_id} ({title}) tool {tool_name!r} must keep tool_node_version "
            f"{expected_version!r}"
        )
    required_tool_parameters: set[str] = expected["required_tool_parameters"]
    tool_parameters = node_data.get("tool_parameters")
    if not isinstance(tool_parameters, dict):
        errors.append(
            f"node {node_id} ({title}) tool {tool_name!r} must include tool_parameters"
        )
    else:
        missing = sorted(required_tool_parameters - set(tool_parameters.keys()))
        if missing:
            errors.append(
                f"node {node_id} ({title}) tool {tool_name!r} missing tool_parameters: {missing}"
            )
    params = node_data.get("params")
    required_params: set[str] = expected["required_params"]
    if isinstance(params, dict):
        missing_params = sorted(required_params - set(params.keys()))
        if missing_params:
            errors.append(
                f"node {node_id} ({title}) tool {tool_name!r} missing params keys: {missing_params}"
            )
    required_outputs: set[str] = expected["output_variables"]
    outputs = node_data.get("outputs")
    if required_outputs and isinstance(outputs, list):
        output_variables = {
            str(output.get("variable"))
            for output in outputs
            if isinstance(output, dict) and output.get("variable")
        }
        missing_outputs = sorted(required_outputs - output_variables)
        if missing_outputs:
            errors.append(
                f"node {node_id} ({title}) tool {tool_name!r} missing output variables: "
                f"{missing_outputs}"
            )


def validate_tool_runtime_contract(
    node_id: str,
    node_data: dict[str, Any],
    errors: list[str],
) -> None:
    if node_data.get("type") != "tool":
        return
    title = node_data.get("title") or node_id
    if "tool_configurations" not in node_data:
        errors.append(
            f"node {node_id} ({title}) tool node must include "
            "tool_configurations: {}; AI Hub ToolNodeData requires this field "
            "at runtime and when opening the tool node panel"
        )
        return
    if not isinstance(node_data.get("tool_configurations"), dict):
        errors.append(
            f"node {node_id} ({title}) tool node field tool_configurations "
            "must be a mapping, usually {}"
        )


def validate_model_quality_node(
    node_id: str,
    node_data: dict[str, Any],
    errors: list[str],
    model_catalog: dict[str, Any],
) -> None:
    if node_data.get("type") != "llm":
        return
    title = node_data.get("title") or node_id
    model = node_data.get("model")
    if not isinstance(model, dict):
        return
    model_name = str(model.get("name", "")).strip()
    if not model_name:
        return
    if model_name.lower() in LOW_QUALITY_LLM_DEFAULTS:
        errors.append(
            f"node {node_id} ({title}) uses low-quality default LLM {model_name!r}; "
            "use a current quality-first AI Hub model for generated DSL"
        )
        return
    validate_model_identifier(
        model_name,
        f"node {node_id} ({title}) LLM model.name",
        errors,
        model_catalog,
    )
    if is_economy_llm_model(model_name, model_catalog):
        errors.append(
            f"node {node_id} ({title}) uses economy/latency-oriented LLM "
            f"{model_name!r} for generated DSL; use a quality-first LLM "
            "such as 'gpt-5.5-2026-04-24' or 'gpt-5.4-2026-03-05' unless "
            "the user explicitly asks for cost or speed optimization"
        )


def validate_dsl(
    data: dict[str, Any],
    *,
    strict_schema: bool = False,
    aigc_quality: bool = False,
    model_quality: bool = False,
    tool_quality: bool = False,
    prompt_quality: bool = False,
) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    model_catalog = load_model_catalog(errors) if (aigc_quality or model_quality) else {}
    observed_tool_shapes = load_observed_tool_shapes(errors) if (aigc_quality or tool_quality) else {}
    observed_component_shapes = load_observed_component_shapes(errors) if aigc_quality else {}

    if data.get("kind") != "app":
        errors.append("kind must be 'app'")
    if not isinstance(data.get("version"), str):
        errors.append("version must be a string such as '0.3.1'")

    app = require_mapping(data.get("app"), "app", errors)
    mode = app.get("mode")
    if mode not in VALID_APP_MODES:
        errors.append("app.mode must be 'workflow' or 'advanced-chat'")
    if not app.get("name"):
        errors.append("app.name is required")

    workflow = require_mapping(data.get("workflow"), "workflow", errors)
    require_list(workflow.get("conversation_variables"), "workflow.conversation_variables", errors)
    environment_variables = require_list(
        workflow.get("environment_variables"), "workflow.environment_variables", errors
    )
    env_refs = collect_env_references(data)
    declared_env_names = declared_environment_variable_names(environment_variables)
    missing_env_refs = sorted(env_refs - declared_env_names)
    if missing_env_refs:
        errors.append(
            "environment variable references are not declared in workflow.environment_variables: "
            f"{missing_env_refs}"
        )
    require_mapping(workflow.get("features"), "workflow.features", errors)
    graph = require_mapping(workflow.get("graph"), "workflow.graph", errors)
    nodes = require_list(graph.get("nodes"), "workflow.graph.nodes", errors)
    edges = require_list(graph.get("edges"), "workflow.graph.edges", errors)
    aigc_graph = graph_has_aigc_surface(nodes)

    node_ids: set[str] = set()
    node_types: dict[str, str] = {}
    for index, node_any in enumerate(nodes):
        node = require_mapping(node_any, f"nodes[{index}]", errors)
        node_id = node.get("id")
        if not isinstance(node_id, str) or not node_id:
            errors.append(f"nodes[{index}].id is required")
            continue
        if node_id in node_ids:
            errors.append(f"duplicate node id: {node_id}")
        node_ids.add(node_id)
        node_data = require_mapping(node.get("data"), f"node {node_id}.data", errors)
        top_level_type = node.get("type")
        is_note_node = top_level_type == "custom-note"
        node_type = node_data.get("type")
        if is_note_node and (not isinstance(node_type, str) or not node_type):
            node_type = "custom-note"
            node_types[node_id] = node_type
        elif not isinstance(node_type, str) or not node_type:
            errors.append(f"node {node_id}.data.type is required")
        else:
            node_types[node_id] = node_type
            replacement_type = RETIRED_AIGC_NODE_TYPE_REPLACEMENTS.get(node_type)
            if replacement_type:
                errors.append(
                    f"node {node_id}.data.type {node_type!r} is a retired AI Hub AIGC node type; "
                    f"use {replacement_type!r}. Recent live import dropped the retired node from "
                    "the workflow canvas."
                )
        if not node_data.get("title") and node_type not in {"loop-start", "iteration-start", "custom-note"}:
            errors.append(f"node {node_id}.data.title is required")
        validate_code_node(node_id, node_data, errors)
        validate_llm_structured_output_shape(node_id, node_data, errors)
        validate_start_node(node_id, node_data, errors)
        validate_end_node(node_id, node_data, errors, warnings)
        validate_agent_node(node_id, node_data, errors)
        validate_tool_runtime_contract(node_id, node_data, errors)
        if prompt_quality:
            validate_production_prompt_quality_node(node_id, node_data, errors)
        if model_quality and not aigc_quality:
            validate_model_quality_node(node_id, node_data, errors, model_catalog)
        if tool_quality and not aigc_quality:
            validate_observed_tool_node(node_id, node_data, errors, observed_tool_shapes)
        if aigc_quality:
            validate_aigc_quality_node(
                node_id,
                node_data,
                errors,
                model_catalog,
                observed_tool_shapes,
                observed_component_shapes,
                aigc_graph=aigc_graph,
            )

    if "start" not in node_types.values():
        errors.append("graph must include a start node")
    if mode == "workflow" and "end" not in node_types.values():
        errors.append("workflow mode must include an end node")
    if mode == "workflow" and "answer" in node_types.values():
        errors.append("workflow mode must not include an answer node; use end as the final output node")
    if mode == "advanced-chat" and "answer" not in node_types.values():
        errors.append("advanced-chat mode must include an answer node")
    if mode == "advanced-chat" and "end" in node_types.values():
        errors.append("advanced-chat mode must not include an end node; use answer as the final output node")

    for index, edge_any in enumerate(edges):
        edge = require_mapping(edge_any, f"edges[{index}]", errors)
        source = edge.get("source")
        target = edge.get("target")
        if source not in node_ids:
            errors.append(f"edges[{index}].source references missing node {source!r}")
        if target not in node_ids:
            errors.append(f"edges[{index}].target references missing node {target!r}")
        edge_data = edge.get("data")
        if isinstance(edge_data, dict):
            expected_source_type = node_types.get(source)
            expected_target_type = node_types.get(target)
            if expected_source_type and edge_data.get("sourceType") not in (None, expected_source_type):
                errors.append(f"edges[{index}].data.sourceType should be {expected_source_type!r}")
            if expected_target_type and edge_data.get("targetType") not in (None, expected_target_type):
                errors.append(f"edges[{index}].data.targetType should be {expected_target_type!r}")

    validate_variable_references(nodes, errors)
    validate_parent_child_positions(nodes, errors)
    validate_iteration_graph_contract(nodes, edges, errors)
    validate_iteration_type_contract(nodes, errors)
    validate_iteration_item_variable_type_contract(nodes, errors)
    if aigc_quality:
        validate_aigc_iteration_blocking_nodes(nodes, errors)
        validate_aigc_diagnostic_model_alignment(nodes, errors, observed_component_shapes)

    for label, schema in find_schema_candidates(data):
        validate_json_schema(schema, label, errors, warnings, strict_schema=strict_schema)

    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a generated Dify app DSL YAML file.")
    parser.add_argument(
        "--strict-schema",
        action="store_true",
        help="Treat downstream-safe JSON Schema style issues as errors instead of warnings.",
    )
    parser.add_argument(
        "--aigc-quality",
        action="store_true",
        help=(
            "Reject generic AIGC HTTP placeholders, retired/stale media model IDs, "
            "low-quality generated defaults, thin LLM prompts/schemas, thin Code nodes, "
            "non-FunctionCalling Agent defaults, workflow-backed AIGC tools in main chains, "
            "bad media-field bindings, and blocking iterator image-generation."
        ),
    )
    parser.add_argument(
        "--model-quality",
        action="store_true",
        help="Reject stale AI Hub LLM model display names/catalog ids and economy defaults in generated DSL.",
    )
    parser.add_argument(
        "--tool-quality",
        action="store_true",
        help="Reject incorrect provider ids, versions, params, and outputs for observed private AI Hub workflow tools.",
    )
    parser.add_argument(
        "--prompt-quality",
        action="store_true",
        help=(
            "Reject thin LLM/Agent prompts that lack role, task, input "
            "interpretation, output contract, quality criteria, constraints, "
            "or iteration feedback signals."
        ),
    )
    parser.add_argument("path", type=Path, nargs="+")
    args = parser.parse_args()

    failed = False
    for path in args.path:
        try:
            data = load_yaml(path)
        except Exception as exc:
            print(f"ERROR: {path}: {exc}", file=sys.stderr)
            failed = True
            continue

        errors, warnings = validate_dsl(
            data,
            strict_schema=args.strict_schema,
            aigc_quality=args.aigc_quality,
            model_quality=args.model_quality,
            tool_quality=args.tool_quality,
            prompt_quality=args.prompt_quality,
        )
        if errors:
            print(f"Dify DSL validation failed: {path}")
            for error in errors:
                print(f"- {error}")
            failed = True
            continue

        if warnings:
            print(f"Dify DSL validation warnings: {path}")
            for warning in warnings:
                print(f"- {warning}")

        print(f"OK: {path} passed static Dify DSL validation")

    if failed:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
