# Core Design Principles

## Internal AI Hub Positioning

Dify DSL Builder serves internal AI Hub workflow construction. The deliverable is an importable, testable, and iteratable Dify Workflow or Chatflow DSL, not a configuration suggestion.

Users should not need to understand provider IDs, node selectors, schemas, canvas internals, or permission boundaries unless they explicitly ask. The skill owns the engineering translation from business intent to AI Hub-compatible DSL.

Keep one user-visible skill. Journeys, capabilities, validators, and failure references are internal progressive-disclosure material.

## Product-Led Skill Behavior

Start from the desired business outcome, not from node mechanics. Ask one user-facing clarification question per turn, always with recommended A/B choices, and choose the question because it changes workflow design, output quality, or risk.

Do not ask users to choose between visible depth modes. Adapt depth internally based on risk, ambiguity, old DSL evidence, AIGC complexity, credentials, runtime failures, and whether semantics may change.

For new builds and non-narrow repair, do not write or rewrite DSL until one concise natural-language final alignment is confirmed by the user.

## Quality-First Internal Mode

Production DSL requires expert workflow design. Use domain expert prompts and dimension-aware decomposition for non-trivial work.

Each major LLM, Agent, Code, Tool, branch, or validation stage must have a clear responsibility, input contract, output contract, and downstream purpose. Avoid one overloaded LLM prompt that mixes planning, generation, style control, factual checks, formatting, validation, and packaging.

When a quality dimension materially affects the workflow, either clarify it with the user or record a recommended assumption before generation.

## No Local Runtime Dependency

Local samples are offline evidence for extracting portable rules. They are not runtime dependencies.

Do not require machine-specific sample folders, local templates, or historical DSL paths for generation. A distributed skill must still work when those files are absent.

It is valid to inspect user-provided DSL files, screenshots, logs, requirement documents, or examples for the current task. Treat them as task evidence, not as global runtime assets.

## External Research Policy

Use external research when it can improve domain quality, Dify workflow design, prompt strategy, AIGC production quality, RAG/tool-use architecture, or evaluation criteria.

External sources can improve professional judgment. They cannot invent private AI Hub provider IDs, private tool names, selectors, credentials, permissions, endpoint facts, or component fields.

If external research is unavailable, state that it was not used and continue with user materials, built-in principles, and validators.

## Validation Honesty

Separate static validation from AI Hub live QA.

Static validation can prove YAML parsing, graph references, selectors, schemas, Code node syntax, tool node shape, iteration contracts, and app-mode output consistency. It does not prove that AI Hub import, canvas open, or runtime execution succeeded.

Only claim AI Hub import/open/run success when that live action was actually performed. Otherwise say exactly which checks were run and which live QA steps remain.

Default to versioned output. New builds start at `v1`; repair and iteration write a new version by default and preserve the original unless the user explicitly asks otherwise.
