# 复核记录

> 状态：`approved`

## 一次完整复核

- `candidate_sha`：`c61c5a67b0b7afd04e6d3d26a4874d6fb5246ce5`
- 基线：`201f6ef935e27593ef6edef43294988d202fb9fb`
- 范围 / 风险：完整增量；本地 R0、GitHub 与生产 R2；产品保持 S1。
- Checks：run `30005142238` attempt 1，四个 required check 全部成功。
- Findings：
  - P2：路径分类删除首尾空白，使异常但可跟踪的 Git 路径可能伪装为治理路径。
  - P2：手动 legacy 恢复未限定可信 workflow、同仓 main push、成功结论和 pre-decision
    范围，可能在制品失败前进入 production environment。
- 结论：不可批准；未发现 P0/P1。

## 针对性复核一

- `candidate_sha`：`bd3f9e6323e8d790a56d2453e0dc53ca917034a9`
- 覆盖：两个原 findings 与 `c61c5a6..bd3f9e6`。
- Checks：run `30006093699` attempt 1，四个 required check 全部成功。
- 结果：异常路径 finding 已关闭；legacy 任意 run、制品和 environment 暴露已关闭。
- 残余 P2：workflow 身份只校验可重复的显示名 `ci-release`，未固定工作流路径。
- 结论：不可批准；没有重新复核未变化的 Web/API/治理区域。

## 针对性复核二

- `candidate_sha`：`8bd15ffca60cbbed6bc44e8d249dd0affb8209ae`
- 覆盖：workflow identity 残余 finding 与 `bd3f9e6..8bd15ff` 的 2 文件 5 行。
- Checks：run `30006413918` attempt 1，四个 required check 全部成功。
- 结果：Actions API `run.path` 必须精确等于 `.github/workflows/ci-release.yml`；同名不同
  path 反例以 `release_run_path_invalid` 拒绝。旧成功 run `29999870811` 的真实只读探针
  继续通过。
- 结论：原 findings 全部关闭，覆盖 diff 未发现新的 P0–P3，候选可批准。

## 结论边界

复核证明最终候选在声明范围内可批准，并证明 finding 驱动的针对性复核没有重复未变化
区域。它不证明生产部署已经执行；生产、公开健康和用户验收由 `result.md` 的后续独立
回执关闭。
