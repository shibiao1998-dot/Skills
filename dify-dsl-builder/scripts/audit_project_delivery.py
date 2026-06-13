#!/usr/bin/env python3
"""Audit one generated Dify DSL Builder project delivery folder."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


FORBIDDEN_README_TERMS = (
    "Gate",
    "Build" + " Plan",
    "Grill with " + "Docs",
    "provider_id",
    "node_id",
)


def collect_errors(project_dir: Path, *, validate_dsl: bool) -> list[str]:
    errors: list[str] = []
    if not project_dir.is_dir():
        return [f"project directory does not exist: {project_dir}"]

    readme = project_dir / "README.md"
    if not readme.is_file():
        errors.append("missing README.md")
    else:
        readme_text = readme.read_text(encoding="utf-8")
        forbidden = [term for term in FORBIDDEN_README_TERMS if term in readme_text]
        if forbidden:
            errors.append(f"README.md exposes internal terms: {forbidden}")

    dsl_files = sorted(
        path
        for path in project_dir.iterdir()
        if path.is_file() and path.suffix.lower() in {".yml", ".yaml"}
    )
    if not dsl_files:
        errors.append("missing versioned DSL file at project root")
    for path in dsl_files:
        stem = path.stem.lower()
        if "-v" not in stem:
            errors.append(f"DSL file name should be versioned with -vN: {path.name}")

    agent_dir = project_dir / ".agent"
    if not agent_dir.is_dir():
        errors.append("missing .agent project memory directory")
    else:
        for name in ("DSL_DISCOVERY_BRIEF.md", "build-log.md", "validation-report.md"):
            if not (agent_dir / name).is_file():
                errors.append(f"missing .agent/{name}")

    if validate_dsl and dsl_files:
        validator = Path(__file__).resolve().parent / "validate_dify_dsl.py"
        for dsl_file in dsl_files:
            result = subprocess.run(
                [
                    sys.executable,
                    str(validator),
                    "--model-quality",
                    "--aigc-quality",
                    "--strict-schema",
                    str(dsl_file),
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            if result.returncode != 0:
                detail = (result.stderr or result.stdout).strip()
                errors.append(f"DSL validation failed for {dsl_file.name}: {detail}")

    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project_dir", type=Path)
    parser.add_argument(
        "--skip-dsl-validation",
        action="store_true",
        help="Only check delivery surface files; do not run validate_dify_dsl.py.",
    )
    args = parser.parse_args(argv)

    errors = collect_errors(args.project_dir, validate_dsl=not args.skip_dsl_validation)
    if errors:
        print(f"Dify DSL project delivery audit failed: {args.project_dir}", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print(f"OK: {args.project_dir} passed Dify DSL project delivery audit")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
