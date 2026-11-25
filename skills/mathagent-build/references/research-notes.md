# research-notes.md — 调研过程与设计决策依据

> 用途：让人能审阅「mathagent-build 治理包为什么长这样」。只记录**思路、API 用法、取舍、踩坑**，
> 不含任何可直接粘贴进项目的第三方实现代码。凡属本地判断均标 **自行决定**。

## 一、调研过程（含失败与降级，如实记录）

| 步骤 | 通道 | 查询 | 结果 |
|---|---|---|---|
| 1 | `learn_code_from_web`（GitHub→Gitee） | AGENTS.md 约定 + PySide6 桌面项目结构 | `ok=false`：GitHub=empty、Gitee=empty |
| 2 | `learn_code_from_web` | PySide6 / PyInstaller `collect_all` onedir 打包 | `ok=false`，同上，降级深度到上限 |
| 3 | `learn_code_from_web`（单源） | 国产模型协议适配 | 无可用结果（插件要求确认后继续） |
| 4 | `web_search` | AGENTS.md 标准、PyInstaller 体积/启动、LiteLLM 协议映射 | 命中官方规范与文档，作为设计依据 |
| 5 | `web_fetch`（一手资料） | agents.md / Qt 部署文档 / Conventional Commits / pre-commit / GitHub CODEOWNERS | 全部 HTTP 200，见 §二 |

**结论**：插件三源本轮均无可解析结果，**未据此编造来源**。设计依据全部来自第 4/5 步可点开的
公开一手资料；本地判断（覆盖率数字、目录命名、体积目标）在 §三 标注「自行决定」。
这是无人值守场景下按「只读、保守」原则做的选择，未对任何远端做写操作。

## 二、来源 → 提炼 → 落成

### 1. AGENTS.md（[agents.md](https://agents.md)）
- **事实**：开放格式，无必需字段；目录树中**最近的一份优先**；用户当场指令优先级最高；
  官方建议放「项目概览 / 构建测试命令 / 代码风格 / 安全注意 / PR 约定」。
- **提炼**：入口文件必须是「短、可索引、含命令」，细则就近放到更具体的一层。
- **落成**：根 `AGENTS.md` 只保留五条红线摘要 + 固定命令 + 读文件顺序；
  细则按角色拆到 `docs/agents/10~13`，任务级流程拆到 `20/21` SOP。

### 2. Qt for Python 官方 PyInstaller 文档（[Qt 部署](https://doc.qt.io/qtforpython-6/deployment/deployment-pyinstaller.html)）
- **事实**：`--onefile` 与 `--onedir` 是两种形态；onedir 产出 `dist/<name>/` 目录 + 同名可执行文件；
  **若系统装了 PySide6/shiboken6，PyInstaller 会静默使用它而不是 venv 里的版本**（官方明确警告）。
- **提炼**：交付形态锁 onedir 有官方依据；打包必须在干净环境，且打包前确认 venv 内 Qt 版本。
- **落成**：`13-role-release.md` §3 打包步骤 + `21-sop-release.md`；
  「旧 Qt 混入」写成 §7 常见错误条目。

### 3. Conventional Commits 1.0.0（[规范](https://www.conventionalcommits.org/en/v1.0.0/)）
- **事实**：`type(scope): subject` + 可选正文 + 可选 footer；`!` / `BREAKING CHANGE` 表示破坏性；
  feat→MINOR、fix→PATCH；其它 type（build/ci/docs/...）允许。
- **提炼**：类型白名单 + 「一个提交只做一件事」+ squash 合并时由负责人统一措辞。
- **落成**：`00-base.md` §3 提交规范、pre-commit 的 `commit-msg` 钩子、PR 模板的自检项。

### 4. pre-commit 官方文档（[pre-commit.com](https://pre-commit.com/)）
- **事实**：`repo: local` 可承载任意语言/系统命令；`pre-commit run --all-files` 可在 CI 复用同一配置；
  `language: fail` / `pygrep` 适合做「禁止某模式」的轻量守卫。
- **提炼**：**统一用 local 钩子**——国产化/内网环境可换镜像，不把外部仓库地址写进配置；
  本地与 CI 共用一份配置，避免「本地过、CI 挂」。
- **落成**：`config/.pre-commit-config.yaml`（全部 local）+ CI 的 `pre-commit run --all-files`。

### 5. GitHub CODEOWNERS 文档（[About code owners](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners)）
- **事实**：**最后匹配的规则生效**；CODEOWNERS 自身也要指定 owner 才真正受保护；
  语法里 `!` 取反与 `[ ]` 字符范围不生效。
- **提炼**：保护 `docs/agents/` 的规则必须写在通配规则之后；并给 `/CODEOWNERS` 单独指定 owner。
- **落成**：`config/CODEOWNERS` 的顺序 + 末尾 `/CODEOWNERS @repo-owner`。

### 6. LiteLLM 协议映射文档（[messages ↔ responses 参数映射](https://docs.litellm.ai/docs/anthropic_unified/messages_to_responses_mapping)）
- **事实**：Anthropic `/v1/messages` 与 OpenAI 风格接口需要逐参数翻译：`system` 的放置、
  `max_tokens` 的命名、`stop` vs `stop_sequences`、工具结构、流式事件形态、用量字段都不同。
- **提炼**：跨协议「一套 payload 通吃」必然出问题；需要**统一契约 + 分协议 adapter + 能力矩阵**。
- **取舍（自行决定）**：不自建网关进程、也不引 LiteLLM/one-api 作为运行时依赖——本项目是单机桌面、
  只有 2 种协议、要求离线可解释且包体敏感；网关会多一跳网络、一棵依赖树、一类升级漂移。
  改为在进程内实现两个 adapter（`httpx` 传输），把差异固化进能力矩阵。
- **落成**：`12-role-ai.md` 的能力矩阵、错误分类、超时/重试预算、契约测试要求。

### 7. PyInstaller / 科学栈的社区经验（[PySide6 打包实践](https://www.volcengine.com/article/3433010) 等）
- **事实**：onedir 启动显著快于 onefile（onefile 每次启动解压到临时目录，且易被杀软误报）；
  科学栈缺 `.dll`/`.dat` 多由未收集 `datas/binaries` 造成；UPX 会提高误报率。
- **提炼**：`collect_all` 收齐 PySide6/scipy/numpy/sklearn；不启用 UPX；资源路径运行期解析。
- **落成**：`13-role-release.md` §2/§4、`20-sop-ui-change.md` 资源路径条目。

## 三、本地判断（**自行决定**，可被架构负责人改）

| 项 | 取值 | 依据 |
|---|---|---|
| 覆盖率门禁 | 总行 80%；`ai/` 与 `solvers/` 各 90% | 错误代价不对称：模型调用与算法结论错最贵；UI 用冒烟+截图兜底 |
| 目录分层 | `app/core/solvers/viz/ai/services/resources/packaging` | 依赖单向、多人并行冲突面最小 |
| 文档行数上限 | 单文件 ≤200 行 | 智能体按需加载，长文挤占上下文 |
| 超时/重试 | 连接 10s / 响应 120s / 流式空闲 300s；仅 429/5xx/网络重试 ≤2 次 | 桌面交互可等待但不可挂死；无超时=最坏体验 |
| 版本策略 | SemVer + 单一版本来源 | 三处各写一份必然漂移 |
| 首次发布体积目标 | 未压缩 ≤300MB（记录而非硬门禁） | onedir + 科学栈的现实量级，先观测再收紧 |

## 四、没做的事（边界）

- 未对任何远端仓库执行写操作（无人值守只读策略）：不建分支、不建 PR、不推送。
- 未实测各家国产模型的「兼容」能力：`12-role-ai.md` 要求用契约测试实测后写矩阵，
  文档本身**不替厂商背书**，避免把传闻写成事实。
