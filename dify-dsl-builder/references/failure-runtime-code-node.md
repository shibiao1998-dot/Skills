# Failure: Runtime Code Node

## Symptom

The DSL imports and opens, but execution fails at a Code node with syntax errors, missing key errors, JSON parse errors, wrong output type, missing `main`, or empty downstream output after a formatter failure.

## Root Cause

Typical causes include hard-throwing on optional upstream values, assuming model text is always valid JSON, mismatching declared output types, using arrays of objects directly in LLM prompts, forgetting fallback to previous Chatflow state, or defining an entrypoint that Dify does not call.

Static YAML checks do not prove Code node runtime safety.

## Prevention Rule

Code nodes should parse defensively, accept expected input variation, provide safe defaults for recoverable missing values, and serialize complex objects before downstream prompts consume them.

Raise only when continuing would produce misleading output. Chatflow modification paths should fall back to the last normalized result when parsing a modification output fails.

## Validator Or Test

Run Python syntax parsing for embedded code when possible. Inspect entrypoint name, declared outputs, selector inputs, JSON parsing branches, fallback paths, and type conversions.

For live QA, run the affected path in AI Hub and report runtime evidence separately from static validation.
