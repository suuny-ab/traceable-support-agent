# 本地候选结果

- `GET /api/v1/health` 新增 `release_sha`；发布镜像只接受完整小写 Git SHA，本地 Compose 使用显式 `local`。
- 回放与 live Docker health 都比较只读身份文件；CI 以 `GITHUB_SHA` 核对回放镜像。
- 生产主机构建显式传入待发布 SHA；release env 记录经 manifest 验证的期望值，候选、公开冒烟和新回滚锚点均精确比较。
- 第一次上线前的旧锚点没有该字段，只保留一次原健康合同兼容；候选仍必须强校验。
- 本地证据见 `spec.md`。当前没有推送、合并、生产部署或 Provider 调用。
