# pgvector 生产接入

## Goal

把产品混合检索的稠密向量存储从仅进程内 numpy 扩展为可在生产启用的 PostgreSQL +
pgvector 后端：只有 DSN、连接、迁移、表、索引和数据库健康全部通过才使用 pgvector；任一
启动或运行期故障都自动退回行为一致的内存检索，并用同一冻结 16 题记录质量与耗时对比。

## Non-goals

- 不新增知识域、问题、标签、检索调参或生成能力，不查看或使用 HOLDOUT。
- 不调用 Provider，不修改 Provider、预算、凭据、人工批准或公开 API 合同。
- 不宣称多机一致性、高可用、线上成功率或检索质量提升；PostgreSQL 只保存公开合成语料的
  可再生向量。
- 本候选只获准推送分支和创建 Draft PR；不转 Ready、不合并、不部署。

## AC

1. **WHEN** 未配置 `TRACEABLE_RETRIEVAL_VECTOR_DSN`，**THEN** 定向测试证明构造并执行的仍是
   现有内存 BGE 路径，排名与错误合同不变。
2. **WHEN** 配置 DSN，**THEN** readiness 检查必须依次验证可连接、`vector` 扩展、schema
   迁移版本、向量表维度、主键、HNSW cosine 索引和 `SELECT 1`；任何一项不满足都不得启用
   pgvector。
3. **WHEN** readiness 在首次检索前失败，**THEN** 定向测试证明请求仍由内存后端完成，服务
   live readiness 与公开 health 四字段不受影响，且错误信息不含 DSN 或凭据。
4. **WHEN** 已启用的 pgvector 在同步或查询时断线，**THEN** 定向测试证明同一请求自动用
   内存路径重试一次并成功，后续请求保持内存降级，不触发 Provider 或外部业务动作。
5. **WHEN** 在同一机器、同一模型和同一冻结 16 题上执行内存与 pgvector 对比，**THEN**
   机器可读结果同时记录 Top-5 / Top-10 完整覆盖、错误型号来源数、冷启动总耗时和热查询
   总耗时，并明确这不是未见集或发布结论。
6. **WHEN** 检查生产 Compose，**THEN** pgvector 使用固定镜像、持久卷、容器健康检查和仅容器
   内部网络，不发布数据库宿主机端口；API 不以数据库存活作为启动前提。
7. **WHEN** 分别在数据库健康与数据库不可用条件下运行容器 / 产品检查，**THEN** API 均能
   启动，且 `/api/v1/health` 仍精确返回 `status`、`service`、`live_experience`、
   `release_sha` 四字段；不可用条件走内存检索。
8. **WHEN** 候选需撤销，**THEN** 运维文档给出移除 DSN / 切回内存和 `revert` 的两层回滚，
   且数据卷不被部署或回滚流程破坏性删除。
9. **WHEN** 候选检查通过并建立 Draft PR，**THEN** 状态只记录已验证候选事实和精确 head，
   合并、自动部署与公网 health / `live_experience` 核验继续标为待授权、待执行。

## 最便宜证伪、复用与停止线

- 先用假 store 定向测试证伪 readiness 与断线 fallback，再用现有 CI / 本地
  `pgvector/pgvector:pg17` 真数据库测试 schema 与排序；不先跑完整产品套件。
- 复用现有 `PgVectorStore`、本地 BGE、模型预过滤、RRF、冻结 16 题、CI pgvector service、
  release health 和持久卷合同；不新增 Python 依赖或 Provider。
- 若需要改变公开 health schema、把私有数据写入向量库、开放数据库端口、自动重试 Provider、
  或在未取得精确 head 授权前合并 / 部署，立即停止并请求用户决定。

## 回滚

运行时先移除 `TRACEABLE_RETRIEVAL_VECTOR_DSN` 或关闭 pgvector 启用配置，重启 API 后恢复内存
检索；代码 / 编排回滚使用单一 squash merge 的 `revert`。既有发布链失败时恢复 previous
版本，不执行 `down -v`，保留 SQLite 与 pgvector 持久卷供核查或后续恢复。

## 规则复述

- 本任务 Provider 调用上限为 0；Git 文件、DSN 或数据库存在都不能授予 Provider、费用、
  凭据或业务外部写入。
- 公开运行身份只以 `/api/v1/health.release_sha` 为准；green / skipped CI 不能代替部署和公网
  核验，本候选也不得改变该 health 合同。
- 当前授权仅包含本分支推送与 Draft PR；转 Ready、精确 head squash merge 和进入既有自动
  部署链必须等待新的当次明文授权。
