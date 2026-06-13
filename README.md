# Skills

这个仓库用来维护我个人开发的 AI 编程助手 Skill。

每个 Skill 都是一个独立目录，可以单独安装、单独更新、单独维护。当前包含
`relay-loop` 和 `dify-dsl-builder` 两个模块。它们都属于个人开发的 Skill，
但用途不同，不应该合并在一起维护。

## 当前包含的 Skill

| Skill | 用途 | 适合的场景 |
| --- | --- | --- |
| `relay-loop` | 用“指挥者 + 执行者”的方式驱动后台编码代理。当前会话负责规划、派发、验收和交接，后台代理负责完成一段明确的实现任务。 | 长任务、多轮实现、需要把任务交给 `codex exec` 或其他后台代理执行，但仍希望保留人工验收和状态交接的场景。 |
| `dify-dsl-builder` | 设计、修复、验证 Dify / AI Hub 的 Workflow 和 Chatflow DSL。 | 生成生产可用的 DSL、修复导入或运行问题、处理 AIGC 工作流、校验 Code 节点和变量契约、做 AI Hub 兼容性检查。 |

## `relay-loop`

`relay-loop` 是一个面向后台编码代理的协作流程 Skill。

它的核心思路是：当前会话作为“指挥者”，负责理解项目、写清楚目标、派发任务、
检查结果和决定下一步；后台代理作为“执行者”，只负责完成一次边界清楚的任务，
完成后写出 Handoff 交回。

适合在这些情况下使用：

- 想把一段实现任务交给 `codex exec` 或其他后台代理；
- 任务较长，需要多轮执行和多次验收；
- 希望每一轮都有明确的目标、验证方式和停止条件；
- 希望减少强模型在具体实现上的消耗，把它主要用于规划和验收。

目录结构：

```text
relay-loop/
├── SKILL.md
├── references/
│   ├── commander-recovery.md
│   ├── executor-dispatch.md
│   ├── goal-contract.md
│   ├── handoff.md
│   └── verify-and-visual.md
└── scripts/
    └── lint_goal.py
```

## `dify-dsl-builder`

`dify-dsl-builder` 是一个面向 Dify / AI Hub DSL 开发的 Skill。

它可以帮助代理把需求整理成可导入、可验证的 DSL 项目，也可以在已有 DSL 出现
导入失败、画布渲染异常、Code 节点报错、工具节点结构不对、AIGC 节点契约不匹配
等问题时做修复。

适合在这些情况下使用：

- 从需求出发设计 Dify Workflow 或 Chatflow；
- 修复已有 DSL，并尽量保留原来的业务含义；
- 设计 AI Hub 原生 AIGC 工作流；
- 输出版本化 DSL、README、验证报告和项目记忆；
- 在交付前运行静态校验，必要时补充 AI Hub 预检。

目录结构：

```text
dify-dsl-builder/
├── SKILL.md
├── agents/
├── assets/
│   └── fixtures/
├── references/
├── scripts/
└── tests/
```

## 下载仓库

先把仓库下载到本地：

```bash
git clone https://github.com/shibiao1998-dot/Skills.git
cd Skills
```

如果只想安装其中一个 Skill，可以在下面的命令中删掉不需要的那一行。

## 安装到 Claude Code

Claude Code 常用的 Skill 目录是 `~/.claude/skills/`。

复制安装：

```bash
mkdir -p ~/.claude/skills
cp -R relay-loop ~/.claude/skills/relay-loop
cp -R dify-dsl-builder ~/.claude/skills/dify-dsl-builder
```

如果你会继续修改这个仓库，建议使用软链接安装，这样仓库里的改动会直接生效：

```bash
mkdir -p ~/.claude/skills
ln -s "$(pwd)/relay-loop" ~/.claude/skills/relay-loop
ln -s "$(pwd)/dify-dsl-builder" ~/.claude/skills/dify-dsl-builder
```

## 安装到 Codex / CodeX

Codex 常用的 Skill 目录是 `~/.codex/skills/`。

复制安装：

```bash
mkdir -p ~/.codex/skills
cp -R relay-loop ~/.codex/skills/relay-loop
cp -R dify-dsl-builder ~/.codex/skills/dify-dsl-builder
```

如果你会继续修改这个仓库，建议使用软链接安装：

```bash
mkdir -p ~/.codex/skills
ln -s "$(pwd)/relay-loop" ~/.codex/skills/relay-loop
ln -s "$(pwd)/dify-dsl-builder" ~/.codex/skills/dify-dsl-builder
```

如果你的代理使用的是其他 Skill 目录，把上面命令里的目标路径替换成对应目录即可。

## 使用方式

安装后，在对话里直接说明要做什么即可。代理会根据 `SKILL.md` 里的描述判断是否使用
对应 Skill。也可以明确点名：

```text
使用 relay-loop，把这个任务拆成一个可以交给后台 Codex 执行的 Goal。
```

```text
使用 dify-dsl-builder，帮我修复这个 Dify DSL 并做静态校验。
```

## 验证命令

每个 Skill 有自己的验证脚本。

检查 `relay-loop` 的 Goal 文档：

```bash
python3 relay-loop/scripts/lint_goal.py path/to/goal.txt
```

校验 Dify DSL 文件：

```bash
python3 dify-dsl-builder/scripts/validate_dify_dsl.py path/to/workflow.yml
```

`dify-dsl-builder/scripts/` 和 `dify-dsl-builder/tests/` 里还包含更多针对 DSL
结构、AIGC fixture、AI Hub 预检和交付质量的测试脚本。

## 维护约定

- 每个 Skill 独立放在一个顶层目录里。
- 通用说明写在对应目录的 `SKILL.md`。
- 需要按需加载的细节放在 `references/`。
- 可复用的检查脚本放在 `scripts/`。
- 不要把个人机器路径、账号、密钥或运行时临时状态提交进仓库。
- 新增个人 Skill 时，新建一个顶层目录，不要塞进已有模块。

## License

MIT. See [LICENSE](LICENSE).
