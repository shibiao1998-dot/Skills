---
name: dify-dsl-builder
description: Use when Codex is asked to clarify, create, design, modify, validate, import-test, or iterate a Dify Workflow/Chatflow DSL for AI Hub, including vague workflow ideas, uploaded requirement docs, old DSL files, AIGC workflows, internal tools, prompts, Code nodes, schemas, and Answer/End outputs.
---

# Dify DSL Builder

## Non-Negotiable Rules

1. Do not ask users to choose visible normal/professional mode; adapt depth internally.
2. Do not generate or rewrite DSL before final alignment and explicit confirmation, except narrow repair.
3. Every user-facing clarification uses exactly one question plus recommended A/B choices; do not ask broad free-form questions when options can reduce effort.
4. For vague requests, ask outcome-first before technical architecture.
5. Do not depend on local sample paths or machine-specific templates at runtime.
6. Do not expose internal process labels as user-facing wording.
7. Use Domain Expert Prompt Mode and dimension-aware decomposition for non-trivial production DSL.
8. For AIGC generation, default to AI Hub native AIGC component nodes before packaged tools.
9. Do not ask business users to choose engineering fallback policy during discovery or final alignment.
10. Formal DSL projects deliver `README.md`, versioned DSL, and `.agent/` project memory.
11. Distinguish static validation from AI Hub import/open/run QA.
12. Do not claim vNext completion without Completion Verification Gate evidence.
13. Treat user-stated source, evidence, and no-fabrication gates as workflow rules, not as reasons to ask for alternate deliverables.
14. When AI Hub runtime credentials are available, add API-level preflight and run QA to the evidence chain; keep secrets masked.
15. For AI Hub native AIGC nodes, follow model-level parameter contracts from `references/ndhy-aigc-component-fingerprints.json`: binding type, allowed values, runtime value type, and normalizer rules are part of the DSL contract.
16. New or repaired Agent nodes default to FunctionCalling: `agent_strategy_label: FunctionCalling`, `agent_strategy_name: function_calling`, `agent_strategy_provider_name: langgenius/agent/agent`. Do not default to ReAct unless the user explicitly asks for it or a runnable DSL proves it is required.
17. Media-generation params must bind to content fields, not process fields. Never bind lyrics, prompt, style, title, or visual prompt params to `handoff`, `diagnostics`, `instruction`, or similar execution-note fields.
18. AIGC main chains default to native AI Hub nodes. Do not use workflow-backed Tool nodes such as packaged image/video/music harnesses unless the user explicitly asks for them or provides a runnable export proving the contract.
19. In multi-shot video workflows, do not put high-failure image-generation nodes in the blocking path by default. Let native `video-generation` consume normalized storyboard prompts; keep keyframes, three-view images, and reference assets optional unless the requested pipeline depends on them.
20. Every AIGC DSL must expose an execution-layer inventory internally: expert/planning nodes, real media-generation nodes, stitching/packaging nodes, and the exact fields flowing from planning outputs into media params.

## User-Facing Clarification Contract

Use this shape for every clarification and final alignment that waits for the user:

1. One warm, plain-language context sentence.
2. One question at most.
3. `我的推荐：A. ... B. ...` with A as the default path.
4. A short expectation sentence: `你可以直接回复 A 或 B，也可以用一句话修正。`

Do not turn internal implementation uncertainty into a user-facing decision. For AI Hub AIGC work, assume the native image, 3D, video, audio, and speech-recognition nodes are the default implementation path until live AI Hub evidence proves otherwise.

Before sending any waiting response, fill this four-line gate mentally. If one line is missing, do not send the response.

```text
context: [one warm sentence]
question: [one business-facing question]
A: [recommended answer]
B: [valid alternate answer]
```

When local tools are available, use `scripts/run_user_turn.py` and `scripts/render_user_response.py` as the response compiler for first-turn discovery, runtime feedback, uploaded documents, old DSL repair, and final alignment. If you choose to write a waiting response manually, it must still match the compiler's shape exactly: context, one business question, `我的推荐：A. ... B. ...`, and the short expectation sentence.

High-risk discovery turns include source evidence, public lookup, original-text verification, media generation, MV/video/audio output, or any complete playable artifact. For these turns, the user-facing question must be about business use, audience, channel, or success standard. Do not add a separate technical contingency paragraph before or after that question.

For source-checked AIGC requests such as public-source lookup, original-text verification, song audio, or MV/video output, the next question must be about business scenario, audience, output channel, or success standard. Do not ask what should happen if a native AI Hub component, model, stitching step, permission, or dependency is missing. Those are internal design and validation work.

Before sending any user-facing waiting response, run this clarification firewall:

- If the draft asks the user to choose what should happen when a component, model, permission, credential, or runtime dependency is unavailable, it is invalid. Rewrite it.
- If the draft asks whether native AI Hub media components exist or whether the user has packaged equivalents for image, 3D, video, audio, or speech recognition, it is invalid. Rewrite it.
- If the draft turns the requested media artifact into a lesser substitute because of assumed implementation uncertainty, it is invalid. Rewrite it.
- If the draft is waiting for the user and does not contain `我的推荐`, `A.`, and `B.`, it is invalid. Rewrite it.
- If the draft gives only a recommendation sentence without explicit `A.` and `B.` choices, it is invalid. Rewrite it.
- If the draft uses a first-person recommendation sentence instead of `我的推荐：A. ... B. ...`, it is invalid. Rewrite it.
- If the user already states a hard quality gate, such as source verification before generation or not fabricating missing facts, record it as a business rule. Do not turn it into a user-facing failure-strategy question.
- Do not copy invalid example wording from failure references. Failure references teach what to avoid, not sentence templates.
- Convert engineering uncertainty into an internal validation assumption, not a user-facing question. Ask only for the business fact that changes the desired result.
- After a source or evidence gate, the next valid user-facing question is about use scenario, audience, output channel, or success standard. Native media component availability belongs in design and live QA, not clarification.

Correct replacement for capability uncertainty:

```text
我会按完整作品来设计，并把来源校验、歌曲音频、视频画面和最终输出链接都放进第一次验证范围。

这个作品优先服务哪类场景？

我的推荐：A. 面向短视频发布，优先可播放、完整和传播效果。 B. 面向内部审核，优先来源证据、歌词和分镜包完整。
你可以直接回复 A 或 B，也可以用一句话修正。
```

## Hard Loading Protocol

1. Read this file and the redlines above.
2. Load `references/core-design-principles.md` before DSL design or repair.
3. Classify the request as new build or repair/iteration.
4. Load exactly one journey file: `references/journey-new-build.md` or `references/journey-repair-iteration.md`.
5. Load only relevant `references/capability-*.md` files.
6. Load only symptom-relevant `references/failure-*.md` files.
7. Run validators and audits before claiming readiness.

## Default Work

For a new build, clarify until the Discovery Sufficiency Rule is met, present one final alignment in plain language, wait for confirmation, then generate and validate the project deliverables.

For repair/iteration, diagnose the failure stage, preserve business semantics by default, use narrow repair only for mechanical fixes, otherwise present one final alignment before rewriting DSL.

## Reference Map

- Core principles: `references/core-design-principles.md`
- Journeys: `references/journey-new-build.md`, `references/journey-repair-iteration.md`
- Architecture and nodes: `references/capability-workflow-chatflow-architecture.md`, `references/capability-dify-node-composition.md`
- Quality design: `references/capability-domain-expert-generation.md`, `references/capability-dimension-aware-decomposition.md`
- Contracts and compatibility: `references/capability-code-schema-variable-contracts.md`, `references/capability-aihub-compatibility.md`
- AIGC production lines: `references/capability-aigc-production-lines.md`, `references/capability-aihub-native-aigc-components.md`
- Validation and delivery: `references/capability-validation-delivery.md`, `references/capability-aihub-api-validation.md`
- Failure cases: `references/failure-canvas-rendering.md`, `references/failure-runtime-code-node.md`, `references/failure-tool-node-shape.md`, `references/failure-generated-interaction.md`, `references/failure-aigc-runtime-contract.md`

## Verification

Use `scripts/validate_dify_dsl.py` for generated DSL static checks. Static pass means the file survived known structural and contract guardrails; it does not prove publish check, model permission, private tool runtime, content safety, or media output quality. When AI Hub export opens a browser save dialog, have the user save the file, then confirm the saved YAML with `scripts/confirm_aihub_export.py` instead of waiting for an automatic browser download event. When browser upload is unstable and an explicit console token is available, use `scripts/verify_aihub_console_import.py` to preflight direct DSL import without printing the YAML or token. When internal AI Hub credentials and app identity are available, run `scripts/verify_aihub_api_preflight.py` before API-level run QA and record only masked evidence. Use `scripts/audit_vnext_completion.py` before claiming the vNext refactor is complete.
