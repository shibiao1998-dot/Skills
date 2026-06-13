# DSL Discovery Brief

> Project: {{project_name}}
> Version: {{version}}
> App shape: workflow / advanced-chat / to be decided
> Status: discovery / aligned / generated / iterating

## 1. Business Review Layer

This layer is for the business user. Keep it in plain language and ask for approval before moving to generation.

### 1.1 What We Are Building

- One-sentence goal:
- Target user:
- When this workflow will be used:
- What the user provides:
- What the workflow returns:

### 1.2 What Good Looks Like

- Good result example:
- Bad result example:
- First-run acceptance checks:
- What the user should inspect first:

### 1.3 Recommended Direction

- Recommended Workflow Harness type:
- Why this direction fits:
- AI Hub capability route in plain language:
- What is intentionally not included:

### 1.4 Business Risk Summary

| 风险提醒 | 对你意味着什么 | 推荐下一步 |
| --- | --- | --- |
|  |  |  |

### 1.5 Alignment Gate

- Confirmed by:
- Confirmation date:
- Generation boundary:

## 2. Engineering Generation Layer

This layer is for the agent and future engineers. Keep it precise and traceable.

### 2.1 Harness Contract

- App mode: workflow / advanced-chat
- Input variables:
- Output fields:
- Conversation variables, if any:
- Versioning rule:
- Preserve-first constraints, if modifying an old DSL:

### 2.2 AI Hub Capability Strategy

- Internal tools or AI production-line particles:
- Direct components:
- Ordinary-node rebuild path:
- External API path, if contract is known:
- Missing permissions, keys, storage, or evidence:
- Main-chain AIGC route: native components / explicitly justified Tool / not applicable
- Runtime checks that static validation cannot prove:

### 2.2.1 AIGC Execution Layer Inventory

| Layer | Node Or Stage | Real Responsibility | Input Field | Output Field | Main Path Or Optional |
| --- | --- | --- | --- | --- | --- |
| Expert planning |  | story/style/prompt/constraints/quality |  |  | main |
| Media execution |  | image/3D/video/audio/speech native generation |  |  | main |
| Packaging/composition |  | concat/storage/manifest/final answer |  |  | main |

Rules:

- Expert `handoff`, `diagnostics`, or `instruction` fields are process notes, not media content.
- Media params must bind to content fields such as `prompt`, `promptLyrics`, `storyboard_prompt`, `style`, and `title`.
- For multi-shot video, keyframes or reference images are optional unless the business request requires them to block video generation.

### 2.3 Expert Role Map

| Node Or Stage | Domain Expert Role | Task | Quality Criteria | Downstream Use |
| --- | --- | --- | --- | --- |
|  |  |  |  |  |

### 2.4 External Expert Evidence

- Retrieval status: available / unavailable / not needed
- Search questions:
- Source summaries:
- Transferable principles:
- Rejected non-transferable points:
- Impact on Expert Role Map:
- Freshness risk:

### 2.5 Evidence-to-Node Mapping

| Evidence | Borrowed Design Principle | What Must Not Be Copied | Affected Node Or Stage | Confidence |
| --- | --- | --- | --- | --- |
|  |  |  |  |  |

### 2.6 Node Quality Plan

For every major LLM or Agent node:

- Node:
- Role:
- Task:
- Input interpretation:
- Output contract:
- Quality criteria:
- Constraints:
- Diagnostics:
- Downstream use:

### 2.7 Risk & Validation Matrix

| Risk | Severity | Impact | Mitigation | Validation Method |
| --- | --- | --- | --- | --- |
| Import failure |  |  |  | `validate_dify_dsl.py` |
| Model or selector mismatch |  |  |  | `--model-quality` / tool fingerprints |
| Static pass but AI Hub runtime failure |  |  | Separate static validation from import/open/run QA | AI Hub live QA |
| Agent strategy mismatch |  |  | Default FunctionCalling, do not auto-fill ReAct | `--aigc-quality` |
| Media param bound to process field |  |  | Bind media nodes only to content fields | `--aigc-quality` |
| Workflow-backed Tool used as AIGC main chain |  |  | Prefer native AIGC component nodes | `--aigc-quality` |
| Blocking image generation in video iterator |  |  | Make reference assets optional or use native video prompts | `--aigc-quality` |
| Weak prompt quality |  |  |  | `--prompt-quality` and first-run review |
| Runtime permission or credential issue |  |  |  | AI Hub run check or explicit user-provided config |
| Business output quality miss |  |  |  | Recommended first test path and feedback menu |

### 2.8 Validation Plan

- Static validation commands:
- Prompt/tool/model quality commands:
- Live AI Hub import/run plan, if requested:
- First representative input:
- Expected output fields:
- Failure classification:

## 3. Iteration Notes

- User feedback received:
- Brief changes:
- DSL version generated:
- Validation result:
