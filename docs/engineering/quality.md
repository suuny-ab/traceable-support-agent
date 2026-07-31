# 质量策略

## 分层

| 层级 | 用途 | 目标耗时 | 默认入口 |
| --- | --- | ---: | --- |
| Fast | 治理、公开边界与稳定 API 冒烟 | `<=10s` | 公开扫描、工具测试和无模型 API 子集 |
| Candidate | 使用固定本地模型的完整 API/产品测试 | `<=60s` | 显式指定模型根目录后运行 `python -m pytest api/tests` |
| Product | Web 构建、回放/离线 live 镜像和 Compose 冒烟 | `<=90s` | Web 测试、回放 Compose 和离线 `live` target 检查 |
| Audit | 公开发布、历史边界或正式候选 | 按需 | 密钥/路径/大文件扫描、全新克隆和部署检查 |

HOLDOUT、付费校准和旧审计默认均不进入 Fast/Product。

## 本地入口

从仓库根目录执行 PowerShell Fast 检查：

```powershell
python tools/check_public_repo.py --scope worktree
python -m unittest discover -s tools/tests -p "test_*.py"
$env:PYTHONPATH = "api/src"
python -m pytest api/tests/test_package_boundaries.py api/tests/test_public_api.py api/tests/test_provider_usage.py
```

Candidate API 检查需要经过字节验证的 BGE 模型。下载器应在干净环境中使用；也可以在本机指定已有且验证通过的模型根目录，但不得把模型复制进仓库：

```powershell
python deploy/download_embedding_model.py --manifest api/src/traceable_support/retrieval/bge-small-zh-v1.5-fastembed.json --root .local-model
$env:PYTHONPATH = "api/src"
$env:TRACEABLE_MODEL_ROOT = "$PWD/.local-model/artifacts/models/fastembed/fast-bge-small-zh-v1.5"
python -m pytest api/tests
```

`.local-model/` 已被忽略，绝不能提交。CI 安装完全锁定的测试/`live` 依赖，从白名单来源下载同一模型，校验每个文件的大小和哈希，再运行 Candidate 入口。`live` 镜像在禁用网络的条件下测试，不产生 Provider 调用。

Web 检查：

```powershell
Set-Location web
npm ci
npm run lint
npm run typecheck
npm test
```

依赖安全与产品功能检查分离：`ci-release` 只在依赖文件变化的候选上执行阻塞性审计——
`web/package.json` 或 `web/package-lock.json` 变化时执行 `npm audit --audit-level=high`；
`api/requirements-*.txt/.lock` 变化时执行钉定 `pip-audit==2.10.1 --disable-pip --no-deps`
对三份锁定清单（base、live、test）的审计。未改代码时出现的 advisory 漂移由定期审计发现。
定期审计由 `.github/workflows/dependency-audit.yml` 每周执行一次（schedule 触发只在
默认分支 `main` 上运行；分支与 PR 上只能 `workflow_dispatch` 手动触发），同时保留
本地入口：

```powershell
python tools/dependency_audit.py
```

该入口对 `web/` 执行 npm audit，并在本机装有 `pip-audit` 时以 `--disable-pip --no-deps`
对三份 API 锁定清单（base、live、test）直接审计固定版本（不让 pip 重新解析，哈希锁文件与平台标记依赖下
重解析会失败）；工具缺失的扫描标记为 skipped，不影响退出码。退出码语义按工具如实
区分：npm audit 非零表示 high 及以上 advisory；pip-audit 无严重度阈值，退出 1 表示
任意已知漏洞；任何非零也可能是扫描环境错误（registry、网络、工具），`fail(exit N)`
只表示“扫描未通过”，以扫描输出为准。定期审计发现漂移后，锁文件更新是独立的依赖
变更，不作为本检查的自动修复。

## CI 证明合同与失败归因

`ci-release` 的每个关键检查都通过 `tools/ci_proof.py` 绑定一条登记主张（claim）和一个
失败归因类别：

- `product`：产品合同步骤失败，默认归候选 diff，修复后重推；处理入口会标明例外
  （如基础镜像拉取属外部依赖）；
- `boundary`：治理、公开安全或依赖安全门停止——输出为内容或依赖问题时修正内容或
  回退；输出为扫描环境错误（registry、网络、工具）时按外部故障重试或等待；不得为
  通过而放松门；
- `external`：外部获取类步骤失败，先核对候选 diff 是否触及该步骤输入（依赖清单、
  模型清单），未触及则重试或等待外部恢复。

合同覆盖范围：`ci-release` 四个 job 内登记主张的检查步骤。checkout、setup actions、
artifact 上传、`publish` job 与 workflow 评估失败在合同外——workflow 评估失败由
GitHub 在 run 页面直接报告（见下方验证边界），`publish` 链由 release-decision 与
release-manifest 门约束。合同不声称覆盖这四类失败。

检查失败时：单命令步骤（`run`）在命令输出之前打印 `ci_check` 归因行，多行脚本步骤
（`record`）以稳定 echo 码定位失败点、在步骤末尾打印归因块；失败块包含主张、类别
归因、claim 边界与处理入口，失败摘要行同时显示边界与处理入口；两者都发出 `::error`
注解。每个 job 末尾（`if: always()`）把证明条目渲染进 GitHub Job Summary：通过只
证明表中明确声明的主张；`governance_only` 变更下运行时检查记录为“故意跳过”；依赖
未变化时依赖审计记录为“故意跳过”；因之前失败或条件错误而未运行的检查列为“未执行”
并使摘要步骤失败关闭——绿色 required Check 不能掩盖一次未执行的检查。绿色 Check
只有在表中对应主张为“通过”时才表示已证明。

依赖文件变化时的候选级阻塞审计分两侧：`web/` 依赖变化触发 npm audit；API 锁定清单
变化触发钉定 `pip-audit==2.10.1 --disable-pip --no-deps` 对三份锁文件的审计（pip
审计发现任意已知漏洞即红，不限 high）。测试通过 `contextlib.redirect_stderr` 隔离
`::error` workflow command，绿色 Check 不携带测试夹具产生的虚假失败注解。

验证边界（2026-07-26 由 Draft PR #32 首次运行暴露）：本地 YAML 解析和 `bash -n` 只能
证明 workflow 的语法有效，不能覆盖 GitHub 对 context 使用位置的语义限制——例如
`runner` context 不允许出现在 job 级 `env`（job env 在 runner 分配前求值），该类错误
只有在真实 runner 评估 workflow 时才显现，表现为 run 0 秒失败、不创建任何 job。proof
文件的路径因此只能在 run 块内以 shell 变量 `$RUNNER_TEMP` 引用，不得经 job 级 `env`
绑定 `runner` context。

## 必需检查

### 治理与公开安全

- 每个活动工作目录都只含规范化四文件并由 `docs/status.md` 链接；允许多个隔离结果并行，
  显式 `ready` 状态允许没有活动工作；
- 除仓库根目录外不存在嵌套 Git 仓库；
- 不存在 Windows 用户目录路径、密钥、凭据、Provider 原始内容、归档、数据库或私有 HOLDOUT；
- 已跟踪文件均不超过 5 MiB，初始例外清单为空；
- 公开主张区分本地默认 `replay_only` 与生产显式 `provider_enabled=true`；健康状态、部署
  manifest 和 `product/0.1.0 not released` 必须与各自环境的当前证据一致；
- 生产包不得导入 `evals`、`tools` 或已完成工作项。

### API

- 四个公开端点和稳定错误码；
- 在组装 Provider 之前完成敏感、越界和安全前置检查；
- 随机运行 ID、精确 CORS、16 KiB 请求体限制、队列/并发限制和原子预算预留；
- SQLite 决定持久化、30 天清理、WAL 清理和重启恢复；
- 回放模式不安装模型、`live` 依赖或凭据也能启动；
- CI 中的 `live` target 只使用离线 transport。

### Web

- lint、TypeScript、单元/协议测试和标准 Next 生产构建；
- `/`、`/design`、`/app`、`/privacy` 均能渲染；
- 加载/输入锁定、回放降级、来源/义务展示以及键盘/手机行为保持有效。

### 容器与部署

- 镜像以内置非 root 用户运行，并通过 Compose 只暴露绑定回环地址的应用端口；
- CI 构建候选默认健康检查报告 `replay_only`；生产部署按 manifest v2 的显式模式检查
  `available` 或 `replay_only`，不得把两者混写；
- 发布清单绑定 Git SHA、镜像摘要以及合同/内容哈希；
- 健康切换失败时恢复上一版本。

## 证据语义

单元测试通过只证明其明确声明的合同。回放证明经过验证的历史产品结果，不是新的 Provider 调用。离线 `live` target 测试证明装配和失败边界，不证明语言质量。只有用户实际体验结果后，才能记录用户验收。

## 正式独立复核

正式复核的门、调用时机、固定 SHA 回执和 finding 后针对性复核见
[`review.md`](review.md)。普通 R0/R1 UI 与缺陷修复不再强制独立复核；高影响边界仍失败关闭。
