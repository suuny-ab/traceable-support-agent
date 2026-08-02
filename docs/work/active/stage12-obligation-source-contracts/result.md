# 结果

> 状态：`candidate_ci_green`

## 两个机械合同

### 义务规划覆盖账本

Stage 12 scorer 现在把每条冻结 `required_fact` 与 package 的 checklist 对照：只有同一条
obligation 的 `approved_source_spans` 按 clause ID 排序拼接后完整承接该事实，才算规划覆盖。
候选若缺这个账本，报 `required_obligation_missing`；即使正文偶然出现该事实也不能把规划写成
通过。规划完整但客户正文缺字面事实时仍报 `required_fact_missing`。

这只读取产品已经保存的 host-owned checklist / source spans，不修改 checklist、prompt、
generation、package 或用户 outcome。

### 必需来源与额外来源账本

expected / observed 都是 candidate 时，来源合同从 exact equality 改为：

1. 冻结必需来源必须全部进入 host-derived `used_evidence_ids`；
2. 额外来源必须适用于 package 的产品型号；
3. 额外 evidence ID 必须由客户可见 claim 使用；
4. claim 的每个 obligation 都必须在 host-derived plan 中批准这个 evidence ID。

满足四项的额外来源保留在 detail 供审计但不误扣；缺必需来源、型号不适用、无 claim 或无
obligation 批准仍报 `source_sections_mismatch`。expected handoff / observed candidate 等 outcome
不匹配组合继续原 exact-set 合同，不借此掩盖边界策略差异。

## 公开等价复现

公开夹具
[`stage12-obligation-source-equivalent-v1.json`](../../../../evals/fixtures/stage12-obligation-source-equivalent-v1.json)
SHA-256 为 `4e64791c4be6a80ab0e01688cf6229fc252c11da42b12e20e848644c44651326`：

| 场景 | 基线结果 | 候选结果 |
| --- | --- | --- |
| 两个条款被拆到两条 obligation，正文也缺完整事实 | `required_fact_missing` | `required_obligation_missing` |
| 单条 obligation 完整承接，正文仍缺事实 | `required_fact_missing` | 不变 |
| 全部必需来源 + 同型号、claim / obligation 完整绑定的额外来源 | `source_sections_mismatch` | 通过 |
| 额外来源没有绑定账本 | `source_sections_mismatch` | 不变 |

另有定向变体证明型号不适用、obligation plan 缺批准仍失败；既有缺必需来源测试保持失败。

## 已消费 24 题离线重评分

固定输入仍为既有 24 份 package，不执行 runner、product 或 generation。脱敏回执为
[`stage12-obligation-source-rescore-v1.json`](../../../../evals/stage12-obligation-source-rescore-v1.json)，
SHA-256 `93a3a0b9b2efa45abf7e141b76754c4fbf40a39559541bcb90f3429f950897fb`。

| 指标 | handoff scorer | 本候选 |
| --- | ---: | ---: |
| 重评分案例 | 24 | 24 |
| 通过案例 | 6 | 6 |
| 失败码出现次数 | 31 | 28 |
| `source_sections_mismatch` | 11 | 8 |
| `required_fact_missing` | 12 | 8 |
| `required_obligation_missing` | 0 | 4 |
| `outcome_mismatch` | 8 | 8 |

只改变 6 个预登记案例：

- R4：`MSQ-003`、`SO-001`、`SO-003` 各移除一个有完整绑定账本的额外来源误扣。
- R5：`MSQ-002`、`ATK-002`、`ATK-003`、`SO-001` 各把
  `required_fact_missing` 一对一改为 `required_obligation_missing`。
- `SO-001` 同时命中两类；其余 18 题逐题失败码不变，新增通过 0。

R5 仍是失败，只是从正文粗码前移到可行动的规划账本；R4 三题还分别有 R5 或 R6 失败，
所以 31→28 不产生通过题增加。

## 历史与结论边界

- 原复验聚合 SHA 仍为 `2de8...57b9`，handoff 重评分回执仍为 `d135...c88e`，
  generation_shape 回执仍为 `82bf...1832`；字节均未改。
- Provider 调用 0、自动重试 0、费用 0；不重跑 Stage 12，不产生模型输出。
- 这证明 scorer 能区分规划遗漏、正文遗漏和合法额外来源；不证明历史回答被修复、模型质量、
  Stage 12 分数、线上成功率或发布成熟度改善。
- safe candidate vs typed handoff 未决定、未实现。

## 验证

- 定向：公开 planning / source fixture、正文缺失、缺必需来源、型号错误、无 claim / plan
  绑定对照 3 tests 通过。
- Stage 12 runner / freeze / 回执：21 tests 通过；unexpected / matched handoff、outcome、预算与
  历史哈希对照不变。
- API 全集：162 tests collected，158 passed / 4 skipped；只有既有依赖弃用 / 版本告警。
- 治理正式口径：122 passed / 8 skipped；generation probe 4/4、8/8 调用离线通过。
- 公开仓：272 files / 8 public cases，通过；园丁 stale 0 / review 1，唯一 review 是既有迁移
  记录；`git diff --check` 通过。
- 私有泄漏专项：153 条 Git 外正文特征长字符串与 13 个候选文本文件逐字比对，命中 0；
  原始记录 SHA 仍为 `6eab...68af`。
- 预期红测先复现旧 planning / source 两码；实现后对照全绿。Stage 12 全文件首次复跑发现
  既有正文遗漏测试使用了冻结门本会拒绝的伪造事实，改为公开夹具中的“规划完整、正文缺失”
  合法场景后仍精确要求 `required_fact_missing`；未为通过而放松 scorer。
- Provider / product / generation / Stage 12 调用均为 0。

本地候选已绿；待提交、推送并确认 Draft PR #62 最终 head required Checks。

## Draft PR 实现回执

实现 head `dd96538850017dac94d87e41940887bcecbc828d` 已推送到既有 Draft PR #62；
`ci-release` run `30761545320` 的 governance、web、api、containers 全部成功，publish 因
Draft 跳过。PR 未转 Ready、未合并、未部署，Provider 调用仍为 0。

本状态回执提交将形成最终 head；最终 head required Checks 仍须另行确认。
