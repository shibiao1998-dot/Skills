# Failure: Generated Interaction

## Symptom

The agent generates DSL too early, asks several clarification questions in one turn, asks the user to pick an engineering mode, asks vague open-ended questions without recommended options, exposes internal process labels, asks the user to choose engineering contingencies, skips final confirmation, or presents technical node internals to a business user before alignment.

## Root Cause

The skill entrypoint or old references may over-emphasize templates, engineering procedures, or historical labels. The agent may shortcut from a vague idea directly to YAML instead of discovering the outcome and confirming the design.

Another common cause is mixing two different concerns: a user-stated source or evidence gate is business behavior inside the workflow, while media component verification is the agent's design and live QA work. Combining them creates a user-facing technical choice that the business user should not need to solve.

This is a product behavior failure even if the generated YAML parses.

## Prevention Rule

For new builds, ask one outcome-first question at a time until discovery is sufficient, then present one plain-language final alignment and wait for confirmation before generating DSL.

For repair, diagnose the failure stage first. Only narrow mechanical repair may skip the extra confirmation; non-narrow repair still needs final alignment.

Do not ask users to choose visible depth modes. Keep process names, internal records, provider IDs, selectors, and schema details out of user-facing alignment unless requested.

For non-technical users, write the clarification as one question with 2-3 choices and a recommended default. The user should be able to answer with `A`, `B`, or a short correction.

Do not ask the user to decide the handling policy for unavailable AI Hub components. The agent owns this engineering assumption: design the best native-node workflow, surface runtime dependency risks in plain language, and verify them separately.

Do not replace the A/B choice block with a first-person recommendation sentence. That still leaves the user with a vague open-ended decision and violates the product interaction contract. Waiting responses must contain `我的推荐：A. ... B. ...` and the user must be able to answer with `A`, `B`, or a short correction.

Invalid pattern category: asking the user to choose an engineering contingency.

Do not write the actual bad sentence in user-facing drafts. The unsafe shape is:

```text
[technical contingency] + [unverified AI Hub/AIGC component] + [choice of reduced result]
```

Why invalid: it asks a business user to solve an engineering uncertainty, has no recommended A/B product choice, and makes the workflow feel fragile before the agent has tried to design or verify it.

Also invalid category:

```text
[unverified media capability] + [choice of reduced deliverable]
```

Why invalid: the user asked for a complete media result. Component discovery, selector selection, and first-run verification are the agent's engineering work, not a business preference.

Preferred pattern:

```text
我会按完整作品来设计：先校验来源，再用 AI Hub 原生音频和视频节点生成可播放结果，首测时我会单独检查组件可用性和输出链接。

这个作品更适合先服务哪类使用场景？

我的推荐：A. 面向短视频发布，优先完整可播放和传播效果。 B. 面向内部审核，优先来源证据、歌词和分镜包完整。
你可以直接回复 A 或 B，也可以用一句话修正。
```

## Validator Or Test

Run interaction regression prompts for vague new builds, clear documents, old DSL repair, known structural repair, final alignment behavior, and narrow repair exceptions.

Assertions should check one-question turns, recommended options, outcome-first discovery, absence of visible mode picking, absence of obsolete process labels, absence of failure-strategy questions, final alignment before generation, and plain-language dimension decomposition.
