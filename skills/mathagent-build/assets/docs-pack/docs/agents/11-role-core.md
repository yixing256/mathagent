# 11-role-core.md — 算法 / 科学栈角色约束

> 适用：`solvers/**`、`core/**` 的数值契约、`tests/regression/**`。前置必读：`00-base.md`。

## 1. 数值契约（先定接口，再写实现）

- 输入/输出用 `core/` 的 dataclass：每个求解器声明 `Problem`（参数、约束、数据）与
  `Solution`（解、目标值、迭代信息、告警）。❌ 禁止用裸 `dict` 在层间传数据。
- 每个求解器必须声明：适用规模、时间复杂度量级、随机性（是否可复现）、失败模式。
- 随机过程必须显式 `seed`（默认 0）并可外部注入；❌ 禁止依赖全局随机状态。
- ❌ 禁止在求解器里 print / 弹窗 / 写日志到 stdout；只允许返回结构化告警。

## 2. 科学栈用法（踩坑结论）

- numpy：❌ 禁止在循环里逐元素 append；预分配 `np.empty` 或向量化。❌ 禁止对 `float` 做
  精确相等比较，用 `np.isclose`。
- pandas：❌ 禁止 `SettingWithCopyWarning` 式链式赋值，用 `.loc`；大表读取显式 `dtype`；
  中文 CSV 显式 `encoding="utf-8"` 或 `"gbk"`（按源文件实际，写清注释）。
- scipy：优化结果必须检查 `res.success` 与 `res.message`，❌ 禁止只看 `res.x`；
  `minimize` 必须给出 `method` 与 `options`（`maxiter`、`ftol`）。
- scikit-learn：❌ 禁止在 `fit` 前泄漏测试集（先 split 后 fit）；`random_state` 必须显式；
  预处理必须包进 `Pipeline`，❌ 禁止分别 fit 后手工拼接。
- ortools：必须设置时间上限（`max_time_in_seconds`）与 `log_search_progress=False`；
  ❌ 禁止无上限求解（会挂死 UI 任务）。
- statsmodels / sko 等：启动成本高的对象在 `services` 层做惰性单例，❌ 禁止每次调用重建大对象。

## 3. 数据与精度

- 统一单位与量纲（在 `core/units.py` 声明），❌ 禁止在不同函数里混用秒/毫秒、米/千米。
- 浮点容差集中定义在 `core/tolerance.py`（如 `RTOL=1e-6`, `ATOL=1e-9`），❌ 禁止散落魔法数。
- 缺失值：❌ 禁止隐式 `fillna(0)`；必须先声明策略（删除/插值/模型），并写进 `Solution.notes`。
- 大数据集（> 100MB）走分块或内存映射；❌ 禁止一次性读入后再复制三份。

## 4. 性能

- 热点函数先用 `pytest --durations` 或 `cProfile` 定位，❌ 禁止凭直觉「优化」。
- 单次求解超过 2 秒必须在 `services` 层变成可取消任务；超过 30 秒必须分片/给进度。
- ❌ 禁止在求解器内部开线程/进程池（并发由 `services` 统一管理，避免线程风暴）。
- 结果缓存只允许在 `services` 层做（键 = 问题参数哈希），❌ 禁止在纯函数里藏全局缓存。

## 5. 测试与回归（算法变更的必交证据）

- 单元测试：每个求解器至少 3 类用例——典型、边界（空/单点/极端量纲）、失败路径。
- 回归：`tests/regression/cases/` 放赛题输入，`tests/regression/expected/` 放基线结果；
  算法变更必须在 PR 里贴对比表：目标值、误差、耗时、迭代次数。
- ❌ 禁止「更新基线」当作修复（基线变化必须解释原因，由 reviewer 确认）。
- 数值测试断言必须带容差，❌ 禁止 `assert result == 0.123` 这种精确断言。

## 6. ❌ 禁止清单（算法专属）

- ❌ 禁止 import `PySide6`（算法层与 UI 完全解耦）。
- ❌ 禁止 import `app/`、`services/`；❌ 禁止读环境变量里的模型 Key。
- ❌ 禁止在 `solvers/` 里做网络请求（数据获取属于 `services`）。
- ❌ 禁止把实验性 notebook 代码直接贴进 `solvers/`（必须先清洗成函数 + 测试）。
- ❌ 禁止提交超过 5MB 的数据文件；大数据放外部存储并用下载脚本 + 校验和。
