# Capability: Dimension-Aware Decomposition

## Operational Rules

Use dimension-aware decomposition for non-trivial production DSL. Treat it as a quality requirement, not an optional embellishment.

Separate major thinking dimensions into focused stages when they materially affect output quality. Each stage needs a responsibility, expert stance, input contract, output contract, and downstream purpose.

Do not split merely to add nodes. Split when a separate stage improves controllability, evidence use, reviewability, reuse, or validation.

## Common Dimensions

Useful dimensions often include:

1. Intent and constraint normalization.
2. Audience, learner, customer, or user analysis.
3. Domain research or evidence retrieval.
4. Planning, outline, or storyboard creation.
5. Artifact generation for a specific medium.
6. Style, brand, tone, or format adaptation.
7. Factual consistency or policy review.
8. Capability-backed enrichment or media generation.
9. Quality scoring and revision.
10. Schema normalization and final packaging.

Choose dimensions from the task. Do not force every workflow to contain all of them.

## Clarification And Assumptions

If a dimension changes the workflow materially, ask one user-facing question about it or make a recommended assumption and surface it in final alignment.

Examples:

1. A teaching workflow may need learner grade and lesson scenario.
2. A marketing workflow may need target audience and distribution channel.
3. A video workflow may need duration, visual style, and asset source.
4. A review workflow may need scoring criteria and accepted evidence.

## Final Alignment Summary

Before new build or non-narrow repair generation, summarize decomposition in plain language.

Use business wording such as: understand inputs, plan structure, generate the artifact, review quality, and package output.

Do not expose node IDs, selectors, provider IDs, internal variable names, or schema details unless the user asks for implementation detail.

## Validation

Static validation cannot fully prove prompt quality, but it can flag missing decomposition in non-trivial DSL.

Check that important LLM and Agent nodes are not overloaded with unrelated responsibilities, and that final output packaging is separated from domain generation when strict output is required.
