# AGENTS.md — 数学建模桌面软件（mathagent）

> 本文件是**所有人与所有智能体的唯一入口**。它不是文档目录，而是「读什么、做什么、什么不许做」的契约。
> 完整约束在 `docs/agents` 目录；本文件只做索引 + 红线摘要。**只写约束与流程，不写业务实现。**

## 1. 项目一句话

Windows 单平台、独立运行的数学建模桌面软件：**PySide6 界面 + Python 科学栈算法内核 + 双协议 AI 接入层**
（OpenAI 兼容协议 / Anthropic 兼容协议，接国产大模型）。首版不含 Rust 与 WebView。

## 2. 开工前必读（按序，不许跳读）

1. 本文件（`AGENTS.md`）
2. `00-base.md` — 全局红线（不可协商）
3. `docs/agents/README.md` — 《技能的使用说明》：读什么、怎么启用、何时加载哪个包、谁能改
4. 对应角色包（`10-role-ui.md` / `11-role-core.md` / `12-role-ai.md` / `13-role-release.md`）
5. 对应 SOP（`20-sop-ui-change.md` / `21-sop-release.md`）

❌ 禁止在未读 1-3 的情况下改代码、改依赖、改 CI。
❌ 禁止把 `docs/agents` 目录下的约束「按本次任务需要」自行放宽。

## 3. 环境与固定命令

| 用途 | 命令 |
|---|---|
| 建环境 | `py -3.11 -m venv .venv` → `.venv\Scripts\activate` |
| 装依赖 | `python -m pip install -e ".[dev]"`（只允许白名单内依赖） |
| 跑界面 | `python -m mathagent` |
| 跑测试 | `pytest -q` |
| 覆盖率 | `pytest --cov=mathagent --cov-report=term-missing`（门禁：总 80%，`mathagent/ai/`、`mathagent/solvers/` 各 90%） |
| 静态检查 | `ruff check .` / `ruff format --check .` |
| 类型检查 | `mypy mathagent`（strict，禁止新增 `# type: ignore` 无理由注释） |
| 密钥扫描 | `pre-commit run detect-secrets --all-files` |
| 打包 | `pyinstaller packaging/mathagent.spec`（onedir，禁止 `--onefile`） |
| 治理包自检 | `python scripts/check_docs_pack.py --kit <本技能包>/assets/docs-pack --target .` |

## 4. 五条红线（摘要，全文见 `00-base.md`）

1. ❌ 禁止引入 Vue / React / Electron / Tauri / PyWebView / WebView2 / Rust / PyO3 / maturin / C++ 扩展；
   只允许 Python + PySide6 + QSS。**任何新依赖先停下问人**，不得自行 `pip install`。
2. ❌ 禁止 `--onefile`；只允许 PyInstaller **onedir（COLLECT）**：一个文件夹 + 双击其中 exe。
   spec 必须 `collect_all` 收齐 PySide6 / scipy / numpy / sklearn，首版不写 Rust 相关 hiddenimport。
3. ❌ 禁止提交任何 API Key / Token / 密码 / `.env` / 密钥文件；`.gitignore` 必须覆盖
   `.env/`、`*.key`、`secrets/`、`config.local.ini`，pre-commit 必须有密钥扫描兜底。
4. ❌ 禁止 `git push --force` 到 `main`、禁止 `--no-verify` 跳过钩子、禁止直接向 `main` 提交；
   必须走 PR + CODEOWNERS 审批。
5. ❌ 禁止在 GUI 线程做数值计算；禁止 `__file__` 拼资源绝对路径（打包后必错）。

## 5. 提交与 PR 门禁

- 分支：`feat/<issue>-<slug>`、`fix/`、`docs/`、`chore/`、`refactor/`、`test/`、`perf/`、`ci/`。
- 提交信息：Conventional Commits（`type(scope): subject`，正文说明动机与影响）。
- PR 必须通过：pre-commit、ruff、mypy、pytest + 覆盖率门禁、密钥扫描、`docs/agents` 目录保护检查。
- 涉及 UI 变更：❌ 禁止无截图合入（PR 模板必填项）。
- 涉及算法变更：❌ 禁止无赛题回归结果合入（`tests/regression/` 输出 + 指标对比）。
- 涉及 AI 接入变更：❌ 禁止无「双协议契约测试 + 能力矩阵更新」合入。

## 6. AI 接入（摘要，全文见 `12-role-ai.md`）

- 统一请求/响应模型 + **两个独立 adapter**；不引第三方网关（LiteLLM / one-api 等）。
- Key 只来自环境变量 / `.env` / Windows 凭据管理器，❌ 禁止写入代码、日志、截图、提交历史。
- 「兼容」不代表一致：未在能力矩阵声明的能力 = 不可用，❌ 禁止静默降级与字段猜测。

## 7. 谁能改这份文件

`AGENTS.md`、`docs/agents` 目录、`CODEOWNERS`、`dependency-whitelist.txt`
**只能由架构负责人（CODEOWNERS 中的 `@mathagent-core`）审批后修改**；其他人提交会被 CI 的
`agents-pack-guard` job 直接拒绝（见 `README.md` 第 3.4 节）。
