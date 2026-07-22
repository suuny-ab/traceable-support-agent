# API

`traceable_support` 是公开 HTTP 控制面与产品运行链的 Python 包。四个公共路由定义在
[`contracts/public-api-v1.json`](contracts/public-api-v1.json)；服务默认且当前始终为
`replay_only`。

本地检查：

```bash
python -m pip install -e "api[live,test]"
python -m pytest api/tests
```

容器目标：

- `replay` 只复制标准库控制面和产品类型，不安装检索或 Provider 依赖；
- `live` 安装固定依赖并校验下载本地 BGE 模型，但仍以
  `TRACEABLE_PUBLIC_LIVE_ENABLED=false` 启动。本轮不发布该目标。

即使存在 `DEEPSEEK_API_KEY`，密钥本身也不能启用实时体验。只有完整装配且显式声明就绪的
`ProductRunner` 才可能让控制面进入 `available`；真实 Provider 仍需独立授权、预算和发布门。
