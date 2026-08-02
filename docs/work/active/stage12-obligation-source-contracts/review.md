# 评审与边界

## 方案判断

- obligation ledger 使用冻结事实与 host 已保存的逐条 source spans，只回答“规划是否完整承接”，
  不做语义 judge，也不把正文缺失改成成功。
- 额外来源只在 expected / observed 都是 candidate 时采用子集合同；额外 evidence 必须同时通过
  型号、claim 和 obligation plan 三层绑定。这个条件复用产品已有的 host-derived 字段，不新增
  自由文本判断。
- outcome 不匹配仍走完整旧合同；缺必需来源、无绑定 extra、预算和工单字段合同不放宽。

## 对照判断

24 题只有 R4 / R5 预登记的 6 个案例变化，R4 三码删除、R5 四码换码，`SO-001` 重叠；
R1 / R2 / R3 / R6 与其余 18 题逐题不变。通过题保持 6，说明本切片没有用消码冒充质量提升。

## 授权与结论边界

本任务完整 / R2 仅因只读使用 Git 外已消费 package；Provider、生产写入和费用均为 0。
不修改产品运行代码、prompt、生成合同或 outcome。机器可以验证 fixture、逐题差异和哈希，
没有未关闭的方案级疑问，因此不触发独立 Reviewer。

候选只允许更新 `night-20260802` / Draft PR #62；不转 Ready、不合并、不部署、不发布。

实现 head `dd96538` 的 CI run `30761545320` 四个 required jobs 已全绿，publish 因 Draft
跳过；没有新阻断 finding。最终状态回执 head 只需通过同一 required Checks，不扩展授权。
