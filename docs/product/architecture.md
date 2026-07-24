# 产品架构

## 背景

本产品把合成客服问题或工单转化为有证据约束、可供人工审核的结果。离线评测衡量检索与生成质量；运行时机械门检查可观察的证据、安全、权限、结构和技术故障，但不假装能够证明任意问题的完整召回。

```text
Next.js Web
    ↓ same-origin /api/v1
Python HTTP boundary
    ↓
Run service / SQLite / budget / queue
    ↓
ProductRunner
    ├─ Boundary: deterministic safety / model-scope handoff
    ├─ Retrieval: model filter + BM25/BGE/RRF
    ├─ Generation: checklist → customer-visible candidate
    ├─ Provider: DeepSeek transport + usage/budget
    └─ Validation: source, LLM-declared visible span, obligation, schema and handoff gates
```

## 模块

- `traceable_support.api`：负责 HTTP、CORS、请求限制、运行生命周期、持久化和公开结果投影。
- `traceable_support.product`：负责生成前业务边界、QA/工单编排与分类。
- `traceable_support.retrieval`：负责合成语料、混合检索和模型清单。
- `traceable_support.generation`：负责义务清单、QA/工单合同，以及对 LLM 声明的客户
  可见语义跨度执行来源、存在性、义务集合和结构硬门。
- `traceable_support.provider`：负责传输合同、DeepSeek 适配、用量与原子预算。
- `evals`：承载公开回归和未来评测适配器；它依赖产品层，产品层不得反向依赖它。

## 公开状态

一次运行依次经过 `queued → preflight → retrieving → planning → generating → validating → completed|handoff`。Provider 关闭时，合法输入返回 `503 live_experience_unavailable`，Web 则提供明确标注的独立回放。敏感输入、声明的安全事件或型号独占能力冲突触发前置转人工时，不构造 transport、不调用 Provider，并以稳定原因码确定性完成。

## 部署

Web 与回放 API 使用两个独立的非 root 镜像。Caddy 终止 HTTPS 并代理同源请求。SQLite 是单节点持久化层；本项目不宣称多节点一致性或生产级高可用。
