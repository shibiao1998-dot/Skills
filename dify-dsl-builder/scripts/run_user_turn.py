#!/usr/bin/env python3
"""Run one Dify DSL Builder vNext conversation turn."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import generate_from_requirement  # noqa: E402
import render_user_response  # noqa: E402


def exit_code_for_result(result: dict) -> int:
    return 0 if result.get("decision") == "generated" else 3


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Print raw JSON payload for tools.")
    parser.add_argument("--project-dir", type=Path, required=True)
    parser.add_argument("--slug", help="Project slug used for generated artifacts.")
    parser.add_argument("--existing-dsl", type=Path)
    parser.add_argument("--requirement-doc", type=Path)
    parser.add_argument("--feedback")
    parser.add_argument("--narrow-repair", action="store_true")
    parser.add_argument("text", nargs="*", help="User turn text. Reads stdin when omitted.")
    args = parser.parse_args(argv)

    requirement = " ".join(args.text) if args.text else sys.stdin.read()
    result = generate_from_requirement.generate_project(
        requirement,
        args.project_dir,
        args.slug,
        existing_dsl=args.existing_dsl,
        requirement_doc=args.requirement_doc,
        feedback=args.feedback,
        narrow_repair=args.narrow_repair,
    )

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        sys.stdout.write(render_user_response.render_response(result))
    return exit_code_for_result(result)


if __name__ == "__main__":
    raise SystemExit(main())
