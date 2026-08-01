# 完成复核

## 已关闭疑问

- 首次 governance 失败只来自缺少活动交付记录；最小修复没有放松扫描器或改变产品代码，
  新 head 的四个 required checks 随后全部通过。
- 第一次 merge 请求使用了未核实的完整 head SHA，GitHub 的 expected-head 门以 409 正确拒绝；
  读取真实 SHA 后，候选保持不变并成功 squash merge。
- main CI 绑定合并 SHA 发布 manifest，生产部署从该绿色运行下载并验证 manifest，公网健康
  再次返回同一完整 SHA。
- 用户授权仅覆盖本次推送、合并和部署；全过程没有创建运行、调用 Provider 或产生模型费用。

## 证据边界

本次证据证明固定候选通过既有发布链并运行在公网，四个页面的新版文案和样式可达。它不证明
移动端真机体验、新的模型质量、长期稳定性、高可用或 SLA。Node 20 action 弃用提示是非阻断
告警，未在本增量中扩展为依赖升级。
