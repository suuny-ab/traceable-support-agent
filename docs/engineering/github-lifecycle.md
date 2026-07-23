# GitHub 任务生命周期

## 所有权转移

```text
未来候选：GitHub Issue
→ 启动：docs/status.md + docs/work/active/<slug>/
→ 候选：Draft PR + 固定 SHA + Checks
→ 外部结果：部署 / 验收回执
→ 稳定事实：PROJECT / engineering / decisions / completed work
→ Agent 关闭 Issue
```

- 未启动任务在 Issue 记录动机、预期结果、优先级、边界和启动条件。
- 进入实施后，Issue 只指向活动工作；范围、当前动作、阻碍和验证事实由仓库活动文件接管。
- PR 只绑定候选 diff、Checks、复核和发布回执，不成为稳定产品事实。
- 所需部署与用户验收齐全后，Agent 回写稳定文档并关闭 Issue。
- PR 不使用 `Closes`、`Fixes` 等自动关闭关键字。合并不是完成的充分条件。

## GitHub 与仓库分工

GitHub 管：

- 未来任务与优先级；
- 候选 diff 与讨论；
- required Checks；
- 发布、部署和外部验收链接。

仓库管：

- 唯一当前状态与活动增量；
- 稳定产品事实、工程合同和长期决定；
- 规范化结果与复核边界。

Issue、评论和标签不授予 Provider、费用、凭据、生产、外部写入或破坏性操作。公开 GitHub
不得包含 secret、私有 HOLDOUT、Provider 原始内容、本机路径或敏感清单。

## 最小标签

- `meta`：元开发与治理。
- `product`：面向用户的产品结果。
- `priority:next`：当前增量结束后的下一候选。
- `priority:later`：已登记但不阻塞当前路线。
- `needs:user`：需要用户范围决定、外部授权或实际体验验收。

不使用 Projects、CODEOWNERS 或新的用户审批来复制现有门。

## 关闭条件

Issue 只有在以下内容全部齐全后由 Agent 关闭：

1. 对应实现已合并；
2. required Checks 成功；
3. 所需正式复核关闭；
4. 若需发布，生产回执绑定正确 SHA；
5. 若需用户体验，用户实际验收完成；
6. 稳定文档与活动工作已收口。

若线上体验未通过，Issue 保持打开并在同一活动增量修复。
