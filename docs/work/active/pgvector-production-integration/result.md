# 结果

## 候选实现

- `PgVectorStore.readiness()` 先执行 schema v1 幂等迁移，再验证 `SELECT 1`、`vector` 扩展、
  migration 版本、`vector(512)`、`(fingerprint, chunk_id)` 主键和 HNSW cosine 索引；失败只
  返回稳定原因码，不输出 DSN。
- DSN 缺失或 readiness 未过时继续构造原 `DenseBgeRetriever`。已启用 store 在同步 / 查询
  时抛出明确的 `VectorStoreUnavailable`，wrapper 会让同一请求改用已经算好的进程内向量，
  并在该检索实例生命周期内锁定内存；模型或输入错误不会被降级掩盖。
- 生产 Compose 使用 digest 固定的 `pgvector/pgvector:pg17`、独立数据 / secret 持久卷、随机
  本地口令、`.pgpass`、健康检查和内部 retrieval 网络，不发布 5432，也不把数据库作为 API
  启动依赖。发布切换前先拉取数据库镜像；候选 / 回滚激活只有在 API health 与 pgvector
  schema readiness 都通过后才提交版本锚点。
- 公开 `/api/v1/health` 合同未增加字段；Provider、预算、凭据、知识、标签和检索参数未改。

## 同一 16 题对比

机器结果：`evals/retrieval-backend-comparison-v1.json`。

| 后端 | Top-5 完整覆盖 | Top-10 完整覆盖 | 错误型号来源 | 冷启动总耗时 | 热态 16 题总耗时中位数 |
| --- | ---: | ---: | ---: | ---: | ---: |
| 内存 | 16/16 | 16/16 | 0 | 2035.846 ms | 192.534 ms |
| pgvector | 16/16 | 16/16 | 0 | 1955.757 ms | 580.385 ms |

16 个案例的 Top-10 排名逐题完全一致，Provider 调用 0。冷启动固定先跑内存、后跑 pgvector，
会受模型 / 文件缓存影响，不能据此宣称 pgvector 更快；热态数字显示本机 Docker 数据库往返
当前约为内存路径的 3 倍。两者都只测同一公开合成开发集，不是未见集或线上质量结论。

## 验证

- 真 PostgreSQL：6 passed，覆盖迁移 / readiness、schema 漂移拒绝、写入、cosine top-k 与
  幂等同步。
- API：148 passed，24 subtests；包含 readiness 失败、运行中断线 fallback、公开 health
  不漂移和已记录对比失败关闭测试。
- live 容器：同一镜像在健康数据库上报告 `container_retrieval_backend=pgvector`，数据库不可达
  时报告 `container_retrieval_backend=memory_fallback`；不可达时 health 仍精确四字段且
  `live_experience=available`；离线检索 8 cases 通过、Provider 调用 0。
- 生产 Compose：真实 pgvector 容器健康；随机口令跨容器重建保持，API UID 可读 `.pgpass`
  但不能读原始口令；Compose 内执行发布 readiness 通过。
- Web：clean install、lint、typecheck、production build、36 tests 通过。
- 治理：114 passed / 8 skipped；公开仓扫描、Workflow YAML、release shell syntax 与
  `git diff --check` 通过。

本地 `docker build --target live` 客户端在 304 秒停止线返回超时且没有错误文本；BuildKit 随后
完成并产出镜像 `sha256:d9d65ecb…`（非 root、revision=`local`），上述容器检查均在该镜像上
实际通过。Draft PR 的 Linux `containers` required check 仍是候选镜像从头构建的权威结论。

## 待执行

候选尚未推送 / 创建 Draft PR。转 Ready、合并、生产部署和公网版本 / `live_experience` 核验
都未获授权、未执行；因此不能声称生产已经使用 pgvector。
