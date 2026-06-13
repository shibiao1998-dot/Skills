# Failure: AIGC Runtime Contract

## Symptom

The DSL passes local static validation, but AI Hub fails during publish checks, canvas opening, model parameter validation, private Tool execution, content safety, or first media generation.

Examples:

- Agent node imports without a usable strategy, or is patched to ReAct when the workflow needs stable tool calling.
- A Suno field such as `promptLyrics` receives an execution handoff instead of lyrics.
- A native video parameter such as `duration`, `ratio`, or `resolution` is bound as a variable when the selected model accepts only constants.
- A workflow-backed image/video/music Tool imports but fails at runtime because its private harness contract is unavailable or different from the generated shape.
- A multi-shot video iterator fails before the video node because a keyframe image-generation step is blocking the main path.

## Root Cause

Static YAML validation covers file structure and known local contracts. It cannot prove the full AI Hub runtime contract: publish checks, model permissions, private tool permissions, content safety, media-node execution, or output quality.

The common design mistake is treating all generated fields as interchangeable strings. Expert nodes produce both process notes and content. Media nodes need content fields, not handoff or diagnostics fields.

## Prevention Rule

Use these defaults for generated AI Hub DSL:

1. Agent nodes default to FunctionCalling:

   ```yaml
   agent_strategy_label: FunctionCalling
   agent_strategy_name: function_calling
   agent_strategy_provider_name: langgenius/agent/agent
   ```

2. AIGC main chains default to native AI Hub component nodes, not workflow-backed Tool nodes.
3. Media params bind only to dedicated content fields such as `prompt`, `promptLyrics`, `storyboard_prompt`, `style`, and `title`.
4. `handoff`, `diagnostics`, `instruction`, `quality_checklist`, and risk fields are process fields. Do not bind them to lyrics, visual prompts, titles, or styles.
5. For multi-shot video, native `video-generation` should consume normalized storyboard prompts directly. Keyframes, three-view images, and reference boards are optional/reference branches unless explicitly required.
6. Report static validation and AI Hub live QA as separate evidence. Do not claim runtime readiness from static validation alone.

## Validator Or Test

Run:

```bash
python3 scripts/validate_dify_dsl.py --aigc-quality path/to/app.yml
```

The AIGC quality pass checks model-level parameter contracts, default Agent strategy, semantic media-field bindings, workflow-backed AIGC tools in the main chain, and blocking image-generation steps inside video iterators.

Live QA still needs AI Hub import/open/run evidence when credentials and scope are available.
