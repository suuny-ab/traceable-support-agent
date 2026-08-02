# Stage 12 今夜修复后唯一复跑

## Goal

在 `night-20260802@fc766709f48bf2989c6589a56db3cec7593ed6cb` 上，用既有
Stage 12 runner 对同一 24 题已消费私有集执行唯一一次真实 Provider 回归，机械比较今夜
四类根因修复与六个 typed handoff 边界落地后的通过数、失败码、handoff 命中和用量。

## Non-goals

- 不修改 runner、评分器、私有集、离线响应、prompt、生成逻辑、检索或知识。
- 不针对结果调案例、抬分、补跑失败题或执行第二轮；自动重试为 0。
- 不倒写首次复验或离线重评分资产，不把回归写成开放域质量或因果改善。
- 不转 Ready、不合并、不部署、不发布 `product/0.1.0`。

## AC

1. **WHEN** 执行前核验身份，**THEN** 候选为 `fc766709f48bf2989c6589a56db3cec7593ed6cb`，
   prompt 集合为 `108ab9aae60eb86806383cc2fea4511d358955f50503531e0da2e82be1ba8584`。
2. **WHEN** 检查私有集，**THEN** 24 题且 SHA-256 为
   `7d73073cd0227b0ced81398fcbadc7e5f85867a633a9654d82bd0b516c358ab0`，冻结检查通过。
3. **WHEN** 发起真实复跑，**THEN** 只调用 `tools/stage12_eval.py`，DeepSeek
   `deepseek-v4-pro`，24 案例 / 150 调用 / ¥10 上限，整套 1 次、自动重试 0。
4. **WHEN** 出现身份、凭据、挂载、费用 / 调用信封、`execution_failure:` 或执行异常，
   **THEN** 立即停止并保留该次结果，不补跑。
5. **WHEN** 运行结束，**THEN** 原始记录只留 Git 外，公开聚合只含案例 ID、机械结果、
   失败分类、身份、停止原因和用量，不含私有输入、期望事实、Provider 原文或凭据。
6. **WHEN** 机械对比结果，**THEN** 同时列出首次复验的 `24/24、2 通过`、matched-handoff
   scorer 的 31 个失败码出现次数、最新 obligation/source scorer 的 28 次基线，以及本轮结果。
7. **WHEN** 核对 typed handoff，**THEN** 六个预登记案例逐题报告 outcome、type、reason、
   Provider 调用数和是否满足冻结期望。
8. **WHEN** 交付，**THEN** Stage 12、API、治理、Web、公开扫描、园丁、差异和泄漏检查通过，
   两层状态、Draft PR #62 最终 head required Checks、派发归档与三行战报全部落盘。

## 验证说明卡

- **问题**：今夜修复在同一已消费集上的描述性机械回归结果是什么？
- **Provider / model / 目的**：DeepSeek / `deepseek-v4-pro` / 本任务唯一一次 Stage 12 回归。
- **固定输入**：24 题 Git 外私有集，SHA-256 `7d730...8ab0`。
- **评分**：当前既有 runner；不新增阈值，不改评分合同。
- **信封**：最多 24 案例、150 调用、¥10 机制估算；单案例最多 2 调用；整套 1 次；重试 0。
- **硬停止**：身份或哈希漂移、凭据 / 私有资产缺失、输出落入 Git、费用 / 调用信封不足、
  执行异常或真实生成返回 `execution_failure:`。
- **允许结论**：固定候选、模型、prompt 与已消费集上的这一次描述性机械观测。
- **禁止结论**：开放域质量、稳定成功率、单一改动因果效果、生产 SLA 或发布成熟度。

## 回滚

关闭 Draft PR #62 并删除 `night-20260802` 可撤销候选；公开聚合与回执可删除，Git 外原始
记录保留审计。首次复验和既有重评分资产不受影响。

## 规则复述

- 唯一一次 Provider 运行消费本次授权；失败、超时或红灯后都不得补跑。
- 私有正文、原始 Provider 内容、凭据和环境清单永不进入 Git。
- 只更新集成分支和 Draft PR；不转 Ready、不合并、不部署。
