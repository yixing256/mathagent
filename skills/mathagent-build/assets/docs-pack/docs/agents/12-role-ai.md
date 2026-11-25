# 12-role-ai.md — 双协议 AI 接入层约束

> 适用：`ai/**`、模型相关配置与测试。前置必读：`00-base.md`。

## 1. 分层与文件职责

`docs/agents` 目录`
ai/contracts.py    LLMRequest / LLMResponse / LLMChunk / ToolSpec / Usage / Capability
ai/errors.py       LLMError 分类（见 §5），禁止在别处 raise 裸 Exception
ai/capability.py   能力矩阵：provider_profile × capability → supported | unsupported | unknown
ai/profiles.py     厂商档案（名称、协议、base_url 来源、模型清单），不含密钥
ai/openai_adapter.py     OpenAI 兼容协议翻译
ai/anthropic_adapter.py  Anthropic 兼容协议翻译
ai/client.py       统一入口：选档案 → 选 adapter → 校验能力 → 发送 → 归一化
ai/redact.py       日志脱敏（key、手机号、赛题隐私）
ai/transport.py    httpx 客户端（超时/重试/取消/流式）
`docs/agents` 目录`

- ❌ 禁止在 `ai/` 之外出现 `openai` / `anthropic` / `httpx` 的 import（UI/算法层不知道协议存在）。
- 两个 adapter 各自只做「字段翻译 + 流式解析 + 错误归一化」，❌ 禁止在 adapter 里做业务 Prompt 拼装。

## 2. 统一契约（先定后写，不许各写一套）

- `LLMRequest`：`messages`（role/text/图片附件）、`system`、`max_tokens`、`temperature`、
  `stop`、`tools`、`response_format`、`model`、`stream`、`timeout_s`、`metadata`。
- `LLMResponse`：`text`、`tool_calls`、`finish_reason`（`stop|length|tool_calls|content_filter|error`）、
  `usage`（input/output/total）、`provider`、`model`、`latency_ms`、`raw_status`。
- 流式统一成 `LLMChunk(kind: text_delta|tool_delta|usage|done, ...)`；❌ 禁止把厂商事件名漏给上层。
- 上层只认 `LLMResponse`/`LLMChunk`；❌ 禁止上层读取适配器内部对象或原始 JSON。

## 3. 能力矩阵（唯一事实源，禁口头约定）

必填能力维度（每个 `provider_profile` 必须给出 `supported/unsupported/unknown`）：

| 能力 | 说明 | 处理策略 |
|---|---|---|
| `system_field` | system 是否独立字段（Anthropic 风格）还是 message 角色 | 由 adapter 按协议放置，上层只写 `system` |
| `max_tokens` | `max_tokens` / `max_completion_tokens` 命名差异 | 按档案声明的字段名发送，❌ 禁止两个都发 |
| `stop` | `stop` vs `stop_sequences`、最多几个 | 超上限则报 `UnsupportedCapability`，❌ 禁止静默丢弃 |
| `stream` | SSE 事件结构（`data:` 载荷 vs 命名事件） | adapter 解析后归一化 |
| `tools` | 函数调用 schema 是否支持/是否需 `tool_choice` | `unsupported` 时禁用工具入口，UI 灰掉 |
| `json_mode` | `response_format` / 原生 JSON | `unsupported` 时用「提示词 + 解析校验」并标注降级 |
| `vision` | 图片输入（base64 / URL 两种形状） | `unsupported` 时禁止选图 |
| `thinking` | 推理/思维链开关与预算字段 | `unknown` 时不下发该字段 |
| `usage` | 是否返回 token 用量 | 缺失时置 `None`，❌ 禁止用字符数估算冒充 |
| `cancel` | 是否支持中断流 | 不支持时只能「丢弃后续 chunk」并在 UI 说明 |

- ❌ 禁止「一套 payload 到处发」；❌ 禁止未知能力时静默猜测（必须 `unknown → 不下发 + 记录`）。
- 新增厂商 = 新增 `profiles.py` 条目 + 跑 §6 契约测试 + 补矩阵行；❌ 禁止只改 base_url 就上线。
- 各家「兼容」不一致的处理策略：**以契约测试实测为准，不以文档承诺为准**。文档说支持但测试失败的，
  矩阵标 `unsupported` 并在 UI 提示原因；矩阵与文档冲突时以测试结果为准。

## 4. 密钥与配置

- Key 来源优先级：环境变量 → 用户级 `.env`（仅本机、已 gitignore）→ Windows 凭据管理器（`keyring`）。
- Key 变量名固定：`MATHAGENT_LLM_API_KEY_<PROFILE>`；base_url 变量：`MATHAGENT_LLM_BASE_URL_<PROFILE>`。
- ❌ 禁止硬编码任何 Key/Token/base_url；❌ 禁止写进仓库、日志、异常栈、截图、测试 fixture。
- ❌ 禁止把 Key 存进 `config.ini`、注册表明文或前端状态；只能存凭据管理器或进程环境。
- 设置界面只显示「已配置/未配置 + 后 4 位」，❌ 禁止回显完整 Key。
- 启动时校验：缺失 Key 不是崩溃，而是把该档案标为「未配置」并给出获取指引。

## 5. 错误分类、超时与重试

- 分类（`LLMError.code`）：`auth`（401/403）、`rate_limit`（429）、`invalid_request`（400/422）、
  `context_length`（超长）、`content_filter`、`network`（连接/超时）、`protocol`（响应结构不符）、
  `canceled`（用户取消）、`unknown`。
- 超时：连接 10s、普通响应 120s、流式空闲 300s；❌ 禁止无超时调用。
- 重试：仅 `rate_limit` / `network` / 5xx，最多 2 次，退避 2s → 4s + 抖动；
  ❌ 禁止重试 `auth` / `invalid_request` / `content_filter`；❌ 禁止在流式已输出后重试（会产生重复内容）。
- 错误必须翻译成人话 + 下一步（如「Key 无效，请在设置中重新配置」），❌ 禁止把原始堆栈弹给用户。

## 6. 测试（AI 变更的必交证据）

- `tests/contract/` 用**录制的 JSON/SSE fixture** 跑两个 adapter：字段翻译、流式聚合、错误映射、
  矩阵一致性（矩阵说 supported 的必须有用例，说 unsupported 的必须有拒绝用例）。
- CI 里 ❌ 禁止真实联网调用（不稳定 + 泄密风险）；如需真机联调，走本地手动脚本，不提交结果。
- 覆盖率：`mathagent/ai/` ≥ 90%（`00-base.md` §4）。
- 脱敏测试：构造含 key/手机号的响应，断言日志中不出现原文。

## 7. ❌ 禁止清单（AI 专属）

- ❌ 禁止引入第三方网关/代理（LiteLLM / one-api / Ollama 服务端等）作为运行时依赖。
- ❌ 禁止在 adapter 里 `try: ... except Exception: pass`（吞掉协议错误）。
- ❌ 禁止把厂商原始响应直接进 UI 或进日志文件（先过 `redact`）。
- ❌ 禁止在没有对应契约测试的情况下改字段映射、改流式解析、改默认模型。
- ❌ 禁止把 `temperature` / `max_tokens` 等参数散落在业务代码里（集中在档案默认值 + 请求对象）。
