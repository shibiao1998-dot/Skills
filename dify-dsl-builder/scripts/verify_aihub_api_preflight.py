#!/usr/bin/env python3
"""Build a masked AI Hub API validation preflight report.

This helper does not execute a request by default. It verifies that a future
API-level run test has the required runtime identity and emits only masked
credential previews.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any


DEFAULT_SDP_APP_ID = "b4fb92a0-af7f-49c2-b270-8f62afac1133"
PROD_API_BASE_URL = "https://ai-hub-api.aiae.ndhy.com"
PROD_WEB_BASE_URL = "https://ai-hub.ndhy.com"
SUPPORTED_AUTH_MODES = {"api-key", "bts"}


def load_text_file(path: Path | str) -> str:
    return Path(path).read_text(encoding="utf-8").strip()


def load_optional_value(*, value: str | None = None, env: str | None = None, file: Path | None = None) -> str:
    if file is not None:
        return load_text_file(file)
    if env:
        return os.environ.get(env, "").strip()
    return (value or "").strip()


def normalize_auth_mode(auth_mode: str) -> str:
    normalized = auth_mode.strip().lower().replace("_", "-")
    if normalized in {"apikey", "api-key"}:
        return "api-key"
    return normalized


def mask_value(value: str) -> str:
    if not value:
        return ""
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]
    return f"<present len={len(value)} sha256={digest}>"


def build_headers_preview(
    *,
    auth_mode: str,
    auth_value: str,
    bot_id: str,
    user_id: str,
    sdp_app_id: str,
) -> dict[str, str]:
    normalized = normalize_auth_mode(auth_mode)
    auth_prefix = "BTS" if normalized == "bts" else "Bearer"
    return {
        "Authorization": f"{auth_prefix} {mask_value(auth_value)}".strip(),
        "X-App-Id": mask_value(bot_id),
        "Userid": mask_value(user_id),
        "sdp-app-id": sdp_app_id,
        "Content-Type": "application/json",
    }


def build_preflight_report(
    *,
    auth_mode: str,
    auth_value: str,
    bot_id: str,
    user_id: str,
    sdp_app_id: str,
    base_url: str,
    endpoint: str,
) -> dict[str, Any]:
    normalized_mode = normalize_auth_mode(auth_mode)
    normalized_base_url = base_url.rstrip("/")
    normalized_endpoint = endpoint if endpoint.startswith("/") else f"/{endpoint}" if endpoint else ""
    missing_fields: list[str] = []

    if normalized_mode not in SUPPORTED_AUTH_MODES:
        missing_fields.append("auth_mode")
    if not auth_value.strip():
        missing_fields.append("auth_value")
    if not bot_id.strip():
        missing_fields.append("bot_id")
    if not user_id.strip():
        missing_fields.append("user_id")
    if not sdp_app_id.strip():
        missing_fields.append("sdp_app_id")
    if not normalized_base_url:
        missing_fields.append("base_url")
    if not normalized_endpoint:
        missing_fields.append("endpoint")

    return {
        "classification": "api_validation_ready" if not missing_fields else "environment_preflight",
        "auth_mode": normalized_mode,
        "base_url": normalized_base_url,
        "endpoint": normalized_endpoint,
        "request_preview": {
            "method": "POST",
            "url": f"{normalized_base_url}{normalized_endpoint}" if normalized_base_url and normalized_endpoint else "",
        },
        "headers_preview": build_headers_preview(
            auth_mode=normalized_mode,
            auth_value=auth_value,
            bot_id=bot_id,
            user_id=user_id,
            sdp_app_id=sdp_app_id,
        ),
        "missing_fields": missing_fields,
        "notes": [
            "Report intentionally masks credentials and runtime identity values.",
            "Use this preflight before API-level AI Hub run validation.",
        ],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--auth-mode", choices=sorted(SUPPORTED_AUTH_MODES), required=True)
    parser.add_argument("--auth-env", help="Environment variable containing BTS token or API key.")
    parser.add_argument("--auth-file", type=Path, help="File containing BTS token or API key.")
    parser.add_argument("--bot-id", help="AI Hub Bot/App ID.")
    parser.add_argument("--bot-id-env", help="Environment variable containing AI Hub Bot/App ID.")
    parser.add_argument("--bot-id-file", type=Path, help="File containing AI Hub Bot/App ID.")
    parser.add_argument("--user-id", help="UC user ID for runtime validation.")
    parser.add_argument("--user-id-env", help="Environment variable containing UC user ID.")
    parser.add_argument("--user-id-file", type=Path, help="File containing UC user ID.")
    parser.add_argument("--sdp-app-id", default=DEFAULT_SDP_APP_ID)
    parser.add_argument("--base-url", default=PROD_API_BASE_URL)
    parser.add_argument("--endpoint", default="")
    parser.add_argument("--json", action="store_true", help="Emit JSON. Text output is the default.")
    return parser


def render_text(report: dict[str, Any]) -> str:
    lines = [
        "AI Hub API validation preflight",
        f"classification: {report['classification']}",
        f"request: {report['request_preview']['method']} {report['request_preview']['url']}",
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
    auth_value = load_optional_value(env=args.auth_env, file=args.auth_file)
    bot_id = load_optional_value(value=args.bot_id, env=args.bot_id_env, file=args.bot_id_file)
    user_id = load_optional_value(value=args.user_id, env=args.user_id_env, file=args.user_id_file)

    report = build_preflight_report(
        auth_mode=args.auth_mode,
        auth_value=auth_value,
        bot_id=bot_id,
        user_id=user_id,
        sdp_app_id=args.sdp_app_id,
        base_url=args.base_url,
        endpoint=args.endpoint,
    )
    output = json.dumps(report, ensure_ascii=False, sort_keys=True) if args.json else render_text(report)
    return (0 if report["classification"] == "api_validation_ready" else 2), output


def main(argv: list[str] | None = None) -> int:
    exit_code, output = run_cli(argv)
    print(output, file=sys.stderr if exit_code else sys.stdout)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
