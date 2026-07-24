# 结果记录

> 状态：`in_progress`
>
> 启动日期：`2026-07-24`

## 当前进度

- 已由用户显式启动 Issue #22。
- 已从最新 `main`
  `146e96ec5b3f45fd9b2c039aa3a3ff0426f7cad5` 创建活动分支。
- 已建立稳定的生成失败阶段 / 原因族分类，并在 QA、工单和 Stage 12 公开聚合中接入。
- 第一阶段仍由 LLM 选择语义义务和证据子句；宿主只推导 evidence ID、忽略原文和顺序。
- 第二阶段仍由 LLM 生成客户正文、逐字 claim 和义务绑定；宿主只推导义务计划、
  `used_evidence_ids` 和 QA `claim_ids`。
- 来源逐字匹配、义务来源绑定、全义务覆盖、安全 / 型号前置门和失败关闭保持。
- 已增加固定 4 个公开合成案例、最多 8 次调用、自动重试 0 的直接 API 探针，并按独立
  授权执行一次真实模式。
- R0 候选代码提交：
  `f67099f871a31b6cf00b6881422744a8240519f0`。
- `issue22-public-synthetic-api-1` 实际 Provider 调用 `4`，自动重试 `0`；未使用本地
  生成 / 分类小模型。

## 本地证据

- 定向合同 / 探针：`10 passed`。
- API 全量：`86` 项收集，执行无失败，`1` 项环境门跳过。
- 工具全量：`68` 项通过，`7` 项环境门跳过。
- Web：lint、typecheck、`18` 项测试和生产构建均通过；后续改动不涉及 Web。
- 公开仓扫描：`passed`，`186` 个文件、8 个公开案例。
- `git diff --check`：通过。
- 使用 `docker build --network=none` 尝试构建该 SHA 的 `live` 执行镜像；基础镜像命中
  本地缓存，但 BGE 检索资产层未命中缓存，构建在 DNS 访问前失败并停止。没有创建候选
  镜像、没有 Provider 调用或费用。该结果只说明 R0 无网络条件下暂不能补齐执行镜像摘要。
- 用户随后只授权锁定公开依赖 / BGE 下载和候选镜像构建。构建成功，重依赖层均命中
  已校验缓存；候选镜像内容摘要为
  `sha256:01b1ad5f43918a23d66dd14a022d03b329f0e54d0ccd7e5988640abee1c2bbe9`，
  标签 revision 精确为候选代码 SHA，运行用户为 `10001:10001`。
- 候选镜像在 `--network none` 下通过全部 8 个公开检索案例，报告
  `provider_calls=0`；镜像内三组 prompt 哈希与验证卡一致。
- 使用初始化数据卷、只读根文件系统、无网络和 `live=false` 启动候选镜像，健康回执为
  `status=ok`、`live_experience=replay_only`。临时容器和验证卷已精确删除。
- `2026-07-24` 重新核对 DeepSeek 当前中文官方模型 / 价格页和 Chat Completion /
  JSON Output 文档：`deepseek-v4-pro`、`https://api.deepseek.com/chat/completions`、
  JSON Object、非流式响应、思考内容和 usage 字段均与当前适配边界一致；中文页价格仍为
  缓存命中 `¥0.025`、未命中 `¥3`、输出 `¥6` / 百万 tokens。英文页显示的是同一价格
  的美元展示，不构成计价合同变化。

## 外部 API 停止回执

- 用户独立批准固定卡后，使用候选代码
  `f67099f871a31b6cf00b6881422744a8240519f0` 和镜像
  `sha256:01b1ad5f43918a23d66dd14a022d03b329f0e54d0ccd7e5988640abee1c2bbe9`
  执行 `issue22-public-synthetic-api-1`。
- 固定 4 例中执行 3 例，共 4 次调用；自动重试 0。第 3 例第一阶段出现
  `provider_response_envelope_invalid` 后按硬停止结束，第 4 例未执行，剩余授权不再
  使用。
- `GEN-DEV-QA-003`：1 次调用后
  `enumeration_contract_failure:two_step_checklist_invalid`，未形成 candidate。
- `GEN-DEV-QA-006`：2 次调用后形成 candidate，第一 / 二阶段合同和 completeness gate
  均通过，但公开评分仍缺 2 条必须逐字出现的事实，因此案例未通过。
- `GEN-DEV-TK-001`：1 次调用后
  `enumeration_execution_failure:provider_response_envelope_invalid`，触发硬停止。
- 公开汇总：执行 `3/4`、通过 `0/3`、调用 `4/8`；生成失败 2 次，分别属于
  `checklist_shape` 和 `provider_response_envelope`。
- 只有成功解析 usage 的两次调用可估算为 `¥0.075783`；两次失败调用的 usage 未进入
  产品包，因此这不是账单或全部实际费用。三例最坏预留为 `¥0.359697`，未越过
  `¥2.80` 授权上限。外层执行墙钟时间约 `334.4s`；探针未公开逐调用延迟，这是回执
  仍需修正的证据缺口。
- 公开报告 SHA-256：
  `c44ba1f50b9fb8cd265045c119854a2e98657649c815677330ea42d01bb7d05b`。
- 仓库外私有记录 SHA-256：
  `ae727603242d0b163cdc59121c39f89d328294aea1a6c8102b6e028dcc27627d`。
  私有内容未写入 Git，公开记录不含 Provider 原始内容。

这些证据证明公开合成与注入式路径能接受省略冗余投影的合法输出，并继续拒绝缺失 /
冲突子句分区、跨子句逐字片段、错误来源和错误义务绑定。它不证明指定外部模型实际遵守
新合同，也不证明真实成功率、Stage 12 结果或开放域质量提高。

本地 Candidate 检查继续使用产品既有的固定 BGE 检索嵌入资产；它不是生成或语义决策
LLM。本增量没有新增或调用本地生成 / 分类小模型，后续语义验证只走经独立授权的外部
API。

## 仍待验证

- Provider 信封实际是哪一项官方字段差异；当前回执只保留稳定原因码，没有保存原始
  信封或足以区分字段的安全形状投影。
- 第一阶段 `two_step_checklist_invalid` 的具体子合同；当前原因码粒度不足。
- QA candidate 缺失事实是生成遗漏还是公开评分与允许改写边界不一致。
- 全部实际费用和逐调用延迟。
- Draft PR 四项 Checks、冻结 head SHA 的正式独立复核和用户实际体验。

## 停止后的本地诊断候选

- 只读复核 `GEN-DEV-QA-006` 的私有 candidate 后确认：两条公开必需事实、正确来源和
  三项义务均已覆盖；失败只来自检索文本已执行 NFKC（中文逗号变半角），评分器却直接
  比较原始全角标点。
- v2 评分器与检索层统一执行 NFKC。使用第一次 attempt 的既有产品包离线重评分，该例
  从 `required_fact_missing` 变为通过；未调用 Provider，也没有把语义判断交给规则。
- checklist 原来的聚合 `two_step_checklist_invalid` 已细分为结果形状、身份、义务数量 /
  形状 / 身份、子句 ID 和关键片段子码。
- Provider 信封在冻结 value parser 前增加只看字段 / 类型的子码，可区分 fingerprint、
  choice、`finish_reason`、`logprobs`、message 和空正文；不持久化推理或正文。
- 探针报告升级为 `generation-contract-probe-report-v2`，公开每次安全 transport 状态和
  延迟，并区分有 usage 的计价调用与没有 usage 的调用。
- 新增固定 `diagnostic-v2`：只运行 `GEN-DEV-QA-003` 与 `GEN-DEV-TK-001`，最多
  2 例 / 4 次调用 / `¥1.40` / 重试 0。
- v2 候选代码：
  `221c2df07736f0b8add23203295b8e1912deb462`；执行镜像：
  `sha256:f923ebc9546de7b90c782d30ba33112add981f4313a62e93f2c876bc02b4db68`。
- v2 证据：API `90` 项无失败（1 项环境门跳过）；工具 `71` 项通过、7 项环境门跳过；
  公开扫描通过；新镜像无网络检索 8/8、Provider 调用 0，revision 和非 root 用户正确。

这些本地证据只证明评分缺陷已修复、下一次失败会获得更具体且不含正文的子码。它不证明
checklist 或 Provider 信封已经兼容，不能恢复第一次授权。

## 当前允许的结论

Issue #22 的 R0 合同候选通过公开合成与注入式回归，机械投影已从模型输出移到宿主且
未放松已声明硬门；但它没有通过固定真实 API 探针，不能声称真实兼容性或成功率改善。
失败关闭和授权停止线实际生效。尚未形成生产就绪、发布或用户验收结论。
