# Journey: New Build

Use this journey when the user asks for a new Dify Workflow, Chatflow, AI Hub app, AIGC production line, RAG tool, content generator, or DSL from an idea, document, or requirement.

## One-Question Clarification

Ask at most one user-facing question per turn.

Choose the next question by impact on the final workflow. Prefer questions about target user, use scenario, expected output, success standard, input variability, required materials, permissions, or delivery format.

Do not ask the user to choose visible engineering depth. Infer the needed depth internally.

Use Recommended Single-Question Clarification for every business-facing clarification:

1. One short context sentence.
2. One question.
3. Two or three answer choices, with `A.` as the recommended default.
4. One short expectation sentence explaining what happens after the user picks.

Do not ask broad open-ended questions when reasonable choices can reduce user effort. Do not end with vague prompts such as “你觉得呢” or “你想怎么做”.

Do not ask business users to choose an engineering fallback policy or decide what should happen when an internal component is unavailable. Treat those as internal engineering assumptions. Mention them only as evidence-backed live QA notes after the agent has actually tested the workflow.

For AI Hub AIGC workflows, image, 3D, video, audio, and speech-recognition components are native design capabilities. Ask for a packaged internal tool only when the user explicitly requires a capability outside those native nodes.

For source retrieval and factual verification, default to a trustworthy-result contract: search public or approved sources, verify the source text, cite or package evidence, and return a clear diagnostic when evidence is insufficient. The workflow must not fabricate source facts.

If the user already defines a hard quality gate, treat it as accepted scope. For example, "找不到可信作者、朝代、原文和来源链接时不继续生成" means the workflow must diagnose insufficient evidence and avoid fabricated outputs. It is not an invitation to ask a failure-strategy question.

Do not combine a correct quality-gate statement with an engineering contingency question. For example, after saying “联网检索和原文校验会作为前置质量门”, the next user-facing question should still ask about business use, audience, output channel, or success standard. Component availability belongs in the internal design and runtime QA plan, not in discovery.

When a sentence says the workflow should not continue if evidence is missing, read it as runtime behavior inside the workflow. Do not treat that sentence as a user instruction to pause the DSL build.

If a source-checked AIGC request mentions public-source lookup, original-text verification, song audio, MV, video, or complete playable work, ask this class of question next unless the answer is already known:

```text
这个完整作品优先用于哪类使用场景？

我的推荐：A. 面向短视频发布，优先完整可播放和传播效果。 B. 面向内部审核或选题验证，优先来源证据、歌词和分镜完整。
你可以直接回复 A 或 B，也可以用一句话修正。
```

If enough information is already available, stop asking and move to final alignment.

## Outcome-First Discovery

Begin by restating the understood outcome in one or two plain-language sentences.

For vague ideas, ask the first question about the result effect, not about node type. Good first questions usually clarify who will use the workflow, where the output will be used, or what a good result looks like.

For clear documents, first extract what is already known: goal, inputs, outputs, user scenario, quality standard, materials, tools, and risks. Ask only for the important missing item that changes design or quality.

Internally decide the likely app shape, capability route, domain expert roles, dimension decomposition, and validation path.

## Discovery Sufficiency Rule

Discovery is sufficient when these are clear enough to design responsibly:

1. Business goal: who the workflow helps and what job it performs.
2. Inputs: what the user, system, file, or upstream workflow provides.
3. Outputs: what result, file, link, structured data, or package should be produced.
4. Scenario and success standard: where the output will be used and what good looks like.
5. AI Hub capability route: Workflow or Chatflow shape, native components, Dify nodes, internal tools only when necessary, and production-line pattern.
6. Key risks: permissions, API keys, required user-provided materials, storage destination, live QA needs, output quality, or unsupported private fields.

This is a sufficiency rule, not a form. Do not keep clarifying after the agent can make defensible assumptions and validate the result.

Risk discovery does not mean asking the user to design technical handling. Ask only for facts the agent cannot infer, such as a credential, file location, target audience, output channel, or business boundary.

## Final Alignment

Before generating DSL, present one concise natural-language alignment and wait for explicit confirmation.

The alignment still follows the recommended choice pattern: `我的推荐：A. 按这个方案生成；B. 先调整边界。`

The alignment should cover:

1. The business outcome the workflow will produce.
2. The inputs and outputs that will be created or preserved.
3. Why the selected Workflow or Chatflow direction fits.
4. A plain-language dimension decomposition summary.
5. Important assumptions, user-provided materials or permissions, and first-run checks.

Do not expose provider IDs, node IDs, schema internals, selectors, or internal variable names in this alignment unless the user asks for engineering detail.

## Output Contract

For a formal DSL project, deliver:

1. `README.md` with what the workflow does, how to import it, how to run the first test, what good output looks like, and how to give feedback.
2. `<slug>-v1.yml` as the importable DSL.
3. `.agent/DSL_DISCOVERY_BRIEF.md` with the business contract and expert design record.
4. `.agent/build-log.md` with decisions, assumptions, and version history.
5. `.agent/validation-report.md` with static checks, live QA status, and remaining risks.

For smaller one-file requests, still deliver a versioned DSL path and a concise validation summary.

State static validation and AI Hub live QA separately. Do not imply import/open/run testing happened unless it actually happened.
