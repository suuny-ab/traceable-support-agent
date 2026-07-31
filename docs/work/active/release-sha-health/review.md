# 候选复核

## 已关闭疑问

- 身份不能由生产 Compose 配置：SHA 位于镜像只读文件，Compose 不暴露覆盖变量。
- manifest 与期望值不能静默漂移：发布脚本在读取期望 SHA 时先比较 manifest `git_sha`。
- 健康新增字段保持兼容：原 `status`、`service`、`live_experience` 不变，Web 全量测试通过。
- 首次旧锚点无法强校验：兼容仅由旧 release env 缺少身份标记触发；新候选缺少标记会失败。

## 仍然不证明

本地候选没有证明生产已经运行该提交，也不证明高可用、SLA、RAG 质量或 Provider 稳定性。生产结论必须等待后续独立授权的推送、合并、自动部署和公网精确 SHA 回执。
