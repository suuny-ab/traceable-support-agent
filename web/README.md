# Web

方向 B 的求职作品集前端，使用标准 Next.js `standalone` 自托管输出。当前迁移只替换构建与部署边界，不进行最终视觉重设计。

页面：

- `/`：产品主页与工程证据；
- `/design`：架构、取舍和失败路线；
- `/app`：QA / 工单工作台、已验证回放与人工决定；
- `/privacy`：合成数据、留存和运行边界。

本地运行需要 Node.js `>=22.13.0`：

```bash
npm ci
npm run dev
```

提交前检查：

```bash
npm run lint
npm run typecheck
npm test
```

`NEXT_PUBLIC_API_BASE_URL` 是可选的同源或显式 API 地址。后端不可用或返回 `replay_only` 时，页面只运行明确选择的预设回放；自由输入不会被悄悄替换成预设答案。

回放资产固定在 `app/lib/replay-presets.json`：两个 QA 预设和一个工单预设。`GEN-DEV-IE-001` 展示无支持性来源时在检索阶段停止、Provider 调用为 0、转人工核实规格；它不声称继承的实时链已经实现同一拦截。

Docker 运行阶段只包含 `.next/standalone`、静态文件和 `public/`，使用非 root `node` 用户。生产 Compose 进一步启用只读根文件系统、`tmpfs /tmp`、移除 capabilities 和 `no-new-privileges`。

当前公开产品仍是合成数据、`replay_only` Beta；Stage 12、实时 Provider 和 `product/0.1.0` 均不在本次前端迁移中。
