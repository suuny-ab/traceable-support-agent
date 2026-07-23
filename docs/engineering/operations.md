# 运维说明

## 当前部署

- 公开地址：<https://47.84.34.86/>。
- 主机：一台阿里云新加坡 Ubuntu 实例。
- Caddy 占用 80/443 端口；Web/API 仅绑定 `127.0.0.1:3000/8000`。
- 当前公开模式为 `replay_only`；未配置 DeepSeek 凭据。
- 在唯一权威仓库的镜像摘要部署及其后一次生产部署都成功之前，现有版本继续作为回滚锚点。

## 目标交付链路

```text
GitHub main → CI → GHCR linux/amd64 images → release manifest
           → automatic production queue → GitHub environment approval
                                        → health → atomic current switch
                                                 ↘ failure: restore previous
```

镜像：

- `ghcr.io/suuny-ab/traceable-support-agent-web`
- `ghcr.io/suuny-ab/traceable-support-agent-api-replay`

生产 Compose 固定不可变的镜像摘要，绝不使用会移动的 tag。服务器将每个版本及其清单保存在 `/opt/traceable-support/releases/<git_sha>/`，并维护 `current`/`previous` 符号链接。

首个唯一权威仓库版本采用可恢复的原地切换，不宣称零停机：单台主机上的 Caddy 始终占用 80/443 端口，回环 Web/API 对会短暂重启。切换前，迁移会把正在运行的旧镜像 ID 固定为服务器本地私有 tag；即使原始构建上下文消失，旧版本仍可执行。唯一权威 API 使用独立命名数据卷；部署绝不运行 `down -v`、镜像清理或旧数据卷清理。

## 部署合同

1. CI 与公开安全扫描全部通过。
2. 基于同一个 Git SHA 构建并发布两个镜像。
3. 生成 `release-manifest.json`，绑定镜像摘要、API 合同哈希、知识/prompt/回放哈希和 `provider_enabled=false`。
4. 拉取两个不可变镜像并验证摘要，再通过一次性属主初始化器创建非 root 的唯一权威数据卷。
5. 在临时回环端口启动候选，检查四个路由、健康状态、精确 CORS 和 Provider 关闭行为。
6. 原子更新 `current`，重启回环生产容器对，再通过 Caddy 重复公开冒烟检查。
7. 任一环节失败时，恢复原符号链接和 root 环境文件，重新激活 `previous`，并报告失败检查门。

公开源站与首次迁移演练标志经过复核后固定在 `deploy/production-target.json`，不接受自由输入的调度参数。首次生产迁移执行受控的 `old → new → old → new` 演练。如果不存在经过验证的旧版回滚锚点，就会在激活唯一权威版本前失败，而不是假装已经测试回滚。三个发布元数据路径使用补偿事务；普通写入失败会先恢复原状态，再重新激活旧容器。激活前读取 Caddy 回执证据；最终回执持久化本身也是检查门，失败时回滚至经过验证的旧版本。旧版本会一直保留到下一次成功的生产部署之后。

部署使用受限服务器用户与 GitHub production environment。服务器主机、用户和私钥作为 Actions secrets 保存；服务器匿名拉取公开 GHCR 镜像。

`main` 的 `ci-release` 全部成功后，GitHub 自动把该次运行的不可变发布清单送入生产队列；PR、失败运行、非 `main` push 和其他仓库来源均不得进入该队列。自动路径把清单精确绑定到触发运行的 ID、Git SHA 和运行尝试号；手动恢复路径至少把清单绑定到用户选择的运行 ID。`production` environment 必须在任何自动队列生效前配置人工审批，部署在用户点击 `Approve and deploy` 前不会读取生产 secrets 或连接服务器。手动 `workflow_dispatch` 入口只作为有界恢复通道保留，仍必须经过同一个 environment 审批门。

生产并发锁永不取消已经开始或正在等待批准的部署；GitHub 最多再保留一个待处理候选，更新的绿色版本可能替换尚未开始的旧待处理候选。审批页的运行名称固定显示来源 `ci-release` 运行 ID，用户应只批准预期版本。

## 数据保留

原始请求内容最多保留 30 天。清理会删除 SQLite 行，并对 WAL 执行 checkpoint/truncate；原始内容不做备份。长期可观察性只保留聚合计数和稳定错误类别。
