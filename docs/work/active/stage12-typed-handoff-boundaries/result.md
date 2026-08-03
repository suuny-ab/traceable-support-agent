# 结果

> 状态：`candidate_ci_green`

## 决策表已编译

- `BoundaryDecision` 现在同时携带 `handoff_type`、稳定 `reason`、细粒度 `rule_id`、来源与
  guidance；零调用 package 和公开结果投影保留 type + reason。
- 新增三类生成前机械边界：CZ-R1 请求 CZ-R2 专属扫拖能力为 `model_scope`，CZ-R2 续扫
  反推与未登记语音接入为 `evidence_gap`，明确退款 / 换新 / 维修履约为
  `human_authority`。
- Runner、QA、ticket 和公共 API preflight 共用同一 evaluator 并显式传入 task type；命中
  售后履约时，公共 API 不保存输入原文、不排队、不构造 Provider。
- 既有 `GEN-DEV-MH-003` 产品差距已关闭；公开八案例集合不变，只删除对应 gap 登记。

## 先红后绿

现有 evaluator 上先增加六个公开等价例，定向执行为 3 failed：不接受 `task_type`、首例会
进入 transport factory、相邻例无法调用新签名。实现后同一组测试 3 passed；六行逐一断言
type、reason、rule 与 guidance，runner 逐例断言 preflight handoff、0 transport、0 Provider、
answer / proposal 均为空。

## 已消费私有集只读回归

私有集 SHA `7d730...8ab0`、既有原始记录 SHA `6eab...68af` 保持不变。Git 外只读执行只输出
以下结构结果，未输出或提交私有正文：

| 案例 | type | reason | rule | Provider 调用 |
| --- | --- | --- | --- | ---: |
| `MBD-001` | `model_scope` | `model_scope_conflict` | `cz_r2_wet_cleaning_not_available_on_cz_r1` | 0 |
| `MBD-002` | `evidence_gap` | `unsupported_claim` | `cz_r2_auto_resume_not_covered` | 0 |
| `IE-001` | `evidence_gap` | `unsupported_claim` | `voice_control_not_covered` | 0 |
| `FC-001` | `human_authority` | `after_sales_commitment` | `after_sales_replacement_requires_human` | 0 |
| `FC-002` | `human_authority` | `after_sales_commitment` | `after_sales_repair_requires_human` | 0 |
| `FC-003` | `human_authority` | `after_sales_commitment` | `after_sales_replacement_requires_human` | 0 |

六例均只有 `preflight=failed`，transport factory 调用总数 0，未形成 candidate。这是已消费集
回归，不是新的 Stage 12 运行，也不改写历史 `24/24、2 通过`。

## 本地验证

- 定向边界 + 公共 API：33 passed。
- API 全集：167 collected，163 passed / 4 skipped；显式复用已校验的 Git 外 BGE 模型根。
- 治理工具：122 passed / 8 skipped；Web lint、TypeScript、Next build 与 36 tests 全绿。
- Web 首次因隔离 worktree 无可再生 `node_modules` 而找不到 eslint；按锁文件 `npm ci` 后
  原命令全绿，未改依赖声明。
- 公开仓扫描 276 files / 8 public cases；文档园丁 stale 0 / review 1，唯一 review 是既有
  迁移记录；507 条基线未出现的 Git 外私有长字符串与候选差异比对命中 0；`git diff --check`
  通过。
- Provider 调用 0、自动重试 0、费用 0；未运行 Stage 12。

本地候选已绿；待提交、推送与 Draft PR Checks。

## 能证明与不能证明

能证明：六个预登记 R2 outcome 缺口与公开等价例都在生成前形成 typed handoff；相邻公开
可回答例未被新规则拦截；公开 false-completion 差距已被可执行测试关闭。

不能证明：历史 Stage 12 通过数或模型回答得到改善、规则覆盖任意开放表达、线上成功率上升，
或 `product/0.1.0` 已达到发布条件。本切片没有运行模型或生产验证。

## Draft PR 实现回执

实现 head `ace8a0e90044e6968d93cccd765ed2ad9b791580` 已推送到既有 Draft PR #62；
`ci-release` run `30762836230` 的 governance、web、api、containers 全部成功，publish 因
Draft 跳过。PR 未转 Ready、未合并、未部署，Provider 调用仍为 0。

本状态回执提交将形成最终 head；最终 head required Checks 仍须另行确认。
