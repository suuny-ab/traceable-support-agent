# 结果

> 状态：`candidate_local_green`

## 判据变化

- 旧判据在候选 outcome 上把冻结 `required_fact` 规范化后直接搜索客户可见正文；自然改写会误报
  `required_fact_missing`，同时缺 claim、越源或伪造 obligation ID 不一定被 R6 捕获。
- 新判据先从冻结命题在 approved source spans 中定位承接 obligation 与必要 evidence，再核对 checklist、
  obligation plan、used evidence 和 claim 的真实 ID、唯一性、范围及完整性。
- 找不到承接 obligation 继续报 `required_obligation_missing`；有承接 obligation 但没有合法绑定收据，报
  `required_proposition_binding_missing`。非候选 outcome 仍运行旧完整候选合同，保留原失败分类。

## 红绿证据与离线回归

- 公开合成 fixture 覆盖自然改写、缺义务、缺 claim、越源和伪造 obligation ID。旧 scorer 出现四处
  预期红测；新 scorer 五例全部符合合同。
- 已消费 24 个 package 只读重评分：六个 R6 案例均只移除 `required_fact_missing`，新增失败码 0；
  其余 18 例分类完全不变。回归视图由 11 通过 / 14 个失败码变为 17 通过 / 8 个失败码。
- 这不是新 Stage 12 运行或新质量分数；历史
  [`stage12-night-fixes-revalidation-v1.json`](../../../../evals/stage12-night-fixes-revalidation-v1.json)
  未修改。公开脱敏收据为
  [`stage12-r6-proposition-receipt-rescore-v1.json`](../../../../evals/stage12-r6-proposition-receipt-rescore-v1.json)。
- Provider 调用 0、自动重试 0、费用 0；产品生成和 outcome 未改变。

## 能证明与不能证明

能证明：host 能确定性验证 proposition 的 obligation / claim / evidence 绑定存在性与范围；自然改写不再
依赖客户可见字面子串；指定缺失和越界样例继续失败关闭；已消费六例的 scorer 回归符合审计结论。

不能证明：claim 声明的开放域语义一定真实、模型在新输入上的质量、正式 Stage 12 新分数、线上成功率、
用户验收或 `product/0.1.0` 发布成熟度。

## 验证

- Stage 12 定向 25 tests；API 全集 163 passed / 4 skipped；治理工具 126 passed / 8 skipped。
- Web lint、typecheck、生产 build 与 36 tests 全部通过；公开扫描 293 files / 8 public cases；
  园丁 stale 0 / review 1，唯一 review 是既有迁移记录；`git diff --check` 通过。
- 泄漏专项从私有集与今夜原始记录抽取 589 条长度不小于 16 的字符串；13 个候选文件精确命中
  33 条均已存在于 HEAD，相对 HEAD 新增私有长字符串命中 0。
- 定向测试首次因命令未传隔离树的只读 BGE 路径，在装配前报
  `embedding_model_file_inventory_invalid`；补齐既有模型路径后复跑 25/25 通过。没有下载模型。
- Provider 调用 0、自动重试 0、费用 0；未修改产品、生成、outcome 或历史评测资产。

本地候选已绿；待提交推送及 Draft PR #62 最终 head required Checks。
