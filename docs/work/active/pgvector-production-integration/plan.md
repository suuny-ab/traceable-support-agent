# 执行计划

1. 已固定 `origin/main@db72aa0e3b31ad749ba1f991ecd5b2ca4c1fa949` 基线和既有
   pgvector、检索、CI、生产编排合同。
2. 已为向量存储增加版本化迁移与结构 readiness，并在 dense retriever 外增加启动 / 运行期
   内存 fallback。
3. 已接入隔离、持久、健康可查但不阻断 API 启动的生产 pgvector 服务，补齐部署 readiness、
   运维和回滚说明。
4. 已用同一冻结 16 题生成内存 / pgvector 质量与冷暖耗时对比，Provider 调用为 0。
5. 已完成定向、真数据库、API、live 容器、Web、治理和公开仓检查。
6. 下一步重建两层状态，提交、推送一次并创建 Draft PR；确认同一 head 的 required Checks 后
   写 Git 外精确 head 授权请求并停止。
