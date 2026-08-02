# 评审与边界

## 方案判断

- 旧码混合四个机械条件，无法从脱敏回执判断下一步；拆码能让未来同类失败直接落到安全、
  可行动的子条件，又不需要保存 Provider 正文。
- 实现没有新增容错、schema 兼容或响应修补；原来失败的值仍在原位置失败，因而不是用放宽
  合同掩盖生成问题。
- 分类表显式把四码钉在 `generation_shape`，避免 identity / count 码因命名 fallback 漂到
  `other`；错误码不含正文、prompt、事实或来源 ID。

## 对照判断

公开等价夹具覆盖旧粗码的全部分支；合同级与产品级各自核验错误码和 handoff。既有生成合同
与 Stage 12 scorer 测试作为对照，任何 candidate 误放行、旧失败族漂移或历史聚合变化都会
阻断候选。

## 未知事实

历史 Provider 正文不存在于保留资产，两个目标案例命中哪个子码不可恢复。不能把四个合成
分支中的任何一个冒充历史精确根因；本结论只到 `generation content shape` 层。

## 授权与停止线

本任务不调用 Provider、不重跑 Stage 12、不改 outcome 策略。候选只允许更新
`night-20260802` / Draft PR #62；不转 Ready、不合并、不部署、不发布。所有条件均可机器
验证，没有未关闭的方案级疑问，因此不触发独立 Reviewer。

实现 head `c606bd3` 的 CI run `30760606556` 四个 required jobs 已全绿，publish 因 Draft
跳过；没有新阻断 finding。最终状态回执 head 只需通过同一 required Checks，不扩展授权。
