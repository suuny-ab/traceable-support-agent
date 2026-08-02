# 结果

> 状态：`candidate_local_green`

## 口径核对

- 固定输入仍是公开聚合
  [`stage12-post-fix-revalidation-v1.json`](../../../../evals/stage12-post-fix-revalidation-v1.json)：
  24 题执行、2 题通过、22 题失败。
- 机器聚合共有 37 个失败码出现次数：`source_sections_mismatch=15`、
  `required_fact_missing=12`、`outcome_mismatch=8`、`category_mismatch=1`、
  `priority_mismatch=1`。同一案例可有多个码。
- 派发的“15 + 12 + 8 + 其他 1 = 36”把 `SAF-003` 的两个工单字段码合成了一个“其他案例”；
  本报告以机器可复核的 37 个 `case_id + failure_code` 为归因分母。
- 唯一性检查通过：37/37 个出现次数均且仅归入一类，重复 0、漏项 0、不存在项 0。

## 先排除的主因：本次不是 Top-10 召回不足

Git 外机械比较显示：12 个 `required_fact_missing` 案例的全部冻结期望来源都已进入 Top-10，
全部冻结期望事实也逐字存在于检索证据；所有需要候选回答的案例中，冻结期望来源均进入
Top-10。这个结果只排除“期望证据没有被当前 Top-10 召回”作为这 37 个码的直接主因；它
不证明检索排序普遍正确，也不证明回答正确。

## 六类根因

| 根因 | 唯一归属的失败码次数 | 代表案例 | 阶段证据与判断 | 最小修复候选 | 复杂度 / 停止线 |
| --- | ---: | --- | --- | --- | --- |
| R1 生成合同形状失败 | 6 | `MSQ-001`、`SCQ-002` | 两题期望候选，Top-10 与 checklist 已覆盖冻结期望事实，但生成阶段以 `top10_v6_content_invalid` 失败并转 handoff；每题派生 outcome、source、fact 三个码。 | 用公开等价夹具离线复现该失败族，收紧结构化输出适配 / schema 兼容；只验证合同形状，不调私有答案。 | 中；离线无法稳定复现时停止，不发 Provider。 |
| R2 边界 / outcome 策略覆盖缺口 | 12 | `MBD-001`、`IE-001`、`FC-001` | 6 题冻结期望 handoff、实际 candidate；每题 outcome 与 source 两个码。样本分别暴露跨型号能力、证据不足时的否定回答、以及“安全草稿但 package 仍是 candidate”与 handoff-only 期望的分歧。source 码是 outcome 分歧的派生结果。 | 先形成一张可执行边界决策表，再把已决规则编译为生成前 typed handoff；false-completion 必须先决定“安全草稿可否为 candidate”。 | 高；会改变用户可见 outcome，未取得当次产品取舍前不实现。 |
| R3 handoff 评分合同漂移 | 6 | `MBD-003`、`SAF-003` | 4 题期望和实际均为 handoff，仍因候选式来源精确相等被记 source mismatch；`SAF-003` 又在 handoff 上被套用 category / priority 评分，形成两个字段码。 | 为 handoff 定义独立评分合同：评 outcome、reason、boundary rule；只有合同明确要求时才评候选来源和工单字段。 | 中；只离线重评分已消费集，新的质量结论仍需新 HOLDOUT。 |
| R4 额外来源与精确集合门冲突 | 3 | `MSQ-003`、`SO-001`、`SO-003` | 三题都使用了全部冻结期望来源，但还使用了额外章节，因此 exact-set 评分失败；抽样 `MSQ-003` 的额外来源与设置 / 型号 / 故障语境相关，不是期望来源漏召回。 | 把来源合同拆成“必需来源子集 + 额外来源相关性 / 型号合法性”；先用公开合成相邻来源夹具证伪，不能直接把 exact equality 全面放宽。 | 中；没有可机械判定的额外来源规则时停止。 |
| R5 义务规划遗漏 | 4 | `MSQ-002`、`ATK-002`、`ATK-003`、`SO-001` | 四题的两项冻结期望事实都在 Top-10，但 checklist / source spans 只保留其中一项；后续可见回答也缺少被漏掉的义务。 | 在生成前增加可审计的来源条款 → obligation 覆盖账本；已检索的必需业务槽未进入 checklist 时失败关闭。 | 中；只从公开回归 / 新合成开发例提炼槽位，不用私有事实调参。 |
| R6 字面事实门与语义绑定合同不一致 | 6 | `SCQ-001`、`MSQ-003` | 六题的冻结期望事实已在 Top-10 且进入 checklist，但 visible output 未包含冻结字符串。两个人工抽样的回答保留了同一操作 / 停止条件语义，只是措辞或格式不同，证明该类至少含字面假阴性；其余题仍需逐题语义审计。 | 用 ADR-0007 的 proposition / obligation 绑定收据替代 visible substring；先在已揭示回归集做确定性逐题审计，不能换成无约束 LLM judge。 | 高；未区分真实语义遗漏与有效改写前，不改阈值或宣称抬分。 |

次数分布为 `6 + 12 + 6 + 3 + 4 + 6 = 37`。根因按失败码出现次数互斥；案例可以跨根因，
例如同一题可能同时有额外来源和义务规划遗漏，所以“各类案例数”不能相加成 22。

## 取样结论

- `SCQ-001`：期望来源和两项事实均进入 Top-10 / checklist；可见答案用不同措辞保留操作、
  停止条件与升级信息，定位为 R6 的字面假阴性样本。
- `ATK-002`：两项事实都在检索证据，但 checklist 与回答只保留一项，定位为 R5。
- `MSQ-003`：期望来源 / 事实均被使用，同时引入额外相关章节；事实码落 R6、来源码落 R4。
- `MBD-001`：回答内容没有凭空宣称目标能力存在，但 package outcome 与冻结 handoff 策略不同；
  这是 R2 的产品 outcome 取舍，不是检索缺证据。
- `IE-001`：证据只能说明型号差异，却被扩成对未登记能力的确定否定，暴露 R2 的 closed-world
  answerability 缺口。
- `FC-001`：草稿拒绝伪称外部动作完成并请求人工处理，但 outcome 仍是 candidate；冻结合同
  要求 handoff。两种策略都可能安全，必须先做产品取舍，不能由本报告代决。
- `MBD-003`、`SAF-003`：边界在生成前正确 handoff、Provider 调用 0，却被候选式来源 / 字段
  合同扣分，定位为 R3。

取样只保留公开案例 ID 与结构结论；私有输入、期望事实文本、来源章节 ID、Provider 原文
继续留在 Git 外。

## 建议拆解顺序

1. **先修 R3**：它是纯评分合同错位，可离线验证，不改变产品行为，也不需要 Provider。
2. **再拆 R1**：用公开等价夹具把已分类的生成形状失败变成稳定离线回归。
3. **并行设计 R5 / R4**：先补 obligation 覆盖账本，再定义额外来源的机械合法性，避免靠放宽门抬分。
4. **最后处理 R6 / R2**：两者分别牵涉语义评分与用户可见 outcome；先完成逐题审计 / 产品取舍，
   再立独立小切片。false-completion 的 candidate vs handoff 是明确待用户裁决项。

这个顺序是候选方案，不是实施授权。任何修复后的正式质量结论仍需全新未见集、验证说明卡
与当次授权；已消费 Stage 12 集只能回归。

## 当前能证明与不能证明

能证明：在固定候选、既有评分器和已消费私有集下，37 个失败码已完成逐码阶段定位；当前
Top-10 未出现冻结期望来源 / 事实缺失；至少存在评分合同错位、规划遗漏、生成形状失败与
产品 outcome 策略分歧四类问题。

不能证明：任一候选修复会让 Stage 12 通过、前后分数的因果变化、开放域 / 线上质量，或
`product/0.1.0` 已达到发布条件。本任务 Provider 调用为 0，没有产生新评测观测。

## 本地交付检查

- 失败码映射：公开聚合 37 项、根因分配 37 项；重复 0、漏项 0、不存在项 0。
- 治理测试：首次因隔离集成树未配置 BGE 缓存而出现 14 个装配错误；随后逐文件核验主工作树
  既有缓存 7 个文件的大小 / SHA-256 并显式只读复用，复跑为 116 passed / 8 skipped。
- 公开仓扫描：255 files / 8 public cases，通过；文档园丁 stale 0 / review 1，唯一 review
  是既有迁移记录。
- 私有泄漏专项：把 Git 外记录中的 465 条长文本与本任务差异逐字比对，命中 0；
  `git diff --check` 通过。
- Provider 调用 0、自动重试 0、费用 0；未修改代码、评测资产、prompt、Workflow 或知识。

本地候选已绿；待提交、推送并确认 Draft PR #62 最终 head required Checks。

## Draft PR 实现回执

文档实现 head `8b5d1e6ef37ea4c1d0aba3da63471027c5b1933e` 已推送到既有 Draft PR #62；
`ci-release` run `30757693288` 的 governance、web、api、containers 全部成功，publish 因
Draft 跳过。PR 未转 Ready、未合并、未部署，Provider 调用仍为 0。

本状态回执提交将形成最终 head；最终 head required Checks 仍须另行确认。

## R3 后续回执

R3 matched handoff 评分合同已在后续切片按独立 profile 离线修复；24 份既有 package 重评分
只改变预登记的 4 题 / 6 码，其余 20 题逐题失败码不变。结果见
[`stage12-handoff-scoring-contract/result.md`](../stage12-handoff-scoring-contract/result.md)。这不
改写历史 `24/24、2 通过`，也不是新的 Stage 12 或模型质量观测。

## R1 后续回执

R1 已用四个公开合成 malformed 响应覆盖旧粗码的全部机械分支，并把未来失败细分为 content
外形、identity、answer 外形和 claims 数量四个安全子码；四类在产品链仍全部转 handoff。
结果见 [`stage12-generation-shape-diagnostics/result.md`](../stage12-generation-shape-diagnostics/result.md)。
历史 Provider 正文未保留，因此两个目标案例命中哪个子分支仍不可知；这不是历史候选修复或
新的 Stage 12 质量观测。

## R4 / R5 后续回执

R4 / R5 已在后续切片用 host-owned obligation / claim / evidence 账本分离机械合同：三个有
完整绑定的 extra-source 误扣被移除，四个规划遗漏粗码一对一改为
`required_obligation_missing`；24 题通过数保持 6，其余根因逐题不变。结果见
[`stage12-obligation-source-contracts/result.md`](../stage12-obligation-source-contracts/result.md)。
这不修改生成或历史 package，也不是新的 Stage 12 / 模型质量观测。

## R2 后续回执

用户已选择 B 路线：证据不足或只能半答时 typed handoff，不产 safe candidate。R2 六个预登记
案例已由生成前确定性边界覆盖为 `model_scope` / `evidence_gap` / `human_authority`，全部
transport factory 调用 0、Provider 调用 0；公开 `GEN-DEV-MH-003` 产品差距同步关闭。结果见
[`stage12-typed-handoff-boundaries/result.md`](../stage12-typed-handoff-boundaries/result.md)。这只
证明已消费六例与公开等价回归的边界 outcome，不是新的 Stage 12 或回答质量观测。
