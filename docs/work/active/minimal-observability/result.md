# 结果

## 当前候选

- `PublicRunService` 幂等创建固定键空间的 `http_request_metrics` 聚合表，不新增逐请求明细。
- ASGI 中间件以规范化路由 ID 记录方法、响应类别和耗时；不保存原始路径、查询串、请求体、
  Cookie、IP 或异常文本。
- `GET /api/v1/observability` 返回总量、错误率、平均 / 最大延迟、三类错误和逐路由聚合；端点
  自身不计数，连续读取不污染结果。
- 观测写入异常被降级为脱敏 warning，原请求响应保持不变。

## 本地验证

- 定向 API：`19 passed`，覆盖固定聚合数学、client / server / transport 三类错误、只读端点
  自身不计数，以及观测写失败时 health 仍为 200。
- API 全集：`147 passed / 4 skipped / 24 subtests passed`；4 项为本地未配置 DSN 时跳过的真
  pgvector 用例，本切片没有改向量存储。
- 治理工具：`114 passed / 8 skipped`；公开仓扫描 `233 files / 8 public cases` 通过。
- 文档园丁：`stale=0 / review=1`；唯一 review 是既有迁移记录的历史相对措辞，不是候选阻断。
- `git diff --check` 通过；没有新增依赖、服务、逐请求明细、Provider 调用、token 或费用。

## 待执行

候选尚待提交、推送、创建 Draft PR 和确认同一 head 的 required Checks 启动。当前证据只证明
本地候选合同，不证明生产已部署、跨实例聚合、高吞吐、SLA 或线上回答质量。
