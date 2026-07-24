# 结果路线

> 当前路线按用户可观察结果组织，不按代码量或历史阶段编号组织。

## 已完成

- [x] 合成知识、来源回查、QA/工单处理包和人工决定基础产品。
- [x] 真实 LLM 两阶段 QA 与工单本地主链固定场景体验。
- [x] 方向 B 四页作品集与阿里云 IP HTTPS 回放版。
- [x] 公共 API 的预算、并发、留存、CORS 和失败回放硬门。
- [x] 建立唯一、可公开、可持续开发的权威单仓。
- [x] 通过冷启动、全新克隆、行为等价和真实小增量验收。
- [x] 用 `GEN-DEV-IE-001` 证据不足回放完成一次治理内的真实产品小增量。
- [x] 用 GitHub Actions 构建并向 GHCR 发布不可变 Web / 回放 API 镜像。
- [x] 按镜像摘要完成生产切换和回滚演练，并启用绿色 `main` 的自动生产部署。
- [x] 用 Issue #7 精简元开发治理，并通过商业 SaaS 四页重设计、冻结候选复核、自动部署和用户验收。
- [x] 用 Issue #12 完成 Stage 12 全新未见正式评测：19/24、9 通过、2 条边界缺陷登记为 Issue #21/#22，`0.1.0` 判断留待 Issue #14。
- [x] 用 Issue #21 建立 QA、工单与公网 API 共用的生成前确定性安全 / 型号边界，并通过固定候选复核、自动部署和用户验收。

## 当前

- [ ] [Issue #22：修复两阶段生成合同在真实模型下的高失败率](https://github.com/suuny-ab/traceable-support-agent/issues/22)。
  已形成失败分类、宿主机械投影和 LLM 客户可见语义跨度候选；v4 进一步让 LLM 直接
  判断义务与 clause 的语义对应，移除脆弱的 `key_elements` 复制合同。有界 QA/工单
  外部单例、Draft PR 最终 Checks 与正式复核待完成，不形成成功率或发布主张。

## 下一步

- [ ] [评估外部 API 语义分类器与确定性硬门的混合边界](https://github.com/suuny-ab/traceable-support-agent/issues/25)。
- [ ] [在费用授权和全部硬门通过后评估开启实时 Provider](https://github.com/suuny-ab/traceable-support-agent/issues/13)。
- [ ] [依据质量门发布 `product/0.1.0`](https://github.com/suuny-ab/traceable-support-agent/issues/14)。
- [ ] [独立域名作为非阻塞增强](https://github.com/suuny-ab/traceable-support-agent/issues/15)。

## 长期范围外

- 自动发送、退款、换新或结单。
- 真实客户数据和生产客服系统。
- 开放式 Agent、多 Agent或通用客服平台。
- 生产级多区高可用与 SLA。
