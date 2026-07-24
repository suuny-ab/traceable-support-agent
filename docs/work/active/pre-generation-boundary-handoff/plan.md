# 实施计划

> 状态：`active`

1. 固定 Issue #21 的公开事实、验证说明卡和非范围。
2. 从公开合成知识提取最小安全 / 型号排他规则，建立 Product 层纯函数判定。
3. 让 `DefaultProductRunner` 在 transport factory 之前执行边界门并返回完整 handoff 包。
4. 让公网 API 的预检复用同一 Product 判定，同时保留敏感与范围控制。
5. 对安全正例、型号冲突正例、词形变化和相邻合法负例增加单元 / runner / API 回归。
6. 先运行最便宜测试，再运行 Fast 和可用的 Candidate 检查。
7. 更新结果和产品事实；本地候选准备好后，推送与 Draft PR 作为独立外部动作处理。
8. Draft PR 四项 Checks 全绿后冻结 head SHA，停止写入并做一次正式独立复核。
