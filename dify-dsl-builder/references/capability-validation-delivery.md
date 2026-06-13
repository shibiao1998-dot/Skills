# Capability: Validation And Delivery

## Operational Rules

Validation evidence must precede readiness claims.

Run static validators before delivery whenever a DSL file is generated or repaired. Run live AI Hub import/open/run QA only when access, credentials, and user scope allow it.

Never merge static validation and live QA into one vague statement.

Static validation proves only the local DSL contract covered by the validator. It does not prove AI Hub publish checks, model permission, private workflow-backed tool permission, content safety, node-side moderation, or that media generation returns usable output. Report those as live QA items.

When runtime credentials and app identity are available, add AI Hub API preflight before browser or API run QA. Use `scripts/verify_aihub_api_preflight.py` and record masked evidence only.

## Static Validation Checklist

Check at minimum:

1. YAML parses.
2. App mode matches final output node type.
3. Node IDs are unique.
4. Every edge source and target exists.
5. Selectors reference existing outputs, `conversation`, or `sys`.
6. JSON Schema uses compatible object and array shapes.
7. Code nodes parse and expose the declared outputs.
8. Tool nodes include required shape fields.
9. Iteration item type and child canvas contracts are consistent.
10. Answer or End output references exist.
11. Prompt text has no unrelated task residue.
12. Non-trivial production DSL has expert prompts and dimension-aware decomposition.
13. Agent nodes use FunctionCalling by default unless ReAct is explicitly justified.
14. AIGC media params bind to content fields, not process fields such as `handoff`, `diagnostics`, or `instruction`.
15. AIGC main chains use native component nodes by default instead of workflow-backed Tool nodes.
16. Iterator-contained AIGC nodes do not add avoidable blocking failure points to the first usable output path.

## Live QA Checklist

When live AI Hub access is available, record separately:

1. Import result.
2. Canvas open result.
3. First run result.
4. Runtime error logs if any.
5. Output quality observations against the success standard.
6. Media-node result status, including moderation/content-safety failures and empty file outputs.

If API-level QA is available, record separately:

1. Preflight classification.
2. Masked header preview.
3. API host and endpoint.
4. HTTP status and AI Hub response identifiers.
5. Runtime result or structured error summary.

For DSL export checks, account for Chrome's manual save prompt. A missing automatic download event is not enough to conclude that export failed. Confirm whether the browser asked for a save location, then inspect the user-selected folder and hash the newest exported `.yml` before using it as evidence. Use `scripts/confirm_aihub_export.py` for this confirmation whenever the local filesystem is available.

If live QA is skipped, state the reason and the exact first test the user should run.

## Delivery Package

For formal projects, deliver a user-facing `README.md`, a versioned DSL file, and agent-facing `.agent/` memory with discovery, build log, and validation report.

For narrow repair, a lighter package is acceptable, but still write a versioned DSL by default and report what changed, what was preserved, and what was verified.

Do not paste large DSL content into chat unless the user asks. Give file paths and concise handoff notes.

## Final Handoff

Final handoff should include:

1. File paths.
2. App mode.
3. Preserved or created inputs and outputs.
4. New capability or repair summary.
5. Static validation results.
6. AI Hub live QA status.
7. Remaining risks or dependencies.

If live QA is not run, write that plainly, for example: `Static validation passed; AI Hub import/open/run was not executed in this session.` Do not shorten that into `ready` or `verified`.
