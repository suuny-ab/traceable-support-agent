# 结果路线

> 当前路线按用户可观察结果组织，不按代码量或历史阶段编号组织。

## 已完成

- [x] 合成知识、来源回查、QA/工单处理包和人工决定基础产品。
- [x] 真实 LLM 两阶段 QA 与工单本地主链固定场景体验。
- [x] 方向 B 四页作品集与阿里云 IP HTTPS 公开 Beta 基线。
- [x] 公共 API 的预算、并发、留存、CORS 和失败回放硬门。
- [x] 建立唯一、可公开、可持续开发的权威单仓。
- [x] 通过冷启动、全新克隆、行为等价和真实小增量验收。
- [x] 用 `GEN-DEV-IE-001` 证据不足回放完成一次治理内的真实产品小增量。
- [x] 用 GitHub Actions 构建并向 GHCR 发布不可变 Web / 回放 API 镜像。
- [x] 按镜像摘要完成生产切换和回滚演练，并启用绿色 `main` 的自动生产部署。
- [x] 用 Issue #12 完成 Stage 12 全新未见正式评测：19/24、9 通过、2 条边界缺陷登记为 Issue #21/#22，`0.1.0` 判断留待 Issue #14。
- [x] 用 Issue #21 建立 QA、工单与公网 API 共用的生成前确定性安全 / 型号边界，并通过固定候选复核、自动部署和用户验收。
- [x] 用 Issue #22 建立两阶段失败分类、宿主机械投影和 clause 级来源绑定，关闭正式复核发现的来源越界；原真实模型候选质量完成门未满足，v15 兼容性保持未知并停止开放域调优。
- [x] 用独立增量建立 CI 证明合同：每个 Check 绑定登记主张，绿灯区分已证明 / 故意跳过 / 未执行并失败关闭，红灯按产品 / 治理边界 / 外部依赖归因；依赖安全与产品功能分离（依赖变化时阻塞审计 + 周频定期审计）；经五轮独立复核、统一基线 `df81ccd` 自动部署；用户验收为 `user_confirmed_external` 外部回执（坐标与核验边界见归档记录，非 GitHub / 自动化证据）。
- [x] 用 Issue #28 完成公开作品集视觉、回放体验与生产验收：live 优先工作台、统一公开运行合同、首页预览绑定批准来源 `KB-CZR1-014`；PR #31 / #34 合并，部署绑定 `34079d7`，独立最终生产体验验收 `PASS`。原始范围中的公开真实 Provider 目标在 Issue #28 关闭时按求职取舍停止（此前从未启用），不作为该 Issue 的验收门通过；Issue 已于 2026-07-28 以 `not planned` 关闭。该历史结论后来由 2026-07-29 的独立授权 live 上线增量更新，工作记录归档于 `docs/work/completed/portfolio-live-experience/`。
- [x] 交付 `real-run-evidence` 真实运行证据持久化增量：transcript 合同接受 `authorized_real`（账单未知三态与 transport 观察一致）、控制面内部持久化 transport 观察、提交探针离线夹具；Draft PR #37 经两轮定向复核全绿后关闭、未直接合并，内容随 PR #38 合入 main；工作记录归档于 `docs/work/completed/real-run-evidence/`。
- [x] 完成真实 Provider live 上线（`2026-07-29`，用户显式授权）：生成门由逐字锚定改为绑定式溯源（ADR-0007，QA + 工单同构，真实 Provider 本地复测过门率 0/2 → 3/3）；部署链路解除刻意锁死（live 镜像健康断言 `available`、release manifest v2、开关显式 opt-in、凭据走服务器 0600 文件）；PR #38 / #40 合入 main 后由流水线自动部署 `766ba3f`（服务器侧构建镜像按摘要固定，回滚演练通过）；公网健康 `available`，首条真实 QA `completed`（live candidate，证据挂载，预算预留 ¥1）；replay 回放预览无退化。

## 当前

- [ ] [Issue #29：以面试官视角完成 GitHub 仓库展示改造](https://github.com/suuny-ab/traceable-support-agent/issues/29)
  已启动：先统一 live / replay 现行口径，再按 10 秒 / 2 分钟 / 10 分钟阅读路径组织产品结果、
  演示、架构、工程证据、限制和复现入口；不借展示改造新增产品能力。

## 下一步

- [ ] [Issue #14：评估并收口 `product/0.1.0`](https://github.com/suuny-ab/traceable-support-agent/issues/14)（继续后置）。

## 长期范围外

- 自动发送、退款、换新或结单。
- 真实客户数据和生产客服系统。
- 开放式 Agent、多 Agent或通用客服平台。
- 生产级多区高可用与 SLA。
