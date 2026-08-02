# 计划

1. 锁定 R4 / R5 历史案例、旧聚合和三个既有回执哈希，确认只读 package 足够机械判定。
2. 建立四个公开合成 package，在当前 scorer 复现规划粗码与 extra-source exact-set 误扣。
3. 增加 obligation coverage ledger 与 bound-extra-source ledger；保持缺来源、无绑定和其他 profile
   失败关闭。
4. 运行公开定向 / 对照测试，再对 24 份既有 package 离线重评分并生成脱敏差异回执。
5. 更新结果、评测口径、根因报告与两层状态；运行 API 全集和治理检查。
6. 提交推送 `night-20260802`，确认 Draft PR #62 最终 head required Checks 后停止。

停止线：公开夹具不能复现、需要改生成 / prompt / outcome、额外来源无法机械验证完整绑定、
或 R1 / R2 / R3 / R6 发生未登记漂移时立即停止。
