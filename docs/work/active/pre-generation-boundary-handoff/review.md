# 独立复核

> 状态：`findings_open`

本增量触及安全边界与公共失败关闭合同，正式独立复核必须在 Draft PR 的
`governance`、`web`、`api`、`containers` 四项 Checks 全绿、head SHA 冻结且主 Agent
停止写入后执行一次。复核者只读，不修改候选。

## 首轮回执

- 候选 SHA：`8b50618de0f59b623de8e7314201931d2310c6a8`。
- 基线 SHA：`0bb97c974d2a5cdc7d455f329ee81aca9a9f9755`。
- Draft PR：`#24`。
- 前置证据：CI run `30058941904` 的 `governance`、`web`、`api`、`containers`
  四项 Checks 全绿；`publish` 因 Draft 按设计跳过。
- 复核方式：固定候选、主 Agent 停止写入、同一工作树只读独立复核。
- 结论：`failed`；该 SHA 不得合入。

### 阻断发现

1. 输入正文只明确提到一个型号、但与 `product_model` 不一致时，型号边界可能被绕过。
2. `product-boundary-handoff-v1` 将来源放在 `boundary_sources`，Stage 12 正式评分器仍只从
   生成结果的 `used_evidence_ids` 取来源，合法 handoff 会被误判为来源不匹配。
3. CZ-R1 的型号排他词规则同时拦截了“有没有自动集尘”和 R1 / R2 差异等合法知识问答。
4. `起火`、`触电` 不在当前规则声明的公开合成来源内，不能作为有来源的安全升级词。

四项均可由公开 API / 正式评分入口触达，且会改变用户行为或结论真实性，因此满足阻断
标准。后续只修复这些 finding 及其覆盖；新候选四项 Checks 全绿后，由同一复核者仅复核
finding 与覆盖 diff。
