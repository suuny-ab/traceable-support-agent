# API

`traceable_support` 是公开 HTTP 控制面与产品运行链的 Python 包。五个公共路由定义在
[`contracts/public-api-v1.json`](contracts/public-api-v1.json)；本地默认以 `replay_only`
启动，生产是否为 live 以部署配置与 `/api/v1/health` 为准。

`GET /api/v1/observability` 返回进程当前 SQLite 生命周期内的请求总量、平均 / 最大延迟、
错误率和 `client_error` / `server_error` / `transport_error` 聚合。记录只使用规范化路由 ID，
不保存原始路径、查询串、请求体、Cookie、IP 或异常文本；观测写入失败只产生脱敏 warning，
不会改变原请求响应。观测端点自身不计数，连续读取不会污染被观察值。

本地检查：

```bash
python -m pip install -e "api[live,test]"
python -m pytest api/tests
```

容器目标：

- `replay` 复制控制面源码和产品类型，只安装 `requirements-base.lock` 锁定清单
  （FastAPI + uvicorn 闭包），不安装检索或 Provider 依赖；
- `live` 安装固定依赖并校验下载本地 BGE 模型，但仍以
  `TRACEABLE_PUBLIC_LIVE_ENABLED=false` 启动。本轮不发布该目标。

即使存在 `DEEPSEEK_API_KEY`，密钥本身也不能启用实时体验。只有完整装配且显式声明就绪的
`ProductRunner` 才可能让控制面进入 `available`；真实 Provider 仍需独立授权、预算和发布门。

实时装配由 `api/live_assembly.py` 承担：`TRACEABLE_PUBLIC_LIVE_ENABLED=true` 时构建
`DefaultProductRunner`，但只有固定嵌入模型清单校验通过、六份合成语料齐备、检索依赖可导入
且凭据占位存在（只检查变量存在性，不读取值）时 `is_ready` 才为真；任一缺失时健康状态继续
`replay_only`。生成前确定性边界（安全、型号范围、`unsupported_claim` 证据不足）在
Provider 调用前失败关闭，`GEN-DEV-IE-001` 对应 `unsupported_claim` 且调用数为 0。

本地端到端验收可用 `tools/local_live_workbench.py`：它用检索派生的离线注入 transport
启动同一控制面，不调用 Provider、不读取凭据，只用于本机验证 live 工作台主路径。
