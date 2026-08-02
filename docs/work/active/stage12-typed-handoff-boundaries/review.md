# 评审与边界

## 执行前判断

- 用户已明确选择 B 路线，safe candidate vs typed handoff 的产品疑问已关闭。
- 类型、reason、rule、guidance 与零调用均可由机器测试；当前没有必须派独立 Reviewer 的
  方案级疑问。
- 私有六例只作已消费集回归，不形成新未见集或模型质量结论。

## 结果判断

- 六行边界与相邻负例均有机器断言，私有六例也已用同一 evaluator 做只读结构核验；没有遗留
  方案级疑问需要 Reviewer。
- 新字段是 additive：candidate 的 `handoff_type=null`，已有 handoff reason / outcome 不变；
  生成失败统一投影为 `generation_failure`，确定性边界使用细分 type。
- 当前结论只到本地候选；实现 head 与最终状态 head 的 required Checks 尚未形成，不能写成
  可合并或可部署候选。
