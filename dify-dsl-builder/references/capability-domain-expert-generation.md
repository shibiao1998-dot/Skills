# Capability: Domain Expert Generation

## Operational Rules

Production DSL requires domain expert prompting. Each important LLM or Agent node should operate from a concrete expert role, not from a generic assistant stance.

Define the expert role from the business domain and artifact: product strategist, curriculum designer, video director, data analyst, prompt engineer, review editor, API integrator, compliance reviewer, or another relevant role.

The expert prompt must specify task, audience, evidence sources, quality standard, constraints, output contract, and what to avoid.

## Prompt Structure

Use this internal prompt shape when designing LLM or Agent nodes:

1. Role: the expert stance and responsibility.
2. Goal: the business outcome of this node.
3. Inputs: exact variables and evidence to use.
4. Method: concise domain method or evaluation rubric.
5. Constraints: facts, style, safety, schema, and tool-use limits.
6. Output: field-level or section-level contract.
7. Quality check: what the node must verify before returning.

Keep chain-of-thought hidden. If the user asks for reasoning, output a business-auditable `decision_trace` or similar step summary.

## Capability, Tool, And Evidence Use

Agent prompts must tell the agent when to use each native component, Dify node, or tool, what input to pass, what the returned evidence means, and when not to call it.

For AIGC generation, native AI Hub components are not optional imported tools. Use the native AIGC component rules first, then add internal tools only when the requested capability cannot be expressed with those components.

Do not rely only on retrieved Skill text from a knowledge base. If current DSL behavior depends on a rule, place the rule in the active Agent or LLM prompt as well.

If external research is used, apply it to professional quality and domain context. Do not use it to create private AI Hub fields, permissions, credentials, or provider IDs.

## Formatting Boundary

Agent free text is evidence, not the final contract. Route it through an LLM formatter or Code node when the final output must be JSON, Markdown, files, or another strict format.

Formatter prompts should extract and normalize; they should not silently redesign the business answer.

Code normalization should repair safe defaults, sequence IDs, empty arrays, and JSON stringification, but it should not invent substantive domain content.
