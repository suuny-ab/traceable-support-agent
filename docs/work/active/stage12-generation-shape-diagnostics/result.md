# 结果

> 状态：`candidate_local_green`

## 历史失败能定位到哪里

`MSQ-001`、`SCQ-002` 的既有脱敏 package 显示 checklist 已通过，安全调用观察显示第二次
Provider 调用成功，随后产品以
`generation_contract_failure:top10_v6_content_invalid` 失败关闭。旧 validator 在这个码之后
才遍历 claim、证据和 obligation binding，因此可以排除义务覆盖、证据引用与 completeness
作为该次失败点，定位到 QA 第二阶段的 content 外形层。

历史记录有意不保留 Provider 响应正文，所以只能知道命中旧粗码覆盖的四个条件之一；不能
知道两个案例分别是 content 容器、identity、answer 外形还是 claims 数量。`IE-003` 也产生过
同码，但冻结期望本来就是 handoff，不能把它当作候选质量改善样本。

## 公开等价复现

新增公开合成夹具
[`generation-shape-equivalent-v1.json`](../../../../evals/fixtures/generation-shape-equivalent-v1.json)，
SHA-256 `fbd2ef93b2a0069a6ae51bb904803ba441414bd60da997422462eb46104e5e21`。它固定一个已验证
checklist 和四个 malformed step-2 响应：

| 公开案例 | 畸形位置 | 基线 `cd1de058` | 修复候选 |
| --- | --- | --- | --- |
| `GEN-SHAPE-PUBLIC-001` | content 容器 / keys | `top10_v6_content_invalid` | `top10_v6_content_shape_invalid` |
| `GEN-SHAPE-PUBLIC-002` | kind / insufficient identity | `top10_v6_content_invalid` | `top10_v6_content_identity_invalid` |
| `GEN-SHAPE-PUBLIC-003` | answer 外形 | `top10_v6_content_invalid` | `top10_v6_answer_shape_invalid` |
| `GEN-SHAPE-PUBLIC-004` | claims 类型 / 数量 | `top10_v6_content_invalid` | `top10_v6_claim_count_invalid` |

改码前四项 4/4 复现旧码；改码后合同级 4/4 返回对应子码，离线产品链 4/4 仍为
`outcome=handoff`、`answer=null`。脱敏机器回执见
[`generation-shape-diagnostics-v1.json`](../../../../evals/generation-shape-diagnostics-v1.json)。

## 最小修复

- 只把三个旧校验分支拆成四个隐私安全子码；校验条件、顺序和允许值未放宽。
- 四个子码的 phase 固定为 `generation_contract`、family 固定为 `generation_shape`；分类不读取
  Provider 内容。
- 离线产品测试注入两个合成响应，证明每个 malformed 结果仍失败关闭，不能形成 candidate。
- checklist、claim shape、客户可见 span、obligation / clause binding、completeness 和 matched
  handoff scorer 的既有合同不改。

## 历史与结论边界

- 历史复验聚合 SHA-256 仍为
  `2de8d63be45974bcb58fdbc2d43d75d470854ae4268a7a30d229989a136b57b9`；matched-handoff
  重评分回执仍为 `d1356190bde6632b92f8482637a8abab35a5c2db8675cca47e51b97e91f3c88e`。
- 不重跑 Stage 12、不读取或恢复历史 Provider 正文；Provider 调用 0、自动重试 0、费用 0。
- 这个修复提高未来失败的诊断分辨率，不会让两个历史候选案例变成通过，也不证明模型质量、
  Stage 12 分数、线上成功率或发布成熟度改善。
- safe candidate vs typed handoff 仍是单独的产品取舍，本切片未决定、未实现。

## 验证

- 定向：generation_shape 合同 / 产品 / 回执 9 tests 通过；四子码和四个 handoff 均精确断言。
- API 全集：162 tests collected，158 passed / 4 skipped；只有既有依赖弃用 / 版本告警。
- 治理正式口径：120 passed / 8 skipped；Stage 12 与 generation probe 对照均通过。
- 公开仓：266 files / 8 public cases，通过；文档园丁 stale 0 / review 1，唯一 review 是既有
  迁移记录；`git diff --check` 通过。
- 私有泄漏专项：把 Git 外原始记录的 153 条含正文特征长字符串与 15 个候选文本文件逐字
  比对，命中 0；历史原始记录 SHA 仍为 `6eab...68af`。
- 首次治理全集未显式传本地 BGE 根目录，在检索装配前以
  `embedding_model_file_inventory_invalid` 停止；补齐仓库登记的只读模型路径后完整复跑全绿，
  未为环境错误改产品实现。
- 公开仓门首次发现 `docs/status.md` 缺 7 个活动目录的机器可识别显式指针；恢复指针后同门
  通过。Provider 调用、Stage 12 执行、generation 真实调用均为 0。

本地候选已绿；待提交、推送并确认 Draft PR #62 最终 head required Checks。
