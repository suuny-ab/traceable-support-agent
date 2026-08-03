# Stage 12 generation_shape 离线复现与诊断修复

## Goal

用公开合成响应复现 Stage 12 的 `top10_v6_content_invalid` 失败族，证明它发生在 QA 第二阶段
内容外形校验而非义务覆盖或证据引用；把当前一个粗码拆成隐私安全、可行动的子码，并用
离线产品链与对照测试证明失败仍然关闭、其他失败族不漂移。

## Non-goals

- 不调用 Provider、不重跑 Stage 12、不恢复或公开历史 Provider 响应正文。
- 不根据缺失的历史正文猜测三个私有案例究竟命中哪个细分条件。
- 不放宽生成合同、不把 malformed 响应升级为 candidate，不修改生成 prompt、检索或知识。
- 不改变 safe candidate vs typed handoff 的产品取舍。
- 不转 Ready、不合并 `main`、不部署、不发布 `product/0.1.0`。

## AC

1. **WHEN** 运行公开等价夹具，**THEN** content 容器、content identity、answer 外形和 claims
   数量四种 malformed 响应在旧合同下均可复现 `top10_v6_content_invalid`。
2. **WHEN** 核对阶段证据，**THEN** 报告明确目标案例 checklist 已通过、第二次 Provider 调用
   成功、失败发生在 claims / obligation binding 前的 content 外形校验；不把它归为义务覆盖
   或证据引用根因。
3. **WHEN** 应用诊断修复，**THEN** 四种公开夹具分别得到稳定子码
   `top10_v6_content_shape_invalid`、`top10_v6_content_identity_invalid`、
   `top10_v6_answer_shape_invalid`、`top10_v6_claim_count_invalid`。
4. **WHEN** 分类这些子码，**THEN** phase 仍为 `generation_contract`、family 仍为
   `generation_shape`，且错误输出不含响应正文、prompt、私有事实或来源 ID。
5. **WHEN** 通过离线产品链运行四种夹具，**THEN** 仍然 outcome=`handoff`、answer=`null`、
   Provider 调用为离线注入 2 次；没有 malformed 响应形成候选。
6. **WHEN** 运行对照回归，**THEN** checklist、claim、obligation binding、semantic coverage、
   completeness 与 matched-handoff scorer 的既有失败码 / family 不变。
7. **WHEN** 检查历史证据，**THEN** Stage 12 历史聚合及前一切片脱敏回执字节 / SHA 不变；
   新公开夹具只含合成内容。
8. **WHEN** 完成交付，**THEN** 定向测试、API 全集、治理、公开仓扫描、文档园丁、泄漏专项
   与差异检查全绿，Provider 调用为 0。
9. **WHEN** 推送候选，**THEN** 只更新 `night-20260802` / Draft PR #62 并确认最终 head
   required Checks 全绿；不转 Ready、不合并、不部署。

## 验证说明卡

- **问题**：`top10_v6_content_invalid` 能否离线复现并缩小到可行动、仍失败关闭的安全子类？
- **历史输入**：只读既有 package / safe observations；私有集 SHA `7d730...8ab0`、原始记录
  SHA `6eab...68af`。记录不保留 Provider 响应正文，因此只能定位到旧粗码覆盖的四个条件之一。
- **公开输入**：固定 QA evidence / checklist 与四个合成 malformed step-2 JSON；不含私有内容。
- **调用 / 费用**：Provider 调用 0、自动重试 0、费用 0；产品链只用 offline injected transport。
- **最便宜证伪**：先让四个公开响应在未改合同上全部复现旧码；若不能复现则停止，不改合同。
- **允许结论**：目标失败在 generation content shape 层；未来同类失败能由安全子码定位。
- **禁止结论**：历史三个响应的确切 malformed 字段、模型质量改善、Stage 12 分数或发布成熟度。

## 回滚

候选阶段关闭 Draft PR #62 并删除 `night-20260802`；若未来合并则 revert 对应 squash。
恢复 QA 合同粗码、failure taxonomy、公开夹具、测试和状态文档即可；历史评测资产不改。

## 规则复述

- 不公开或猜测历史 Provider 正文；只使用合成等价夹具和隐私安全错误码。
- 修复诊断分辨率而非放宽合同，malformed 响应继续失败关闭。
- 不运行 Stage 12 / Provider，只更新集成分支和 Draft PR；不转 Ready、不合并、不部署。
