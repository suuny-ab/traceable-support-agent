# 数字口径卡

> 目的：面试或复核时，每个量化数字都能回答“定义是什么、怎么算、在哪个数据集上、能否
> 复跑、不能说明什么”。本页只汇总仓库已经公开的数字，不新增测量或质量结论。

## 收录范围

收录 `README.md`、`PROJECT.md`、`PUBLIC_CONTEXT.md` 与公开证据表中可复用的产品结果、
评测结果和运行约束。日期、版本、提交 SHA、端口、Issue / PR 编号、文档修订号，以及
“60 秒体验”“10 秒理解 / 2 分钟体验”这类导航标签不是测量结果，不纳入指标卡。

## M1 · 合成语料与 16 题检索开发集

- **数字**：2 个型号、6 份合成知识文档、27 个有效章节；16 题按 CZ-R1 / CZ-R2 各 8 题。
  冻结基线的 BM25 / BGE / RRF Top-5 全标签覆盖为 14/16、14/16、16/16；三路 Top-10
  均为 16/16，Top-10 错误型号来源均为 0。当前 BM25 产品候选在同一开发集上由 14/16
  变为 15/16，BGE 仍为 14/16，RRF 仍为 16/16。
- **定义**：一道题只有在截止名次内包含其全部人工标注的必需来源章节，才记为“全标签覆盖”；
  错误型号来源是型号过滤后仍出现在 Top-10 的其他型号章节数。
- **测量方法**：型号过滤发生在排序前；同题分别运行 BM25、固定本地 BGE 与 RRF，按人工
  标签计算 Top-5 / Top-10。候选只给 BM25 增加已登记的领域等价标记，不改题或标签。
- **数据集**：[`retrieval-checkup-v1.json`](../../evals/retrieval-checkup-v1.json)；基线结果
  [`retrieval-checkup-v1.json`](../../web/app/lib/retrieval-checkup-v1.json)；候选结果
  [`retrieval-badcase-candidate-v1.json`](../../evals/retrieval-badcase-candidate-v1.json)。
- **单次 / 可复跑**：公开开发集，可用
  [`retrieval_checkup.py`](../../tools/retrieval_checkup.py) 的 `--check` / `--candidate-check`
  在固定模型清单下复跑；结果漂移会失败。
- **边界 / 不是什么**：14→15/16 是对同一开发集的定向改善，不是未见集增益；覆盖只表示
  来源找全，不表示回答正确、线上成功率、开放域泛化或发布成熟度。Provider 调用为 0。

## M2 · Stage 12 正式未见集历史观测

- **数字**：计划 24 题，实际执行 19 题，其中 9 题通过；第 20 题执行前命中信封完整性停止，
  余下 5 题未执行。调用 31/150，机制估算费用 ¥0.7096008 / ¥10，自动重试 0。
- **定义**：19/24 是“已执行 / 计划”，9 是 19 个已执行案例中逐题 outcome、来源与必需事实
  合同全部满足的数量；不是 9/24 的线上成功率。
- **测量方法**：固定候选、模型、prompt 哈希和私有未见集承诺，逐题运行真实 Provider；按
  预注册评分器聚合，Provider 响应信封不完整时立即停止且不重试。
- **数据集**：24 题私有未见集只公开承诺哈希；公开聚合为
  [`stage12-aggregate-v1.json`](../../evals/stage12-aggregate-v1.json)，执行解释见
  [`stage12-formal-eval/result.md`](../work/completed/stage12-formal-eval/result.md)。
- **单次 / 可复跑**：这是一次已完成的正式观测；公开聚合可复核，但原未见集不得作为调试
  工具。任何新正式执行都需新验证说明卡、独立授权和新的候选身份。
- **边界 / 不是什么**：不能写成“Stage 12 通过”、模型成功率或上线门；5 个未执行案例没有
  观测。Issue #21 后续修复了已知安全 / 型号机制，但没有重跑或改写此历史结果。

## M3 · 绑定式溯源生成门

- **数字**：本地真实 Provider 复测的过门数从旧合同 0/2 变为新合同 3/3；3 个案例为 2 条
  QA 和 1 条工单。
- **定义**：过门表示候选完成机械合同并形成 `completed` / candidate，且客户可见结论绑定
  真实存在的来源与业务义务；不是答案语义正确。
- **测量方法**：在同一修复切片中把逐字跨度合同改为 ID + 义务绑定合同，保持无自动重试，
  用获准的真实 Provider 对固定案例复测；同时用离线合同测试覆盖伪造 ID、越源和义务缺失。
- **数据集**：固定的 2 QA + 1 工单复测；决定与回执见
  [ADR-0007](../decisions/ADR-0007-binding-traceability-over-verbatim-spans.md)，机械合同见
  [`test_generation_contract_v3.py`](../../api/tests/test_generation_contract_v3.py)。
- **单次 / 可复跑**：0/2→3/3 是一次有授权的真实调用观察，不能无授权重跑；机械绑定合同
  可离线复跑。
- **边界 / 不是什么**：不是开放域准确率、长期 Provider 稳定性或 Stage 12 改善；候选仍由
  人工最终决定，绑定存在不等于结论必然正确。

## M4 · 10 题公开合成检索 HOLDOUT

- **数字**：10 题，CZ-R1 / CZ-R2 各 5 题，16 个独立评测知识单元；与开发集的问题全文、
  来源引用、知识全文重复均为 0。BM25 / BGE / RRF 的 Top-5 与 Top-10 全标签覆盖均为
  10/10，Top-10 错误型号来源均为 0；Provider / generation 调用均为 0。
- **定义**：覆盖与错误型号来源沿用 M1；“零重复”分别比较规范化问题全文、来源 ID 和规范化
  知识单元全文。
- **测量方法**：先把题、标签和评测知识提交冻结，再用完整 freeze commit 绑定唯一一次
  BM25 / Local BGE / RRF 排名；型号过滤在排序前。
- **数据集**：[`retrieval-holdout-v1.json`](../../evals/retrieval-holdout-v1.json)；首次观察
  [`retrieval-holdout-observation-v1.json`](../../evals/retrieval-holdout-observation-v1.json)；
  执行回执见 [`result.md`](../work/active/retrieval-unseen-holdout/result.md)。
- **单次 / 可复跑**：首次观察只执行一次；揭示后的 v1 只作回归资产，不再产生“首次”结论，
  也不得针对结果改检索、题、标签或知识。
- **边界 / 不是什么**：这是公开合成、独立评测知识上的检索来源覆盖，不是私有 Stage 12、
  回答质量、真实用户泛化、线上成功率或发布结论。

## M5 · 内存与 pgvector 两路对比

- **数字**：同一 16 题上，两路 Top-5 / Top-10 均为 16/16、错误型号来源均为 0，逐题
  Top-10 排名完全一致。固定执行顺序下，内存 / pgvector 冷启动总耗时为
  2035.846 / 1955.757 ms；热态 16 题总耗时中位数为 192.534 / 580.385 ms，各 3 次样本。
- **定义**：质量指标沿用 M1；冷启动包含模型初始化、文本向量化与 pgvector 同步，热态值是
  三次完整 16 题运行总耗时的中位数。
- **测量方法**：同机、同模型、同检索合同，固定先内存后 pgvector；真 Postgres 使用 cosine
  Top-K，结果逐题比较并记录总耗时。
- **数据集**：M1 的 16 题公开开发集；机器结果
  [`retrieval-backend-comparison-v1.json`](../../evals/retrieval-backend-comparison-v1.json)，
  环境与回执见 [`pgvector-production-integration/result.md`](../work/completed/pgvector-production-integration/result.md)。
- **单次 / 可复跑**：来源覆盖和排名可用
  [`retrieval_backend_compare.py`](../../tools/retrieval_backend_compare.py) 在具备真 pgvector 的
  固定环境复核；时间数字是该机器、该顺序的一次记录，不承诺跨机复现到相同毫秒。
- **边界 / 不是什么**：不是未见集、线上成功率或生成质量；不能从冷启动顺序宣称 pgvector
  更快，也不能把热态约 3 倍往返开销推广到其他机器。Provider 调用为 0。

## M6 · 公开运行与回放资产

- **数字**：普通实时 QA / 工单最多调用 Provider 2 次，自动重试 0；固定证据不足挑战在
  Provider 前转人工，调用 0。公开回放固定为 2 个 QA + 1 个工单。README GIF 对应一次
  真实 QA，Provider 调用 2 次、自动重试 0、4 道机械检查均 PASS。
- **定义**：调用数是一次 run 实际构造的 Provider 请求数；“4 道检查”是该候选展示的四项
  机械质量门，不是四次模型调用。
- **测量方法**：产品运行记录累计调用次数；边界挑战断言 transport factory 零构造；回放
  资产由固定清单计数；GIF 数字绑定同一个已完成 run。
- **数据集 / 对象**：公开合成运行与
  [`replay-presets.json`](../../web/app/lib/replay-presets.json)；当前公开回执见
  [`README.md`](../../README.md) 和 [`evidence-map.md`](evidence-map.md)。
- **单次 / 可复跑**：回放和离线合同可复跑且不调用 Provider；GIF 的真实 run 是一次历史
  观察，新真实调用必须重新授权并形成新身份。
- **边界 / 不是什么**：一次 run 的 2 次调用和 4 项 PASS 不是长期成功率、SLA 或模型质量；
  回放不冒充新运行，0 调用边界只覆盖已声明的固定规则。

## M7 · 公共控制面限制

- **数字**：每个获准实时 run 先预留 ¥1；全局日 / 月硬预算 ¥20 / ¥100；每浏览器每日软限
  10 次；最多同时运行 2 个任务、另排队 4 个；HTTP 请求体最大 16 KiB、用户内容最多
  500 个中文字符；原始输入最长保留 30 天；Provider 自动重试 0。
- **定义**：预算是接受 run 前的最坏成本预留上限，不是实际账单；“2 + 4”分别是执行槽和
  等待槽；浏览器限额是软防滥用标识，全局预算与队列是服务端硬门。
- **测量方法**：读取控制面固定常量，并由 API / SQLite 测试覆盖原子预算预留、并发拒绝、
  浏览器限额、输入拒绝、到期清理和重启恢复。
- **数据集 / 对象**：当前公共控制面默认配置
  [`runs.py`](../../api/src/traceable_support/api/runs.py)；威胁模型与边界见
  [`security.md`](../engineering/security.md)，合同测试见
  [`test_public_api.py`](../../api/tests/test_public_api.py)。
- **单次 / 可复跑**：确定性配置，可在同一提交上重复读取并跑测试；生产是否临时调整必须以
  部署配置和运行回执另行核验，本页不把代码默认值冒充动态遥测。
- **边界 / 不是什么**：¥1 是预留而非单次实际费用，¥20 / ¥100 不是消费承诺；2 + 4 是单机
  Beta 的限流合同，不是吞吐、容量、可用性或 SLA 测量。

## M8 · README CI 固定快照

- **数字**：README 首屏绑定的 main CI run `30690110223` 为 5/5 jobs 成功；其中 API 日志
  记录 137 passed / 2 skipped，Stage 12 runner 13 passed。
- **定义**：这些数字是该固定 run 的 job 和测试日志计数，不是当前分支的测试清单大小。
- **测量方法**：读取同一不可变 GitHub Actions run 的 job 结论与日志，不跨 run 拼接。
- **数据集 / 对象**：[`README.md`](../../README.md) 绑定的
  [GitHub Actions run 30690110223](https://github.com/suuny-ab/traceable-support-agent/actions/runs/30690110223)；
  本地回执见 [`2026-08 状态日志`](../status-log/2026-08.md)。
- **单次 / 可复跑**：这是历史交付快照，run 本身不可重写；新提交会产生新 run 和可能不同的
  测试数，不能用新 run 覆盖旧快照。
- **边界 / 不是什么**：5/5 只说明该 run 的登记 jobs 成功；137 / 2 / 13 不是产品准确率，
  也不能证明未执行或被跳过的运行时主张。

## 使用规则

引用数字时必须同时带上本页对应的“对象 / 数据集”和“边界”。若证据文件变化，先更新或
撤回公开数字并让既有机器检查通过；不得只改本页文字来制造更好的结果。
