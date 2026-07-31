# 发布版本身份小切片（已完成）

## 产品价值

让面试官或维护者能从公开健康接口直接确认“线上实际运行的是哪次 Git 提交”，并让部署与回滚门自动发现版本错配。这补齐作品集的可验证交付证据，不扩展 RAG 或模型能力。

## 开工三问

- 做什么：构建时把完整 Git SHA 写入 API 镜像；`GET /api/v1/health` 返回 `release_sha`；候选部署、公开冒烟和可识别的新回滚锚点核对精确 SHA。
- 不做什么：不引入监控平台，不修改检索、生成、Provider、数据库或 Web 展示，不处理 pgvector、Issue #14 或依赖升级，不调用 Provider。
- 怎样算完成：用已知 40 位 SHA 构建的回放镜像原样返回该 SHA；API 与发布测试覆盖正确值和错配失败；相关 Fast / Candidate 检查通过；形成边界清楚的本地提交候选后停止。推送、合并和部署是后续独立动作。

## 风险与最便宜证伪

- 风险：生产服务器构建 live 镜像时漏传 SHA。证伪：公共仓库检查固定生产构建参数，部署健康门再比较清单 SHA。
- 风险：运行时配置伪造镜像身份。证伪：构建参数写入镜像内只读身份文件，生产 Compose 不接受该身份变量。
- 风险：第一次回滚锚点来自旧版本，没有 `release_sha`。证伪：只对没有身份标记的旧锚点保留一次兼容检查；新发布写入期望身份，之后候选和回滚都强校验。
- 风险：健康接口新增字段破坏 Web。证伪：保留原字段与取值，运行现有 Web/API 合同测试。

## 复用、投入与停止线

复用现有 `VCS_REF` 构建参数、release manifest `git_sha`、健康冒烟、回滚演练和公共仓库扫描器，不新增依赖或服务。投入限制为一个小切片；若需要监控系统、持久化迁移、Provider 调用或改变公开体验，立即停止并另行决定。

本切片完成后只允许形成以下结论：健康接口能报告并由流水线核对发布提交身份。它不证明高可用、SLA、RAG 质量或线上运行长期稳定。

## 本地候选证据

- 固定 `aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa` 构建回放镜像；镜像只读文件与 `/api/v1/health.release_sha` 完全一致，Docker health 为 `healthy`；未传 `VCS_REF` 的 `unknown` 构建被拒绝。
- `python -m pytest api/tests -q`：全量 API 通过，3 项环境型用例跳过；无 Provider 调用。
- `python -m unittest discover -s tools/tests -p "test_*.py"`：108 项通过，8 项 Linux 专属用例在 Windows 跳过；`bash -n` 对三份发布脚本通过。
- Web `lint`、`typecheck`、构建及 27 项行为测试通过。
- 工作树公共扫描仅被已有未跟踪 `clean/` npm 缓存阻断；该目录不属于候选。提交范围使用 Git index 扫描，并要求结果通过后才提交。
