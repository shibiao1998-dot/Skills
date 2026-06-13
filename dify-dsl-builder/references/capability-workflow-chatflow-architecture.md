# Capability: Workflow And Chatflow Architecture

## Operational Rules

Choose app shape internally from the interaction contract.

Use `app.mode: workflow` when the task is a single-run API style process, batch generation, report creation, structured transformation, or an upstream automation step. Workflow normally ends with an `end` node.

Use `app.mode: advanced-chat` when the user needs iterative conversation, follow-up natural-language edits, saved previous output, or multi-turn refinement. Chatflow ends with `answer` nodes and uses conversation variables when prior state matters.

Workflow and Chatflow are app shapes. AIGC, RAG, Agent, Tool use, content generation, and media production are capability domains inside those shapes.

Do not ask the user to choose an engineering depth or internal app label when the business goal is enough to decide. Explain the chosen direction in the final alignment only in business language.

## Workflow Shape

Common Workflow skeleton:

1. Start inputs.
2. Optional Code node for time, normalization, or search terms.
3. Retrieval or Tool nodes when external facts are needed.
4. Branching for materially different business cases.
5. LLM or Agent stages with domain expert prompts.
6. Code or LLM formatter for schema normalization.
7. End node with preserved output semantics.

Avoid conversation variables in Workflow unless a user-provided sample requires a special platform behavior.

## Chatflow Shape

Common Chatflow skeleton:

1. Start inputs plus system query.
2. Branch for first generation vs natural-language modification.
3. First generation path builds context, performs expert generation, formats output, saves state, and answers.
4. Modification path reads previous state plus `sys.query`, applies the change, formats a complete output, updates state, and answers.

Prefer a conversation variable such as `conv_last_output_text` to detect whether a previous result exists. Do not rely only on a project name field to distinguish first generation from modification.

Every modification answer should output the complete current result, not only a diff, unless the user explicitly asks for diff-only behavior.

## Output Consistency

Workflow uses End outputs. Chatflow uses Answer nodes. Do not deliver a Chatflow that relies on End as the user-visible final response.

Preserve original output field semantics during conversion or repair. If a Workflow produced `result`, the Chatflow should still expose a `result`-equivalent field even when adding fields such as `decision_trace`.

Use static validation to confirm node IDs, edges, selectors, output node type, and mode consistency before delivery.
