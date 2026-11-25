# 21-sop-release.md — 示例 SOP 技能包：出一次 onedir 发布包

> 触发：要交付可双击运行的 Windows 版本、要发版、要验证打包。
> 前置必读：`AGENTS.md` → `00-base.md` §2 → `13-role-release.md`。

## 0. 前置条件（不满足不打包）

- [ ] 目标 commit 已合入 `main`，CI 全绿（lint + mypy + pytest + 覆盖率 80%/90%）。
- [ ] 版本号已更新（单一来源 `mathagent/__version__.py`），`pyproject.toml` 与 spec 引用一致。
- [ ] 干净 venv 可用；确认无系统级 PySide6（`python -c "import PySide6; print(PySide6.__file__)"`
      路径在 venv 内）。
- [ ] 发布说明草稿已写：变更摘要 / 已知限制 / 升级方式 / 回滚方式。

## 1. 构建

`docs/agents` 目录`bash
py -3.11 -m venv .venv-build
.venv-build\Scripts\activate
python -m pip install -e ".[dev]"
python -m pytest -q
pyinstaller --clean --noconfirm packaging/mathagent.spec
`docs/agents` 目录`

- ❌ 禁止加 `--onefile`；❌ 禁止加 UPX；❌ 禁止 `console=True`。
- 构建失败时先读 `build/mathagent/warn-mathagent.txt`，按缺失模块判断是否 `collect_all` 漏项；
  ❌ 禁止「加一堆 hiddenimport 重试」。

## 2. 产物核对（逐项）

- [ ] `dist/mathagent/mathagent.exe` 双击可启动，无黑窗、无缺 DLL 弹窗。
- [ ] `_internal/` 内有 PySide6 / scipy / numpy / sklearn。
- [ ] `_internal/PySide6/plugins/platforms/qwindows.dll` 存在。
- [ ] exe 属性版本 = `pyproject.toml` 版本。
- [ ] 无 `.env`、无本地配置、无 `tests/`、无 `.pyc` 源码残留。
- [ ] 记录未压缩总量与压缩后大小。

## 3. 干净机器冒烟（发布阻断项）

- [ ] 在另一台 Windows 10/11（无 Python、无 Qt、无本项目环境）解压整个 zip。
- [ ] 双击 `mathagent.exe`，等主窗口出现（记录冷启动秒数）。
- [ ] 主链路：新建工程 → 载入数据 → 求解（含取消一次）→ 出图 → 导出。
- [ ] 模型调用：配置 Key（用测试 Key）→ 发一次请求 → 断网再发一次看错误提示。
- [ ] 关闭再启动一次（热启动），无残留进程。
- [ ] 记录：机器型号/系统版本/启动耗时/异常与截图。

## 4. 出行包

`docs/agents` 目录`bash
# 在 dist 同级打包（示例命令形态，按实际版本号）
powershell Compress-Archive -Path dist\mathagent -DestinationPath mathagent-<version>-win64.zip
# 生成校验和
certutil -hashfile mathagent-<version>-win64.zip SHA256
`docs/agents` 目录`

- [ ] zip 内含整个 `mathagent/` 文件夹（❌ 禁止只发 exe）。
- [ ] `SHA256SUMS.txt` 与 zip 一并交付。
- [ ] ❌ 禁止把 `dist/`、zip 提交进仓库；走发布附件/内部分发。

## 5. 发布

- [ ] 打 tag：`v<version>`（附发布说明）。
- [ ] 发布说明含：变更摘要、体积、启动耗时、已知限制、**升级方式 = 整包替换**、回滚 = 用上一版 zip。
- [ ] 通知相关人：版本、zip 校验和、已知问题。

## 6. 完成判据

- [ ] 干净机器冒烟记录 + 截图齐全。
- [ ] zip + SHA256 已交付，发布说明已发。
- [ ] 上一版 zip 仍可下载（回滚可用）。
- [ ] 若本次发现打包问题，已在复盘里写成条目（见 `README.md` 第 3.5 节）。

## 7. 常见错误

| 现象 | 根因 | 正确处理 |
|---|---|---|
| 干净机器缺 DLL | 科学栈未 `collect_all` | spec 补齐 collect_all，重建 |
| 用的是旧 Qt | 系统级 PySide6 被选中 | 干净 venv 重建 |
| 首启 20s+ | 用了 onefile（❌ 禁止：每次启动解压） | 改回 onedir |
| 资源找不到 | `__file__` 拼路径 | 运行期解析 |
| 杀软报毒 | UPX 压缩 | 关闭 UPX 重建 |
| 升级后崩溃 | 只替换了 exe | 整目录替换 |
