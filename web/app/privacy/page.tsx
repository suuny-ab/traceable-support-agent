import type { Metadata } from "next";
import { SiteFooter, SiteHeader } from "../components/SiteChrome";

export const metadata: Metadata = {
  title: "隐私与运行边界",
  description: "公开体验的数据、Provider、留存和外部动作边界。",
};

const boundaries = [
  ["数据", "只使用合成数据", "不要输入姓名、电话、订单、公司机密、内部日志或任何真实客户问题。自由输入上限为 500 字。"],
  ["Provider", "当前公网已启用实时能力", "只有页面明确显示实时可用时才会提交模型请求；不可用或未知状态失败关闭，预设回放保持独立且明确标记。"],
  ["留存", "实时原始内容最多保留 30 天", "原始内容只为故障诊断和证据回读保留；到期从 SQLite 与 WAL 清理，不建立原文备份。"],
  ["调用", "最多两次，零自动重试", "模型不能调用工具、决定重试或绕过预算。连接未知时不会自动重新提交，避免重复调用与费用。"],
  ["决定", "人工批准不等于已经发送", "批准、编辑和拒绝只记录审核意图；系统不会发送回复、关闭工单、退款、换新或改变账号。"],
];

export default function PrivacyPage() {
  return (
    <div className="site-frame">
      <SiteHeader />
      <main className="shell inner-page narrow-page">
        <header className="page-intro privacy-intro">
          <p className="eyebrow"><span>信任边界</span> Privacy & operations</p>
          <h1>你可以体验工作流，<br /><em>但这里不是客服入口。</em></h1>
          <p>这是一套面向作品集的合成数据公开 Beta。下面集中说明什么会发生、什么不会发生，
            以及系统在无法证明状态时如何停止。</p>
        </header>

        <section className="boundary-summary" aria-label="当前公开状态">
          <div><span>公开模式</span><strong>实时 + 已验证回放</strong></div>
          <div><span>Provider</span><strong>仅服务端启用</strong></div>
          <div><span>自动业务动作</span><strong>0</strong></div>
          <div><span>真实客户数据</span><strong>不允许</strong></div>
        </section>

        <section className="policy-list">
          {boundaries.map(([label, title, copy], index) => (
            <article key={label}>
              <span>{String(index + 1).padStart(2, "0")} · {label}</span>
              <h2>{title}</h2>
              <p>{copy}</p>
            </article>
          ))}
        </section>

        <aside className="privacy-callout">
          <div><span>失败关闭</span><h2>状态未知时，页面不会替系统猜答案。</h2></div>
          <p>连接中断只说明浏览器无法证明结果；它不等于“没有调用”，也不等于已经失败。
            页面保留原 run ID、停止自动重试，并明确提示人工接管。</p>
        </aside>
      </main>
      <SiteFooter />
    </div>
  );
}
