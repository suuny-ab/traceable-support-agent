# 计划

1. 锁定 B 路线授权、六个 R2 案例 ID、私有集 / 原始记录哈希及既有公共边界。
2. 用六个公开等价例建立预期失败测试，分别覆盖跨型号半答、近似反推、未登记能力和三种
   人工售后履约请求；保留可回答相邻负例。
3. 扩展 host-owned `BoundaryDecision`：增加稳定 `handoff_type` 与 guidance，将决策表编译为
   生成前 predicate，并让 runner / QA / ticket 三条入口统一传入 task type。
4. 在内部 package 与公开投影保留 type + reason；关闭公开 `GEN-DEV-MH-003` 差距并增加机器断言。
5. 运行定向 / API 全集 / 治理，再对私有六例做只读结构核验；只报告 ID 与机械结果。
6. 更新结果、根因后续回执与两层状态，提交推送 `night-20260802`，确认 Draft PR #62 最终
   head required Checks 后停止。

停止线：任一规则必须依赖私有逐字短语、相邻可回答例被误拦、需要修改生成 / prompt / 知识、
需要 Stage 12 / Provider，或 required Check 失败无法在本切片内定位时立即停手并写战报。
