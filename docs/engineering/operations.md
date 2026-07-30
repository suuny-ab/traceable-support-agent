# 运维说明

## 当前部署

- 公开地址：<https://47.84.34.86/>。
- 主机：一台阿里云新加坡 Ubuntu 实例。
- Caddy 占用 80/443 端口；Web/API 仅绑定 `127.0.0.1:3000/8000`。
- 当前生产真实 Provider live 已显式启用（`2026-07-29`）；凭据仅存服务器
  `/opt/traceable-support/provider.env`（0600），不进入 Git、流水线或镜像。
- 公开 Web 以健康状态为准开放新运行；实时不可用时失败关闭，并保留独立标记的已验证回放。
- 在唯一权威仓库的镜像摘要部署及其后一次生产部署都成功之前，现有版本继续作为回滚锚点。

## 目标交付链路

```text
GitHub main → CI → GHCR linux/amd64 images → release manifest
           → protected production environment → automatic deployment
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
3. 生成 `release-manifest.json`，绑定镜像摘要、API 合同哈希、知识/prompt/回放哈希和运行模式；CI 构建默认保持 `provider_enabled=false`，生产部署只有在显式 live 配置与凭据预检通过后才生成 `provider_enabled=true` 的 manifest v2。
4. 拉取两个不可变镜像并验证摘要，再通过一次性属主初始化器创建非 root 的唯一权威数据卷。
5. 在临时回环端口启动候选，检查四个路由、健康状态、精确 CORS，以及健康合同与 manifest 声明的 live / replay 模式一致。
6. 原子更新 `current`，重启回环生产容器对，再通过 Caddy 重复公开冒烟检查。
7. 任一环节失败时，恢复原符号链接和 root 环境文件，重新激活 `previous`，并报告失败检查门。

公开源站与首次迁移演练标志经过复核后固定在 `deploy/production-target.json`，不接受自由输入的调度参数。首次生产迁移执行受控的 `old → new → old → new` 演练。如果不存在经过验证的旧版回滚锚点，就会在激活唯一权威版本前失败，而不是假装已经测试回滚。版本切换在 `docker compose down` 后显式等待该项目的容器和网络清理完成，再启动目标版本；这是一道有界状态屏障，不是部署重试。每次本地健康通过后，Caddy 公网路径使用统一 15 秒 deadline 验证四个路由和健康合同；受控 `/usr/bin/curl --max-time`、Python 子进程 timeout 和成功返回后的绝对 deadline 复核共同限制总等待，只对 502 / 503 / 504、连接错误和超时等待就绪，4xx、证书错误和内容合同错误立即失败关闭。三个发布元数据路径使用补偿事务；普通写入失败会先恢复原状态，再重新激活旧容器。激活前读取 Caddy 回执证据；最终回执持久化本身也是检查门，失败时回滚至经过验证的旧版本。旧版本会一直保留到下一次成功的生产部署之后。

部署使用受限服务器用户与 GitHub production environment。服务器主机、用户和私钥作为 Actions secrets 保存；服务器匿名拉取公开 GHCR 镜像。

`main` 的 `ci-release` 全部成功后，GitHub 自动把该次运行的不可变发布清单送入生产环境并直接部署；PR、失败运行、非 `main` push 和其他仓库来源均不得进入该队列。自动路径把清单精确绑定到触发运行的 ID、Git SHA 和运行尝试号；手动恢复路径至少把清单绑定到用户选择的运行 ID，再验证清单自洽且提交属于 `main`。`production` environment 只接受受保护分支，不再要求逐次人工 reviewer；这是用户明确授予的常设 R2 自动部署授权。手动 `workflow_dispatch` 入口只作为有界恢复通道保留，并与自动路径共享清单、健康和回滚门。

每次 PR 和 `main` 运行都会先生成不可变 `release-decision`，绑定 schema、Git SHA、GitHub
run ID / attempt、影响分类、是否部署和规范化变化路径哈希。只有明确列入白名单的仓库治理
路径可以分类为 `governance_only`；未知路径、工作流、工具、Web、API、部署资产和公共事实
变化均按 `runtime` 处理。四个 required check 始终存在；未受影响任务返回明确成功。

生产工作流先在没有 `production` environment 的 preflight job 中验证 decision。若
`deploy_required=false`，后续 deploy job 被跳过，因此不读取 production secrets、不生成
镜像、不进入 environment、不连接服务器。若为 `true`，继续执行既有发布清单、SSH、健康、
回滚和正式回执门。手动恢复只兼容固定白名单中的、引入 decision 之前且已经验证成功的
`ci-release` main push；当前唯一兼容 run ID 为 `29999870811`。预检在进入 production
environment 前核验同仓来源、工作流、push / main / success 身份、唯一未过期 manifest
和完整 SHA / attempt 绑定。其他缺少 decision 的 run 一律失败关闭，自动入口也不例外。

受保护 `main` 会在检出待发布提交前，把统一 SSH 控制器和端口校验器暂存到 runner 私有临时目录，并在 secret 步骤之前按固定 SHA-256 重新验证两份文件。部署 step 顺序、默认 shell、job 环境和 secret step 环境都由公开扫描器精确约束，不能插入额外 step、覆盖 shell 或附加环境变量。控制器在任何网络连接前一次性读取 `DEPLOY_HOST`、`DEPLOY_USER`、`DEPLOY_PORT`、`DEPLOY_SSH_KEY` 和 `DEPLOY_KNOWN_HOSTS`：每项只允许移除一个开头的 UTF-8 BOM，多行内容统一为 LF；主机、受限用户和端口执行精确格式校验，私钥通过 `ssh-keygen -y` 验证为无口令可用密钥，`known_hosts` 同时验证文件语法和目标主机条目。标准端口只接受普通主机条目，非标准端口只接受 `[host]:port`；明文通配模式失败关闭，经过 `ssh-keygen -F` 匹配的哈希主机条目可以使用。任一失败只输出 `deploy_*_invalid` 稳定错误码，不回显原始 secret，也不会运行 SSH / SCP。

服务器端失败只允许通过白名单格式返回稳定阶段码；任意路径、命令原文、环境值和未分类 stdout/stderr 均不进入 Actions 日志。没有安全阶段码时只报告 `deploy_ssh_transport_failed:activate`。该边界用于区分首次引导、镜像、权限、候选健康和回滚失败，不把增强可观察性变成服务器信息泄漏。

`DEPLOY_PORT` 可省略并默认使用 `22`；提供时必须是 `1..65535` 的 ASCII 十进制整数。换行、空格、引号、非 ASCII 数字和越界值均以 `deploy_port_invalid` 失败关闭。所有三次传输动作只能由统一控制器使用参数数组执行，工作流不得直接展开 secret、写私钥文件或调用 SSH / SCP；子进程不会继承五项部署 secret 或 SSH agent，控制器创建的私有临时目录和 `0600` 文件在退出时删除。

生产并发锁永不取消已经开始的部署；GitHub 最多再保留一个待处理候选，更新的绿色版本可能替换尚未开始的旧待处理候选。运行名称固定显示来源 `ci-release` 运行 ID，便于把生产回执绑定到唯一发布。

## 数据保留

原始请求内容最多保留 30 天。清理会删除 SQLite 行，并对 WAL 执行 checkpoint/truncate；原始内容不做备份。长期可观察性只保留聚合计数和稳定错误类别。
