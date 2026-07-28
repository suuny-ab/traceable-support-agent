# 实施计划

1. 建立工作记录并把 `docs/status.md` 切换为 `developing`。
2. `provider/contract.py`：
   - 新增 `_validate_attempt_mode_facts`，按 `offline_injected` / `authorized_real`
     分派 attempt 事实校验；offline 分支逐条保留原全零约束；
   - `validate_transcript` 按模式分派计数约束，real 要求 `network_attempt_count>=1`、
     `credential_read_count>=1`，并强制转录计数与记录事实一致、记录模式与转录模式一致；
   - `finalize_transcript` 增加 `execution_mode` / `transport_kind` 参数（默认 offline，
     行为不变），计数从记录事实求和，拒绝模式 / kind 错配；
   - manifest 更新 `tg07a_execution_mode` 与 `real_transport_wiring_status`，
     重钉 `api/tests/test_migration_equivalence.py` 中的 `manifest_sha256`。
3. `product/qa.py` / `product/ticket.py`：新增 `_provider_observations` 鸭型快照，
   在每次 Provider 调用后写入包内 `provider_observations`。
4. `api/runs.py`：新增内部 `run_evidence` 表；`_finish` 事务内持久化观察记录；
   `cleanup_expired` 清理孤儿证据；新增 `load_run_evidence` 内部读回；公开
   `get_run` 形状不变。
5. 生成并提交 `evals/fixtures/generation-contract-probe-offline-v1.json`
   （从当前检索输出确定性生成，纯合成）。
6. 测试：`api/tests/test_real_run_transcript.py` 新建；扩展
   `test_product_qa.py` / `test_product_ticket.py` / `test_public_api.py` /
   `tools/tests/test_generation_contract_probe.py`。
7. 本地验证：Fast 子集、`api/tests` 全量（本机模型）、`tools/tests` 全量、
   `check_public_repo --scope worktree`、探针离线全过。
8. 写 `result.md` / `review.md`，报告父 Agent 集成。

停止条件：任何步骤需要 Provider 调用、凭据、网络、费用、公开合同 / 响应 / 预算常量
变更或生产姿态变化时，停止并升级给用户。
