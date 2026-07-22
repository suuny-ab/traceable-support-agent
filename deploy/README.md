# 部署说明

唯一权威仓库版本由两个公开 `linux/amd64` 镜像组成，并按摘要固定：

- `ghcr.io/suuny-ab/traceable-support-agent-web`
- `ghcr.io/suuny-ab/traceable-support-agent-api-replay`

生产环境有意保持 `replay_only`。`live` API target 会使用离线 transport 构建和测试，但本增量既不发布也不部署它。

## 本地回放

```bash
docker compose -f deploy/compose.local.yaml up --build
```

Web 和 API 仅绑定 `127.0.0.1:3000/8000`。API 使用独立的 `traceable-support-local-data` 数据卷，既不包含嵌入模型，也不包含 Provider 凭据。一次性、禁用网络的初始化器会把该本地数据卷的属主设置为非 root API 用户；API 进程本身绝不以 root 运行。

如果这些端口已被占用，请在执行 `docker compose up` 前设置 `TRACEABLE_LOCAL_WEB_PORT` 和 `TRACEABLE_LOCAL_API_PORT`；容器内部端口和生产合同保持不变。

## 主分支发布

CI Workflow 运行四个必需 job：`governance`、`web`、`api` 和 `containers`。Pull Request 只运行测试。推送到 `main` 且全部通过后，流水线发布 Web 与回放 API 镜像、生成 `release-manifest.json`，并将清单保存为该次运行的 artifact。流水线绝不发布 `latest` 或 `live` 镜像。

生产调度只接受该次成功发布的运行 ID。经过复核的目标和强制首次迁移演练固定在 `deploy/production-target.json`，不作为自由输入的调度参数。因此，未来域名变化必须先经过正常仓库变更与复核，才能改变 CORS 或公开冒烟目标。

首批 GHCR package 必须先在 GitHub package 界面中改为 Public，再从未登录客户端匿名拉取验证；完成这一步之前不得切换服务器。不要向服务器添加 registry PAT。

## 首次唯一权威版本迁移

当前服务器运行的是从源码构建的旧版本，尚未按镜像摘要发布，因此首次迁移有独立的引导检查门：

1. 确认现有公开健康状态为 `replay_only`、Provider 开关为 false、凭据不存在、磁盘空间充足，并且 Caddy/IP TLS 健康。
2. 在服务器上，将已经复核的 `production-target.json` 与 `capture_legacy_release.py` 放在一起并运行。该脚本只记录镜像 ID、安全哈希和现有数据卷名称，添加专用回滚别名，并创建不依赖源码的旧版 Compose release；它绝不导出 SQLite 或环境变量值。
3. 移动或删除任何源码树之前，确认旧版回滚 release 可以重现当前运行容器。
4. 调度 `deploy-production.yml`。它安装唯一权威版本，在随机回环端口预检两个镜像，执行可恢复的“旧版本 → 唯一权威版本 → 旧版本 → 唯一权威版本”演练；任一检查门失败后，最终停留在旧版本。

首次激活唯一权威版本前，必须已有旧版锚点。发布元数据（`previous`、`server.env`、`current`）使用补偿机制提交：三个替换步骤中的任何普通失败都会恢复原字节和指针，再由 shell 编排器恢复原容器。激活前读取主机 Caddy 证据。最终部署回执也是发布检查门：如果无法持久化回执，编排器会回滚到旧版本并重复公开冒烟，而不是留下未记录版本。

这台 2 GiB 主机使用可恢复的原地切换，存在短暂重启窗口。这不属于零停机或高可用。`current` 符号链接记录最近一次健康版本，并不是流量路由器。

## 主机边界

Caddy 继续作为主机服务占用 80/443 端口。首次迁移不会替换其证书、IP `default_sni` 修复或证书 guard。每个版本都提供 `current/deploy/compose.yaml`，同时原子同步 `/opt/traceable-support/server.env` 以兼容 guard。应用端口继续只绑定回环地址。

唯一权威版本使用独立的 `traceable-support-data-canonical` 数据卷。切换前，一个禁用网络的一次性容器只修复该唯一权威数据卷对 UID/GID 10001 的属主；该步骤绝不挂载旧数据卷。

旧数据卷、镜像和版本在本次迁移后的下一次成功生产部署之前保持不动。该 Workflow 中绝不使用 `docker compose down -v` 或任何 prune 命令。

## 密钥与输入

部署 Workflow 只使用 GitHub production environment：

- `DEPLOY_HOST`
- `DEPLOY_USER`
- `DEPLOY_SSH_KEY`
- `DEPLOY_KNOWN_HOSTS`
- 可选的 `DEPLOY_PORT`

SSH 私钥只存在于 Actions runner 临时目录。必须执行 known-host 验证。发布清单、镜像引用和已跟踪生产目标不含密钥。Provider 密钥不属于该流水线，并且本增量禁止使用。
