#!/usr/bin/env python3
"""Audit the Dify DSL Builder vNext completion criteria."""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


FORBIDDEN_ACTIVE_SNIPPETS = [
    "Mode " + "Selection Gate",
    "普" + "通模式",
    "专" + "业模式",
    "Unified DSL " + "Build" + " Plan",
    "Build" + " Plan",
    "Grill with " + "Docs",
    "assets/" + "templates",
    "template" + "-first",
    "business" + "-approved",
    "engineering" + "-approved",
    "approved" + "-generation",
]

FORBIDDEN_JSON_SNIPPETS = [
    "Mode " + "Selection Gate",
    "Unified DSL " + "Build" + " Plan",
    "Build" + " Plan",
    "Grill with " + "Docs",
    "assets/" + "templates",
    "template" + "-first",
    "business" + "-approved",
    "engineering" + "-approved",
    "approved" + "-generation",
]

REQUIRED_SKILL_SNIPPETS = [
    "Non-Negotiable Rules",
    "Hard Loading Protocol",
    "scripts/run_user_turn.py",
    "references/core-design-principles.md",
    "references/journey-new-build.md",
    "references/journey-repair-iteration.md",
    "references/capability-aihub-api-validation.md",
    "scripts/verify_aihub_console_import.py",
    "scripts/verify_aihub_api_preflight.py",
    "Completion Verification Gate",
]

REQUIRED_REFERENCES = [
    "core-design-principles.md",
    "journey-new-build.md",
    "journey-repair-iteration.md",
    "capability-workflow-chatflow-architecture.md",
    "capability-dify-node-composition.md",
    "capability-domain-expert-generation.md",
    "capability-dimension-aware-decomposition.md",
    "capability-code-schema-variable-contracts.md",
    "capability-aihub-compatibility.md",
    "capability-aigc-production-lines.md",
    "capability-aihub-native-aigc-components.md",
    "capability-aihub-api-validation.md",
    "capability-validation-delivery.md",
    "failure-canvas-rendering.md",
    "failure-runtime-code-node.md",
    "failure-tool-node-shape.md",
    "failure-generated-interaction.md",
    "failure-aigc-runtime-contract.md",
]

REQUIRED_FIXTURES = [
    "dsl-discovery-brief.md",
    "user-action-card-readme.md",
    "validation-report.md",
]

REQUIRED_INTERACTION_SCENARIOS = [
    "vague-idiom-video.json",
    "document-generation-not-upload.json",
    "native-aigc-node-default.json",
    "native-aigc-no-failure-strategy-question.json",
    "missing-component-not-question.json",
    "public-source-music-mv-no-failure-strategy.json",
    "source-quality-gate-generation-confirmation.json",
    "source-checked-aigc-choice-shape-regression.json",
    "aigc-source-music-mv-no-engineering-choice.json",
    "recommended-single-question-options.json",
    "final-alignment.json",
    "confirmation-start-generation.json",
    "uploaded-document-boundary.json",
    "runtime-feedback-options.json",
    "old-dsl-preserve-choices.json",
    "old-dsl-narrow-repair.json",
]

ALLOWED_SPEC_CHECKS = {
    "static",
    "interaction",
    "validator",
    "manifest",
    "manual_evidence",
}

GLOBAL_FORBIDDEN_USER_RESPONSE_SNIPPETS = [
    "失败策略",
    "缺失依赖",
    "缺失组件",
    "缺少组件",
    "停止并提示",
    "直接停止",
    "停止生成",
    "允许降级",
    "是否降级",
    "朗诵配乐",
    "素材包",
    "音视频合成/拼接",
    "有没有可用",
    "有没有组件",
    "有没有工具",
    "我建议",
    "我的建议",
]

FORBIDDEN_PROMPT_SEEDS = [
    "还需要确认" + "一个失败策略",
    "如果 AI Hub 运行环境" + "缺少",
    "你希望流程" + "直接停止",
    "还是允许" + "降级成",
    "如果 AI Hub 缺少" + "人声歌曲生成",
]

LOADED_INSTRUCTION_PROMPT_HAZARDS = [
    "失败策略",
    "缺失依赖",
    "缺失组件",
    "缺少组件",
    "停止并提示",
    "直接停止",
    "停止生成",
    "允许降级",
    "是否降级",
    "音视频合成/拼接",
    "有没有可用",
    "有没有组件",
    "有没有工具",
    "我的建议",
    "我建议",
]

NO_BYTECODE_ENV = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}

def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(read_text(path))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path} is invalid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def write_json_if_changed(path: Path, data: dict[str, Any]) -> None:
    text = json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if path.exists() and read_text(path) == text:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def fail(errors: list[str]) -> int:
    for error in errors:
        print(f"FAIL: {error}")
    return 1


def active_scan_paths(skill_dir: Path) -> list[Path]:
    paths: list[Path] = [skill_dir / "SKILL.md", skill_dir / "agents" / "openai.yaml"]
    references = skill_dir / "references"
    if references.is_dir():
        paths.extend(sorted(path for path in references.glob("*.md") if path.is_file()))
        paths.extend(sorted(path for path in references.glob("*.json") if path.is_file()))
    scripts = skill_dir / "scripts"
    if scripts.is_dir():
        paths.extend(
            sorted(
                path
                for path in scripts.glob("*.py")
                if path.is_file() and not path.name.startswith("test_")
            )
        )
    return paths


def loaded_instruction_paths(skill_dir: Path) -> list[Path]:
    paths: list[Path] = [skill_dir / "SKILL.md", skill_dir / "agents" / "openai.yaml"]
    references = skill_dir / "references"
    if references.is_dir():
        paths.extend(sorted(path for path in references.glob("*.md") if path.is_file()))
    return [path for path in paths if path.is_file()]


def active_text(skill_dir: Path, *, include_json: bool = True) -> str:
    parts: list[str] = []
    for path in active_scan_paths(skill_dir):
        if not include_json and path.suffix == ".json":
            continue
        if path.is_file():
            parts.append(read_text(path))
    return "\n".join(parts)


def check_required_and_forbidden_snippets(skill_dir: Path, errors: list[str]) -> None:
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        errors.append("Missing SKILL.md")
        return

    skill_text = read_text(skill_md)
    for snippet in REQUIRED_SKILL_SNIPPETS:
        if snippet not in skill_text:
            errors.append(f"SKILL.md missing required snippet: {snippet}")

    for path in active_scan_paths(skill_dir):
        text = read_text(path)
        rel = path.relative_to(skill_dir).as_posix()
        snippets = FORBIDDEN_JSON_SNIPPETS if path.suffix == ".json" else FORBIDDEN_ACTIVE_SNIPPETS
        for snippet in snippets:
            if snippet in text:
                errors.append(f"{rel} contains forbidden active snippet: {snippet}")
        for snippet in FORBIDDEN_PROMPT_SEEDS:
            if snippet in text:
                errors.append(f"{rel} contains copyable forbidden prompt seed: {snippet}")

    for path in loaded_instruction_paths(skill_dir):
        text = read_text(path)
        rel = path.relative_to(skill_dir).as_posix()
        for snippet in LOADED_INSTRUCTION_PROMPT_HAZARDS:
            if snippet in text:
                errors.append(f"{rel} contains copyable user-facing prompt hazard: {snippet}")


def check_flat_references(skill_dir: Path, errors: list[str]) -> None:
    references_dir = skill_dir / "references"
    if not references_dir.is_dir():
        errors.append("Missing references directory")
        return
    for name in REQUIRED_REFERENCES:
        if not (references_dir / name).is_file():
            errors.append(f"Missing flat reference: references/{name}")
    nested = sorted(path.name for path in references_dir.iterdir() if path.is_dir())
    if nested:
        errors.append(f"references must be flat; nested directories remain: {nested}")


def check_delivery_fixtures(skill_dir: Path, errors: list[str]) -> None:
    fixtures_dir = skill_dir / "assets" / "fixtures"
    if not fixtures_dir.is_dir():
        errors.append("Missing assets/fixtures directory")
        return
    for name in REQUIRED_FIXTURES:
        if not (fixtures_dir / name).is_file():
            errors.append(f"Missing delivery fixture: assets/fixtures/{name}")

    brief_path = fixtures_dir / "dsl-discovery-brief.md"
    if brief_path.is_file():
        brief_text = read_text(brief_path)
        stale_terms = [
            "guided_build_or_deep_engineering",
            "business" + "-approved",
            "ready" + "-for-generation",
            "Business layer approved",
            "Approval date",
            "Approved generation boundary",
        ]
        for term in stale_terms:
            if term in brief_text:
                errors.append(f"assets/fixtures/dsl-discovery-brief.md contains stale brief term: {term}")


def is_excluded(rel_path: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatch(rel_path, pattern) for pattern in patterns)


def entry_covers(entry_path: str, rel_path: str) -> bool:
    clean = entry_path.rstrip("/")
    return rel_path == clean or rel_path.startswith(clean + "/")


def inventory_runtime_files(skill_dir: Path, manifest: dict[str, Any]) -> list[str]:
    runtime_inventory = manifest.get("runtime_inventory")
    if not isinstance(runtime_inventory, dict):
        raise ValueError("manifest.runtime_inventory must be a mapping")
    include_globs = runtime_inventory.get("include_globs")
    exclude_globs = runtime_inventory.get("exclude_globs", [])
    if not isinstance(include_globs, list) or not include_globs:
        raise ValueError("manifest.runtime_inventory.include_globs must be a non-empty list")
    if not isinstance(exclude_globs, list):
        raise ValueError("manifest.runtime_inventory.exclude_globs must be a list")

    files: set[str] = set()
    for pattern in include_globs:
        if not isinstance(pattern, str):
            raise ValueError("manifest.runtime_inventory.include_globs entries must be strings")
        for path in skill_dir.glob(pattern):
            if path.is_file():
                rel = path.relative_to(skill_dir).as_posix()
                if not is_excluded(rel, [str(item) for item in exclude_globs]):
                    files.add(rel)
    return sorted(files)


def check_manifest(skill_dir: Path, errors: list[str]) -> None:
    manifest_path = skill_dir / "tests" / "legacy-audit-manifest.json"
    if not manifest_path.is_file():
        errors.append("Missing tests/legacy-audit-manifest.json")
        return
    try:
        manifest = read_json(manifest_path)
        runtime_files = inventory_runtime_files(skill_dir, manifest)
    except ValueError as exc:
        errors.append(str(exc))
        return

    allowed_decisions = set(manifest.get("allowed_decisions", []))
    entries = manifest.get("entries")
    if not isinstance(entries, list) or not entries:
        errors.append("Legacy manifest entries must be a non-empty list")
        return

    entry_paths: list[str] = []
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            errors.append(f"Legacy manifest entry {index} must be a mapping")
            continue
        for key in ("path", "current_role", "decision", "new_home", "conflict_removed", "verification"):
            if not str(entry.get(key, "")).strip():
                errors.append(f"Legacy manifest entry {index} missing {key}")
        decision = entry.get("decision")
        if decision not in allowed_decisions:
            errors.append(f"Legacy manifest entry {index} has invalid decision: {decision!r}")
        entry_path = str(entry.get("path", "")).strip()
        if entry_path:
            entry_paths.append(entry_path)

    for rel_path in runtime_files:
        if not any(entry_covers(entry_path, rel_path) for entry_path in entry_paths):
            errors.append(f"Runtime artifact missing from legacy manifest: {rel_path}")

    active_text = "\n".join(read_text(path) for path in active_scan_paths(skill_dir) if path.is_file())
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        if entry.get("decision") not in {"converted", "deprecated"}:
            continue
        old_path = str(entry.get("path", "")).strip().rstrip("/")
        if old_path == "assets/fixtures":
            continue
        if old_path and old_path in active_text:
            errors.append(f"Converted/deprecated artifact is still active-loading referenced: {old_path}")


def check_assets(skill_dir: Path, errors: list[str]) -> None:
    legacy_assets = "assets/" + "templates"
    fixture_assets = "assets/" + "fixtures"
    if (skill_dir / "assets" / "templates").exists():
        errors.append(f"{legacy_assets} still exists; converted assets must live under {fixture_assets}")
    if not (skill_dir / "assets" / "fixtures").is_dir():
        errors.append("Missing assets/fixtures")
    if (skill_dir / "assets" / "fixtures" / "legacy-references").exists():
        errors.append("assets/fixtures/legacy-references must not be distributed in the active skill package")
    if (skill_dir / "assets" / "fixtures" / "legacy-scripts").exists():
        errors.append("assets/fixtures/legacy-scripts must not be distributed in the active skill package")
    if any(skill_dir.rglob("__pycache__")):
        errors.append("__pycache__ directories must not remain in the distributable skill tree")
    fixtures_dir = skill_dir / "assets" / "fixtures"
    if fixtures_dir.is_dir():
        for fixture in sorted(fixtures_dir.glob("aigc-*.yml")) + sorted(fixtures_dir.glob("aigc-*.yaml")):
            text = read_text(fixture)
            if "workflow-backed" in text or "\n        type: tool\n" in text or "\n          type: tool\n" in text:
                errors.append(
                    f"{fixture.relative_to(skill_dir)} must not teach tool-backed AIGC as a fixture; "
                    "native AI Hub AIGC component fixtures are allowed"
                )


def check_interaction_scenarios(skill_dir: Path, errors: list[str]) -> None:
    scenario_dir = skill_dir / "tests" / "scenarios" / "interaction"
    run_user_turn = skill_dir / "scripts" / "run_user_turn.py"
    render_user_response = skill_dir / "scripts" / "render_user_response.py"
    if not run_user_turn.is_file():
        errors.append("Missing scripts/run_user_turn.py")
        return
    if not render_user_response.is_file():
        errors.append("Missing scripts/render_user_response.py")
        return

    for name in REQUIRED_INTERACTION_SCENARIOS:
        scenario_path = scenario_dir / name
        if not scenario_path.is_file():
            errors.append(f"Missing interaction scenario fixture: tests/scenarios/interaction/{name}")
            continue
        try:
            scenario = read_json(scenario_path)
        except ValueError as exc:
            errors.append(str(exc))
            continue

        user_input = str(scenario.get("input", "")).strip()
        if not user_input:
            errors.append(f"Interaction scenario {name} missing input")
            continue

        with tempfile.TemporaryDirectory(prefix="dify-dsl-vnext-") as tmp_dir:
            tmp = Path(tmp_dir)
            command = [
                sys.executable,
                str(run_user_turn),
                "--json",
                "--project-dir",
                str(tmp),
                "--slug",
                str(scenario.get("id") or name.removesuffix(".json")),
            ]
            feedback = str(scenario.get("feedback") or "").strip()
            if feedback:
                command.extend(["--feedback", feedback])
            command.append(user_input)
            json_result = subprocess.run(
                command,
                cwd=skill_dir,
                env=NO_BYTECODE_ENV,
                text=True,
                capture_output=True,
                check=False,
            )
            generated_files = [
                path.relative_to(tmp).as_posix()
                for path in tmp.rglob("*")
                if path.is_file()
                and (
                    path.suffix.lower() in {".yml", ".yaml"}
                    or path.name == "README.md"
                    or ".agent" in path.relative_to(tmp).parts
                )
            ]
        diagnostic = (json_result.stdout or "") + ("\n" + json_result.stderr if json_result.stderr else "")
        if json_result.returncode != 3:
            errors.append(
                f"Interaction scenario {name} must stop before generation with exit 3, "
                f"got {json_result.returncode}: {diagnostic[:500]}"
            )
            continue
        try:
            payload = json.loads(json_result.stdout)
        except json.JSONDecodeError as exc:
            errors.append(f"Interaction scenario {name} returned invalid JSON payload: {exc}")
            continue
        if not isinstance(payload, dict):
            errors.append(f"Interaction scenario {name} JSON payload must be an object")
            continue
        if payload.get("decision") == "generated":
            errors.append(f"Interaction scenario {name} generated before final confirmation")
        if generated_files:
            errors.append(f"Interaction scenario {name} wrote files before confirmation: {generated_files}")

        render_result = subprocess.run(
            [sys.executable, str(render_user_response)],
            cwd=skill_dir,
            env=NO_BYTECODE_ENV,
            input=json_result.stdout,
            text=True,
            capture_output=True,
            check=False,
        )
        if render_result.returncode != 0:
            errors.append(f"Interaction scenario {name} renderer failed: {render_result.stderr[:500]}")
            continue
        output = render_result.stdout
        response_type = str(payload.get("response_type") or "")
        if response_type != "narrow_repair_confirmation":
            for snippet in GLOBAL_FORBIDDEN_USER_RESPONSE_SNIPPETS:
                if snippet in output:
                    errors.append(
                        f"Interaction scenario {name} contains globally forbidden user-facing text: {snippet}"
                    )
        for snippet in scenario.get("must_not_contain", []):
            if isinstance(snippet, str) and snippet and snippet in output:
                errors.append(f"Interaction scenario {name} contains forbidden text: {snippet}")
        for snippet in scenario.get("must_contain_all", []):
            if isinstance(snippet, str) and snippet and snippet not in output:
                errors.append(f"Interaction scenario {name} missing required text: {snippet}")
        any_snippets = scenario.get("must_contain_any", [])
        if isinstance(any_snippets, list) and any_snippets:
            if not any(isinstance(snippet, str) and snippet in output for snippet in any_snippets):
                errors.append(f"Interaction scenario {name} missing any accepted text: {any_snippets}")
        if payload.get("recommended_next_question") and payload.get("message"):
            errors.append(f"Interaction scenario {name} returned both message and next question")
        questions = payload.get("questions")
        if isinstance(questions, list) and len(questions) > 1:
            errors.append(f"Interaction scenario {name} returned multiple structured questions")
        if output.count("?") + output.count("？") > 1:
            errors.append(f"Interaction scenario {name} asks more than one user-facing question")
        if response_type != "narrow_repair_confirmation":
            for required_choice_token in ("我的推荐", "A.", "B."):
                if required_choice_token not in output:
                    errors.append(
                        f"Interaction scenario {name} must render recommended A/B choices; "
                        f"missing {required_choice_token!r}"
                    )
            if "你可以直接回复 A 或 B" not in output:
                errors.append(
                    f"Interaction scenario {name} must end with a low-pressure A/B expectation sentence"
                )


def interaction_probe(skill_dir: Path) -> tuple[dict[str, dict[str, Any]], list[str]]:
    scenario_dir = skill_dir / "tests" / "scenarios" / "interaction"
    run_user_turn = skill_dir / "scripts" / "run_user_turn.py"
    render_user_response = skill_dir / "scripts" / "render_user_response.py"
    results: dict[str, dict[str, Any]] = {}
    errors: list[str] = []
    if not run_user_turn.is_file() or not render_user_response.is_file():
        return results, ["missing interaction runner scripts"]
    for name in REQUIRED_INTERACTION_SCENARIOS:
        scenario_path = scenario_dir / name
        if not scenario_path.is_file():
            errors.append(f"missing scenario {name}")
            continue
        scenario = read_json(scenario_path)
        with tempfile.TemporaryDirectory(prefix="dify-dsl-vnext-spec-") as tmp_dir:
            tmp = Path(tmp_dir)
            command = [
                sys.executable,
                str(run_user_turn),
                "--json",
                "--project-dir",
                str(tmp),
                "--slug",
                str(scenario.get("id") or name.removesuffix(".json")),
            ]
            feedback = str(scenario.get("feedback") or "").strip()
            if feedback:
                command.extend(["--feedback", feedback])
            command.append(str(scenario.get("input") or ""))
            json_result = subprocess.run(
                command,
                cwd=skill_dir,
                env=NO_BYTECODE_ENV,
                text=True,
                capture_output=True,
                check=False,
            )
            generated_files = [
                path.relative_to(tmp).as_posix()
                for path in tmp.rglob("*")
                if path.is_file()
                and (
                    path.suffix.lower() in {".yml", ".yaml"}
                    or path.name == "README.md"
                    or ".agent" in path.relative_to(tmp).parts
                )
            ]
        try:
            payload = json.loads(json_result.stdout)
        except json.JSONDecodeError:
            payload = {}
        render_result = subprocess.run(
            [sys.executable, str(render_user_response)],
            cwd=skill_dir,
            env=NO_BYTECODE_ENV,
            input=json_result.stdout,
            text=True,
            capture_output=True,
            check=False,
        )
        results[name] = {
            "exit_code": json_result.returncode,
            "payload": payload,
            "output": render_result.stdout,
            "generated_files": generated_files,
        }
    return results, errors


def validator_tests_pass(skill_dir: Path) -> tuple[bool, str]:
    scripts_dir = skill_dir / "scripts"
    result = subprocess.run(
        [sys.executable, "-m", "unittest", "test_validate_dify_dsl.py"],
        cwd=scripts_dir,
        env=NO_BYTECODE_ENV,
        text=True,
        capture_output=True,
        check=False,
    )
    output = (result.stdout or "") + ("\n" + result.stderr if result.stderr else "")
    return result.returncode == 0, output.strip()


def check_project_delivery_audit(skill_dir: Path, errors: list[str]) -> None:
    audit_script = skill_dir / "scripts" / "audit_project_delivery.py"
    if not audit_script.is_file():
        errors.append("Missing scripts/audit_project_delivery.py")
        return

    fixtures_dir = skill_dir / "assets" / "fixtures"
    with tempfile.TemporaryDirectory(prefix="dify-dsl-delivery-audit-") as tmp_dir:
        project = Path(tmp_dir) / "sample-project"
        agent_dir = project / ".agent"
        agent_dir.mkdir(parents=True)
        (project / "README.md").write_text(
            read_text(fixtures_dir / "user-action-card-readme.md"),
            encoding="utf-8",
        )
        (project / "sample-workflow-v1.yml").write_text(
            read_text(fixtures_dir / "minimal-workflow.yml"),
            encoding="utf-8",
        )
        (agent_dir / "DSL_DISCOVERY_BRIEF.md").write_text(
            read_text(fixtures_dir / "dsl-discovery-brief.md"),
            encoding="utf-8",
        )
        (agent_dir / "validation-report.md").write_text(
            read_text(fixtures_dir / "validation-report.md"),
            encoding="utf-8",
        )
        (agent_dir / "build-log.md").write_text(
            "- sample delivery audit fixture\n",
            encoding="utf-8",
        )
        result = subprocess.run(
            [sys.executable, str(audit_script), str(project)],
            cwd=skill_dir,
            env=NO_BYTECODE_ENV,
            text=True,
            capture_output=True,
            check=False,
        )
        if result.returncode != 0:
            errors.append(
                "Project delivery audit fixture failed: "
                + ((result.stderr or result.stdout).strip()[:500])
            )


def manifest_status(skill_dir: Path) -> tuple[bool, str]:
    manifest_path = skill_dir / "tests" / "legacy-audit-manifest.json"
    if not manifest_path.is_file():
        return False, "manifest missing"
    try:
        manifest = read_json(manifest_path)
        runtime_files = inventory_runtime_files(skill_dir, manifest)
    except ValueError as exc:
        return False, str(exc)
    entries = manifest.get("entries")
    if not isinstance(entries, list):
        return False, "manifest entries is not a list"
    entry_paths = [
        str(entry.get("path", "")).strip()
        for entry in entries
        if isinstance(entry, dict) and str(entry.get("path", "")).strip()
    ]
    missing = [
        rel_path
        for rel_path in runtime_files
        if not any(entry_covers(entry_path, rel_path) for entry_path in entry_paths)
    ]
    if missing:
        return False, f"runtime artifacts missing from manifest: {missing[:5]}"
    converted_active: list[str] = []
    text = active_text(skill_dir)
    for entry in entries:
        if not isinstance(entry, dict) or entry.get("decision") not in {"converted", "deprecated"}:
            continue
        old_path = str(entry.get("path", "")).strip().rstrip("/")
        if old_path and old_path != "assets/fixtures" and old_path in text:
            converted_active.append(old_path)
    if converted_active:
        return False, f"converted/deprecated active references: {converted_active[:5]}"
    return True, f"{len(runtime_files)} runtime files covered by {len(entries)} manifest entries"


def spec_acceptance_evidence(skill_dir: Path) -> dict[int, dict[str, Any]]:
    skill_md = read_text(skill_dir / "SKILL.md") if (skill_dir / "SKILL.md").is_file() else ""
    references_dir = skill_dir / "references"
    refs = {path.name: read_text(path) for path in references_dir.glob("*.md")} if references_dir.is_dir() else {}
    active_non_json = active_text(skill_dir, include_json=False)
    active_all = active_text(skill_dir)
    interaction_results, interaction_errors = interaction_probe(skill_dir)
    validator_ok, validator_output = validator_tests_pass(skill_dir)
    manifest_ok, manifest_evidence = manifest_status(skill_dir)
    manual_evidence = skill_dir / "tests" / "evidence" / "spec-acceptance-manual-evidence.md"
    fixtures_dir = skill_dir / "tests" / "scenarios"
    required_refs_present = all((references_dir / name).is_file() for name in REQUIRED_REFERENCES)
    failure_refs_have_sections = all(
        all(heading in refs.get(name, "") for heading in ("## Symptom", "## Root Cause", "## Prevention Rule", "## Validator Or Test"))
        for name in REQUIRED_REFERENCES
        if name.startswith("failure-")
    )
    forbidden_user_labels_absent = all(snippet not in active_non_json for snippet in FORBIDDEN_ACTIVE_SNIPPETS)
    interaction_stops = all(
        result.get("exit_code") == 3
        and not result.get("generated_files")
        and (result.get("payload") or {}).get("decision") != "generated"
        for result in interaction_results.values()
    )
    scenarios_present = all(
        (fixtures_dir / "interaction" / name).is_file()
        for name in REQUIRED_INTERACTION_SCENARIOS
    ) and (fixtures_dir / "dsl-structural" / "tool-missing-config.yml").is_file()
    split_scenarios = (fixtures_dir / "interaction").is_dir() and (fixtures_dir / "dsl-structural").is_dir()
    nested_refs = [path.name for path in references_dir.iterdir() if path.is_dir()] if references_dir.is_dir() else []
    local_sample_path = str(Path.home() / "workspace" / "workfile" / "yaml")
    local_selector_name = "select_" + "local_samples"
    legacy_template_path = "assets/" + "templates"
    visible_mode_a = "普" + "通模式"
    visible_mode_b = "专" + "业模式"
    local_runtime_paths_absent = local_sample_path not in active_all and local_selector_name not in active_all
    no_templates = not (skill_dir / "assets" / "templates").exists() and legacy_template_path not in active_all

    return {
        1: {"passed": len(skill_md.splitlines()) <= 120 and "Hard Loading Protocol" in skill_md, "evidence": f"SKILL.md line count={len(skill_md.splitlines())} and loader sections present"},
        2: {"passed": "references/core-design-principles.md" in skill_md, "evidence": "SKILL.md requires core principles before DSL design or repair"},
        3: {"passed": "journey-new-build.md" in skill_md and "journey-repair-iteration.md" in skill_md and refs.get("journey-new-build.md") != refs.get("journey-repair-iteration.md"), "evidence": "new build and repair journey files are both mapped and distinct"},
        4: {"passed": "Load only relevant `references/capability-*.md` files" in skill_md, "evidence": "Hard Loading Protocol uses conditional capability loading"},
        5: {"passed": failure_refs_have_sections, "evidence": "all failure references contain required failure-analysis sections"},
        6: {"passed": validator_ok, "evidence": validator_output.splitlines()[-1] if validator_output else "validator tests executed"},
        7: {"passed": validator_ok and scenarios_present, "evidence": "validator tests and structural fixtures exist and run"},
        8: {"passed": local_runtime_paths_absent, "evidence": "active path has no machine-specific local sample path or selector helper"},
        9: {"passed": forbidden_user_labels_absent, "evidence": "active non-JSON path has no forbidden user-facing process labels"},
        10: {"passed": interaction_stops and not interaction_errors, "evidence": "all interaction scenarios exit 3 without generated files before confirmation"},
        11: {"passed": visible_mode_a not in active_non_json and visible_mode_b not in active_non_json, "evidence": "active non-JSON path does not ask for visible mode choice"},
        12: {"passed": "final-alignment.json" in interaction_results and "拆成" in str(interaction_results.get("final-alignment.json", {}).get("output", "")), "evidence": "final alignment scenario renders concise plain-language decomposition"},
        13: {"passed": "README.md" in refs.get("journey-new-build.md", "") and ".agent/" in refs.get("journey-new-build.md", ""), "evidence": "new-build journey defines README, versioned DSL, and .agent memory"},
        14: {"passed": manifest_ok, "evidence": manifest_evidence},
        15: {"passed": manifest_ok and forbidden_user_labels_absent, "evidence": "manifest coverage plus forbidden active-path scan passed"},
        16: {"passed": manifest_ok, "evidence": manifest_evidence},
        17: {"passed": manifest_ok, "evidence": manifest_evidence},
        18: {"passed": manifest_ok, "evidence": "converted/deprecated entries are checked against active loading text"},
        19: {"passed": "Discovery Sufficiency Rule" in refs.get("journey-new-build.md", ""), "evidence": "new-build journey defines discovery sufficiency"},
        20: {"passed": "overloaded" in refs.get("capability-dimension-aware-decomposition.md", "").lower() or "one overloaded" in refs.get("capability-dimension-aware-decomposition.md", "").lower(), "evidence": "dimension decomposition capability warns against overloaded LLM nodes"},
        21: {"passed": "拆成" in str(interaction_results.get("final-alignment.json", {}).get("output", "")), "evidence": "final-alignment interaction output includes plain decomposition"},
        22: {"passed": scenarios_present, "evidence": "interaction scenarios plus structural fixture cover requested scenario classes"},
        23: {"passed": split_scenarios, "evidence": "interaction and DSL structural regression directories are separate"},
        24: {"passed": manual_evidence.is_file(), "evidence": "manual evidence file exists and completion audit checks core gates"},
        25: {"passed": "Non-Negotiable Rules" in skill_md and required_refs_present, "evidence": "entrypoint redlines and progressive references exist"},
        26: {"passed": all(token in skill_md for token in ("Read this file", "core-design-principles.md", "journey-new-build.md", "capability-", "failure-", "Run validators")), "evidence": "SKILL.md contains ordered loading protocol"},
        27: {"passed": required_refs_present and not nested_refs, "evidence": f"required flat references present; nested refs={nested_refs}"},
        28: {"passed": no_templates, "evidence": "legacy template folder absent and active path has no production template dependency"},
    }


def check_spec_acceptance(skill_dir: Path, errors: list[str]) -> None:
    acceptance_path = skill_dir / "tests" / "spec-acceptance-vnext.json"
    if not acceptance_path.is_file():
        errors.append("Missing tests/spec-acceptance-vnext.json")
        return
    try:
        acceptance = read_json(acceptance_path)
    except ValueError as exc:
        errors.append(str(exc))
        return
    criteria = acceptance.get("criteria")
    if not isinstance(criteria, list):
        errors.append("tests/spec-acceptance-vnext.json criteria must be a list")
        return

    ids = sorted(item.get("id") for item in criteria if isinstance(item, dict))
    if ids != list(range(1, 29)):
        errors.append(f"spec-acceptance-vnext.json must cover exact ids 1-28, got {ids}")
    for item in criteria:
        if not isinstance(item, dict):
            errors.append(f"Spec acceptance criterion must be a mapping: {item!r}")
            continue
        if item.get("check") not in ALLOWED_SPEC_CHECKS:
            errors.append(f"Spec acceptance criterion has invalid check type: {item!r}")
        if not str(item.get("text", "")).strip():
            errors.append(f"Spec acceptance criterion missing text: {item!r}")

    if any(isinstance(item, dict) and item.get("check") == "manual_evidence" for item in criteria):
        evidence_path = skill_dir / "tests" / "evidence" / "spec-acceptance-manual-evidence.md"
        if not evidence_path.is_file():
            errors.append("Manual acceptance criteria require tests/evidence/spec-acceptance-manual-evidence.md")

    evidence = spec_acceptance_evidence(skill_dir)
    missing_evidence = [criterion_id for criterion_id in range(1, 29) if criterion_id not in evidence]
    if missing_evidence:
        errors.append(f"Spec acceptance evidence missing criteria: {missing_evidence}")
    failed = {
        criterion_id: item
        for criterion_id, item in evidence.items()
        if not item.get("passed")
    }
    for criterion_id, item in failed.items():
        errors.append(f"Spec acceptance criterion {criterion_id} failed: {item.get('evidence')}")
    write_json_if_changed(
        skill_dir / "tests" / "evidence" / "spec-acceptance-audit.json",
        {
            "criteria": [
                {
                    "id": criterion_id,
                    "passed": bool(item.get("passed")),
                    "evidence": str(item.get("evidence", "")),
                }
                for criterion_id, item in sorted(evidence.items())
            ]
        },
    )


def check_structural_fixtures(skill_dir: Path, errors: list[str]) -> None:
    fixture_dir = skill_dir / "tests" / "scenarios" / "dsl-structural"
    required = fixture_dir / "tool-missing-config.yml"
    if not required.is_file():
        errors.append("Missing structural fixture: tests/scenarios/dsl-structural/tool-missing-config.yml")
        return
    fixtures = sorted(fixture_dir.glob("*.yml")) + sorted(fixture_dir.glob("*.yaml"))
    if not fixtures:
        errors.append("No DSL structural fixtures found")
        return
    validator = skill_dir / "scripts" / "validate_dify_dsl.py"
    for fixture in fixtures:
        result = subprocess.run(
            [sys.executable, str(validator), str(fixture)],
            cwd=skill_dir,
            env=NO_BYTECODE_ENV,
            text=True,
            capture_output=True,
            check=False,
        )
        if result.returncode == 0:
            errors.append(f"Structural fixture unexpectedly passed validation: {fixture.relative_to(skill_dir)}")


def check_aigc_fixture_quality(skill_dir: Path, errors: list[str]) -> None:
    fixtures_dir = skill_dir / "assets" / "fixtures"
    validator = skill_dir / "scripts" / "validate_dify_dsl.py"
    if not fixtures_dir.is_dir() or not validator.is_file():
        return
    fixtures = sorted(fixtures_dir.glob("aigc-*.yml")) + sorted(fixtures_dir.glob("aigc-*.yaml"))
    for fixture in fixtures:
        result = subprocess.run(
            [sys.executable, str(validator), "--aigc-quality", str(fixture)],
            cwd=skill_dir,
            env=NO_BYTECODE_ENV,
            text=True,
            capture_output=True,
            check=False,
        )
        if result.returncode != 0:
            output = (result.stdout or "") + ("\n" + result.stderr if result.stderr else "")
            errors.append(
                f"AIGC fixture failed --aigc-quality validation: "
                f"{fixture.relative_to(skill_dir)}\n{output[:1000]}"
            )


def check_validator_unit_tests(skill_dir: Path, errors: list[str]) -> None:
    scripts_dir = skill_dir / "scripts"
    result = subprocess.run(
        [sys.executable, "-m", "unittest", "test_validate_dify_dsl.py"],
        cwd=scripts_dir,
        env=NO_BYTECODE_ENV,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        output = (result.stdout or "") + ("\n" + result.stderr if result.stderr else "")
        errors.append(f"Validator unit tests failed: {output[:1000]}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skill-dir", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args(argv)

    skill_dir = args.skill_dir.resolve()
    errors: list[str] = []
    check_required_and_forbidden_snippets(skill_dir, errors)
    check_flat_references(skill_dir, errors)
    check_delivery_fixtures(skill_dir, errors)
    check_manifest(skill_dir, errors)
    check_assets(skill_dir, errors)
    check_interaction_scenarios(skill_dir, errors)
    check_spec_acceptance(skill_dir, errors)
    check_validator_unit_tests(skill_dir, errors)
    check_structural_fixtures(skill_dir, errors)
    check_aigc_fixture_quality(skill_dir, errors)
    check_project_delivery_audit(skill_dir, errors)
    if errors:
        return fail(errors)
    print("vNext completion audit passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
