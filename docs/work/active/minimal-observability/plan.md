# 执行计划

1. 固定 `origin/main@8ca825d58d2b42fdaecfb59e0ca6a0ade45d6f24`，在隔离 worktree 建立
   `night-20260802`，保留主工作区既有改动。
2. 在 `PublicRunService` 复用现有 SQLite 与锁，增加固定键空间的 HTTP 聚合表和只读聚合方法。
3. 在现有 ASGI 外层增加规范化路由观测；写入异常只输出脱敏类型并保持原响应。
4. 增加 `GET /api/v1/observability`、合同 JSON、API 文档与公开证据边界。
5. 先跑 API 定向测试，再跑 API 全集、治理、公开仓和差异检查；Provider 调用保持 0。
6. 更新两层状态，提交并推送集成分支，创建 Draft PR后核对同一 head 的 required Checks 启动。
7. 归档派发并在战报顶部写三行；停止在 Draft，不转 Ready、不合并、不部署。
