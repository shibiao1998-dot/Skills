# Capability: Dify Node Composition

## Operational Rules

Build nodes around contracts: what each node receives, what it produces, and why the downstream node needs it.

Every edge source and target must reference an existing node. Every selector must point to an existing node output, `conversation`, or `sys`.

Keep node names business-readable. Keep node IDs stable within the file and unique across the graph.

## Core Nodes

Start nodes define only necessary user inputs. Preserve labels, variable names, and required flags from an existing DSL unless a confirmed change requires otherwise.

Code nodes handle deterministic normalization, JSON parsing, fallback, sequence numbering, and conversion of complex objects into strings. They should not contain business reasoning that belongs in a prompt.

LLM nodes perform focused expert tasks. If structured output is needed, define a compatible schema and add a normalization step when downstream consumers need strings.

Agent nodes can call tools and reason across evidence, but their free text should not be treated as final JSON. Use a formatter or Code node before final output.

New or repaired Agent nodes in generated AI Hub DSL default to FunctionCalling:

```yaml
agent_strategy_label: FunctionCalling
agent_strategy_name: function_calling
agent_strategy_provider_name: langgenius/agent/agent
```

Do not fill missing Agent strategy fields with ReAct by default. ReAct is allowed only when the user explicitly asks for it or an existing runnable DSL provides evidence that the same node requires it.

IF/ELSE nodes should express meaningful business or state branches. Do not trust node names alone; verify the actual conditions and outgoing edges.

Variable Aggregator nodes combine branch results when the next node needs one selector. Assigner nodes save Chatflow state after output normalization.

Answer nodes are for Chatflow user responses. End nodes are for Workflow outputs.

## Tool Nodes

Tool nodes must include all required shape fields for the target AI Hub/Dify version. Include an explicit empty `tool_configurations: {}` when no configuration values are needed.

Tool parameters should use the direct variable expected by the tool. Do not add decorative prefixes such as `project name:` unless the tool contract requires that literal string.

Do not invent private provider IDs, tool IDs, credentials, or permissions. Preserve verified values from user-provided DSL evidence or documented AI Hub material.

For AIGC main chains, Tool nodes are not the default implementation path. Prefer native AI Hub component nodes for image, 3D, video, audio, and speech recognition. Use workflow-backed Tool nodes only for explicitly requested harnesses or verified capabilities outside native component contracts.

## Iteration And Child Canvas

Iteration nodes must align the input selector type with the declared item type.

Child nodes inside iteration or nested canvases must preserve parent references, canvas placement, and source/target contracts expected by AI Hub. Canvas-open failures often come from graph shape, not YAML parsing.

Validate child node IDs, parent references, and iteration output selectors before delivery.

For multi-shot video generation, do not place image-generation nodes in the blocking iteration path by default. A keyframe, character three-view, or style reference image can be useful, but it should be an optional/reference branch unless the user explicitly requires image-gated video. The core path should let native `video-generation` consume normalized storyboard prompts.

## Composition Floor

For production DSL, include domain expert prompting and dimension-aware decomposition unless the task is a narrow mechanical repair.

Do not collapse planning, generation, validation, and packaging into one LLM node when those dimensions materially affect quality.
