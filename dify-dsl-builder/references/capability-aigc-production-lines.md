# Capability: AIGC Production Lines

## Operational Rules

AIGC workflows are production lines inside Workflow or Chatflow shapes. They are not a separate app mode.

Design AIGC DSL as staged production: normalize intent, plan assets, generate or retrieve materials, call AI Hub native AIGC component nodes, review quality, and package outputs.

The default implementation path is native AI Hub AIGC components, not packaged tools. Do not ask the user whether they have an existing tool for image, 3D, video, audio, or speech-recognition generation when a native component can express the work.

Only use a Tool node when the workflow needs a capability outside the native component contract, such as proprietary post-processing, storage, orchestration, moderation, or a previously verified internal harness that the user explicitly wants to preserve.

Workflow-backed media tools are not interchangeable with native components. Their parameters, permissions, input file format, moderation path, and runtime errors can diverge from static DSL shape. AIGC main chains must use native `image-generation`, `model-3d-generation`, `video-generation`, `audio-generation`, or `speech-recognition` nodes unless verified evidence or an explicit user request says otherwise.

Do not invent private media providers, tool IDs, credentials, storage buckets, permissions, or component fields. Preserve verified values from user materials. If runtime evidence shows a missing dependency, record it in the validation or live QA report; ask the user only for a specific credential, file, permission, or business boundary that cannot be inferred.

## Production-Line Stages

Choose only the stages the task needs:

1. Input normalization: topic, audience, duration, language, style, constraints, and materials.
2. Concept or script planning: story, shot list, prompt set, narration, interaction logic, or learning flow.
3. Asset preparation: images, audio, subtitles, style references, uploaded files, or retrieved knowledge.
4. Native component calls: image generation, 3D resource generation, video generation, audio generation, or speech recognition.
5. Quality review: factual, style, safety, consistency, duration, and completeness checks.
6. Final packaging: links, file manifests, JSON, Markdown, or user-facing instructions.

Separate creative planning from component execution. A generation node should receive a well-formed prompt and parameter set, not a vague all-purpose instruction.

Every AIGC workflow should keep a clear execution-layer inventory:

| Layer | What It Contains | Required Evidence |
| --- | --- | --- |
| Expert planning | Domain expert LLM/Agent nodes for story, style, constraints, prompts, storyboard, quality goals | Structured outputs and downstream field names |
| Media execution | Native image/3D/video/audio/speech nodes that actually generate or recognize media | Exact model selector, params, output selector |
| Packaging or composition | Code, aggregator, subtitle, stitching, storage, Answer/End nodes | Final fields, links, manifests, diagnostics |

The user should be able to see that expert planning drives real media nodes through named content fields. Do not hide the only important logic inside an opaque handoff string.

For image workflows, do not let clear aspect-ratio or channel requirements disappear when optional form fields are empty. If the business brief says `16:9`, `9:16`, `封面`, `课件投屏`, `竖屏`, or similar channel language, the parameter-normalization Code node should convert that requirement into a concrete native-node `size` and expose the decision in diagnostics.

For node-level contracts, load `references/capability-aihub-native-aigc-components.md`.

For video workflows, distinguish the user's target duration from the native model's per-call duration enum. If the selected model caps a segment at 12 seconds, plan multiple generation calls or an iteration with `max_segment_duration=12`. A 45-60 second target should be decomposed into enough segments, not forced into invalid values such as `18`.

For multi-shot videos, do not default to a blocking image-generation step inside the iterator. Native `video-generation` should consume a normalized per-shot video prompt directly. Character three-view images, keyframes, or style boards are optional/reference assets unless the user explicitly requires image-gated video generation.

Media params must bind to content fields. Do not bind lyrics, image prompts, video prompts, style, title, or negative prompts to `handoff`, `diagnostics`, `instruction`, `quality_checklist`, or other process fields. A `handoff` field can tell a downstream node what to do; it is not the media content itself.

## Domain Expertise

AIGC production needs domain expert roles such as creative director, storyboard designer, instructional designer, sound designer, post-production editor, or quality reviewer.

The expert role must match the artifact. A classroom activity video, brand campaign image set, and interactive game script need different planning dimensions and evaluation criteria.

## External Research

Use external research for style, genre, domain expectations, media quality standards, or Dify/AIGC best practices when available.

Do not use research to invent private AI Hub permissions, provider IDs, internal tools, or guaranteed runtime behavior.

If research or model knowledge is uncertain, keep the user-facing path outcome-led: design the best native-node production line, state the first-run verification plan plainly, and avoid asking the user to choose an engineering contingency.

## Validation

Validate both DSL structure and production-line logic:

1. Required materials are represented as inputs or documented dependencies.
2. Native component params match verified component contracts.
3. Media params bind to content fields rather than process fields.
4. Workflow-backed AIGC tools are absent from the main chain unless explicitly justified.
5. Iteration branches do not add avoidable blocking AIGC failure points.
6. Generated outputs have stable names and selectors.
7. Media links, file outputs, or manifests are passed in consumable form.
8. Static validation and live AI Hub run status are reported separately.
