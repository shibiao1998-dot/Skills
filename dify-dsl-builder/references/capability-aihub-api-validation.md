# Capability: AI Hub API Validation

## Purpose

Use API-level validation as an internal QA path when AI Hub runtime credentials and scope are available. This is for the agent and reviewer, not a business-user discovery step.

The API path complements browser import/open/run QA. It does not replace DSL static validation, and it must not become a reason to ask business users for engineering choices during discovery.

## Internal Inputs

Accept runtime identity from environment variables or user-provided local files. Do not paste values into chat, project README, generated DSL, or evidence logs.

Required for API preflight:

1. Auth mode: `bts` or `api-key`.
2. Auth value: BTS token or API key.
3. AI Hub Bot/App ID for the imported app.
4. UC user ID for request headers.
5. `sdp-app-id`; default to `b4fb92a0-af7f-49c2-b270-8f62afac1133` unless the user or internal docs provide another value.
6. API host and endpoint for the target app mode.

Known production hosts from internal docs:

- API: `https://ai-hub-api.aiae.ndhy.com`
- Web: `https://ai-hub.ndhy.com`

## Header Contract

Build request previews with these headers:

```text
Authorization: BTS <masked>        # for BTS mode
Authorization: Bearer <masked>     # for API-key mode
X-App-Id: <masked Bot/App ID>
Userid: <masked UC user ID>
sdp-app-id: b4fb92a0-af7f-49c2-b270-8f62afac1133
Content-Type: application/json
```

Only log masked previews. A valid evidence record can include value length and hash prefix, never raw values.

## Preflight Procedure

Run `scripts/verify_aihub_api_preflight.py` before any API-level run test.

Example shape:

```bash
python3 scripts/verify_aihub_api_preflight.py \
  --auth-mode bts \
  --auth-file /path/to/local/bts.txt \
  --bot-id-env AIHUB_BOT_ID \
  --user-id-env AIHUB_USER_ID \
  --endpoint /v1/workflows/run \
  --json
```

If the script returns `api_validation_ready`, API-level run validation may proceed with the confirmed endpoint and request body.

If it returns `environment_preflight`, record the named fields as QA prerequisites and continue with static validation and browser QA. Do not classify this as a DSL design failure.

## Console Import Diagnostic

When the browser upload channel is unstable, and the user explicitly provides an AI Hub console token or a safe environment variable containing it, preflight direct DSL import with `scripts/verify_aihub_console_import.py`.

The observed console import request shape is:

```text
POST https://ai-hub-api.aiae.ndhy.com/console/api/apps/imports
Authorization: Bearer <masked console token>
Content-Type: application/json
body.mode: yaml-content | yaml-url
```

Use `yaml-content` for a local DSL file and `yaml-url` for an HTTP(S) URL that AI Hub can reach. Do not use `file://` URLs for server-side import.

The preflight report may include YAML byte length and SHA-256. It must not print the YAML content or console token.

Use explicit execution only after confirming the token is intended for console import:

```bash
python3 scripts/verify_aihub_console_import.py \
  --yaml-path /path/to/app.yml \
  --console-token-file /path/to/console-token.txt \
  --execute \
  --json
```

If execution returns `console_import_failed`, keep the HTTP status and response summary as environment evidence. Do not mark the DSL invalid unless the response points to YAML structure or import parsing.

## Endpoint Discipline

Do not invent endpoint paths. Use the internal API document, imported app metadata, or a previously verified request sample. When the endpoint is not confirmed, preflight can still validate credentials and headers, but the API run itself remains pending.

For Chatflow/Bot calls, expect a chat-message style request body. For Workflow calls, expect a workflow-run style request body. Confirm the exact path and payload from the internal docs before executing.

## Project Key Use

Project Key and model authorization explain whether an imported app can call models and AI Hub components. Treat Project Key status as runtime environment evidence.

When Project Key context is available:

1. Record the app or bot binding status in the validation report.
2. Use it to explain model/component authorization failures.
3. Do not require business users to decide implementation paths because of authorization mechanics.

## Evidence Rules

Evidence may include:

- Preflight classification.
- Masked header preview.
- API host and endpoint.
- Request mode: chat or workflow.
- HTTP status, response event type, message ID, workflow run ID, or error code.
- Runtime result quality notes.

Evidence must not include:

- Raw BTS token.
- Raw API key.
- Full user identity token.
- Private Project Key value.
