import type { Metadata } from "next";
import { SiteFooter, SiteHeader } from "../components/SiteChrome";

export const metadata: Metadata = { title: "隐私与运行边界" };

export default function PrivacyPage() {
  return <div className="site-frame"><SiteHeader /><main className="shell inner-page narrow-page">
    <header className="page-intro"><p className="eyebrow"><span>04</span> Privacy & Boundaries</p><h1>这是合成数据演示，<br />不是生产客服入口</h1><p>页面允许自由输入，是为了体验失败边界，而不是接收真实客户问题。</p></header>
    <section className="policy-list">
      <article><span>部署候选</span><h2>实时能力以页面检测结果为准</h2><p>预设案例始终可在浏览器中回放；只有页面明确显示“实时体验可用”时，运行按钮才会提交模型请求。未知状态不会被包装成可用。</p></article>
      <article><span>数据留存</span><h2>实时接口启用后，原始内容最多保留30天</h2><p>公开部署必须先验证定时清理硬门：实时运行包只为故障诊断和证据回读保留；到期从SQLite与WAL清理，不建立原文备份，不提供公开历史页，只长期保留聚合指标。</p></article>
      <article><span>输入限制</span><h2>请勿输入真实敏感信息</h2><p>不要提交姓名、电话、订单、公司机密、内部日志、真实客户问题或生产数据。自由输入最多500字。</p></article>
      <article><span>模型边界</span><h2>最多两次调用，零自动重试</h2><p>每次完整体验最多两次Provider请求。模型不能调用工具、写数据库、决定重试或执行客服动作。</p></article>
      <article><span>人工决定</span><h2>批准不等于已经发送</h2><p>批准、编辑和拒绝只记录审核意图；系统不会发送回复、关闭工单、改变账号或触发售后流程。</p></article>
    </section>
  </main><SiteFooter /></div>;
}
