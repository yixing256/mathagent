# E 组连续线性规划内核验收记录

## 调用与结果

A 的 worker 可同步调用下例。数据和解可跨进程序列化。调用期间由调用方保持输入稳定，求解器借用可用的 float64 数组和 CSR 存储。C 传入的变量顺序同时标记目标向量与矩阵列，约束顺序标记矩阵行与右端项。错误位置从零开始计数，同时保留对应的实体 ID。

```python
from mathagent.core.lp_types import Constraint, Problem, SolveOptions, Variable
from mathagent.solvers import solve

problem = Problem(
    variables=(Variable("甲", "批", 0, 2), Variable("乙", "批", 0, 3)),
    objective=[3, 2], matrix=[[1, 1]],
    constraints=(Constraint("机时", "<=", "小时"),), rhs=[4],
    direction="max", objective_unit="万元",
)
result = solve(problem, SolveOptions(time_limit_seconds=30))
```

`result.objective` 为 10 万元。乙的上界诊断给出实际 2 批、上限 3 批、余量 1 批、违反量 0。等式残差采用实际值减指定值。逐项容差为 `1e-9 + 1e-7 × max(|实际值|, |限值|)`，最大违反量保留未取整的原值。失败时调用方可读 `issues` 和原始后端状态，目标值为空。超时由求解器返回达限，用户主动取消及退出工作进程由 A 裁决。

## 排产回归

参考值取自专业版记录的 R2026b Update 1 结果。耗时为本次单次编译、求解、回验之和，迭代数来自 SciPy 或矛盾边界预检。

| 案例 | 状态／业务核对 | 目标绝对误差 | 迭代 | 耗时 ms |
| --- | --- | ---: | ---: | ---: |
| M01 | 最优，甲 2、乙 2、利润 10 | 0 | 1 | 2.067 |
| M02 | 最优，甲 2、乙 1、利润 8 | 0 | 0 | 1.090 |
| M03 | 机时 −1，不可行 | — | 0 | 0.482 |
| M04 | 仅有非负下界，最大化时无界 | — | 0 | 0.416 |
| M05 | 负下界生效，最小值 −2 | 0 | 0 | 0.501 |
| M06 | 上下界矛盾，调用后端前返回不可行 | — | 0 | 0.060 |
| M07 | 矩阵超出一列，定位到机时行、第 3 列 | — | 无 | 0.026 |
| M08 | 稀疏、乙甲换序，利润 10 | 0 | 1 | 1.035 |
| M08b | 换序且机时 3，乙 1、甲 2、利润 8 | 0 | 0 | 0.866 |
| M09 | 最大化目标加常数 7，得到 17 | 0 | 1 | 0.597 |

## 性能与适用规模

参考机为 Intel Core Ultra 5 226V、Windows x64 build 26300，Python 3.11.18、NumPy 1.26.4、SciPy 1.14.1。每组先预热一次再计时五次。阶段和总耗时分别取中位数。矩阵存储为输入数值和稀疏索引占用的字节数。误差与违反量取五次最大值。

| 工作负载 | 非零元 | 矩阵字节 | 编译 ms | 求解 ms | 回验 ms | 总计 ms | 迭代 | 目标值 | 绝对误差 | 最大违反量 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 256 × 256 稠密 | 65,536 | 524,288 | 1.03 | 32.31 | 0.98 | 33.96 | 272 | 256 | 0 | 0 |
| 10,000 × 10,000 CSR | 100,000 | 1,240,004 | 16.83 | 155.08 | 34.53 | 207.62 | 10,692 | 10,000 | 0 | 1.78 × 10⁻¹⁵ |

两题均采用全一矩阵加单位阵的块结构。对所有约束求和可证明目标上界为变量数，全一解取到上界，题目和求解过程均无随机输入。标准稠密输入的编译与回验工作量随行列乘积增长，规范 CSR 按行数、列数及非零元数增长；未规范稀疏输入另需转换、排序及合并重复项。双单纯形耗时取决于实例与迭代数，最坏情形为指数级。一次独立的稀疏题 cProfile 测量中，linprog 累计约 148 ms，是主要耗时项。

对于极小目标或极端行系数，内核以正比例缩放后端输入，并在原始单位回验。有限边界达到 HiGHS 的无穷阈值（绝对值 ≥ 10²⁰），或缩放后仍会丢失非零系数时，返回 `numerical_failure` 及字段位置，调用方可调整单位后重算。

## 复验

在仓库根目录的白名单 Python 3.11 环境运行。

```powershell
python -m pytest -q --durations=5 --cov=mathagent --cov-fail-under=80
python -m pytest -q tests/solvers tests/regression --cov=mathagent.solvers --cov-fail-under=90
python -m mypy --strict mathagent
ruff check .
ruff format --check mathagent tests
python -m mathagent.numeric_smoke
python -m tests.regression.benchmark_lp
```

开发机上 124 项测试通过，当前 mathagent 总行覆盖率 98.13%，solvers 行覆盖率 98.00%。原生矩阵乘法、线性方程求解、CSR 创建和稠密／稀疏 LP 冒烟通过。应用代码仅引用白名单内的 NumPy、SciPy 和标准库。

全仓格式检查还指出 main 已有的 skills/mathagent-build/scripts/check_docs_pack.py 格式差异。团队签收还需 C 使用独立数据交叉复核，以及 A 在正式 onedir 程序中调用 `mathagent.solvers.smoke.run_numeric_smoke()`，在无 Python／Qt 的 Windows 上记录返回的版本和各检查项。
