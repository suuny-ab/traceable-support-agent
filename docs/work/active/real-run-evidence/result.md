# 结果记录

> 状态：作者侧实现与本地验证完成；已本地提交 `def6072`（分支
> `codex/real-run-evidence`，基于 `origin/main` `79892eb`）；推送、Draft PR、CI
> 与冻结 head 后的正式独立复核尚未执行。

## 实际交付

- `api/src/traceable_support/provider/contract.py`
  - 新增 `_validate_attempt_mode_facts`：attempt 事实按执行模式分派。
    `offline_injected` 保持原全零约束逐条不变；`authorized_real` 要求
    `transport_kind=="official_https"`、四个事实位为 bool、`dns==network`、
    `credential_read==transport_attempted`、有响应或 HTTP 状态必有 network、
    timeout / transport_error 必有 network、`paid_call_performed==(status=="succeeded")`、
    `actual_paid_cost_cny_nanos==0`（未知未开票语义）；两种模式都要求
    `automatic_retry_count==0`。
  - `validate_transcript`：模式 / kind 必须配对；offline 计数保持全零；real 要求
    `network_attempt_count>=1` 且 `credential_read_count>=1`；记录模式必须与转录
    模式一致；转录计数必须与记录事实求和一致（含 `actual_paid_cost_cny_nanos`）。
    哈希链、`expected_calls` 阶段顺序和估算成本语义不变。
  - `finalize_transcript`：新增 `execution_mode` / `transport_kind` 参数（默认
    offline，现有调用方行为不变），计数从记录事实求和，模式 / kind 错配失败关闭。
  - manifest：`tg07a_execution_mode` → `offline_injected_and_authorized_real`，
    `real_transport_wiring_status` → `wired_for_authorized_real_runs_only`；
    `manifest_sha256` 变为 `2efdaad06f5f0f261cd7e01a842b61478239b8dad8e9b724260071427a5f78b4`，
    `api/tests/test_migration_equivalence.py` 钉定值同步更新；冻结的迁移基线
    `evals/migration-equivalence-v1.json` 保持旧哈希（历史事实，与 prompt 分流
    的处理方式一致）。
- `api/src/traceable_support/product/qa.py` / `ticket.py`：新增
  `_provider_observations` 鸭型快照（无 `safe_observations` 时返回 `[]`），每次
  Provider 调用后刷新包内 `provider_observations`；观察记录不含 prompt / 响应 /
  凭据（transport 边界已 canary 校验）。
- `api/src/traceable_support/api/runs.py`：新增内部 `run_evidence`
  表（`run_id` 主键）；`_finish` 在同一事务内更新 runs 并写入证据（只在 runs
  行实际更新时写入，杜绝孤儿）；`cleanup_expired` 同步清理过期证据，保留期语义
  不变；新增内部 `load_run_evidence` 读回。`get_run` 公开响应形状不变。
- `evals/fixtures/generation-contract-probe-offline-v1.json`：4 个固定公开案例的
  两阶段合成响应夹具，由当前本地检索输出一次性生成（生成逻辑与
  `tools/tests/test_generation_contract_probe.py` 的 `_steps` 配方一致），重新生成
  字节级一致；无 Provider 输出、无凭据。
- 测试：新建 `api/tests/test_real_run_transcript.py`（11 例：连贯 real 通过、
  offline 全零不变、offline 带 network 事实拒绝、real 零 network 拒绝、两种模式
  retry>0 拒绝、credential 未读拒绝、计数 / 模式不一致拒绝）；扩展
  `test_product_qa.py` / `test_product_ticket.py`（包内观察记录断言 + 鸭型 guard）、
  `test_public_api.py`（公开响应键集合不变、证据内部持久化、保留期清理、无观察
  无证据行）、`tools/tests/test_generation_contract_probe.py`（提交夹具全量探针通过）。

## 验证（全部离线）

- Fast 子集 `test_package_boundaries.py` / `test_public_api.py` /
  `test_provider_usage.py`：通过。
- `python -m pytest api/tests`（本机已验证模型根，`TRACEABLE_MODEL_ROOT` 指向
  `artifacts/models/...`）：119 项全部通过，无失败。
- `python -m unittest discover -s tools/tests -p "test_*.py"`：105 项，
  `OK (skipped=7)`（环境门跳过，如 pip-audit 未安装）。
- `python tools/check_public_repo.py --scope worktree`：`passed`，192 文件。
- `python tools/generation_contract_probe.py --mode offline --offline-responses
  evals/fixtures/generation-contract-probe-offline-v1.json`：`cases=4/4 calls=8/8
  passed=true`，零 Provider 调用。
- 夹具重新生成与提交内容字节级一致（确定性）。

## 证据边界

- 本候选只证明：合同校验接受 / 拒绝的语义、包与控制面的内部持久化、公开形状不变、
  离线探针端到端通过。它不证明任何真实 Provider 行为；真实运行仍需独立授权、
  验证说明卡与 Stage 12 门。
- 公开响应形状不变由测试钉定（键集合断言），但 `run_evidence` 的内部读回尚无
  面向用户的复核界面；当前仅供工具 / 测试使用。

## 剩余风险

- 夹具钉定当前知识库与检索排序；知识库变化会使夹具失配，探针按合同失败关闭
  （这是设计内的显式信号，需要按同一配方重新生成夹具）。
- `actual_paid_cost_cny_nanos==0` 在 real 模式表示“未知 / 未开票”，真实账单仍只能
  由账号侧确认；合同不声称计量真实费用。
- SQLite `run_evidence` 为纯增量表，不触及既有迁移路径；旧库打开时由
  `CREATE TABLE IF NOT EXISTS` 自动建立。
