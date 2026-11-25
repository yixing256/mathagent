# 00-base.md — 全局红线（不可协商）

> 适用于所有人 + 所有智能体 + 所有分支。与其它文件冲突时**以本文件为准**。
> 修改本文件：仅架构负责人审批。单文件 ≤200 行。

## 0. 优先级与解释权

1. 本文件 > 角色包 > SOP > 任何任务描述。
2. 智能体与人的指令冲突时，**停下并上报**，不得自行选择「更省事」的一方。
3. 规则与「一个月交付」冲突时，砍功能，不砍规则。

## 1. 技术栈锁定（硬性）

- 允许：Python 3.11.x、PySide6 6.7.x、QSS、numpy / scipy / pandas / scikit-learn / ortools /
  statsmodels / pyqtgraph / matplotlib（静态图）、httpx。
- ❌ 禁止 Vue / React / Electron / Tauri / PyWebView / WebView2 / QtWebEngine（本项目不做 Web UI）。
- ❌ 禁止 Rust / PyO3 / maturin / C++ 扩展 / Cython（Rust 仅作 v2 备选，首版一行不写）。
- ❌ 禁止任何需要编译工具链的依赖（Windows 上「装不上」的依赖等于「交付不了」）。
- **新增依赖流程（缺一不可）**：① 提 RFC issue（用途/替代方案/包体影响/许可证/是否纯 Python）
  ② 架构负责人批准 ③ 更新 `dependency-whitelist.txt`（带版本上限）④ 更新
  `pyproject.toml` 与锁文件 ⑤ 打包冒烟。❌ 禁止先 `pip install` 再补流程。
- ❌ 禁止在代码里 `import` 白名单外的第三方包（CI 的 `whitelist-check` 会拦）。

## 2. 交付形态（硬性）

- 只允许 **PyInstaller onedir**：`Analysis → PYZ → COLLECT`，产物为 `dist/mathagent/` 文件夹，
  用户双击其中 `mathagent.exe` 启动。
- ❌ 禁止 `--onefile`（启动要解压到临时目录 → 慢 + 杀软误报 + 资源路径全错）。
- spec 必须用 `collect_all` 收齐 **PySide6 / scipy / numpy / sklearn** 的
  `datas / binaries / hiddenimports`。
- ❌ 首版禁止写任何 Rust / PyO3 / maturin 相关的 `hiddenimports` 或 hook。
- ❌ 禁止依赖系统级 Qt：打包环境必须是干净 venv（否则 PyInstaller 会静默用系统 PySide6）。
- ❌ 禁止把 `.venv`、`build/`、`dist/`、`.secrets.baseline` 之外的本地产物提交进仓库。

## 3. Git 与提交安全（硬性）

- ❌ 禁止提交 API Key / Token / 密码 / `.env` / `*.key` / `*.pem` / 证件证书 / 含密钥的截图。
- 根 `.gitignore` 必须包含：`.env`、`.env/`、`*.key`、`*.pem`、`secrets/`、`config.local.ini`、
  `.venv/`、`build/`、`dist/`、`__pycache__/`。
- pre-commit 必须包含密钥扫描兜底（`detect-secrets` + 自定义正则钩子）；❌ 禁止删钩子或放宽
  `.secrets.baseline` 来「修好」扫描失败。
- ❌ 禁止 `git commit --no-verify`、❌ 禁止 `git push --force` 到 `main`、
  ❌ 禁止直接向 `main` 提交（`main` 由分支保护 + CODEOWNERS 审批保护）。
- 提交信息遵循 Conventional Commits：`type(scope): subject`；type 仅限
  `feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert`；一个提交只做一件事。
- 分支命名：`feat/<issue>-<slug>`、`fix/<issue>-<slug>`、`docs/`、`test/`、`perf/`、`ci/`、`chore/`。
- ❌ 禁止在 PR 中混入无关格式化改动（会淹没评审，破坏 blame）。

## 4. 合并门禁（数字写死，不许口头放宽）

- lint：`ruff check` + `ruff format --check` 零错误。
- 类型：`mypy mathagent` strict 零错误。
- 测试：`pytest` 全绿。
- 覆盖率（行覆盖率，`--cov-branch` 不单独设门禁）：**总 ≥ 80%**；
  **`mathagent/ai/` ≥ 90%**；**`mathagent/solvers/` ≥ 90%**。
- 密钥扫描：`detect-secrets` 零新增命中。
- 依赖：`whitelist-check` 通过（无白名单外 import）。
- 治理包：`agents-pack-guard` 通过（约束文件改动必须架构负责人批准）。
- UI 变更：❌ 禁止无截图（三态：默认/悬停或交互后/异常态）。
- 算法变更：❌ 禁止无赛题回归结果（`tests/regression/` 输出 + 指标与耗时对比表）。
- AI 接入变更：❌ 禁止无「双协议契约测试 + 能力矩阵更新」。
- ❌ 禁止「先合入再补测试/再补文档」；缺证据 = 未完成。

## 5. 代码结构与依赖方向

- 目录：`app/`(PySide6 UI) `core/`(领域模型与契约) `solvers/`(算法) `viz/`(pyqtgraph)
  `ai/`(接入层) `services/`(任务编排/导出) `resources/`(QSS/图标) `packaging/`。
- 依赖方向单向：`app → services → (core, solvers, ai, viz)`。❌ 禁止反向 import：
  `solvers` 不许 import `app`/`services`；`ai` 不许 import `app`；`core` 不许 import 任何其它层。
- ❌ 禁止跨层「顺手拿一下」：UI 不直接调 `solvers`，必须经 `services` 的任务接口。
- 数据结构用 `dataclasses` / `pydantic`（白名单内）定义在 `core/`；❌ 禁止把 UI 控件或
  `QObject` 传进算法层。
- ❌ 禁止循环依赖、❌ 禁止 `from x import *`、❌ 禁止在 `__init__.py` 里做重逻辑。
- 公共接口必须有类型注解；❌ 禁止无说明的 `Any`、❌ 禁止裸 `except:`。

## 6. 线程、资源与性能

- ❌ 禁止在 GUI 线程执行数值计算、文件大批读写、网络请求、`time.sleep`。
- 统一用 `QThreadPool` + `QRunnable`（或受控的 `QThread`）承载任务，结果用 `Signal` 回主线程；
  任务必须支持取消，UI 必须有进度与失败提示。
- ❌ 禁止在 worker 里碰任何 `QWidget`（只能在主线程更新 UI）。
- 大数据（> 5 万点）绘图必须先降采样（`setDownsampling` / `setClipToView`）。
- 资源路径只允许运行期解析（打包后 `_internal` 目录），❌ 禁止 `__file__` 拼绝对路径、
  ❌ 禁止把资源路径写进配置文件当常量。
- 文件 IO 显式 `encoding="utf-8"`；❌ 禁止依赖系统默认编码（Windows 中文环境是 GBK）。

## 7. 安全与合规

- 网络：只允许出站到用户显式配置的模型服务地址；❌ 禁止硬编码服务地址、❌ 禁止明文 HTTP（必须 HTTPS）。
- 日志：❌ 禁止打印完整请求体/响应体中的密钥与个人信息；只允许打印脱敏后缀（后 4 位）与状态码。
- 遥测：❌ 首版禁止任何未经用户同意的数据上报。
- 第三方许可证：新增依赖必须许可证兼容（禁 GPL 系进闭源分发前需法务确认）。

## 8. 违规处理

- 违反 §1–§3（技术栈/交付形态/提交安全）：PR 直接关闭，不计入工作量，责任人补复盘。
- 违反 §4 门禁：CI 失败即视为未完成，❌ 禁止求「这次先合」。
- 发现已合入的违规：当周内开修复 PR，并在复盘中写成条目（见 README 第 3.5 节）。
