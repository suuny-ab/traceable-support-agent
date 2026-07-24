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
npm audit --audit-level=high --registry=https://registry.npmjs.org
npm run lint
npm run typecheck
npm test
```

## 必需检查

### 治理与公开安全

- 每个活动工作目录都只含规范化四文件并由 `docs/status.md` 链接；允许多个隔离结果并行，
  显式 `ready` 状态允许没有活动工作；
- 除仓库根目录外不存在嵌套 Git 仓库；
- 不存在 Windows 用户目录路径、密钥、凭据、Provider 原始内容、归档、数据库或私有 HOLDOUT；
- 已跟踪文件均不超过 5 MiB，初始例外清单为空；
- 公开主张与 `provider_enabled=false`、`replay_only`、`product/0.1.0 not released` 一致；
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
- 本增量健康检查报告 `replay_only`；
- 发布清单绑定 Git SHA、镜像摘要以及合同/内容哈希；
- 健康切换失败时恢复上一版本。

## 证据语义

单元测试通过只证明其明确声明的合同。回放证明经过验证的历史产品结果，不是新的 Provider 调用。离线 `live` target 测试证明装配和失败边界，不证明语言质量。只有用户实际体验结果后，才能记录用户验收。

## 正式独立复核

正式复核的门、调用时机、固定 SHA 回执和 finding 后针对性复核见
[`review.md`](review.md)。普通 R0/R1 UI 与缺陷修复不再强制独立复核；高影响边界仍失败关闭。
