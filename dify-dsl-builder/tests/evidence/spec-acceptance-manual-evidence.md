# Dify DSL Builder vNext Manual Acceptance Evidence

## Criteria Covered By Manual Evidence

- Criterion 24: Completion cannot be claimed until Legacy Audit Manifest check, Interaction Regression, DSL Structural Regression, and Spec Acceptance Audit have run or have manual evidence with explicit residual risks.

## Evidence

- Legacy Audit Manifest check: `python3 scripts/audit_vnext_completion.py` returned `vNext completion audit passed`.
- Interaction Regression: `scripts/audit_vnext_completion.py` executed all JSON scenarios under `tests/scenarios/interaction/` through `scripts/run_user_turn.py`; all required/forbidden text checks passed.
- DSL Structural Regression: `python3 scripts/validate_dify_dsl.py tests/scenarios/dsl-structural/tool-missing-config.yml` failed with the expected `tool_configurations` error only.
- Spec Acceptance Audit: `tests/spec-acceptance-vnext.json` covers exact criterion IDs 1-28 and is checked by `scripts/audit_vnext_completion.py`.
- 2026-05-27 AI Hub AIGC selector QA: `e2e-runs/2026-05-27-idiom-video-native/live-aihub-export-evidence.md` records that browser automation did not receive an automatic download event because Chrome prompted for a manual save location. After the user saved the file, `scripts/confirm_aihub_export.py` found the exported DSL under the configured local export directory, reported its path and SHA256, and showed duplicate saved exports with the same hash. The export was then re-imported into AI Hub, opened without `模型信息加载失败`, and produced a usable `video_url` in a live run. This selector is now documented as production-safe with saved-export evidence.
- 2026-05-27 AI Hub native music QA: `e2e-runs/2026-05-27-music-native/runtime-limits-fix.md` records a live AI Hub import and run of `aigc-music-audio-workflow.yml`. The imported app opened with `Suno V5 / Suno · 音乐生成`, no model load failure, no packaged tool node, and returned `status: success` plus a usable `audio_url`. This run also captured the fixes for `suno-v5-music_generate`, Code node output type limits, and Suno `negativeTags` length limits.

## Residual Risks

- Live AI Hub import/open/run QA is not included unless explicitly executed in this task.
- Static validation can catch known structural DSL issues but cannot prove private AI Hub tool permissions, API keys, or workspace-specific model availability.
- UI model selection alone is partial evidence. AIGC selectors require saved export plus re-import/open evidence before production-safe documentation. If Chrome prompts for a save location, the saved local file can satisfy the export evidence once its path and hash are recorded.
