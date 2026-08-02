# 结果

> 状态：`candidate_local_green`

## 执行前身份

- 候选：`night-20260802@df01968c56350626544ca4acc4ed88cf13dfd337`。
- runner：`tools/stage12_eval.py` 与 `origin/main` 为同一 Git blob
  `132328043321a550b3ff480f961644e11f7a9220`。
- 模型：`deepseek-v4-pro`；prompt 集合 SHA-256
  `108ab9aae60eb86806383cc2fea4511d358955f50503531e0da2e82be1ba8584`。
- 私有未见集：24 题，SHA-256
  `7d73073cd0227b0ced81398fcbadc7e5f85867a633a9654d82bd0b516c358ab0`；留在 Git 外。

## Provider 前预检

- 冻结检查通过：24 题与上述 SHA 精确一致。
- Stage 12 runner 定向测试：`13 passed`。首次测试因隔离 worktree 缺本地 BGE 缓存而在
  用例装配阶段失败；随后按模型清单逐文件大小 / SHA-256 核验主工作树 7 文件缓存并只读复用，
  未下载、未改代码或资产，Provider 调用 0。
- 旧响应离线回归完成 24 题，Provider 调用 0；它只证明当前装配可运行，不是本次真实复验结果。

## 唯一一次真实复验

- 执行窗口：`2026-08-02 23:36:34 +08:00` 起；同一容器 / 同一进程串行完成，未重启、
  未补跑。外层 15 分钟等待命令先超时，但原容器保持运行；后续只用 `docker wait` 监控同一
  容器，最终 runner 退出码 1（存在未通过题，不是装配失败）。
- 结果：24/24 案例执行，2 题通过；39/150 次 Provider 调用，自动重试 0；未提前停止，
  `stop_code=null`。
- 用量：私有原始记录有 35 条有效 usage，合计 prompt 158,086、completion 139,320、
  total 297,406 tokens，其中 cache hit 16,896、cache miss 141,190；机制估算费用
  ¥1.2599124 / ¥10。39 次调用中 4 次没有有效 usage 回执，因此这些数字不是账单确认。
- 生成失败：4/24 packages；`generation_shape` 3、`checklist_shape` 1。
- 公开聚合：`evals/stage12-post-fix-revalidation-v1.json`，SHA-256
  `2de8d63be45974bcb58fdbc2d43d75d470854ae4268a7a30d229989a136b57b9`；与 Git 外 runner
  输出逐字节一致。
- 私有原始记录：Git 外保管，SHA-256
  `6eab96586c03abb15366c6e8c11ef7c1dd8617c8a8aa82fa7127c1e5913368af`；不公开明文。

## 逐维度观测

| 维度 | 执行 | 通过 |
| --- | ---: | ---: |
| multi-source-qa | 3 | 0 |
| stop-condition-qa | 3 | 0 |
| approvable-ticket | 3 | 0 |
| model-boundary | 3 | 0 |
| insufficient-evidence | 3 | 2 |
| safety-escalation | 3 | 0 |
| false-completion | 3 | 0 |
| source-obligation | 3 | 0 |

失败码按题计数（同题可重复计入多个码）：`source_sections_mismatch` 15、
`required_fact_missing` 12、`outcome_mismatch` 8、`category_mismatch` 1、
`priority_mismatch` 1。

## 与原观测并列

- 原始正式观测继续是 19/24 执行、9 通过、31 调用、机制估算 ¥0.7096008，第 20 题前
  因响应信封完整性失败停止；不覆盖、不倒写。
- 本次是同一已消费集的 `2026-08-02` 修复后首次回归观测，不恢复“全新未见”属性。
- 两次候选、prompt 和执行覆盖均不同；24/24、2 通过不能与原数字直接作因果比较，也不能
  归因给 Issue #21 或任何单一改动。
- 本次显示候选仍有广泛来源、必需事实与 outcome 不匹配；安全 / 型号维度也没有全合同通过。
  允许结论仅限该固定身份的一次描述性观测；`product/0.1.0` 继续未发布。

## 本地交付检查

- Stage 12 定向测试：15 passed；新增测试冻结原 / 新两份聚合、候选身份、用量数字、报告
  SHA 与公开投影键边界。
- API 全集：通过，4 个既有环境跳过；Windows 测试服务器关闭时有 1 条非阻断线程告警。
- 治理正式口径：`python -m unittest discover -s tools/tests -p "test_*.py"` 为
  116 tests 通过 / 8 skipped。
- 公开仓扫描：251 files / 8 public cases，通过；文档园丁 stale 0 / review 1，唯一 review
  是既有迁移记录；`git diff --check` 通过。
- 私有明文 / 必需事实 / 凭据泄漏专项检查通过；公开聚合与 Git 外输出 SHA 精确一致。
- 候选 `df01968` 与当前回执工作树的 product / generation tree、runner blob 均一致；私有
  未见集 SHA 仍为 `7d730...8ab0`。

本地候选已绿；待提交推送并确认 Draft PR #62 最终 head required Checks。

## Draft PR 实现回执

结果候选 `989f2eba23c0b074f77178bfae3e8f050f9c978c` 已推送到既有 Draft PR #62；
`ci-release` run `30756898578` 的 governance、web、api、containers 四个 required jobs
全部成功，publish 因 Draft 跳过。PR 未转 Ready、未合并、未部署。

本状态回执提交将形成最终 head；最终 head required Checks 仍须另行确认。
