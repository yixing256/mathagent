# 13-role-release.md — 打包 / 发布角色约束

> 适用：`packaging/**`、`*.spec`、版本号、发布流程。前置必读：`00-base.md` §2。

## 1. 交付形态（硬性，重复次数不限）

- PyInstaller **onedir**：`Analysis → PYZ → COLLECT`。产物 = `dist/mathagent/` 整个文件夹，
  用户双击其中 `mathagent.exe`。
- ❌ 禁止 `--onefile`；❌ 禁止用 `zipapp` / `cx_Freeze` / `Nuitka` 替代；❌ 禁止打包成安装器以外
  的「自解压 exe」来伪装 onedir。
- ❌ 禁止在 spec 里写任何 Rust / PyO3 / maturin / C++ 扩展相关的 `hiddenimports`、`binaries`、hook。
- ❌ 禁止依赖开发机的系统级 PySide6：打包必须在**干净 venv** 里做（PyInstaller 会静默选中系统 Qt）。

## 2. spec 骨架（约束项，不是实现代码）

- `datas / binaries / hiddenimports` 用 `collect_all("PySide6")`、`collect_all("scipy")`、
  `collect_all("numpy")`、`collect_all("sklearn")` 合并结果，❌ 禁止手写零散 `datas` 猜测路径。
- `excludes` 必须排除测试与无用后端：`tests`、`matplotlib.tests`、`tkinter`、`PySide6.QtWebEngine*`、
  `PyQt5`、`PyQt6`。❌ 禁止排除 `PySide6.QtCore` 等核心模块。
- `console=False`（GUI 程序，无黑窗）；❌ 禁止 `console=True` 交付给用户。
- `icon`、`version`（Windows 版本资源）、`name="mathagent"` 三者与 `pyproject.toml` 版本一致。
- ❌ 禁止启用 UPX 压缩（杀软误报率高，得不偿失）；如需减小体积，走排除模块与精简依赖。
- 生成物 `dist/mathagent/_internal/` 由 PyInstaller 6 自动产生，❌ 禁止手工改其结构。

## 3. 打包步骤（照做，不改顺序）

1. 干净环境：新建 venv → `python -m pip install -e ".[dev]"` → 确认 `python -c "import PySide6"` 版本
   与白名单一致；确认系统 site-packages 无 PySide6。
2. `python -m pytest -q` 全绿 + 覆盖率门禁通过（不绿不打包）。
3. `pyinstaller --clean --noconfirm packaging/mathagent.spec`。
4. 产物核对（见 §4 清单）+ 本机冒烟。
5. 干净机器冒烟（另一台 Windows 10/11，无 Python、无 Qt）：双击 exe，走一遍「新建工程 → 载入数据 →
   求解 → 出图 → 导出」主链路。
6. 产出发行包：`mathagent-<version>-win64.zip` + `SHA256SUMS.txt`；❌ 禁止直接分发 `dist/` 目录或提交进仓库。

## 4. 产物核对清单（逐项打勾，缺一即失败）

- [ ] `dist/mathagent/mathagent.exe` 存在且双击启动（无黑窗、无缺 DLL 弹窗）
- [ ] `dist/mathagent/_internal/` 存在，内含 `PySide6`、`scipy`、`numpy`、`sklearn` 相关目录
- [ ] Qt 平台插件存在：`_internal/PySide6/plugins/platforms/qwindows.dll`
- [ ] 科学栈二进制齐全：`scipy` 的 `.dll`、`sklearn` 的 `.dat/.pyd` 未被剪掉
- [ ] 首启可用：冷启动 ≤ 8s（参考机），主窗口 3s 内可见
- [ ] 资源可加载：QSS、图标、默认配置在打包后可读（无「资源不存在」）
- [ ] 版本一致：exe 属性版本 = `pyproject.toml` = 关于对话框
- [ ] 体积记录：onedir 未压缩总量与压缩后大小写进发布说明
- [ ] 无残留：`dist/` 内无 `.pyc` 源码、无 `tests/`、无 `.env`、无本地配置
- [ ] 干净机器冒烟通过（记录机器与系统版本）

## 5. 版本与发布

- SemVer：`MAJOR.MINOR.PATCH`；破坏性数据格式变更 → MAJOR。
- 版本号单一来源：`mathagent/__version__.py`，`pyproject.toml` 与 spec 引用同一值；❌ 禁止三处各写一份。
- 发布说明必须含：变更摘要、已知限制、升级方式（覆盖整个文件夹，❌ 禁止只替换 exe）、
  回滚方式（保留上一版 zip，解压即回滚）。
- ❌ 禁止在发布分支上做功能开发；发布只允许版本号 + 发布说明 + 必要修复。

## 6. 失败处理

- 打包失败先看 `build/mathagent/warn-mathagent.txt` 的缺失模块，❌ 禁止「加一堆 hiddenimport 试」。
- 干净机器缺 DLL：优先用 `collect_all` 修，❌ 禁止把 DLL 手工拷进 `dist/` 后当作修复。
- 启动即崩：先在**同一台干净机器**上用 `console=True` 临时构建取堆栈，定位后改回 `False`。
- ❌ 禁止把「本机能跑」当作发布通过；❌ 禁止绕过 §4 清单发版。

## 7. ❌ 禁止清单（发布专属）

- ❌ 禁止 `--onefile`、❌ 禁止 UPX、❌ 禁止 `console=True` 交付。
- ❌ 禁止在开发机系统 Python 里打包（复用全局 site-packages）。
- ❌ 禁止提交 `build/`、`dist/`、`*.spec` 生成物之外的临时目录。
- ❌ 禁止无干净机器冒烟记录就宣布「发布完成」。
