# 当前开发状态

> 本文件保存项目结果队列和固定候选；Conversation / Turn 运行状态在 Git 外控制系统。
> 项目 Agent 仅在确有隔离、候选或恢复治理需要时建立 Task / Run，并把恢复事实留在项目
> checkpoint；个人 Work 和新 Conversation 入口不默认登记。

| 字段 | 内容 |
| --- | --- |
| `state` | `developing` |
| 更新时间 | `2026-07-27` |
| 当前产品目标 | Issue #28：完成最终作品集视觉与三个固定示例的受控真实体验 |
| 当前集成任务 | 候选经复核阻断修正后四项 required checks 全绿，已冻结 `f873906`，等待针对原 finding 与覆盖 diff 的针对性复核 |
| 复杂度 | 完整；候选涉及前端、API、持久化和受控 live 路径 |
| 风险 / 成熟度 | 当前候选核验为 `R0`；产品保持 `S1 公开 Beta`，实时 Provider、费用、凭据、生产开关和部署仍需独立授权 |
| 产品候选 | `codex/portfolio-experience`（Draft PR #31）@ `f873906`：Worker 候选 `71104ee` → 集成 `e3fc2a5` → 收敛 `8819408` → 同步 `95f0bcb` → 公开合同修正 `f873906` |
| 项目基线 | `origin/main` @ `95f0bcb`（唯一权威位置：主 worktree `traceable-support-agent`） |
| 活动工作 | `docs/work/active/portfolio-live-experience/` |
| 最近完成 | `docs/work/completed/ci-proof-contract/`（CI 证明合同，统一基线 `df81ccd` 已部署并验收） |
| 阻碍 | npm 依赖漂移（11 high、test 锁 2 个）为已登记缺口，修复与否待用户立项；候选触碰依赖锁文件时会被新阻塞审计拦下，属设计内检测 |
| Provider | 生产仍禁用：`provider_enabled=false`、`provider_calls=0`、`provider_cost_cny=0`；v14 两次调用估算 `¥0.080325`、预留 `¥0.287007`，重试 0；v11 / v13 各有一次未计价，历史实际账单仍待账号侧确认 |
| 下一检查点 | 针对性复核回执（原 finding + 覆盖 diff `932b28f..f873906`）；通过后由用户决定转 Ready、合并与部署；定期依赖审计首跑（周一 07:43 UTC）预计变红告警，届时按分层处理 |

## 当前队列

| Task | 状态 | 候选 / 结果 |
| --- | --- | --- |
| `TASK-TRACEABLE-LIVE-WORKBENCH` | `converged` | Worker 候选 `71104ee` 经集成提交 `e3fc2a5` 汇合入基线，并已同步到 CI 合同基线 `95f0bcb`；验证记录见 result.md |

Task 可以并行，进入受保护 `main`、正式复核、部署和用户验收仍按依赖串行。

## 当前产品事实

- 方向 B 的公开回放体验位于 <https://47.84.34.86/>。
- 健康状态必须保持 `replay_only`；实时 Provider 不因控制系统启用而获得授权。
- `product/0.1.0` 尚未发布；Stage 12 已执行一次（19/24、9 通过），Issue #21 已修复当时的
  两条边界缺陷但未重跑未见集；Issue #22 已以部分结果和已知限制收口，不形成成功率主张。
- 结果顺序仍为 Issue #28 最终网站与受控真实演示、Issue #29 仓库展示、Issue #14 发布或
  保持 Beta 判断；并行 Task 不自动改变产品依赖。
- 当前工作树和公开 GitHub 仓库是产品唯一权威开发来源。
- 唯一权威开发位置为主 worktree `traceable-support-agent`（分支 `codex/portfolio-experience`）；
  `traceable-support-agent-live-workbench` 与 `traceable-support-agent-live-integration` 已退出
  当前事实来源，物理移除仍需单独授权。
- 收敛前主 worktree 未提交修改完整保存在本地分支 `backup/portfolio-experience-wip-20260726`
  （`a683dff`），可用 `git restore --source=backup/portfolio-experience-wip-20260726 .` 恢复。
- 旧仓和临时回滚材料不是权威来源；删除仍是未经授权的独立破坏性动作。
- 受保护 `main` 的 CI 全绿后自动进入既有生产部署流程；失败部署不自动重试。

## 权威来源

- 产品事实：`PROJECT.md`
- 结果路线：`ROADMAP.md`
- 最近完成记录：`docs/work/completed/ci-proof-contract/`
- 工程规则：`docs/engineering/`
- Agent 协作规则：`docs/engineering/agent-workflow.md`
