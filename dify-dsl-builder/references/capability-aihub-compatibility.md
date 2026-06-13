# Capability: AI Hub Compatibility

## Operational Rules

AI Hub compatibility is fact-bound. Do not fabricate private provider IDs, component fields, permissions, credential names, tool IDs, or endpoint facts.

Preserve verified private fields from user-provided DSLs when repairing or iterating. If a required private value is missing, surface it as an assumption or gap instead of inventing it.

External research may improve Dify design and domain quality, but it cannot define private AI Hub internals.

## Static Compatibility

Static checks should cover:

1. YAML parseability.
2. `app.mode` and final output node consistency.
3. Node ID uniqueness and edge source/target existence.
4. Selector references.
5. Tool node shape, including empty configuration maps when required.
6. LLM structured output metadata and schema.
7. Code node syntax and output declarations.
8. Iteration item type and child canvas contracts.
9. Absence of unrelated old task fields in prompts and output schemas.

Static compatibility is necessary but not equal to AI Hub live success.

## Live QA Boundary

Live AI Hub QA is separate:

1. Import test proves the platform accepts the DSL.
2. Canvas open test proves the graph renders.
3. Run test proves runtime contracts, credentials, models, tools, and prompts work together.

Report these as separate evidence lines. If live QA was not run, say so directly.

## Private Tools And Providers

When a user-provided DSL contains private tool or provider metadata, preserve it unless there is a confirmed reason to change it.

When building a new DSL without verified private metadata, use only known safe public Dify structures or clearly mark private values as needing AI Hub confirmation.

Do not let external examples override AI Hub-specific field shapes observed in the user's files or validated platform evidence.

## Delivery Impact

If compatibility risk remains, include it in the validation report and final handoff. The handoff should distinguish "ready for import attempt" from "import/open/run verified".
