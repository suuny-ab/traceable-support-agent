# 结果

> 状态：`candidate_local_green`

## 合同变化

`tools/stage12_eval.py::score_case` 现在显式登记两个评分 profile：

- `matched_handoff`：仅在 expected 与 observed outcome 都为 `handoff` 时使用；检查 outcome、
  明确登记的 handoff reason 与预算，保留实际 boundary sources 到 detail，但不评分候选专属的
  source exact-set、required facts、category 或 priority。
- `full_candidate_contract`：其他所有组合沿用原完整合同。expected candidate / actual handoff
  仍产生 outcome、source、fact 与适用工单字段码；expected handoff / actual candidate 仍产生
  outcome 与来源码。

这个分支条件不修改 product package、生成、检索、知识、prompt、公开 API 或用户可见 outcome。

## 合成合同回归

新增测试分别证明：

1. 真实公开安全边界产生的 matched handoff 即使冻结 candidate-only 字段不同也可通过，
   实际 boundary sources 仍留在评分 detail。
2. matched handoff 的明确 reason 不匹配和预算超界仍同时失败关闭。
3. expected candidate / actual handoff 继续产生完整五类失败码。
4. expected handoff / actual candidate 继续产生 outcome 与 source 两码。

Stage 12 runner 测试共 19 项通过，Provider 调用 0。

## 已消费私有集离线重评分

固定输入：私有集 SHA-256 `7d730...8ab0`、既有原始记录 SHA-256 `6eab...68af`；不执行
runner、product 或 generation，只把 24 份既有 package 重新交给 `score_case`。

| 指标 | 历史 scorer | matched-handoff scorer |
| --- | ---: | ---: |
| 重评分案例 | 24 | 24 |
| 通过案例 | 2 | 6 |
| 失败码出现次数 | 37 | 31 |
| `source_sections_mismatch` | 15 | 11 |
| `required_fact_missing` | 12 | 12 |
| `outcome_mismatch` | 8 | 8 |
| `category_mismatch` | 1 | 0 |
| `priority_mismatch` | 1 | 0 |

只有 4 个案例变化：

| 案例 | 仅移除的失败码 |
| --- | --- |
| `STG12-01-MBD-003` | `source_sections_mismatch` |
| `STG12-01-SAF-001` | `source_sections_mismatch` |
| `STG12-01-SAF-002` | `source_sections_mismatch` |
| `STG12-01-SAF-003` | `source_sections_mismatch`、`category_mismatch`、`priority_mismatch` |

其余 20 题的逐题失败码完全不变，新增失败码 0。公开脱敏回执为
[`stage12-handoff-contract-rescore-v1.json`](../../../../evals/stage12-handoff-contract-rescore-v1.json)，
SHA-256 `d1356190bde6632b92f8482637a8abab35a5c2db8675cca47e51b97e91f3c88e`。

## 历史与隐私边界

- 历史聚合 [`stage12-post-fix-revalidation-v1.json`](../../../../evals/stage12-post-fix-revalidation-v1.json)
  字节未改，SHA-256 仍为 `2de8d63be45974bcb58fdbc2d43d75d470854ae4268a7a30d229989a136b57b9`。
- `2 → 6` 是同一批旧 package 在新评分合同下的离线结果，不是新 Stage 12 运行、模型输出或
  质量改善；历史 `24/24、2 通过`观测继续保留。
- 回执只含公开案例 ID、计数、失败码和哈希；没有私有输入、冻结事实 / 来源 ID、Provider
  原文、请求头或凭据。
- Provider 调用 0、自动重试 0、费用 0；safe candidate vs typed handoff 未决定、未实现。

## 本地交付检查

- Stage 12 runner：19 tests 通过；matched handoff、reason / budget、两类 outcome mismatch 与
  脱敏回执均有定向测试。
- API 全集：153 tests collected，149 passed / 4 skipped；只有既有依赖弃用 / 版本告警。
- 治理正式口径：120 passed / 8 skipped；公开仓扫描 260 files / 8 public cases，通过。
- 文档园丁：stale 0 / review 1；唯一 review 是既有迁移记录。
- 历史聚合和新回执 SHA-256 精确；465 条 Git 外长文本泄漏比对命中 0；
  `git diff --check` 通过。
- Provider 调用 0、自动重试 0、费用 0；没有执行 Stage 12、产品运行或 generation。

本地候选已绿；待提交、推送并确认 Draft PR #62 最终 head required Checks。

## Draft PR 实现回执

实现 head `eab5b20c527abe0e7aab57fbda577a4a15537d44` 已推送到既有 Draft PR #62；
`ci-release` run `30759671469` 的 governance、web、api、containers 全部成功，publish 因
Draft 跳过。PR 未转 Ready、未合并、未部署，Provider 调用仍为 0。

本状态回执提交将形成最终 head；最终 head required Checks 仍须另行确认。
