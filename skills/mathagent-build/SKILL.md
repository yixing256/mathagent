---
name: mathagent-build
description: >
  Install, verify and enforce a project-level AI development governance pack for a Windows-only
  PySide6 + Python math-modeling desktop app built by several humans and AI agents: AGENTS.md
  entry, role constraints, SOP packs, pre-commit / CI / PR template / CODEOWNERS / dependency
  allowlist fragments, onboarding chapter. Use when a team needs project AI coding governance,
  coding-agent onboarding, AI coding red lines, role boundaries, review gates, PyInstaller onedir
  packaging discipline, or OpenAI-compatible plus Anthropic-compatible domestic LLM adapters.
  Triggers: mathagent-build, project AI coding governance, AI coding red lines, coding-agent
  onboarding, role constraints, review gates, dependency allowlist, PySide6 desktop rules,
  mathematical modeling app, onedir packaging, 数学建模, 桌面软件, 项目级 AI 开发技能,
  AGENTS.md 治理包, 多智能体协作, AI 写代码红线, 国产大模型接入, 打包规范, 代码评审门禁,
  依赖白名单.
version: 1.0.2
compatibility: Windows 10/11; target project is Python 3.11+ / PySide6 6.7 / PyInstaller 6 onedir. The pack is Markdown plus YAML config fragments; scripts/check_docs_pack.py needs only the Python standard library.
metadata:
  author: mathagent-core
  audience: humans and coding agents
---

# mathagent-build

交付一套**可直接落地到仓库**的 AI 开发治理包：本技能负责「装进去、查得动、按角色分派、
按门禁卡合」，不负责写业务代码。治理包在 `assets/` 下的 `docs-pack` 目录里（15 个文件），
下文提到包内文件时用**裸文件名**，全部位于该目录（或其中 `docs/agents`、`config` 子目录）。

## 1. 产物对照表（包内 → 落盘位置）

| 包内文件 | 落盘位置 | 说明 |
|---|---|---|
| `AGENTS.md` | 仓库根 | 入口（≤200 行，索引 + 红线摘要） |
| `README.md`（docs/agents 子目录） | agents 目录 | 调研说明 + 《技能的使用说明》 |
| `00-base.md` | agents 目录 | 全局红线（架构负责人审批） |
| `10-role-ui.md` | agents 目录 | UI / QSS / 线程 角色约束 |
| `11-role-core.md` | agents 目录 | 科学栈与算法内核 角色约束 |
| `12-role-ai.md` | agents 目录 | 双协议接入层 角色约束 |
| `13-role-release.md` | agents 目录 | 打包 / 发布 角色约束 |
| `20-sop-ui-change.md` | agents 目录 | 示例 SOP：改 UI |
| `21-sop-release.md` | agents 目录 | 示例 SOP：出 onedir 包 |
| `.pre-commit-config.yaml`（config 子目录） | 仓库根 | ruff/mypy/pytest + 密钥扫描兜底 |
| `ci.yml`（config 子目录） | 工作流目录 | lint + type + test + 覆盖率门禁 |
| `PULL_REQUEST_TEMPLATE.md`（config 子目录） | 评审模板目录 | PR 自检与证据栏 |
| `CODEOWNERS.txt`（config 子目录） | 评审模板目录 | 落盘时改名为 `CODEOWNERS` |
| `dependency-whitelist.txt`（config 子目录） | agents 目录 | 依赖白名单 |
| `gitignore.append.txt`（config 子目录） | 追加进根 `.gitignore` | 不单独落盘 |

## 2. 工作流（按序执行，不跳步）

1. **确认目标仓库**：`--target <repo>`。目标已有 agents 目录时，禁止直接覆盖——
   先列差异并让架构负责人确认（见第 6 节写操作规则）。
2. **自检包完整性**（只读）：
   `docs/agents` 目录`bash
   python scripts/check_docs_pack.py --kit assets/docs-pack --list
   python scripts/check_docs_pack.py --kit assets/docs-pack --json
   `docs/agents` 目录`
   退出码 0 = 全通过；1 = 有违规（逐条列出 id 与文件）；2 = 参数错误。必须修到 0 再安装。
3. **安装**：按 §1 对照表复制到落盘位置；`gitignore.append.txt` 的内容**追加**进根 `.gitignore`。
   `00-base`/`10~13-role` 这 5 个文件如需与团队既有约定一致的扩展名，安装时统一改名即可（内容与引用不变）。
4. **校验落地**：
   `docs/agents` 目录`bash
   python scripts/check_docs_pack.py --kit assets/docs-pack --target <repo> --json
   `docs/agents` 目录`
   target 模式额外检查 6 个落地文件、入口文件对《使用说明》的引用、覆盖率数字（80 / 90）。
5. **交回门禁**：安装本身也走 PR，PR 描述里贴 `--json` 全绿输出；治理文件改动必须由
   架构负责人（`CODEOWNERS` 里的 `@mathagent-core`）审批。

## 3. 该读哪个角色包（按任务类型分派，禁止全量通读浪费上下文）

| 任务 | 必读顺序 |
|---|---|
| 任何任务（含 AI） | `AGENTS.md` → `00-base.md` → 对应角色包 → 对应 SOP |
| 新增/修改界面、QSS、图表 | + `10-role-ui.md` → `20-sop-ui-change.md` |
| 数值算法、求解器、数据处理 | + `11-role-core.md` |
| 模型调用、协议适配、key 管理 | + `12-role-ai.md` |
| spec/依赖/打包/发版 | + `13-role-release.md` → `21-sop-release.md` |
| 加新依赖 | 先读 `00-base.md` 的依赖规则 + `dependency-whitelist.txt` |

## 4. 触发词（何时加载本技能）

**应触发**：项目级 AI 开发规范 / AI 写代码红线 / 多智能体协作约束 / 角色分工与边界 /
AGENTS.md 治理包 / 代码评审门禁 / 依赖白名单 / 国产大模型双协议接入规范 / onedir 打包规范 /
新成员或新智能体 onboarding；英文：project AI coding governance, AI coding red lines,
coding-agent onboarding, role constraints, review gates, dependency allowlist, PySide6 desktop
rules, PyInstaller onedir packaging, AGENTS.md governance pack.

**不应触发**（近失配）：实现具体界面、写求解器实现代码、调某个 CLI 的 Key、读某个报错、
写单测、改单点打包参数——这些是业务任务，交给对应角色包，不要加载本技能。

## 5. 角色包与 SOP（包内文件，落盘位置见 §1）

- 红线：`00-base.md`（技术栈锁定、onedir、Git 安全、覆盖率 80%/90%、分层与线程）
- 角色：`10-role-ui.md`（UI/QSS/图表）、`11-role-core.md`（科学栈/数值契约）、
  `12-role-ai.md`（能力矩阵/错误分类/密钥）、`13-role-release.md`（spec/冒烟/版本）
- SOP：`20-sop-ui-change.md`（UI 变更 checklist + 证据）、`21-sop-release.md`（发布 checklist）
- 使用说明：`README.md`（读文件顺序、启用步骤、何时加载、谁能改、如何迭代）

## 6. Gotchas（没有这条就会做错，逐条是踩坑结论）

- **包内文件名一律白名单扩展名**（`.md`/`.yaml`/`.txt`/`.py`/`.json`）；落盘时才改名
  （如 `CODEOWNERS`、扩展名调整）。反过来做会被结构校验拒绝。
- **PyInstaller 的 `--onefile` 是硬禁止**，spec 必须是 `Analysis → PYZ → COLLECT`（onedir），
  产物是 `dist/<app>/` 整个文件夹 + 其中 exe，双击启动；出现 onefile 的 PR 直接拒。
- **系统级 PySide6 会被 PyInstaller 静默选中**（Qt 官方文档明写）：打包前在干净 venv 里
  `python -m pip uninstall` 全部 PySide6/shiboken6，或用独立干净环境打包。
- 科学栈（`scipy`/`numpy`/`sklearn`）不 `collect_all` 就会在运行期缺 `.dll`/`.dat`/二进制扩展，
  表现为「开发机正常、干净机器崩」。
- 资源路径（QSS、图标、模型清单）**只能运行期解析**（打包后是 `_internal`），
  禁止 `__file__` 拼绝对路径。
- Windows 中文路径：所有文件 IO 显式 `encoding="utf-8"`，禁止依赖系统默认 GBK。
- 计算永远不进 GUI 线程：`numpy/scipy/sklearn/ortools` 必须在 `QThreadPool`/`QRunnable`
  或独立进程里，用 Signal 回主线程；在 `QWidget` 方法里直接算 = 界面假死，评审必拒。
- `pyqtgraph` 默认全量绘制百万点会卡：必须开 `setDownsampling`/`setClipToView`，
  超过 5 万点先降采样再画。
- OpenAI 与 Anthropic 协议**不是字段级兼容**：`system` 是否独立字段、`max_tokens` 命名、
  `stop` vs `stop_sequences`、流式事件名、工具调用结构都不同。禁止「一套 payload 到处发」。
- 「兼容」不等于「一致」：未在能力矩阵声明的能力 = 不可用，禁止静默降级或字段猜测。
- pre-commit 的密钥扫描是**兜底**，不是许可：`.env`、`*.key`、`secrets/`、
  `config.local.ini` 必须在 `.gitignore` 里。
- `CODEOWNERS` 是「最后匹配的规则生效」：治理目录的规则必须写在通配规则**之后**。
- CI 覆盖率门禁：**总行 ≥80%**、`app/ai/` 与 `solvers/` **≥90%**；文档里数字必须一致。
- 文档单文件 **≤200 行**，超了就拆并在入口文件索引里登记。

## 7. 不做什么（边界，越界即拒）

- ❌ 不生成业务实现代码、不写算法源码、不改目标仓库的 `app/` 或 `solvers/` 代码。
- ❌ 不引入第三方网关/代理（LiteLLM、one-api 等）：桌面端单机、两种协议、离线可解释、
  包体敏感，接入层自行实现（理由见 research-notes）。
- ❌ 不新增依赖：白名单外一律先停、先问人（提 RFC，架构负责人批）。
- ❌ 不改红线去「适配本次任务」。
- ❌ 不替用户执行 `git push`、`git rebase`、创建/合并 PR 等远端变更。

## 8. 写操作与删除操作（必须先确认）

- **写操作**：安装/覆盖治理文件、入口文件、pre-commit、CI 配置前，先输出「将创建 / 将覆盖」
  清单；目标已存在时**必须**得到人工明确确认（架构负责人），否则只输出差异报告，不落盘。
- **删除操作**：任何删除（删旧 SOP、删白名单条目、删 CI job、删 hook）**默认拒绝执行**，
  必须先出删除清单 + 影响面 + 回滚方式，人工逐项确认后才可执行；无确认时只打印计划。
- 安装路径冲突按「保留现状 + 差异报告」处理，不做静默覆盖。

## 9. 参考

- `references/research-notes.md`：调研过程、来源、关键设计决策与「自行决定」标记。
- `evals/evals.json`：5 条只读/语法夹具用例（命令 + 期望退出码 + 观测值），可逐条复跑。
