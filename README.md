# Traceable Support Agent

一个面向 AI 应用工程师岗位的可追溯客服决策支持项目。系统使用合成知识与合成工单，展示混合检索、两阶段生成、证据绑定、机械质量门、失败关闭与人工最终决定怎样组合成可审查的 LLM Workflow。

当前公开体验：<https://47.84.34.86/>

> 当前版本是公开 Beta 回放版，健康状态为 `replay_only`。真实 LLM 已在本地 QA 与工单主链中完成有界验证，但尚未执行 Stage 12 全新未见评测，`product/0.1.0` 尚未发布。

## 产品边界

- QA 与工单双入口；结果包含来源、义务清单、候选正文、质量门和人工决定。
- 证据不足、安全风险、越界或技术失败时转人工，不包装为成功。
- 批准只表示“等待外部动作”；系统不会发送回复、退款、换新或结单。
- 只使用虚构品牌和合成数据，不接入真实客服、订单或客户信息。
- 当前公网 Provider 关闭，页面在服务不可用时仍可展示已验证回放。

## 架构

```text
Browser → Next.js portfolio → Python public API → SQLite
                                      ├─ hybrid retrieval
                                      ├─ two-stage generation
                                      ├─ mechanical validation
                                      └─ human decision
```

运行依赖方向固定为：

```text
HTTP API → Product → Retrieval / Generation / Provider
Evals → Product
```

产品运行包不得反向依赖评测、脚本或历史实验代码。

## 本地运行

回放版容器：

```bash
docker compose -f deploy/compose.yaml up --build
```

开发模式：

```bash
python -m traceable_support.api.http
cd web && npm ci && npm run dev
```

默认地址：Web <http://127.0.0.1:3000/>，API <http://127.0.0.1:8000/api/v1/health>。

## 仓库导航

| 路径 | 职责 |
| --- | --- |
| `web/` | 产品主页、设计说明、在线体验和隐私页 |
| `api/` | 公共 API、产品运行链、检索、生成和 Provider 边界 |
| `evals/` | 公开回归案例、合同和离线评测入口 |
| `data/knowledge/` | 六份合成知识资料 |
| `docs/product/` | 架构、设计、隐私、限制和公开主张证据 |
| `docs/engineering/` | 开发、质量、评测、运维和安全协议 |
| `docs/meta/` | 元开发原则、演进记录和精选案例 |
| `deploy/` | 容器、Caddy、发布清单和回滚部署 |

当前事实以 `PROJECT.md` 为准，唯一开发状态以 `docs/status.md` 为准，结果路线以 `ROADMAP.md` 为准。

## 许可

本仓库未授予开源许可证。源码公开供查看和求职评审，版权保留；未经许可不得复制、分发或用于衍生项目。

