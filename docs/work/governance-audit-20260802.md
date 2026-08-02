# 开发治理问题定位（2026-08-02）

> 审计窗口：`2026-07-26 00:00 +08:00` 至 `2026-08-02`。
>
> 范围：`AGENTS.md`、`docs/engineering/` 全部文件、近 7 天 Git 历史、Traceable 派发/战报与相关 Codex 会话。
>
> 本文只记录问题与证据，不提出解决方案，不改变产品、生产、Provider、费用或安全边界。

## 审计口径

- 做什么：定位“状态文件老出问题”是否属于开发治理问题，并把规则文本与实际执行分成
  “写了没执行 / 执行了没写 / 写了反而碍事”。
- 不做什么：不改规则、代码、测试、Workflow 或产品事实，不处理 PR #55 冲突，不给治理方案。
- 完成线：规则族总量和引用关系可复核；近 7 天事故有 Git / 文件 / 会话证据；问题按损失排序；
  未证实的越界不写成事实。

## 规则族盘点

| 文件 | 行数 | 标题数 | 主要职责 | 直接指向的治理入口 |
| --- | ---: | ---: | --- | --- |
| `AGENTS.md` | 180 | 14 | 启动、权限、协作、风险、验证、完成总则 | `agent-workflow.md`、`github-lifecycle.md`、`quality.md`、`review.md` |
| `docs/engineering/agent-workflow.md` | 66 | 6 | Conversation / Task / Run / 候选协作 | `AGENTS.md` |
| `docs/engineering/development-flow.md` | 87 | 8 | 三问、规模、复用、停止与完成 | `github-lifecycle.md`、`review.md`、`AGENTS.md` |
| `docs/engineering/evaluation.md` | 43 | 5 | 回归集、HOLDOUT 与 Stage 12 边界 | 无 |
| `docs/engineering/github-lifecycle.md` | 67 | 5 | Issue / PR / 状态 / 外部回执所有权 | `docs/status.md`、`ROADMAP.md` |
| `docs/engineering/migration-record.md` | 73 | 8 | 迁移基线与历史验收记录 | 无 |
| `docs/engineering/operations.md` | 70 | 5 | 当前部署与自动发布合同 | 无 |
| `docs/engineering/quality.md` | 167 | 12 | 检查分层、CI 证明与机器门 | `evidence-map.md`、`docs/status.md`、`review.md` |
| `docs/engineering/review.md` | 72 | 5 | 机器 / 授权 / Reviewer 三层拦截 | `evidence-map.md` |
| `docs/engineering/security.md` | 28 | 5 | 安全、隐私与实时模式门 | 无 |
| **合计** | **853** | **73** | 1 个根规则文件 + 9 个工程文件 | — |

引用结构以 `AGENTS.md` 为中心，但不是单向树：`agent-workflow.md` 反向引用 `AGENTS.md`；
`development-flow.md` 不在启动顺序的明确文件指针中，却重复承载三问、工作规模和完成条件；
`evaluation.md`、`migration-record.md`、`operations.md`、`security.md` 在该规则族内没有继续指向
其他治理入口。三问、单写者、状态所有权、当次授权和 Reviewer 条件至少分布在 3—5 份文件中
（`AGENTS.md:61-93`、`docs/engineering/agent-workflow.md:18-32`、
`docs/engineering/development-flow.md:6-16,29-51`、
`docs/engineering/github-lifecycle.md:15-23`、`docs/engineering/review.md:28-56`）。

## 近 7 天事故与摩擦

| 日期 | 事件 | 直接损失 | 证据 |
| --- | --- | --- | --- |
| 2026-07-31 | PR #43 报 `active_increment_count:0`；状态从 `in_progress` 改为 `ready` 才绕开四文件要求 | 候选停下并向用户追加一次治理确认 | 会话 `019fb5f4-e12b-7670-9352-fab76d08615c`，JSONL 1947-1950 行 |
| 2026-08-01 | PR #52 首次 head 再次因 `active_increment_count:0` 失败，产品 job 未失败 | 追加 `f8ab75e`，生成 `spec/plan/result/review` 四文件；随后 `3dc0c00` 再归档 | 提交 `f8ab75e`、`3dc0c00`；会话 `019fbd57-2b0e-7791-9c4c-797d66fd8d5d` JSONL 67-68 行 |
| 2026-08-01 | 通信链路测试要求把一次时间戳追加进 `docs/status.md` | 会话运行事实进入 Git 工作区并永久占据“当前状态”末尾 | `docs/status.md:3-5,149`；`派发/已回执/traceable-通信测试-20260801.md` |
| 2026-08-01—02 | 工作树扫描被本地 `AGENTS.md` 中用户目录绝对路径和未跟踪 `clean/` 拦截，只能改用干净 index / 隔离 worktree | 同一候选存在“当前工作树失败、候选快照通过”两套口径 | `AGENTS.md:9-15`；`tools/check_public_repo.py:234-239`；`docs/status.md:50-57` |
| 2026-08-02 | 检索候选在隔离 worktree 又一次因状态标为 active 触发 `active_increment_count:0` | 再次读取机器合同并改写状态语义 | 会话 `019fc00d-1e29-7680-8584-a15b54c2800c`，JSONL 290-296 行 |
| 2026-08-02 | PR #54 已合并，但合并后的 `origin/main` 仍写“等待 Checks、未合并” | 权威公开状态在动作成功后立即过期 | `origin/main:docs/status.md:10-21`，提交 `8a306165`；实际回执见 `docs/status.md:70-89` |
| 2026-08-02 | PR #55 与新 main 的唯一冲突是 `docs/status.md` | 候选不可合并、没有 PR workflow run，需要新 head 与新授权 | `git merge-tree b6b68e8 origin/main origin/codex/retrieval-badcase-loop`；提交 `d8cd208`、`80953b5`、`45db89f` |

量化补充：近 7 天 `--all` 的 38 个提交中，30 个触碰 `docs/status.md`（78.9%）；该文件累计
448 行新增、322 行删除，共 770 行 churn。文件从 `df81ccd` 时 35 行增长到 `origin/main` 的
100 行、检索分支的 126 行和本地工作区的 149 行。17 个提交只修改文档族，其中多个是纯状态
推进或治理收口。以上统计来自 `git rev-list/log --all --since=2026-07-26 -- docs/status.md`。

## 按损失排序的问题清单

### 1. `docs/status.md` 的职责组合使它无法同时保持“当前、权威、可合并”

- 分类：**写了没执行 + 写了反而碍事**。
- 规则：它既是当前状态与候选权威（`AGENTS.md:24-32`），又要接收每个默认通过动作的回执
  （`AGENTS.md:40-44`），还要承接候选、阻碍和验证事实
  （`docs/engineering/github-lifecycle.md:15-23`）。
- 实际：同一个单文件同时保存顶部当前表、9 条长期队列、三段派发/授权回执、历史产品事实、
  环境限制和通信测试时间戳。PR #54 合并后，公开 main 仍停留在“等待 Checks”；本地补写版
  又在 `docs/status.md:20` 记录生产 `release_sha=915ca4e…`，同时在
  `docs/status.md:116-118` 声称当前生产版本及健康 SHA 是 `66af626…`。
- 损失：启动摘要会给出错误当前态；外部动作完成后需要另一次状态写入才能追平；并行候选
  必然争写同一热点文件。PR #55 已把该风险变成实际合并阻断。
- 证据：`docs/status.md:3-21,40-149`；`origin/main:docs/status.md:10-21`；
  近 7 天 30/38 次提交、770 行 churn；PR #55 merge-tree 唯一冲突。

### 2. “轻治理”文本与仍然生效的四文件机器门不一致

- 分类：**写了反而碍事**。
- 规则：PR #48 后，默认立项只需三问，完整工作或部署/费用/安全/R2 才要求完整规格
  （`AGENTS.md:81-85`、`docs/engineering/development-flow.md:6-16,40-47`）。
- 实际：机器门仍要求任何非 `ready + 活动工作无` 的状态必须存在且只能存在
  `spec.md/plan.md/result.md/review.md` 四文件，并由状态链接
  （`tools/check_public_repo.py:1018-1043`、`docs/engineering/quality.md:124-131`）。该代码来自
  PR #48 之前，轻治理改写没有同步改变机器合同。
- 损失：三天内至少三次同码失败（PR #43、PR #52、检索候选）；PR #52 为通过治理门新增四文件
  和后续归档提交，检索候选则把正在形成的候选改写为 `ready`。机器绿灯因此同时带来返工和
  状态语义失真。
- 证据：提交 `64162f1`、`f8ab75e`、`3dc0c00`；上述三个会话指针。

### 3. 当前实际执行的启动/授权规则没有进入权威 Git，且会被自己的公开扫描器拒绝

- 分类：**执行了没写 + 写了反而碍事**。
- 规则/实际：工作区 `AGENTS.md:9-15,40-44` 新增心跳、派发绝对路径和授权三档；当前每轮确实
  依这些条款执行，但 `git diff` 显示它仍是未提交本地修改，公开 `origin/main` 不含这些规则。
  同时公开扫描器明确拒绝 Windows 用户目录路径
  （`tools/check_public_repo.py:234-239`、`docs/engineering/quality.md:128-132`、
  `docs/engineering/security.md:26-28`）。
- 损失：不同 worktree / 新会话读到的规则不同；当前规则一旦纳入候选又会让治理检查失败。
  2026-08-01 的工作树扫描已经因此失败，候选只能避开当前工作区验证。
- 证据：`git diff -- AGENTS.md`；`docs/status.md:50-57,67-68`；会话
  `019fc00d-1e29-7680-8584-a15b54c2800c` JSONL 21-25 行。

### 4. 同一授权动作在规则族中存在不同默认值

- 分类：**写了反而碍事**。
- 规则 A：当前 `AGENTS.md:40-44` 把 CI 绿后的非 main 分支推送列为默认通过，把建 PR 列为
  异步授权请求。
- 规则 B：`docs/engineering/review.md:28-41` 把公开/外部写入列为本次具体候选的当次明确确认；
  `docs/engineering/agent-workflow.md:62-66` 又把推送、合并、发布、部署并列为需要当前动作授权。
- 实际：检索分支推送和 Draft PR #55 采用了更严格的精确 head 当次授权，没有发生未授权写入；
  但文本本身允许另一个 Agent 把相同行为判断为默认通过。
- 损失：边界判断依赖读者选择哪份文件，而不是动作本身；这会制造额外授权往返，也保留越界风险。
- 证据：上述文件行；`派发/授权请求.md` 的 2026-08-02 Traceable 裁决与执行回执。

### 5. 明确要求留在 Git 外的会话/进程事实仍被写进“当前状态”

- 分类：**写了没执行**。
- 规则：快速变化的 session、进程和额度状态由 Git 外控制系统保存
  （`AGENTS.md:77-79`）；`docs/status.md:3-5` 也声明 Conversation / Turn 运行状态在 Git 外。
- 实际：`docs/status.md:53-57` 保存某次执行环境的 `.git` 只读、终端网络阻断、失效 `gh` token；
  `docs/status.md:149` 保存通信链路测试时间戳。到本审计时，本地 Git 已可 fetch/push，旧环境描述
  仍留在当前文件。
- 损失：瞬时故障被后续摘要当成当前阻碍；状态继续膨胀并增加冲突面。
- 证据：上述文件行；`派发/已回执/traceable-通信测试-20260801.md`；会话
  `019fbd57-2b0e-7791-9c4c-797d66fd8d5d` JSONL 25-30 行。

### 6. “唯一权威主 worktree”是文档主张，不是当前可恢复事实

- 分类：**写了没执行**。
- 规则：相信文档前先查 Git，完成时提交干净有界改动
  （`AGENTS.md:16-20,164-174`）；状态声称主 worktree 是唯一权威位置
  （`docs/status.md:16,132-138`）。
- 实际：本审计开工时主 worktree 位于已删除远端的
  `codex/frontend-polish-delivery-closeout@3dc0c00`；本地 `main@e52bae3` 落后
  `origin/main@8a30616` 三个提交；工作区混有 `AGENTS.md`、`README.md`、`docs/status.md` 修改和
  未跟踪 `clean/`。检索候选另在隔离 worktree。
- 损失：启动恢复无法从所谓权威位置直接得到干净基线；状态回写与候选实现被迫分散，进一步
  放大第 1 项的事实分叉。
- 证据：会话 `019fc00d-1e29-7680-8584-a15b54c2800c` JSONL 21-25、105-111 行；
  本轮 `git branch -avv` / `git worktree list`。

### 7. 历史记录使用“当前”措辞，已与现行稳定事实相反

- 分类：**写了没执行**。
- 规则：当前事实优先于旧报告，未知/未验证必须标记
  （`AGENTS.md:22`）；稳定事实由 `PROJECT.md` 保存（`AGENTS.md:24-32`）。
- 实际：迁移记录尾部仍写“当前公网版本保持 `replay_only`”
  （`docs/engineering/migration-record.md:62-73`），而运维合同和稳定产品事实已经写明
  2026-07-29 起 live、健康为 `available`
  （`docs/engineering/operations.md:3-11`、`PROJECT.md:33,50`）。
- 损失：按“只读相关工程文件”的启动策略读取到迁移记录尾部时，会把历史快照摘要成当前产品状态；
  这正是可复现的摘要误读源。
- 证据：上述文件行；提交 `dc29538`、`8a74bd6`、`766ba3f`。

### 8. 三行战报是覆盖式快照，无法承担事故历史证据

- 分类：**执行了没写**。
- 规则：里程碑、连续失败和边界不清时写固定路径三行战报
  （`AGENTS.md:10-15`）。
- 实际：2026-08-01—02 至少 6 份 Traceable 派发都要求写同一个
  `战报-traceable.md`，当前文件只保留最后一次 PR #54 / #55 结果；已回执文件多数保存任务正文，
  不保存当时被覆盖的三行结果，其中第二轮心跳文件还以“已取消”命名。
- 损失：本次审计无法从战报本身还原近 7 天里程碑、失败或边界升级，只能回查膨胀的
  `docs/status.md` 与会话 JSONL。
- 证据：`派发/战报-traceable.md`；`派发/已回执/traceable-*.md` 的文件名、正文和时间戳。

## 分类汇总

| 分类 | 对应问题 | 已观察结果 |
| --- | --- | --- |
| 写了没执行 | 1、5、6、7 | 权威 main 过期、瞬时状态入 Git、主 worktree 不在权威基线、历史文档冒充当前事实 |
| 执行了没写 | 3、8 | 实际运行规则只在本地脏文件；战报结果被后续覆盖 |
| 写了反而碍事 | 1、2、3、4 | 单状态文件冲突、四文件门三次阻断、自身路径扫描冲突、授权口径分叉 |

## 未发现的越界

近 7 天证据中未发现未经当次授权的 Provider 调用、生产部署、PR #54 合并或 PR #55 公开写入。
PR #54 合并绑定精确 head `d8cd2081…`；PR #55 只推送并创建 Draft，绑定精确 head
`45db89fe…`，未合并。部署链对 PR #54 的 `governance_only` 决定执行 preflight 后跳过 deploy，
公网运行版本未改变。这里的问题是治理造成事实滞后、冲突和返工，不是已证实的 R2 越界事故。
