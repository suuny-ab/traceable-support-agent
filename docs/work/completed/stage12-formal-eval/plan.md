# Stage 12 全新未见正式评测计划

> 规格：[`spec.md`](spec.md)。本文件只列执行顺序与检查点。

## 阶段 1：建立活动增量（R0，纯文档）

1. 本工作目录与 `spec.md`（含验证说明卡）。
2. `docs/status.md` 指向本增量；`ROADMAP.md` 当前项更新。

## 阶段 2：评测 runner、冻结校验器与公开工件（R0 代码，PR #1）

1. `tools/stage12_eval.py`：只读执行器（模式同 `tools/check_live_retrieval.py`）。
   - 输入：未见集路径（容器外挂载）、私有输出目录、信封参数。
   - 经 `DefaultProductRunner` + `MODE_AUTHORIZED_REAL` 逐案例执行，逐请求预算预留。
   - 机械评分：来源章节匹配、`required_facts` 逐字覆盖（复用
     `generation/checklist.py` 核对逻辑）、outcome / 失败码、工单 category / priority、
     预算合规。
   - 输出：①私有原始记录（Provider 输出、逐请求身份 / 用量）；②可公开聚合报告
     （案例 ID、维度、机械结果、调用 / 费用合计、身份哈希——无明文、无 Provider 原文）。
2. `tools/stage12_freeze_check.py`：验证 `required_facts` 逐字存在于绑定语料章节、
   章节 ID 存在、schema 完整。
3. `tools/tests/test_stage12_eval.py`：注入式离线传输覆盖信封记账、机械评分、
   冻结校验器、失败即停、聚合报告无明文。
4. `evals/stage12-unseen-dims-v1.json`：公开维度定义（无输入明文）。
5. 检查：Fast → Candidate；Draft PR 四项 Checks 全绿；S3 正式复核一次；squash merge。
6. 候选冻结点：合并后的部署 main SHA；从该次 `ci-release` 发布清单取知识 / prompt /
   合同哈希写入 `spec.md` 与回执。

## 阶段 3：未见集起草与机械冻结（私有，无 Provider）

1. 阅读 `data/knowledge/` 六份合成语料，按 8 维度起草 ≤24 个 `STG12-` 案例，期望全部
   从语料原文逐字派生。
2. 保存到仓库外私有路径（默认 `Documents/Codex/private/traceable-stage12/unseen-set-v1.json`）。
3. 跑冻结校验器，全部语料可追溯才冻结；SHA-256 写入 `spec.md`。
4. 冻结后不再改动案例，也不据此调整产品代码或 prompt。
5. 离线预检：注入式传输跑通 runner（0 Provider 调用）。

## 阶段 4：授权确认与生产主机执行（用户显式批准后才发生费用）

1. 授权门：向用户出示最终信封（provider / model / 案例数 / 调用上限 / 费用上限 /
   重试 0 / 停止条件 / 候选 SHA / 镜像摘要），获明确批准才继续。
2. 从冻结 SHA 构建 `live` target 镜像（记录摘要），`docker save | ssh docker load`。
3. 一次性容器执行：私有挂载，`DEEPSEEK_API_KEY` 仅命令行临时传入；仅出站 HTTPS；
   不绑定端口、不动 Caddy / 回放容器 / 数据卷。
4. 核对总调用 ≤150、记账费用 ≤¥10；失败按停止条件中止并保留证据。
5. 原始记录拉回本地私有目录；主机侧私有材料删除。

## 阶段 5：正式回执与收口（PR #2）

1. 机械评分汇总：不变量逐例二元核查 + 候选生成类观测分数，无阈值判决。
2. 正式回执（`result.md` + 公开聚合报告）：绑定候选身份，明确允许 / 不允许结论。
3. 修订 `docs/engineering/evaluation.md` 末行定位为"Stage 12 证据 + 用户判断"。
4. 回写 `docs/product/evidence-map.md`、`docs/product/limitations.md`、`PROJECT.md`
   （如证据允许）、`docs/status.md`、`ROADMAP.md`。
5. 冻结 head SHA 正式复核；工作目录移入 `docs/work/completed/`；按生命周期关闭
   Issue #12（不用自动关闭关键字）。
