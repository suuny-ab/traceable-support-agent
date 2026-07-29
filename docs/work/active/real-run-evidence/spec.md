# 增量说明

> 状态：`developing`
>
> 复杂度：标准
>
> 外部风险：`R0`（仅本地代码、测试与文档；无网络、无费用、无外部写入）
>
> 成熟度：产品保持 `S1 公开 Beta`、生产 `replay_only`；本候选不启用实时模式

## 用户结果

未来经独立授权的真实 Provider 运行所产生的证据今天无法落地：transcript 合同只接受
`offline_injected` 事实（真实 transcript 会被拒绝），产品运行包不携带 transport
观察记录，控制面只持久化公开投影。本增量让未来授权真实运行的证据可持久化、可复核、
可复现，同时公开 API 合同、公开响应形状、预算常量和生产 `replay_only` 姿态完全不变。

## 当前问题与证据

- `provider/contract.py` 的 `_validate_attempt` / `validate_transcript` /
  `finalize_transcript` 硬编码 offline-only 事实（`execution_mode=="offline_injected"`、
  network / DNS / credential / paid 计数全为 0）；manifest 声明
  `tg07a_execution_mode: "offline_injected_only"` 与
  `real_transport_wiring_status: "not_connected_until_tg07b"`，与
  `AuthorizedRealTransport` 已评审存在的事实不符。
- `run_qa` / `run_ticket` 不把 `transport.safe_observations()` 放进运行包；控制面
  `runs.result_json` 只保存公开投影，观察记录随进程结束丢失。
- `tools/generation_contract_probe.py --mode offline` 需要的
  `generation-contract-probe-offline-v1` 响应夹具未提交，离线探针无法仅凭仓库内容
  端到端运行。

## 最便宜证伪

- 用 `DeepSeekContentAdapter` 与手工构造的 attempt 记录直接调用 `validate_transcript`：
  连贯 `authorized_real` transcript（含 transport 可产生的 credential_missing、
  零 network transport_error、两种 response_too_large 形状）必须通过；offline 携带
  network 事实、real 成功 attempt 零 network、real 账单标记非 `None`、任一模式
  `automatic_retry_count>0`、计数与记录不一致、混合模式必须按固定 code 拒绝；
  offline 严格性逐条保持不变。
- 用既有离线脚本 transport 跑 `run_qa` / `run_ticket`，断言包内
  `provider_observations` 与 `safe_observations()` 一致，且 `get_run` 公开响应键集合
  不变、证据只从内部 `run_evidence` 表读回并随 30 天保留期清理。
- 用提交的夹具运行 `python tools/generation_contract_probe.py --mode offline`，
  期望 4/4 案例、8 次调用、全过、零 Provider 调用。

## 范围

- transcript 校验支持 `authorized_real`（事实语义与已评审 transport 观察一致：
  账单未知三态、实际可产生失败组合全覆盖），offline 语义不变，哈希链
  语义不动；manifest 两个状态字段更新为新现实并重钉 `manifest_sha256`。
- 运行包携带 `provider_observations`（鸭型 guard）；控制面新增内部 `run_evidence`
  表持久化观察记录，公开投影与响应不变；保留期清理覆盖该表。
- 提交 `evals/fixtures/generation-contract-probe-offline-v1.json`（纯合成、可复现）。
- 补齐四组测试与本工作记录。

## 非目标

- 不启用实时模式、不装配生产 runner、不做任何 Provider 调用、不读取凭据。
- 不改变公开 API 合同、公开 HTTP 响应、预算常量、重试语义和生产 `replay_only` 姿态。
- 不重设计证据 schema（attempt / transcript 键集合不变）；不持久化原始请求 / 响应。
