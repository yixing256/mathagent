# docs/agents/README.md — 调研说明 + 技能使用手册

> 本目录是项目的 AI 开发治理包。约束正文在各约束文件与 SOP 文件里；本文件负责
> **说明设计依据**与**怎么用这套技能**。单文件 ≤200 行，超了就拆。

## 一、我是怎么调研的、据此做了什么决定

### 1.1 调研路径（含失败与降级，如实记录）

| 步骤 | 通道 | 查询 | 结果 |
|---|---|---|---|
| 1 | 代码检索插件（learn_code_from_web） | PySide6 目录结构 / PyInstaller onedir 打包实践 | `ok=false`，GitHub、Gitee 均返回空 |
| 2 | 同上 | AGENTS.md / CLAUDE.md / Cursor Rules / conventional commits / CODEOWNERS / pre-commit | `ok=false`，同上，降级深度到上限 |
| 3 | 同上（单源 CSDN） | onedir collect_all / 国产模型协议适配 | 无可用结果 |
| 4 | 直接抓原始资料（降级补证） | 见 1.2 | 命中官方规范与文档，作为设计依据 |

结论：插件三源本轮均无可解析结果，**未据此编造任何来源**；设计依据全部来自第 4 步可点开的
公开一手资料，凡属本地判断（覆盖率数字、目录命名等）在 1.3 标 **自行决定**。

### 1.2 参考的一手资料与提炼

- **AGENTS.md 开放格式**（[agents.md](https://agents.md)）：它是「给智能体的 README」，
  最近的一层文件优先、无必需字段、可嵌套。→ 提炼：**入口只做索引与红线摘要，细则放到最近层**，
  因此 `AGENTS.md` 短、`docs/agents` 目录 每文件主题单一。
- **Qt for Python 官方 PyInstaller 说明**（[Qt 部署文档](https://doc.qt.io/qtforpython-6/deployment/deployment-pyinstaller.html)）：
  明确 onedir 是原生目录形态；并警告「系统级 PySide6/shiboken6 会被静默选中」。→ 提炼：锁定 onedir、
  打包前清干净系统级 Qt、打包在干净 venv 里做。
- **Conventional Commits 1.0.0**（[规范](https://www.conventionalcommits.org/en/v1.0.0/)）：类型前缀、
  可选 scope、`!`/`BREAKING CHANGE` 语义。→ 提炼：提交类型白名单 + 一个提交只做一件事。
- **pre-commit 官方文档**（[pre-commit.com](https://pre-commit.com/)）：`repo: local` 钩子、
  `pre-commit run --all-files`、CI 中复用同一配置。→ 提炼：钩子走 `repo: local`（不写外部仓库域名，
  适配国产化内网镜像）、本地与 CI 同一份配置。
- **GitHub CODEOWNERS 文档**（[About code owners](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners)）：
  最后匹配的规则生效；CODEOWNERS 本身也要指定 owner；fork 场景用 base 分支版本。→ 提炼：
  `/docs/agents/` 规则写在通配规则**之后**，并给 `CODEOWNERS` 自身也指定 owner。
- **LiteLLM 的协议映射文档**（[messages ↔ responses 参数映射](https://docs.litellm.ai/docs/anthropic_unified/messages_to_responses_mapping)）：
  `system` 是否独立字段、`max_tokens`、`stop` vs `stop_sequences`、工具与流式结构都要显式翻译。
  → 提炼：**能力矩阵 + 双 adapter + 禁止静默降级**；网关方案的取舍见 1.3 D2。

### 1.3 关键设计决策（D = decision）

| 编号 | 决策 | 理由 | 来源 |
|---|---|---|---|
| D1 | 采用 `src`-式分层：`app/`(UI) `core/`(契约) `solvers/`(算法) `viz/`(图表) `ai/`(接入) `services/`(编排) `packaging/` | 依赖方向单向（UI→services→core/solvers/ai），多人多智能体并行时冲突面最小 | AGENTS.md 最近层优先 + 桌面项目实践 |
| D2 | **自研两个 adapter，不引第三方网关** | 单机离线、只有 2 种协议、包体与升级面敏感；网关多一跳网络与一棵依赖树 | LiteLLM 映射文档 + 自行决定 |
| D3 | 统一 `LLMRequest/LLMResponse` + **能力矩阵**，未声明能力直接报错 | 「兼容」实现差异大，显式失败优于静默降级 | 协议映射文档 |
| D4 | PyInstaller **onedir + COLLECT + collect_all**；干净 venv 打包 | 官方文档：onedir 为目录形态；系统级 Qt 会被静默选中 | Qt 官方部署文档 |
| D5 | pre-commit 全用 `repo: local` 钩子 | 内网/国产化镜像可配、不硬编码外部仓库 | pre-commit 文档 + 自行决定 |
| D6 | **覆盖率：总行 80%，`ai/` 与 `solvers/` 各 90%** | 这两处错最贵（钱/结论错），UI 用冒烟+截图兜底 | 自行决定 |
| D7 | `docs/agents` 目录 由架构负责人独占审批，CI 加守卫 job | 约束文件被顺手放宽是治理包失效的头号原因 | CODEOWNERS 文档 + 自行决定 |
| D8 | 文档单文件 ≤200 行，按角色/SOP 拆分 | 智能体按需加载，避免一次吞长文 | 自行决定 |

## 二、目录地图

`docs/agents` 目录`
AGENTS.md                    入口：索引 + 五条红线摘要 + 固定命令
docs/agents/README.md        本文件：调研依据 + 使用说明 + 迭代规则
docs/agents/00-base.md      全局红线（技术栈/交付/Git/分层/线程/安全）
docs/agents/10-role-ui.md   UI 角色：QSS、线程、资源路径、交互
docs/agents/11-role-core.md 算法角色：科学栈用法、数值契约、性能
docs/agents/12-role-ai.md   AI 角色：双协议 adapter、能力矩阵、密钥、错误分类
docs/agents/13-role-release.md 发布角色：spec、onedir、冒烟、版本
docs/agents/20-sop-ui-change.md  示例 SOP：一次 UI 变更怎么走完
docs/agents/21-sop-release.md    示例 SOP：出一次 onedir 发布包
dependency-whitelist.txt  依赖白名单（新增需 RFC）
.github/  .pre-commit-config.yaml  workflows/ci.yml  PULL_REQUEST_TEMPLATE.md  CODEOWNERS
`docs/agents` 目录`

## 三、《技能的使用说明》

### 3.1 智能体接任务前必须读什么、什么顺序

| 任务类型 | 最小必读集（按序） | 禁止 |
|---|---|---|
| 任意任务 | `AGENTS.md` → `00-base.md` → 对应角色包 | ❌ 禁止只读任务描述就动手 |
| UI / QSS / 图表交互 | 上述 + `10-role-ui.md` → `20-sop-ui-change.md` | ❌ 禁止跳过截图与线程规则 |
| 算法 / 求解器 / 数据处理 | 上述 + `11-role-core.md` | ❌ 禁止在 GUI 线程算、禁止无回归结果 |
| 模型调用 / 协议 / key | 上述 + `12-role-ai.md` | ❌ 禁止改协议字段映射而不更新能力矩阵 |
| 打包 / 依赖 / 发版 | 上述 + `13-role-release.md` → `21-sop-release.md` | ❌ 禁止 `--onefile`、禁止擅自加依赖 |
| 加新依赖 | `00-base.md` §1 + `dependency-whitelist.txt` | ❌ 禁止先装后补流程 |

读完先在 PR/回复里复述：**本任务属于哪个角色、哪些红线相关、要交哪些证据**，再动手。

### 3.2 新成员 / 新智能体如何启用（clone 之后按序执行）

`docs/agents` 目录`bash
py -3.11 -m venv .venv && .venv\Scripts\activate
python -m pip install -e ".[dev]"
python -m pip install pre-commit && pre-commit install --install-hooks
pre-commit run --all-files          # 首次会建 detect-secrets 基线，必须提交 .secrets.baseline
python -c "import PySide6, numpy, scipy, sklearn; print(PySide6.__version__)"   # 环境自检
pytest -q --cov=mathagent --cov-fail-under=80                                    # 基线自检
python scripts/check_docs_pack.py --target . --json                              # 治理包自检
`docs/agents` 目录`

四条自检全绿才算「启用完成」；任一失败**先修环境、不进业务任务**。
合并门禁数字（写死，不许口头放宽）：行覆盖率 总 80%、`mathagent/ai/` 90%、`mathagent/solvers/` 90%。智能体额外确认：
`.venv` 内 PySide6 版本与 `dependency-whitelist.txt` 一致，且系统级 site-packages 无 PySide6。

### 3.3 什么时候触发加载哪个技能包

- 改 `app/**`、`resources/qss/**`、`viz/**` → 加载 `10-role-ui.md` + `20-sop-ui-change.md`；
  完成条件：截图 + 线程规则 + 视觉回归说明。
- 改 `solvers/**`、`core/**` 的数值契约 → 加载 `11-role-core.md`；完成条件：单元测试 +
  `tests/regression/` 赛题结果对比（指标、耗时、误差）。
- 改 `ai/**`、新增厂商配置 → 加载 `12-role-ai.md`；完成条件：双协议契约测试 +
  能力矩阵更新 + 密钥扫描通过 + 日志脱敏检查。
- 改 `packaging/**`、spec、版本号 → 加载 `13-role-release.md` + `21-sop-release.md`；
  完成条件：干净机器冒烟 + 包体清单 + 启动耗时记录。
- 任何「想加依赖 / 想改 CI / 想改约束」→ 加载 `00-base.md` §1、§8，走 RFC，**停手等审批**。

### 3.4 谁能改 `docs/agents` 目录 下的约束文件

- 只有**架构负责人**（CODEOWNERS `@mathagent-core`）能批准 `AGENTS.md`、`docs/agents` 目录、
  `CODEOWNERS`、`.pre-commit-config.yaml`、`dependency-whitelist.txt` 的变更。
- 其他人（含智能体）可以提交 PR 说明「为什么现有约束不合适」，但 **❌ 禁止在同一 PR 里同时改约束和业务代码**。
- CI 守卫：`agents-pack-guard` job 检查两点——① 改动的路径命中保护清单时，需要 CODEOWNERS
  批准（缺则 fail）；② 保护文件的 diff 不得同时包含 `app/`、`solvers/`、`ai/` 的业务改动（缺则 fail）。
- ❌ 禁止在 PR 里用 `--no-verify`、跳过 CI、或改 CI 里守卫 job 自身来规避审批。

### 3.5 技能本身如何迭代

- **节奏**：每两周复盘一次；每个赛题/大版本结束后必须复盘；同一类错误出现第 2 次即当周加条目。
- **加严判据**（满足其一就加）：同类错误重复 ≥2 次；某红线被侥幸绕过 1 次；CI 漏检导致返工 ≥1 次；
  新依赖/新协议进入项目。新增条目必须写「错误现象 + 正确做法 + 检查方式」，否则不合入。
- **删除/放宽判据**（满足其一才删）：连续 8 周零触发且已被 lint/CI 自动覆盖；
  工具已强制（如 ruff 规则替代人工约定）；与另一条重复或冲突。删除同样走架构负责人审批。
- **不留冗余**：每次复盘后 `docs/agents` 目录 总量不增，新增条目优先替换旧条目而非追加。
- **记录**：变更写在 PR 描述里（现象/改了什么/如何验证），不另建变更日志文件。
