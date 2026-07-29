# 结果记录

> 状态：候选为 Draft PR #37（base `main`），当前 head `b49e379`（合同修复
> `9c7ed59` + 第 1 轮文档同步）；新 head 四项 Checks 全绿（run 30421455186）。
> 第 1 轮正式复核两项阻断（合同不能忠实表达 transport 未知账单与部分失败
> 事实；候选事实文档滞后于 PR 生命周期）已完成修复；第 2 轮定向复核确认代码
> 语义修复通过，结论 `BLOCKED`：唯一剩余阻断为 PR 说明与项目事实停在旧候选，
> 本目录与状态 / 路线文档的本轮同步即该阻断的收口。

## 实际交付

- `api/src/traceable_support/provider/contract.py`
  - 新增 `_validate_attempt_mode_facts`：attempt 事实按执行模式分派。
    `offline_injected` 保持原全零约束逐条不变；`authorized_real` 要求
    `transport_kind=="official_https"`，network / dns / credential 三个事实位为
    bool，`dns==network`、`credential_read==transport_attempted`、有响应或 HTTP
    状态必有 network、timeout 必有 network；账单事实与已评审 transport 观察严格
    一致（未知三态）：`paid_call_performed` 必须为 `None`（transport 永不确知
    是否计费），`actual_paid_cost_cny_nanos` 只允许 `None`（未知）或 `0`
    （无已确认计费）；两种模式都要求 `automatic_retry_count==0`。
  - 失败矩阵覆盖 transport 实际可产生的组合：`provider_credential_missing` 纳入
    `FAILURE_CODES`（real 专属：凭据读取未得、零 network、无响应）；
    `provider_response_too_large` 接受两种忠实形状（adapter 丢弃已接收的 200
    响应；real transport 读出超限后丢弃整个响应对象：无接收事实、无 HTTP 状态、
    有 network）；`provider_transport_error` 不强制 network（发送前构造异常可零
    network），`provider_timeout` 保持必有 network。
  - `validate_transcript`：模式 / kind 必须配对；offline 计数保持全零；real 要求
    `credential_read_count>=1`（每次调用必读凭据），network 计数不设下界
    （credential_missing 可忠实零 network）；记录模式必须与转录模式一致；转录
    计数必须与记录事实求和一致（`paid_call_count` 只统计确认付费，real 恒 0；
    `actual_paid_cost_cny_nanos` 求和只计 int 值，0 表示无已确认计费）。
    哈希链、`expected_calls` 阶段顺序和估算成本语义不变。
  - `finalize_transcript`：新增 `execution_mode` / `transport_kind` 参数（默认
    offline，现有调用方行为不变），计数从记录事实求和，模式 / kind 错配失败关闭。
  - manifest：`tg07a_execution_mode` → `offline_injected_and_authorized_real`，
    `real_transport_wiring_status` → `wired_for_authorized_real_runs_only`；
    `manifest_sha256` 为 `2efdaad06f5f0f261cd7e01a842b61478239b8dad8e9b724260071427a5f78b4`，
    `api/tests/test_migration_equivalence.py` 钉定值同步；冻结的迁移基线
    `evals/migration-equivalence-v1.json` 保持旧哈希（历史事实，与 prompt 分流
    的处理方式一致）。阻断修复不触及 manifest，哈希不变。
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
- 测试：`api/tests/test_real_run_transcript.py`（18 例：连贯 real 通过、账单
  未知三态钉定（标记非 `None` / 非零实际账单拒绝）、credential_missing 与零
  network transport_error 接受、零 network timeout 拒绝、两种
  response_too_large 形状接受、offline 新形状拒绝、offline 全零不变、offline
  带 network 事实拒绝、两种模式 retry>0 拒绝、credential 未读拒绝、
  计数 / 模式不一致拒绝）；扩展
  `test_product_qa.py` / `test_product_ticket.py`（包内观察记录断言 + 鸭型 guard）、
  `test_public_api.py`（公开响应键集合不变、证据内部持久化、保留期清理、无观察
  无证据行）、`tools/tests/test_generation_contract_probe.py`（提交夹具全量探针通过）。

## 验证（全部离线）

- Fast 子集 `test_package_boundaries.py` / `test_public_api.py` /
  `test_provider_usage.py`：通过（含于 api 全量）。
- `python -m pytest api/tests`（本机模型根 `TRACEABLE_MODEL_ROOT` 指向
  `artifacts/models/...`）：126 项通过 + 20 subtests，无失败。
- `python -m unittest discover -s tools/tests -p "test_*.py"`：105 项，
  `OK (skipped=7)`（环境门跳过，如 pip-audit 未安装）。
- `python tools/check_public_repo.py --scope worktree`：`passed`，192 文件。
- `python tools/generation_contract_probe.py --mode offline --offline-responses
  evals/fixtures/generation-contract-probe-offline-v1.json`：`cases=4/4 calls=8/8
  passed=true`，零 Provider 调用。
- 夹具重新生成与提交内容字节级一致（确定性）。

## 复核轮次

- 第 1 轮（冻结 `b30221a`，四项 Checks 绿）：正式独立复核，两项阻断 finding
  （见 `review.md` 正式回执）；候选变化使旧回执失效。
- 阻断修复覆盖 diff：`contract.py`、`test_real_run_transcript.py`、本工作记录与
  状态 / 路线文档；未触及 `qa.py` / `ticket.py` / `runs.py` / 探针夹具 /
  公开合同 / manifest。
- 第 2 轮（head `b49e379`，run 30421455186 四项 Checks 绿）：定向复核确认
  finding 1 修复通过（账单未知三态：付费标记恒 `None`、实际账单仅 `None`/`0`；
  失败矩阵补齐；18 例钉定，api 全量 126 项 + 20 subtests）；finding 2 仍成立，
  结论 `BLOCKED`——唯一阻断为 PR 说明与项目事实未同步；本轮文档与 PR 说明
  同步即收口，解除以复核者确认为准（回执见 `review.md`）。

## 证据边界

- 本候选只证明：合同校验接受 / 拒绝的语义与已评审 transport 可产生事实组合
  一致（由手工构造 attempt 钉定）、包与控制面的内部持久化、公开形状不变、
  离线探针端到端通过。它不证明任何真实 Provider 行为；真实运行仍需独立授权、
  验证说明卡与 Stage 12 门。adapter 接 real transport 的端到端 wiring 属未来
  工作（TG-07B 方向），不在本候选。
- 公开响应形状不变由测试钉定（键集合断言），但 `run_evidence` 的内部读回尚无
  面向用户的复核界面；当前仅供工具 / 测试使用。

## 剩余风险

- 夹具钉定当前知识库与检索排序；知识库变化会使夹具失配，探针按合同失败关闭
  （这是设计内的显式信号，需要按同一配方重新生成夹具）。
- real 模式账单事实保持未知三态（`paid_call_performed=None`、
  `actual_paid_cost_cny_nanos=None`）；transcript 求和口径下 0 只表示"无已确认
  计费"，真实账单仍只能由账号侧确认；合同不声称计量真实费用。
- SQLite `run_evidence` 为纯增量表，不触及既有迁移路径；旧库打开时由
  `CREATE TABLE IF NOT EXISTS` 自动建立。
