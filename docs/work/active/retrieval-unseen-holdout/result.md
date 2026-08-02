# 结果

## 冻结资产

- `evals/retrieval-holdout-v1.json` 含 10 题（CZ-R1 / CZ-R2 各 5）和 16 个独立评测知识单元。
- 前置冻结提交为 `6e57c5e229af01f4949df9c99d6ec6bdf03af74a`；题集 SHA-256 为
  `7e3163b26062615440a49825d2d10d0409890d026fc82b8387b7a6f4c247afb6`。
- 与 16 题开发集相比，问题规范化全文、来源引用、知识单元规范化全文的重复数均为 0；全部
  16 个新知识单元被人工标签覆盖，且标签与型号一致。

## 唯一一次首次观测

| 检索器 | Top-5 全标签覆盖 | Top-10 全标签覆盖 | Top-10 错误型号来源 |
| --- | ---: | ---: | ---: |
| BM25 | 10/10 | 10/10 | 0 |
| Local BGE | 10/10 | 10/10 | 0 |
| BM25 + BGE + RRF | 10/10 | 10/10 | 0 |

完整逐题名次和 Top-10 已写入 `evals/retrieval-holdout-observation-v1.json`。首次命令因隔离
worktree 没有默认相对模型缓存，在构建检索器前失败且没有产生排名或文件；随后只读核验主仓
既有 7 个模型文件的大小与 SHA-256，显式指向同一固定缓存后完成第一次实际排名。没有下载、
替换模型或重试排名。

## 结论边界

该结果只证明这 10 个公开合成问题在独立评测知识上的来源覆盖与型号过滤观察值；不证明回答
正确率、生成质量、线上成功率、真实用户泛化或发布成熟度。揭示后本版本只作回归记录，禁止
针对结果修改检索、问题、标签或知识。

## 本地验证

- API 全集：149 passed / 4 skipped / 24 subtests；新增测试只核对冻结结构和观察回执，没有
  重跑 HOLDOUT 排名。
- 治理工具：114 passed / 8 skipped；公开仓扫描 241 files / 8 public cases 通过。
- 文档园丁：stale 0 / review 1；唯一 review 是既有迁移记录中的历史相对措辞。
- `git diff --check` 通过；冻结提交后 `api/src`、生产知识、题集与排名工具均为零差异。

## Draft PR 回执

观察实现 head `a21afb20bd7bd7e6a4c777dc96ffd478e31fc3b0` 已推送到既有 Draft PR
[#62](https://github.com/suuny-ab/traceable-support-agent/pull/62)。`ci-release` run
`30752922314` 成功，governance、web、api、containers 全绿；publish 因 Draft 状态跳过，
没有合并或部署。状态回执提交会形成新的最终 head，只要求确认其 required Checks 启动，
不转 Ready、不合并、不部署。
