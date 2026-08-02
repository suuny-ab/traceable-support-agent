# 结果

> 状态：`candidate_local_green`

## 固定身份与审计方法

- 候选生成身份保持 `night-20260802@fc766709f48bf2989c6589a56db3cec7593ed6cb`；本审计不生成
  新输出。私有集 SHA-256 `7d73073cd0227b0ced81398fcbadc7e5f85867a633a9654d82bd0b516c358ab0`，
  今夜原始记录 SHA-256 `73d272e9ddfa2910bc86567e35e4314421ec790e4f004cd0d02828a99260c850`。
- 公开聚合中的六个 `required_fact_missing` 案例全部进入本审计；共 11 条冻结事实，按各案例
  原有顺序编号为 `P1` / `P2`。编号不跨案例复用，也不公开事实明文。
- 审计逐条核对 `冻结命题 → approved clause → obligation → claim → customer-visible support`。
  前四层用现有 ID 机械锁定，最后一层由有界人工判断是否表达相同动作、条件、禁止、状态效果或
  维护周期；没有使用 LLM judge。
- 公开机器收据为
  [`stage12-r6-semantic-audit-v1.json`](../../../../evals/stage12-r6-semantic-audit-v1.json)；
  私有明文只在 Git 外固定输入中读取。

## 逐题收据

| 案例 | 命题 | obligation | approved clause | claim | 有界理由 | 判定 |
| --- | --- | --- | --- | --- | --- | --- |
| `MSQ-001` | `P1` | `o1` | `c003,c004,c005,c006,c041` | `c1,c2` | 当前问题语境下的动作与跨型号禁止改写 | 字面假阴性 |
| `MSQ-001` | `P2` | `o5` | `c019,c020` | `c6` | 状态效果改写 | 字面假阴性 |
| `SCQ-001` | `P1` | `o1` | `c004,c005` | `c3,c4` | 操作顺序改写 | 字面假阴性 |
| `SCQ-001` | `P2` | `o1` | `c006,c007,c008,c009` | `c5` | 停止条件与升级信息改写 | 字面假阴性 |
| `SCQ-002` | `P1` | `o2` | `c002,c003,c004` | `c2` | 组合动作改写 | 字面假阴性 |
| `SCQ-002` | `P2` | `o4,o5` | `c006,c067,c068,c069` | `c4,c5` | 前一 claim 建立最后一次尝试，后一 claim 承接失败停止条件 | 字面假阴性 |
| `ATK-003` | `P1` | `o1` | `c001,c002,c003` | `c1` | 工单回复与步骤共同表达组合动作 | 字面假阴性 |
| `ATK-003` | `P2` | `o1` | `c004,c005` | `c1` | 维护周期与防完全放空改写 | 字面假阴性 |
| `SO-002` | `P1` | `o1` | `c006,c007` | `c1` | 型号行为改写 | 字面假阴性 |
| `SO-002` | `P2` | `o2` | `c008` | `c2` | 禁止 / 禁区要求改写 | 字面假阴性 |
| `SO-003` | `P1` | `o2` | `c002,c003,c004` | `c2` | 操作顺序改写 | 字面假阴性 |

逐案例结论：真语义遗漏 `0/6`，字面假阴性 `6/6`。逐命题结论：真语义遗漏 `0/11`，
绑定且客户可见语义覆盖 `11/11`。这只纠正六个已消费案例的 R6 归因；当前公开聚合仍是
24/24 执行、11 通过、14 个失败码，历史文件不改写，也不在本切片重评分。

## R6 修复方案候选（未实现）

1. 冻结集把每条 `required_fact` 投影为案例内 `proposition_id`，并冻结其批准 clause 集；保留
   原文只用于私有冻结校验，公开报告只保存命题 ID 和哈希。
2. scorer 不再对 customer-visible 全文做 required-fact 子串检查；改为验证每个 proposition
   都有完整收据：批准 clause 被 obligation 承接，至少一条真实 claim 绑定该 obligation，claim
   的 evidence 在批准范围内，且 ID / schema / outcome 合同全部有效。
3. 找不到承接 obligation 时继续报 `required_obligation_missing`；有 obligation 但没有合法绑定
   claim 时，候选新码为 `required_proposition_binding_missing`。越源、伪造 ID、结构失败和
   unexpected outcome 继续使用现有失败关闭规则。
4. 允许一个 proposition 由多个 claim / obligation 组合承接，以覆盖条件在前文建立、动作或
   停止结果在后文表达的情况；组合成员必须全部出现在同一 package 的 host-derived 账本。
5. 该方案遵循 ADR-0007：模型声明语义映射，宿主验证绑定存在性。它不能发现“ID 都合法但
   claim 语义声明错误”的开放域漂移，因此候选仍需人工最终审核；不能写成“只要绑定就真实”。

这份方案的“只拦真漏”严格指机械可判定的收据缺失，不承诺宿主自动证明开放域语义等价。
若后续获准实现，应先用公开合成正反例证明：自然改写通过；缺 obligation、缺 claim、越源和
伪造 ID 仍失败。已消费六题只作回归，不作为新质量分数。

## 能证明与不能证明

能证明：固定六题的 11 条冻结命题都能回绑到客户可见等价表达，六个 R6 码均为当前字面评分
合同的假阴性；公开收据可由案例 ID、账本 ID 与私有内容哈希复核。

不能证明：模型在新输入上的语义忠实、绑定声明一定真实、修复后正式通过数、单一修复因果
效果、线上成功率、用户验收或 `product/0.1.0` 发布成熟度。

## 验证

- 私有回放核验：公开六题集合与源聚合精确一致；11 个命题事实哈希、客户可见投影哈希、
  obligation / clause / claim ID 和支撑 span 哈希全部与固定 Git 外输入匹配。
- Stage 12 定向 23 tests；API 全集 163 passed / 4 skipped；治理工具 124 passed / 8 skipped。
- Web lint、typecheck、生产 build 与 36 tests 全部通过；公开扫描 287 files / 8 public cases；
  园丁 stale 0 / review 1，唯一 review 是既有迁移记录；`git diff --check` 通过。
- 泄漏专项从私有集与今夜原始记录抽取 589 条长度不小于 16 的字符串；候选文件精确命中 32 条
  均已存在于 HEAD，新增私有长字符串命中 0。
- 定向测试首次因隔离树没有本地 BGE 文件而在装配前报
  `embedding_model_file_inventory_invalid`；逐文件核验主工作树既有缓存的 7 个大小 / SHA 后，
  显式只读复用并复跑全绿。没有下载模型或改仓库。
- Provider 调用 0、自动重试 0、费用 0；未修改 scorer、产品或历史评测资产。

本地候选已绿；待提交推送并确认 Draft PR #62 最终 head required Checks。

## Draft PR 审计实现回执

审计实现 head `1b9f67e3f1afe42f0d4d0de531092b84802ae809` 已推送到既有 Draft PR #62；
`ci-release` run `30766175961` 的 governance、web、api、containers 四项 required jobs 全部
成功，publish 因 Draft 跳过。PR 未转 Ready、未合并、未部署，Provider 调用仍为 0。

本状态回执提交将形成最终 head；只确认该 head required Checks，全绿后停止。
