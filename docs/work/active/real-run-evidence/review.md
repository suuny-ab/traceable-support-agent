# 复核

> 本增量触及持久化（新增内部 `run_evidence` 表）与 Provider 证据合同语义
> （transcript 接受 `authorized_real`、manifest 重钉）。按仓库规则，持久化与
> 公共合同变化在收口时需要正式独立复核；当前为实施 Agent 自复核，正式复核在
> Draft PR 四项 Checks 全绿、冻结 head SHA 后调用一次，本文件不作最终收口结论。

## 自复核范围

- 公开边界：`api/contracts/public-api-v1.json` 未改；`get_run` 响应键集合由
  `test_public_api.py` 精确断言钉死；`provider_observations` 不进入投影
  （`project_package` 只构造固定键的新 dict，从不拷贝未知键）。
- 安全姿态：无 Provider 调用、无凭据读取、无网络；观察记录在 transport 边界
  已做 canary 校验，持久化路径不再引入原始内容；`run_evidence` 随 30 天保留期
  与 VACUUM 一起清理，隐私语义不扩大。
- 失败关闭：伪造 / 不一致组合全部以固定 code 拒绝（offline 带 network 事实、
  real 零 network、retry>0、计数与记录不一致、混合模式）；`finalize_transcript`
  模式 / kind 错配直接失败。
- 生产姿态：`replay_only`、`provider_enabled=false`、预算常量、重试 0 均未触碰；
  本候选不启用实时模式。
- 迁移路径：既有 `_migrate_provider_calls_nullable` 与 metric_rollups 迁移不受影响；
  `run_evidence` 由 `CREATE TABLE IF NOT EXISTS` 建立，新旧库均可打开。

## 验证证据

见 `result.md` 验证一节：Fast 子集、api 全量 119 项、tools 全量 105 项
（7 项环境门跳过）、公开仓扫描、探针离线 4/4 通过、夹具确定性重生成一致。

## 待复核者确认的问题

- `authorized_real` attempt 事实规则是否恰为 `AuthorizedRealTransport` 可产生的
  全部组合（credential 读取与 transport 尝试耦合、DNS 与 network 耦合、付费标记
  只在成功调用）；是否存在过严导致合法真实 transcript 被拒的组合。
- manifest 两个状态字段的新措辞是否准确描述“已接线、仅供未来授权运行、生产不
  连接”的现实。
- 内部证据表不公开读回界面是否符合本候选“可复核”的最小口径。
