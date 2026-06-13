# Capability: AI Hub Native AIGC Components

## Default Rule

AI Hub already exposes native AIGC component nodes for image generation, 3D resource generation, video generation, audio generation, and speech recognition.

When an AIGC request fits one of these component families, build the DSL with the native node type by default. Do not ask the user to provide a packaged tool, imported harness, provider ID, or workflow-backed tool unless the requested behavior is outside the native component contract.

Treat these five families as available design primitives during planning. Do not ask the user to provide packaged equivalents or decide contingency handling before DSL generation. If live import/open/run later proves a native node, permission, credential, or storage path is unavailable, handle it as runtime repair evidence and ask only for the missing factual input that cannot be inferred.

Capability uncertainty is not a business clarification question. If the agent is unsure about a native component's exact selector, model version, or runtime availability, it must verify through AI Hub evidence when possible, use only verified component contracts in the DSL, and report any unresolved runtime check separately. It must not ask the user to choose a reduced artifact because of that uncertainty.

## Native Node Families

| User intent | Node type | Stable selector evidence | Typical output selector |
| --- | --- | --- | --- |
| Generate or edit images | `image-generation` | `model_info.model_id` such as `gpt-image-2-t2i` or `jimeng-seedream-4.5-img2img` | `images` as `array[file]` |
| Generate 3D resources | `model-3d-generation` | `hunyuan-3d-3.1-pro-text` for the `文生3D模型` tab | `models` as `array[file]` |
| Generate videos | `video-generation` | Use only selectors with runnable canvas/export evidence. A saved canvas export on 2026-05-27 showed UI label `即梦 3.5 Pro 文生视频` exports as `jimeng-seedance-1.5-pro-text2video` with param `camera_fixed`. Do not write stale `jimeng-3.5-pro-text2video` or `camerafixed` directly. | `videos` as `array[file]` |
| Generate audio or TTS | `audio-generation` | `seed-tts-2.0`, `kling-v2a`, or `suno-v5-music_generate` for Suno V5 music | `audios` as `array[file]` |
| Recognize speech | `speech-recognition` | Use exported selector `doubao-asr-speech2text` (`豆包语音识别`). Do not write model-list id `volc.seedasr.auc` directly; it imported with `模型信息加载失败` in the current AI Hub workspace. | `text`, `duration`, `utterances` |

Use the exported canvas selector as `model_info.model_id`; do not copy public model-list names into direct component nodes. AIGC model cards may not expose the same version field as LLM cards.

Keep user-visible diagnostics and packaging code consistent with the actual component selector. If the native node uses `jimeng-seedance-1.5-pro-text2video`, downstream Code nodes, `diagnostics_json`, `selected_model`, and `selected_model_note` must not mention stale catalog or canvas-only ids such as `jimeng-3.5-pro-text2video`.

A selector that is merely visible in the dropdown is not enough. The evidence ladder is:

1. Dropdown visible: useful only for exploration.
2. Node selected and canvas saved: proves the UI can hold the model, but not that hand-written DSL can reproduce it.
3. Saved canvas exported to DSL: proves the exact `model_info`, `params`, and capability tab contract.
4. Exported DSL re-imported and opened without `模型信息加载失败`: minimum evidence for documenting a production-safe selector.
5. First run returns usable media output or a clear runtime diagnostic: minimum evidence for delivery confidence.

AI Hub export may be mediated by the browser save dialog. If clicking `导出 DSL` does not produce an automatic download event, do not immediately treat it as export failure. Ask the user to confirm/save the browser prompt, then inspect the actual save directory and use the newest matching `.yml` export as evidence. Prefer `scripts/confirm_aihub_export.py --dir <save-dir> --name-contains <app-name>` to record the path, modified time, file size, SHA256, and duplicate count before using the export.

If automation can select a model and save the canvas but cannot obtain the exported DSL, do not backfill the missing YAML by guessing. Quarantine that selector and continue with a verified alternative or report the export evidence gap separately.

## Common Node Shape

Native AIGC nodes use this core shape:

```yaml
data:
  type: image-generation
  title: 生成图像资产
  model_info:
    config_version: v1
    model_id: gpt-image-2-t2i
    model_name: GPT Image 2.0 文生图
    provider: openai
    provider_name: OpenAI
  params:
    prompt:
      type: variable
      value_selector: [normalize_request, prompt]
```

Each `params` entry is either:

- `type: variable` with a `value_selector` from Start, LLM, or Code output.
- `type: constant` with a stable scalar value.

Parameter binding is semantic, not only structural. Content params such as `prompt`, `promptLyrics`, `promptDescription`, `style`, `title`, `negativeTags`, image prompts, and video prompts must bind to fields that contain the actual user-facing media content. Do not bind them to process fields such as `handoff`, `diagnostics`, `instruction`, `quality_checklist`, or `risk`. If an expert node produces both an execution note and media content, expose separate fields such as:

```yaml
outputs:
  storyboard_prompt:
    type: string
  promptLyrics:
    type: string
  execution_handoff:
    type: string
```

Then bind native media params only to `storyboard_prompt`, `promptLyrics`, `style`, `title`, or similarly dedicated content fields.

## Parameter Floors

Use the exact parameter names required by the selected model. Common floors:

- `image-generation`: `prompt`; text-to-image commonly also uses `size`, `quality`, `n`, `output_format`, `background`, `enable_cs_transfer`.
- `image-generation` image-to-image: `prompt`, `images`, `size`, `max_images`, `watermark`, `sequential_image_generation`, `enable_cs_transfer`.
- `model-3d-generation` text-to-3D: use the exported selector `hunyuan-3d-3.1-pro-text` with exact param keys `Prompt`, `GenerateType`, `EnablePBR`, `FaceCount`, `ResultFormat`, and `enable_cs_transfer`. These keys are case-sensitive. A live AI Hub export on 2026-05-27 showed `GenerateType: Normal`, `FaceCount: 500000`, `EnablePBR: false`, and `ResultFormat: null` as the valid `文生3D模型` shape. For downstream packaging, bind only `models` as `array[file]`; do not bind `resources` or `files` in generated DSL until a fresh run/export proves they are accepted, because the 2026-05-27 canvas marked those bindings invalid in variable check. Do not write stale lowercase keys such as `prompt`, `generation_mode`, `image_url`, or `white_model` for this selector. Do not use the retired `3d-resource-generation` type: a live AI Hub import on 2026-05-27 dropped that node from the workflow canvas.
- `video-generation`: `prompt`, `duration`, `ratio`, `resolution`, `seed`, `watermark`, `return_last_frame`, `enable_cs_transfer`; add model-specific params only from observed export evidence. For `jimeng-seedance-1.5-pro-text2video`, include `camera_fixed` and `generate_audio`.
- `audio-generation` TTS: `text`, `speaker`, `style_prompt`, `audio_params_format`, `audio_params_speech_rate`, `enable_language_detector`, `enable_cs_transfer`.
- `audio-generation` video audio: `video_url`, `video_input_type`, `sound_effect_prompt`, `bgm_prompt`, `asmr_mode`, `enable_cs_transfer`.
- `audio-generation` Suno V5 music: use exported selector `suno-v5-music_generate`, include `customMode`, `instrumental`, `promptLyrics`, `promptDescription`, `style`, `title`, `negativeTags`, `styleWeight`, `weirdnessConstraint`, `audioWeight`, and `enable_cs_transfer`. The `instrumental` switch must be a boolean constant in simple BGM/song workflows. AI Hub Code nodes cannot declare boolean outputs, so do not bind this switch to Code output. If the same workflow must dynamically choose pure music vs vocal music, split with IF/ELSE and use two native Suno nodes with constant `instrumental: true` and `instrumental: false`.
- Suno V5 field limits are runtime-enforced. Keep `negativeTags` at or below 200 characters; normalize to about 180 characters to leave room for punctuation and model-side validation.
- `speech-recognition`: for the verified `doubao-asr-speech2text` URL-input shape, include `audio_file: null`, `audio_source: url`, `audio_url`, `audio_format: mp3`, and `language: ""` for automatic recognition. The old `audio_input_type` key and dynamic `language` selector caused the canvas to show `模型信息加载失败` / `[object Object]` after import; do not use that stale shape without a fresh saved export proving it works.

## Model-Level Parameter Contracts

Do not treat native AIGC params as generic key-value fields. Each model can restrict whether a parameter accepts a variable binding, which constant values are valid, and what runtime scalar type is accepted. Load `references/ndhy-aigc-component-fingerprints.json` and follow each model's `param_contracts` before writing DSL.

Known hard contracts:

- `jimeng-seedance-1.5-pro-text2video.duration`: constant only. Runtime accepts `-1` or string values `"4"` through `"12"`. Do not pass `"18"` or bind business duration as a variable.
- `jimeng-seedance-1.5-pro-text2video.ratio` and `resolution`: constant only. Normalize channel and resolution before the node; do not bind them to Code output, because the AI Hub canvas reports invalid variables for these fields.
- `jimeng-seedance-1.5-pro-text2video.prompt`: may be a variable from a prompt-normalization node.
- `suno-v5-music_generate.vocalGender`: constant only; allowed values are `""`, `"m"`, and `"f"`. Map `男/男声/male` to `"m"`, `女/女声/female` to `"f"`, and pure music/no vocal to `""`. Never pass Chinese values directly.

For requested 45-60 second video outputs, do not make long per-node durations such as `3 x 18`. Use `max_segment_duration=12` and generate enough native video segments to cover the target duration, for example `5 x 12` for a 60-second first-pass plan. If the current implementation intentionally keeps three segments for a quick run-through, report it as an approximately 36-second run-through version rather than claiming 45-60 seconds.

Image sizing is a production parameter, not just a prompt detail. If the user states a ratio or channel in natural language, normalize it deterministically before the native node instead of passing `auto` by default:

- `16:9`, `4:3`, `landscape`, `wide`, `横版`, `封面`, `课件`, `投屏`, `PPT` -> `1536x1024`.
- `9:16`, `portrait`, `竖屏`, `竖版`, `抖音`, `快手`, `Reels`, `Stories` -> `1024x1536`.
- `1:1`, `square`, `方图`, `正方形`, `头像`, `logo` -> `1024x1024`.
- `3:4` -> `1024x1536`.

Use explicit Start parameters first, then planner output if it is concrete, then infer from `image_brief` and `output_use`. Record the source in diagnostics as `explicit`, `planned`, `brief_inferred`, `explicit_auto`, or `auto`.

## Composition Pattern

Use this production pattern for each media component:

1. LLM node produces focused expert planning: prompt, style, constraints, and quality checklist.
2. Code node normalizes params into primitive strings, numbers, arrays, and diagnostics.
3. Native AIGC node performs generation or recognition.
4. Code node unwraps `array[file]` or recognition output into stable fields such as `image_url`, `video_url`, `audio_url`, `model_url`, `transcript_text`, package JSON, and raw response JSON.
5. End or Answer node exposes the user-facing contract.

Do not collapse creative planning, parameter normalization, component execution, and output packaging into one LLM node.

For video workflows, keep the main chain robust. If native `video-generation` can create the requested segment from text, feed it the normalized storyboard prompt directly. Put keyframe image generation, character reference boards, and three-view assets into optional/reference branches unless the requested effect explicitly depends on them. This reduces the number of AIGC calls that can block the first usable video.

## Fallback Rule

If a requested effect cannot be expressed by the five native component families, explain the missing capability in plain language and design the closest viable native-node workflow first. Ask for an existing internal tool only when it is truly necessary for the missing capability, not as the default path.

Do not ask the user to choose a technical handling policy if a native component is unavailable. Default to a production-grade contract: generate with the native node, package clear diagnostics, and report live AI Hub import/open/run status separately. Ask the user only for missing business facts, credentials, or permissions that are truly required to run the workflow.
