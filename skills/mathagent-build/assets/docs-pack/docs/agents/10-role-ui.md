# 10-role-ui.md — UI / 交互角色约束

> 适用：`app/**`、`resources/qss/**`、`viz/**`、任何用户可见行为。前置必读：`00-base.md`。

## 1. 结构分层

- `app/main_window.py` 只做装配（菜单/工具栏/状态栏/停靠），❌ 禁止在窗口类里写业务计算。
- `app/views/` 放纯展示控件；`app/viewmodels/` 放状态与信号；`app/services_bridge.py` 负责把
  `services` 的异步任务接成 Qt 信号。❌ 禁止 view 直接 import `solvers`。
- 一个窗口一个职责；❌ 禁止 800 行以上的窗口类（超了就拆 `views/<feature>/`）。

## 2. 样式（QSS）

- 所有颜色、间距、字号进 `resources/qss/tokens.qss`（变量注释块），❌ 禁止在控件里写
  `setStyleSheet("color:#123456")` 这种一次性内联样式。
- 组件样式集中在 `resources/qss/components.qss`；页面级覆盖只允许 `#objectName` 选择器。
- ❌ 禁止用 QSS 做布局（`margin` 拼版式）；布局用 `QVBoxLayout/QHBoxLayout/QGridLayout`。
- 高 DPI：使用 `pt`/`px` 明确单位，图标提供 1x/2x；❌ 禁止位图硬缩放导致模糊。
- 主题切换只在 token 层做，❌ 禁止在两套 QSS 里复制粘贴组件样式。

## 3. 线程与响应

- ❌ 禁止主线程做任何 > 16ms 的工作（计算、IO、网络、模型调用）。
- 长任务必须是可取消的 `QRunnable`，UI 提供「取消」；取消后必须回收资源并复位状态。
- 进度反馈：任务开始 ≤ 200ms 内出现忙碌指示；❌ 禁止「点了没反应」。
- ❌ 禁止在 `paintEvent` / `resizeEvent` 里做重计算或创建控件。

## 4. 交互与状态

- 每个耗时操作三态齐全：进行中 / 成功 / 失败（失败必须有可读原因 + 下一步建议）。
- ❌ 禁止阻塞式弹窗轰炸；同一错误只提示一次，详情进日志面板。
- ❌ 禁止静默忽略用户输入（非法输入要就地校验 + 说明）。
- 危险操作（删除工程、覆盖结果、清空数据）必须二次确认，并说明影响面。

## 5. 资源与本地化

- 资源统一走 `services/resources.py` 的 `resource_path()`（打包后指向 `_internal`）。
- ❌ 禁止 `Path(__file__).parent / ...` 拼资源路径。
- 文案集中管理（`app/i18n/zh_CN.py` 或等价文件）；❌ 禁止在 QSS/控件里散落硬编码长文案。
- 中文字体显式设置（如 `Microsoft YaHei UI`），❌ 禁止依赖系统默认字体导致方框。
- Windows 中文路径：所有文件对话框返回路径直接可用，❌ 禁止对路径做 `encode()`/`decode()`。

## 6. 图表（pyqtgraph）

- 数据点 > 5 万：必须 `setDownsampling(auto=True, mode='peak')` + `setClipToView(True)`。
- 重绘频率 > 10Hz 必须节流；❌ 禁止在循环里 `clear()` + 全量重画。
- 坐标轴单位、图例、导出（PNG/SVG）在 `viz/` 内统一封装；❌ 禁止各页面各写一套。
- 绘图数据来源必须是 `core/` 的只读结果对象，❌ 禁止直接持有 `numpy` 大数组副本多份。

## 7. UI 变更的交付证据（缺一不可）

- 截图三张：默认态 / 交互后 / 异常态（或空数据态）。
- 变更前后对比（像素或描述），说明是否影响布局在 1280×720 与 1920×1080 下正常。
- 若涉及样式令牌：贴出 token 变更 diff。
- `pytest tests/ui_smoke -q` 通过；❌ 禁止只手动点一遍就算验收。

## 8. ❌ 禁止清单（UI 专属）

- ❌ 禁止在 UI 层出现 `requests` / `httpx` / `openai` / `anthropic` 的 import。
- ❌ 禁止把 API Key 显示在输入框默认值里（只能显示掩码 + 「已配置」状态）。
- ❌ 禁止在界面里出现未完成的占位按钮（可见即必须可用，否则隐藏）。
- ❌ 禁止改动 `resources/qss/tokens.qss` 只为「一次看起来更好看」而不更新设计记录。
