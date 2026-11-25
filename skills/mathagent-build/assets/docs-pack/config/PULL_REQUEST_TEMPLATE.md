<!-- PULL_REQUEST_TEMPLATE.md -->
## 变更摘要

<!-- 一句话：改了什么、为什么改。禁止只写「优化」「修复 bug」 -->

关联 issue：#<n>

## 变更类型

- [ ] feat（新功能）
- [ ] fix（缺陷修复）
- [ ] refactor / perf（无行为变化的整理或性能）
- [ ] docs / chore / ci
- [ ] 治理文件（`AGENTS.md` / `docs/agents/` / CI / CODEOWNERS）→ **需要架构负责人审批**

## 自检（全部勾选才能合并）

- [ ] `ruff check .` / `ruff format --check .` 通过
- [ ] `mypy mathagent` 通过（strict）
- [ ] `pytest -q` 通过；覆盖率：总 ≥80%，`mathagent/ai/` ≥90%，`mathagent/solvers/` ≥90%
- [ ] `pre-commit run --all-files` 通过（密钥扫描零新增）
- [ ] 无白名单外依赖（若有 → 已附 RFC 链接：）
- [ ] 提交信息符合 Conventional Commits
- [ ] 已确认本 PR 不含 `--no-verify`、不含直接推 main 的历史

## UI 证据（涉及 `mathagent/app/`、`resources/qss/`、`viz/` 时必填）

- [ ] 截图：默认态
- [ ] 截图：交互后
- [ ] 截图：异常态 / 空数据态
- [ ] 1280×720 与 1920×1080 无截断/重叠

## 算法证据（涉及 `mathagent/solvers/`、`core/` 数值契约时必填）

- [ ] `tests/regression/` 运行结果（指标 + 耗时对比）：
- [ ] 基线变化原因（如更新 expected）：由 reviewer 确认

## AI 接入证据（涉及 `mathagent/ai/` 时必填）

- [ ] 双协议契约测试通过（fixture 回放，无真实联网）
- [ ] 能力矩阵已更新（说明新增/变化的能力行）
- [ ] 日志脱敏用例通过（key/隐私不落日志）

## 发布证据（涉及 `packaging/`、版本号时必填）

- [ ] ❌ 禁止 `--onefile`：spec 仍为 onedir（`COLLECT`），无 UPX 压缩
- [ ] 干净机器冒烟记录（机器/系统/启动耗时）：
- [ ] 包体大小与 `SHA256SUMS.txt`

## 本次不改的内容

<!-- 明确写出范围外内容，避免评审误解（例如：不改历史数据格式、不动设置页布局） -->
