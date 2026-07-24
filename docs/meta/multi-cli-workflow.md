# Traceable Support Agent 多 CLI 项目适配器

> 状态：`current`
>
> 采用协议：`ai-work-control/0.1`
>
> 采用日期：`2026-07-24`

本文件把跨项目 AI 工作控制协议适配到本仓库。通用运行注册表和协议由用户的 Git 外个人
控制仓库 `ai-work-control` 管理；本文件只定义软件项目特有的工作树、候选、复核和集成
边界。仓库规则保持自包含，Worker 不需要读取个人 Work 的私密内容。

## 角色与对象

- **用户**：只从个人 Work 的 Codex 入口讨论方向、选择执行器，并决定产品范围、体验、
  外部风险和不可逆取舍；
- **Codex**：统一入口、项目 controller 和默认 integrator；恢复事实、形成 Task、登记 Run、
  管理依赖、透明转述消息并路由候选；
- **Worker**：某个 `executor + run_id + workspace + role`，在隔离空间自主实现；
- **Reviewer**：只读固定候选并按 `docs/engineering/review.md` 出具所需复核；
- **Delivery**：把候选通过 direct、stacked 或 batch 关系送入 PR、受保护 `main` 和必要部署。

长期连续性属于 Work Object 和 Task，不属于会话。一个 Task 可以跨多个 Run；同一个 CLI
也可以同时拥有多个隔离 Run。

## Task 从哪里来

GitHub Issue 是已经确认的未来产品工作和公开追踪载体之一，不是执行前置条件。开发中自然
产生且需要立即处理的缺陷、探索、集成或元开发事项可以直接成为 Task。Task 必须至少固定：

- 用户或项目新增得到的结果；
- 最便宜且相关的验收；
- 依赖、候选基线和 Delivery；
- 风险需求、隔离位置和唯一写入者；
- 能形成和不能形成的结论。

常规文件、库、类和测试形态由 Worker 决定。改变产品范围、公开主张、隐私、安全、费用、
外部状态或不可逆边界时，返回用户决定。

## 并行与隔离

- 后台 Task 和 Run 不设人为数量上限；
- 同一可写 worktree 同一时刻只有一个写入 Run；
- 并行写入使用不同分支和 worktree，只读调查可以共享固定候选；
- 可并行不等于无依赖，Task 要显式声明 `depends_on`；
- 同一 Task 可以由多个 Run 接续，也可以使用独立 Run 做方案、实现、验证或集成；
- `main`、正式复核、发布、部署和最终用户验收仍按候选顺序串行收口。

`docs/status.md` 只保存项目结果队列、固定候选和稳定边界。高频 Run 状态、CLI 会话、进程
日志和事件位于 Git 外控制注册表，不复制进仓库。

## 派发与消息透明

派发消息使用自然、目标导向的委托，说明产品背景、期望结果、参考、边界、工作树和角色，
邀请 Worker 自主调查、规划、实现和验证。除非接口或命令本身是合同，不规定逐文件机械步骤。

Codex 每次发送初始委托、追问或纠偏后，立即向用户公开：

- CLI、Run ID、角色和 worktree；
- 附带的文件或素材；
- 实际发送的完整消息。

Worker 回复时，Codex提取理解、已完成内容、决定、意外发现、风险、验证和下一步，并区分
`Worker 报告`、`Codex 已核验` 和 `待核验`。原始 stdout、模型思维和无关日志不进入 Git。

## Worker 责任与检查点

标准 / 完整 Task 可以在其工作包中维护 `spec.md`、`plan.md`、`result.md`；强制独立复核时
由 reviewer 维护 `review.md`。轻量 Task 可以只留下代码、测试和简洁结果。

每个 Run 结束、额度触线、切换执行器或让渡前，必须留下可恢复检查点：

- 已完成与未完成；
- 实际修改和关键决定；
- 测试、自验和限制；
- Git 状态、commit 或候选引用；
- 失败、额度和唯一恢复动作。

Codex 先核对真实 diff、Git 状态、测试和回执，再改变 Task 或 Delivery 状态。Run 完成不等于
Task 候选合格，Task 候选合格也不等于 Delivery 已应用。

## 候选与集成

软件候选支持三种关系：

- **direct**：候选直接以目标分支为基线；
- **stacked**：候选依赖另一个尚未进入 `main` 的候选，PR 明确 base 和依赖；
- **batch**：多个独立候选先由 integrator 在专用分支组合、解决语义冲突并统一验证。

实现 Worker 不默认负责最终合并。Codex 依据依赖和风险决定让原 Worker、独立 integrator 或
平台完成集成；任何方式都必须通过受保护分支和当前 GitHub 生命周期。文本无冲突不能证明
语义兼容，合并前应在最新目标基线上运行最便宜且相关的检查。

PR 绑定固定候选、Checks、复核和外部回执。不要用自动关闭关键字；所需部署和用户实际体验
齐全后再更新稳定事实并关闭 Issue。推送、合并、部署和公开发布是不同外部动作。

## 复核与验收

- 普通 R0/R1 UI 与缺陷 Task 由自动化和 integrator 关闭；
- 元规则、S2/S3、生产、发布、安全、隐私、认证、费用、持久化、公共合同或公开主张变化，
  按 `docs/engineering/review.md` 对绿色 Draft PR 固定 SHA 做一次独立复核；
- finding 修复后默认只复核 finding 和覆盖 diff；
- Worker 专业自验、工程集成、正式复核和用户实际体验互不冒充。

## 权限

CLI 选择、Task、Issue、仓库文件和控制注册表都不能授予 Provider、凭据、费用、部署或外部
写入。Run 必须引用当前、Git 外授权；没有授权时失败关闭。产品实时 Provider 还必须遵守本
仓库的数据、健康门和 Stage 12 边界。

## 新会话恢复

Codex 从个人 Work 统一入口恢复控制台，再读取本仓库 `PROJECT.md`、`docs/status.md` 和相关
候选。Worker 从派发消息、`AGENTS.md`、项目状态和自己的 worktree 恢复，不依赖旧聊天。

协议升级不会自动进入本项目。只有显式修改本适配器并记录采用版本后，新的跨项目规则才对
本仓库生效。
