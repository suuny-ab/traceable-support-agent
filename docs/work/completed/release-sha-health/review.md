# 完成复核

## 已关闭疑问

- 身份不能由生产 Compose 配置：SHA 位于镜像只读文件，Compose 不暴露覆盖变量。
- manifest 与期望值不能静默漂移：发布脚本在读取期望 SHA 时先比较 manifest `git_sha`。
- 健康新增字段保持兼容：原 `status`、`service`、`live_experience` 不变，Web 全量测试通过。
- 首次旧锚点无法强校验：兼容仅由旧 release env 缺少身份标记触发；新候选缺少标记会失败。

## 仍然不证明

生产回执证明公网进程报告并由发布门核对了合并提交身份，也证明本次单机回滚演练通过；
它不证明代码正确、高可用、SLA、RAG 质量或 Provider 长期稳定性。
