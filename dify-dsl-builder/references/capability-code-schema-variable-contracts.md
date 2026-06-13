# Capability: Code, Schema, And Variable Contracts

## Operational Rules

Treat Code, JSON Schema, selectors, and variables as hard contracts. Flexible design ends where runtime shape begins.

Prefer structured parsing over string slicing. Prefer defensive defaults over hard crashes when upstream model output is missing or malformed.

## JSON Schema

For Dify LLM structured output, use basic JSON Schema that AI Hub can consume:

1. Root `type` is `object`.
2. Every object has `type`, `properties`, `required`, and `additionalProperties`.
3. Every array has `items`.
4. Avoid `$ref`, `oneOf`, `anyOf`, `allOf`, and conditional schema features.
5. Avoid `boolean`, `null`, and platform-ambiguous types when AI Hub compatibility is uncertain.
6. Use string enums such as `"true"` and `"false"` when a truth value must be represented safely.

Only expose fields that downstream nodes can consume reliably.

## Variable Selectors

LLM prompt variables should directly reference only strings, numbers, or arrays of strings.

When downstream prompts need objects, arrays of objects, arrays of numbers, or files, convert them first with Code using `json.dumps(..., ensure_ascii=False, indent=2)` or another explicit serialization step.

Validate every `value_selector`, `variable_selector`, `query_variable_selector`, and condition selector against existing node outputs, `conversation`, or `sys`.

## Code Nodes

Code nodes should define the entrypoint expected by Dify, normally `main`.

Validate syntax locally when possible. Also inspect runtime risks that syntax cannot catch: missing keys, wrong item types, non-JSON model text, empty planner output, and output values whose declared type does not match the node contract.

AI Hub Code node output declarations accept only `string`, `number`, `object`, `array[string]`, `array[number]`, and `array[object]`. Do not declare `boolean`, `file`, or `array[file]` as Code outputs. For boolean-like decisions, output `"true"` or `"false"` strings; when a downstream native AIGC component requires an actual boolean parameter, use a constant boolean or split with IF/ELSE into branches that each use a constant.

Use safe parsing:

1. Accept strings, dicts, and empty values when upstream shape may vary.
2. Fall back to previous conversation output when a Chatflow modification formatter fails.
3. Return stable empty arrays or objects instead of raising for recoverable missing optional content.
4. Raise only when continuing would produce misleading output.

## Conversation Variables

Chatflow state should store normalized strings or JSON strings when possible.

Common useful variables include last output text, last result JSON, project name, parent project name, skill or evidence content, and decision trace. Use names that match the local DSL style and preserve existing variables during repair.

Modification branches should use the user's latest `sys.query` plus prior normalized state, then output a complete updated result.

## Contract Checks

Before delivery, check schema validity, selector existence, Code syntax, output type declarations, Answer or End references, and any conversion needed before LLM prompts.
