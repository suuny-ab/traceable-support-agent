# GitHub 任务生命周期

## 所有权转移

```text
计划来源之一：GitHub Issue
→ 当前项目 Conversation + 必要的 docs/work/active/<slug>/
→ 可选：项目 Agent 为隔离、候选或恢复治理建立 Task / Run
→ 候选：Draft PR + 固定 SHA + Checks
→ 外部结果：部署 / 验收回执
→ 稳定事实：PROJECT / engineering / decisions / completed work
→ Agent 关闭 Issue
```

- 已确认但尚未启动的未来工作在 Issue 记录动机、预期结果、优先级、边界和启动条件；
  开发中自然产生且立即执行的 Task 不必先建立 Issue。
- 进入实施后，当前项目 Conversation Agent 自行规划和执行；只有确有隔离、候选或恢复治理
  需要时才建立项目 Task / Run。控制系统不为每条开发消息默认登记 Task / Run。
- 当前项目结果、固定候选、阻碍和下一检查点由 `docs/status.md` 接管；历史验证事实与回执只追加到 `docs/status-log/YYYY-MM.md`，必要的活动工作文件保留领域细节。
- PR 只绑定候选 diff、Checks、所需当次授权、触发时的评审记录和发布回执，不成为稳定产品
  事实。
- 所需部署与用户验收齐全后，Agent 回写稳定文档并关闭 Issue。
- PR 不使用 `Closes`、`Fixes` 等自动关闭关键字。合并不是完成的充分条件。

## GitHub 与仓库分工

GitHub 管：

- 项目范围内的未来技术结果与项目优先级；
- 候选 diff 与讨论；
- required Checks；
- 发布、部署和外部验收链接。

仓库管：

- 当前项目状态、活动产品结果和固定候选；
- 稳定产品事实、工程合同和长期决定；
- 规范化结果与三层拦截边界。

Issue、评论和标签不是授权来源；授权默认值的唯一正文见
[`review.md` 的授权层](review.md#授权层唯一默认值正文)。公开 GitHub 不得包含 secret、
私有 HOLDOUT、Provider 原始内容、本机路径或敏感清单。

Issue 不保存裁决入口侧的用户长期计划、跨项目现实顺序、用户精力或 CLI Conversation
状态，也不能覆盖 `ROADMAP.md` 之外的用户现实安排。

## 最小标签

- `product`：面向用户的产品结果。
- `priority:next`：当前增量结束后的下一候选。
- `priority:later`：已登记但不阻塞当前路线。
- `needs:user`：需要用户范围决定、外部授权或实际体验验收。

不使用 Projects、CODEOWNERS 或新的 GitHub 审批来复制现有门；GitHub 生命周期不改写
[`review.md` 的授权默认值](review.md#授权层唯一默认值正文)。

## 关闭条件

Issue 只有在以下内容全部齐全后由 Agent 关闭：

1. 对应实现已合并；
2. required Checks 成功；
3. 所需当次授权已记录，触发的方案级评审疑问已关闭；
4. 若需发布，生产回执绑定正确 SHA；
5. 若需用户体验，用户实际验收完成；
6. 稳定文档与活动工作已收口。

若线上体验未通过，Issue 保持打开并在同一活动增量修复。
