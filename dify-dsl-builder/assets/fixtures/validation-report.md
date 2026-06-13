# Validation Report

> Project: {{project_name}}
> DSL version: {{version}}
> Date: {{date}}

## 1. Static Validation

| Check | Result | Evidence |
| --- | --- | --- |
| YAML parses | pending / pass / fail |  |
| App mode matches output node | pending / pass / fail |  |
| Node and edge references are complete | pending / pass / fail |  |
| Selectors point to available outputs | pending / pass / fail |  |
| JSON Schema is compatible | pending / pass / fail |  |
| Code nodes parse | pending / pass / fail |  |
| Tool or native component shape is valid | pending / pass / fail |  |
| Agent strategy uses FunctionCalling by default | pending / pass / fail |  |
| AIGC native component params match model contracts | not needed / pending / pass / fail |  |
| Media params bind to content fields, not handoff/diagnostics/instruction | not needed / pending / pass / fail |  |
| Workflow-backed AIGC tools are absent or explicitly justified | not needed / pending / pass / fail |  |
| Iterator AIGC nodes do not block the main media path | not needed / pending / pass / fail |  |
| Prompt residue scan is clean | pending / pass / fail |  |

Static validation does not prove AI Hub publish checks, model permission, private tool runtime, content safety, or that media nodes return usable files. Record those only under live QA.

## 2. Quality Validation

| Area | Result | Notes |
| --- | --- | --- |
| Domain expert roles | pending / pass / fail |  |
| Dimension-aware decomposition | pending / pass / fail |  |
| Input/output contract | pending / pass / fail |  |
| AIGC/native component evidence | not needed / pending / pass / fail |  |
| User-facing README usefulness | pending / pass / fail |  |

## 3. AI Hub Live QA

State live evidence separately from static checks.

| Step | Result | Evidence |
| --- | --- | --- |
| Import into AI Hub | not run / pass / fail |  |
| Canvas opens | not run / pass / fail |  |
| First representative run | not run / pass / fail |  |
| Runtime logs checked | not run / pass / fail |  |
| Output quality checked | not run / pass / fail |  |
| Native media node output checked | not run / pass / fail |  |
| Content-safety or moderation result checked | not run / pass / fail |  |

## 4. First Test Input

```json
{{first_test_input_json}}
```

## 5. Result Summary

- What passed:
- What failed:
- What remains unverified:
- Recommended next iteration:
