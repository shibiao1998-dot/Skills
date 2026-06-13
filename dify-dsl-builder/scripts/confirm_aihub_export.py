#!/usr/bin/env python3
"""Confirm the newest AI Hub DSL export saved by a browser save dialog."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Iterable


YAML_SUFFIXES = {".yml", ".yaml"}


class ExportNotFoundError(Exception):
    """Raised when no exported DSL YAML can be found."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def iter_yaml_files(directories: Iterable[Path], *, recursive: bool) -> Iterable[Path]:
    for directory in directories:
        if not directory.is_dir():
            continue
        iterator = directory.rglob("*") if recursive else directory.iterdir()
        for path in iterator:
            if path.is_file() and path.suffix.lower() in YAML_SUFFIXES:
                yield path


def matches_name(path: Path, needles: list[str]) -> bool:
    if not needles:
        return True
    name = path.name.lower()
    return all(needle.lower() in name for needle in needles)


def format_mtime(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds")


def confirm_export(
    directories: list[Path],
    *,
    name_contains: list[str] | None = None,
    recursive: bool = False,
    after_unix: float | None = None,
) -> dict[str, object]:
    """Return evidence for the newest matching AI Hub DSL export."""

    needles = name_contains or []
    candidates: list[Path] = []
    for path in iter_yaml_files(directories, recursive=recursive):
        if not matches_name(path, needles):
            continue
        if after_unix is not None and path.stat().st_mtime < after_unix:
            continue
        candidates.append(path)

    if not candidates:
        searched = ", ".join(str(path) for path in directories)
        filters = f"; name contains {needles}" if needles else ""
        raise ExportNotFoundError(f"No exported DSL YAML found in {searched}{filters}")

    candidates.sort(key=lambda path: (path.stat().st_mtime_ns, str(path)), reverse=True)
    newest = candidates[0]
    newest_hash = sha256_file(newest)
    same_hash_paths = [
        str(path)
        for path in candidates
        if path == newest or sha256_file(path) == newest_hash
    ]

    return {
        "path": str(newest),
        "modified_at": format_mtime(newest),
        "modified_unix": newest.stat().st_mtime,
        "size_bytes": newest.stat().st_size,
        "sha256": newest_hash,
        "matched_count": len(candidates),
        "same_hash_count": len(same_hash_paths),
        "same_hash_paths": same_hash_paths[:10],
    }


def render_text(report: dict[str, object]) -> str:
    lines = [
        "AI Hub DSL export confirmed",
        f"path: {report['path']}",
        f"modified_at: {report['modified_at']}",
        f"size_bytes: {report['size_bytes']}",
        f"sha256: {report['sha256']}",
        f"matched_count: {report['matched_count']}",
        f"same_hash_count: {report['same_hash_count']}",
    ]
    same_hash_paths = report.get("same_hash_paths")
    if isinstance(same_hash_paths, list) and same_hash_paths:
        lines.append("same_hash_paths:")
        lines.extend(f"- {path}" for path in same_hash_paths)
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dir",
        action="append",
        dest="directories",
        type=Path,
        help="Directory to inspect. Repeat for multiple save locations. Defaults to ~/Downloads.",
    )
    parser.add_argument(
        "--name-contains",
        action="append",
        default=[],
        help="Require the exported filename to contain this text. Repeat to require all terms.",
    )
    parser.add_argument(
        "--after-unix",
        type=float,
        help="Only consider files modified after this Unix timestamp.",
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="Search directories recursively.",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of text.")
    return parser


def run_cli(argv: list[str] | None = None) -> tuple[int, str]:
    parser = build_parser()
    args = parser.parse_args(argv)
    directories = args.directories or [Path.home() / "Downloads"]

    try:
        report = confirm_export(
            directories,
            name_contains=args.name_contains,
            recursive=args.recursive,
            after_unix=args.after_unix,
        )
    except ExportNotFoundError as exc:
        return 2, str(exc)

    if args.json:
        return 0, json.dumps(report, ensure_ascii=False, sort_keys=True)
    return 0, render_text(report)


def main(argv: list[str] | None = None) -> int:
    exit_code, output = run_cli(argv)
    print(output, file=sys.stderr if exit_code else sys.stdout)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
