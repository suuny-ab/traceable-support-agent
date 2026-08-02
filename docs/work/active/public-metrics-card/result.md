# 结果

## 当前候选

- 新增 `docs/product/metrics-card.md`，用 8 张卡覆盖语料 / 检索开发集、Stage 12、绑定式
  生成门、公开检索 HOLDOUT、内存 / pgvector、公开运行 / 回放、公共控制面和 README CI
  固定快照。
- 每张卡均登记数字、定义、测量方法、数据集 / 对象、单次 / 可复跑属性、仓库证据和
  “不是什么”；证据表增加统一入口。
- 明确排除日期、版本、SHA、端口、Issue / PR 编号和阅读导航标签，避免把身份或说明文字
  冒充产品指标。

## 只读一致性检查

- 8 张卡结构完整，22 个仓库相对证据链接全部存在。
- baseline / candidate、Stage 12、HOLDOUT、pgvector 四组 JSON 数字与卡片一致。
- 公共控制面的预算、队列、浏览器、输入与留存常量和卡片一致；ADR 0/2→3/3、回放 2 QA
  + 1 工单及 README 固定 CI 快照均已核对。
- 检查只读取既有事实，正式评测 0 次、Provider / generation / 产品运行调用均为 0。

## 本地治理

- 治理工具：114 tests 通过 / 8 skipped。
- 公开仓扫描：246 files / 8 public cases，通过。
- 文档园丁：stale 0 / review 1；唯一 review 是既有迁移记录中的历史相对措辞。
- `git diff --check` 通过；差异全部位于 `docs/`，没有产品代码、评测资产、Workflow 或依赖
  变化。

待形成 Draft PR 回执。本任务没有修改 Provider、生产或公开页面。
