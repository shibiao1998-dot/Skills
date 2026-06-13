#!/usr/bin/env python3
"""Build a masked AI Hub console DSL import preflight report."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


PROD_CONSOLE_API_BASE_URL = "https://ai-hub-api.aiae.ndhy.com/console/api"
IMPORT_PATH = "/apps/imports"


@dataclass(frozen=True)
class ImportRequest:
    url: str
    headers: dict[str, str]
    body: str


@dataclass(frozen=True)
class ImportResponse:
    status: int | str
    text: str


def load_text_file(path: Path | str) -> str:
    return Path(path).read_text(encoding="utf-8").strip()


def load_optional_value(*, value: str | None = None, env: str | None = None, file: Path | None = None) -> str:
    if file is not None:
        return load_text_file(file)
    if env:
        return os.environ.get(env, "").strip()
    return (value or "").strip()


def mask_value(value: str) -> str:
    if not value:
        return ""
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]
    return f"<present len={len(value)} sha256={digest}>"


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def normalize_base_url(base_url: str) -> str:
    return base_url.rstrip("/")


def is_http_url(url: str) -> bool:
    return re.match(r"^https?://[^\s]+$", url.strip()) is not None


def build_headers_preview(console_token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {mask_value(console_token)}".strip(),
        "Content-Type": "application/json",
    }


def build_import_headers(console_token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {console_token}",
        "Content-Type": "application/json",
    }


def default_transport(request: ImportRequest) -> ImportResponse:
    data = request.body.encode("utf-8")
    http_request = urllib.request.Request(request.url, data=data, method="POST")
    for key, value in request.headers.items():
        http_request.add_header(key, value)
    try:
        with urllib.request.urlopen(http_request, timeout=30) as response:
            text = response.read(4000).decode("utf-8", errors="replace")
            return ImportResponse(status=response.status, text=text)
    except urllib.error.HTTPError as exc:
        text = exc.read(4000).decode("utf-8", errors="replace")
        return ImportResponse(status=exc.code, text=text)
    except Exception as exc:
        return ImportResponse(status="exception", text=f"{type(exc).__name__}: {exc}")


def build_yaml_content_import_report(
    *,
    yaml_path: Path,
    console_token: str,
    base_url: str,
) -> dict[str, Any]:
    missing_fields: list[str] = []
    normalized_base_url = normalize_base_url(base_url)
    yaml_text = ""

    if not console_token.strip():
        missing_fields.append("console_token")
    if not normalized_base_url:
        missing_fields.append("base_url")
    if not yaml_path.is_file():
        missing_fields.append("yaml_path")
    else:
        yaml_text = yaml_path.read_text(encoding="utf-8")
        if not yaml_text.strip():
            missing_fields.append("yaml_content")

    return {
        "classification": "console_import_ready" if not missing_fields else "environment_preflight",
        "request_preview": {
            "method": "POST",
            "url": f"{normalized_base_url}{IMPORT_PATH}" if normalized_base_url else "",
            "path": IMPORT_PATH,
        },
        "headers_preview": build_headers_preview(console_token),
        "body_preview": {
            "mode": "yaml-content",
            "yaml_path": str(yaml_path),
            "yaml_bytes": len(yaml_text.encode("utf-8")),
            "yaml_sha256": sha256_text(yaml_text) if yaml_text else "",
        },
        "missing_fields": missing_fields,
        "notes": [
            "Report intentionally does not print YAML content or console tokens.",
            "Use only with a console token explicitly provided through a file, value, or environment variable.",
        ],
    }


def summarize_import_response(response: ImportResponse) -> dict[str, Any]:
    text = response.text or ""
    preview = text[:1000]
    app_id = ""
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        payload = None
    if isinstance(payload, dict):
        value = payload.get("app_id") or payload.get("id")
        if isinstance(value, str):
            app_id = value
    return {
        "http_status": response.status,
        "response_preview": preview,
        "app_id": app_id,
    }


def execute_yaml_content_import(
    *,
    yaml_path: Path,
    console_token: str,
    base_url: str,
    transport: Callable[[ImportRequest], ImportResponse] = default_transport,
) -> dict[str, Any]:
    preflight = build_yaml_content_import_report(
        yaml_path=yaml_path,
        console_token=console_token,
        base_url=base_url,
    )
    if preflight["classification"] != "console_import_ready":
        return preflight

    yaml_text = yaml_path.read_text(encoding="utf-8")
    body = json.dumps({"mode": "yaml-content", "yaml_content": yaml_text}, ensure_ascii=False)
    request = ImportRequest(
        url=str(preflight["request_preview"]["url"]),
        headers=build_import_headers(console_token),
        body=body,
    )
    response = transport(request)
    response_summary = summarize_import_response(response)
    success = isinstance(response.status, int) and 200 <= response.status < 300
    return {
        **preflight,
        "classification": "console_import_pass" if success else "console_import_failed",
        **response_summary,
    }


def build_yaml_url_import_report(
    *,
    yaml_url: str,
    console_token: str,
    base_url: str,
) -> dict[str, Any]:
    missing_fields: list[str] = []
    normalized_base_url = normalize_base_url(base_url)
    normalized_url = yaml_url.strip()

    if not console_token.strip():
        missing_fields.append("console_token")
    if not normalized_base_url:
        missing_fields.append("base_url")
    if not is_http_url(normalized_url):
        missing_fields.append("yaml_url")

    return {
        "classification": "console_import_ready" if not missing_fields else "environment_preflight",
        "request_preview": {
            "method": "POST",
            "url": f"{normalized_base_url}{IMPORT_PATH}" if normalized_base_url else "",
            "path": IMPORT_PATH,
        },
        "headers_preview": build_headers_preview(console_token),
        "body_preview": {
            "mode": "yaml-url",
            "yaml_url": normalized_url if is_http_url(normalized_url) else "",
        },
        "missing_fields": missing_fields,
        "notes": [
            "URL import requires an HTTP or HTTPS URL reachable by AI Hub.",
            "Do not use a local file URL for server-side import.",
        ],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--console-token", help="AI Hub console bearer token.")
    parser.add_argument("--console-token-env", help="Environment variable containing AI Hub console bearer token.")
    parser.add_argument("--console-token-file", type=Path, help="File containing AI Hub console bearer token.")
    parser.add_argument("--base-url", default=PROD_CONSOLE_API_BASE_URL)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--yaml-path", type=Path, help="Local DSL YAML path for yaml-content import preflight.")
    source.add_argument("--yaml-url", help="HTTP(S) DSL YAML URL for yaml-url import preflight.")
    parser.add_argument("--execute", action="store_true", help="Execute yaml-content import after preflight.")
    parser.add_argument("--json", action="store_true", help="Emit JSON. Text output is the default.")
    return parser


def render_text(report: dict[str, Any]) -> str:
    lines = [
        "AI Hub console import preflight",
        f"classification: {report['classification']}",
        f"request: {report['request_preview']['method']} {report['request_preview']['url']}",
        f"body_mode: {report['body_preview']['mode']}",
        "headers_preview:",
    ]
    for key, value in report["headers_preview"].items():
        lines.append(f"- {key}: {value}")
    missing = report.get("missing_fields") or []
    lines.append(f"missing_fields: {', '.join(missing) if missing else 'none'}")
    return "\n".join(lines)


def run_cli(argv: list[str] | None = None) -> tuple[int, str]:
    parser = build_parser()
    args = parser.parse_args(argv)
    console_token = load_optional_value(
        value=args.console_token,
        env=args.console_token_env,
        file=args.console_token_file,
    )
    if args.execute and args.yaml_path:
        report = execute_yaml_content_import(
            yaml_path=args.yaml_path,
            console_token=console_token,
            base_url=args.base_url,
        )
    elif args.yaml_path:
        report = build_yaml_content_import_report(
            yaml_path=args.yaml_path,
            console_token=console_token,
            base_url=args.base_url,
        )
    else:
        report = build_yaml_url_import_report(
            yaml_url=args.yaml_url or "",
            console_token=console_token,
            base_url=args.base_url,
        )

    output = json.dumps(report, ensure_ascii=False, sort_keys=True) if args.json else render_text(report)
    passing = report["classification"] in {"console_import_ready", "console_import_pass"}
    return (0 if passing else 2), output


def main(argv: list[str] | None = None) -> int:
    exit_code, output = run_cli(argv)
    print(output, file=sys.stderr if exit_code else sys.stdout)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
