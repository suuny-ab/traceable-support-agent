# 当前开发状态

> 本文件保存项目结果队列和固定候选；CLI 会话与高频 Run 状态在 Git 外控制注册表。

| 字段 | 内容 |
| --- | --- |
| `state` | `developing` |
| 更新时间 | `2026-07-24` |
| 当前产品目标 | Issue #28：完成最终作品集视觉与三个固定示例的受控真实体验 |
| 当前集成任务 | 核验并集成 live workbench 候选 |
| 复杂度 | 完整；候选涉及前端、API、持久化和受控 live 路径 |
| 风险 / 成熟度 | 当前候选核验为 `R0`；产品保持 `S1 公开 Beta`，实时 Provider、费用、凭据、生产开关和部署仍需独立授权 |
| 产品候选 | `codex/live-llm-workbench` @ `71104ee`，等待从 Worker 候选进入工程集成 |
| 项目基线 | `codex/portfolio-experience` |
| 活动工作 | `docs/work/active/portfolio-live-experience/` |
| 阻碍 | 无工程阻碍；产品候选的 Worker 测试结果尚未由当前 Codex 复跑 |
| Provider | 生产仍禁用：`provider_enabled=false`、`provider_calls=0`、`provider_cost_cny=0`；历史账单事实不提供当前调用授权 |
| 下一检查点 | 按候选依赖核验和集成 `71104ee`；不自动启用 Provider、推送、合并或部署 |

## 当前队列

| Task | 状态 | 候选 / 结果 |
| --- | --- | --- |
| `TASK-TRACEABLE-LIVE-WORKBENCH` | `candidate_ready` | Kimi 候选 `71104ee`；Worker 报告 API 110、tools 71、Web 23 通过，当前 Codex 待核验 |

Task 可以并行，进入受保护 `main`、正式复核、部署和用户验收仍按依赖串行。

## 当前产品事实

- 方向 B 的公开回放体验位于 <https://47.84.34.86/>。
- 健康状态必须保持 `replay_only`；实时 Provider 不因控制系统启用而获得授权。
- `product/0.1.0` 尚未发布；Stage 12 已执行一次（19/24、9 通过），Issue #21 已修复当时的
  两条边界缺陷但未重跑未见集；Issue #22 已以部分结果和已知限制收口，不形成成功率主张。
- 结果顺序仍为 Issue #28 最终网站与受控真实演示、Issue #29 仓库展示、Issue #14 发布或
  保持 Beta 判断；并行 Task 不自动改变产品依赖。
- 当前工作树和公开 GitHub 仓库是产品唯一权威开发来源。
- 旧仓和临时回滚材料不是权威来源；删除仍是未经授权的独立破坏性动作。
- 受保护 `main` 的 CI 全绿后自动进入既有生产部署流程；失败部署不自动重试。

## 权威来源

- 产品事实：`PROJECT.md`
- 结果路线：`ROADMAP.md`
- 工程规则：`docs/engineering/`
- Agent 协作规则：`docs/engineering/agent-workflow.md`
