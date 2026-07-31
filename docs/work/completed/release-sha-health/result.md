# 交付结果

- `GET /api/v1/health` 新增 `release_sha`；发布镜像只接受完整小写 Git SHA，本地 Compose 使用显式 `local`。
- 回放与 live Docker health 都比较只读身份文件；CI 以 `GITHUB_SHA` 核对回放镜像。
- 生产主机构建显式传入待发布 SHA；release env 记录经 manifest 验证的期望值，候选、公开冒烟和新回滚锚点均精确比较。
- 第一次上线前的旧锚点没有该字段，只保留一次原健康合同兼容；候选仍必须强校验。
- 本地证据见 `spec.md`。PR #50 的四个 required checks 全绿后 squash 合并为
  `66af626ba4debf4c8a1cf91da023754168c5b908`；main CI `30629303699` 与生产部署
  `30629464871` 成功，受控回滚演练通过。
- 公网 `/api/v1/health` 返回 `release_sha=66af626ba4debf4c8a1cf91da023754168c5b908`
  和 `live_experience=available`，与合并提交精确一致；`/`、`/design`、`/app`、
  `/privacy` 均返回 `200`。交付过程没有创建产品运行或调用 Provider。
