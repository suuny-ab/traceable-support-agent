import Link from "next/link";
import { SiteFooter, SiteHeader } from "./components/SiteChrome";

const stages = [
  ["01", "Hybrid Retrieval", "型号约束下融合稀疏与语义候选。"],
  ["02", "Obligation Planning", "生成前先枚举必须覆盖的业务义务。"],
  ["03", "Generation", "模型只在批准来源范围内组织客户正文。"],
  ["04", "Mechanical Gates", "来源、结构或完整性失败立即转人工。"],
  ["05", "Human Decision", "客服主管批准、编辑或拒绝，不自动执行。"],
];

export default function Home() {
  return (
    <div className="site-frame">
      <SiteHeader />
      <main>
        <section className="hero shell">
          <div className="hero-copy">
            <p className="eyebrow"><span>01</span> Evidence-first LLM Workflow</p>
            <h1>
              让每个 LLM 结论都有<span className="outline-word">证据</span>，
              让每次失败<span className="lime-word">诚实停止</span>
            </h1>
            <p className="hero-lede">
              一个面向客服决策支持的可追溯 AI 工作流。它不追求“总能回答”，
              而是把检索证据、业务义务和机械质量门变成每次生成都能检查的合同。
            </p>
            <div className="hero-actions">
              <Link className="button button-primary" href="/app">进入在线体验 <span>↗</span></Link>
              <Link className="button button-secondary" href="/design">查看设计说明 <span>→</span></Link>
            </div>
            <div className="role-notes">
              <span>AI APPLICATION ENGINEERING</span>
              <span>RAG · EVALS · GUARDRAILS</span>
            </div>
          </div>

          <aside className="trace-console" aria-label="证据链运行预览">
            <div className="console-header">
              <div>
                <p>VERIFIED TRACE / QA PIPELINE</p>
                <h2>CZ-R1 怎么开始局部清扫？</h2>
              </div>
              <code>RUN DEMO-01<br />REPLAY READY</code>
            </div>
            <div className="console-body">
              <div className="source-stack">
                <div className="source-chip"><strong>KB-CZR1-014</strong><span>清扫模式</span></div>
                <div className="source-chip"><strong>SCOPE</strong><span>型号 CZ-R1</span></div>
                <div className="source-chip"><strong>POLICY</strong><span>人工最终决定</span></div>
              </div>
              <div className="trace-nodes">
                <div className="trace-node"><b>01</b><div><strong>Obligation Planning</strong><span>按键动作 · 清扫范围 · 停止条件</span></div></div>
                <div className="trace-node"><b>02</b><div><strong>Evidence-bound Generation</strong><span>3 obligations / 1 approved source</span></div></div>
                <div className="trace-node trace-gate"><b>03</b><div><strong>Mechanical Gates</strong><span className="pass-tag">EVIDENCE PASS</span><span className="pass-tag">SCOPE PASS</span></div></div>
              </div>
            </div>
            <div className="console-footer"><span>NO EXTERNAL ACTION EXECUTED</span><strong>READY FOR HUMAN DECISION →</strong></div>
          </aside>
        </section>

        <section className="metrics shell" aria-label="当前产品事实">
          <div><strong>QA + 工单</strong><span>双主链，共用证据合同</span></div>
          <div><strong>≤ 2</strong><span>次 Provider 调用上限</span></div>
          <div><strong>启用后 ≤ 30 DAYS</strong><span>原始内容留存上限</span></div>
          <div><strong>0 ACTION</strong><span>自动外部业务动作</span></div>
        </section>

        <section className="system-section shell">
          <div className="section-heading">
            <p>02 / SYSTEM CONTRACT</p>
            <h2>一条可以回读、<br />也允许失败的技术链</h2>
          </div>
          <div className="pipeline">
            {stages.map(([index, title, copy]) => (
              <article className="pipeline-stage" key={index}>
                <span>STEP {index}</span>
                <h3>{title}</h3>
                <p>{copy}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="proof-section shell">
          <div className="proof-copy">
            <p className="section-kicker">03 / ENGINEERING EVIDENCE</p>
            <h2>把失败过程也变成作品的一部分</h2>
            <p>项目没有隐藏失败候选。它用公开开发切片、独立未见评测和人工复核区分“结构正确”“事实完整”和“业务可用”。</p>
          </div>
          <div className="proof-grid">
            <article><span>FORMAL B1</span><strong>27 / 36</strong><p>护栏未达到冻结发布门，候选正式失败。</p></article>
            <article><span>TOP-10 V3</span><strong>11 / 15</strong><p>正文义务通过，机械结构6/6仍不能替代语义完整。</p></article>
            <article><span>STAGE 11</span><strong>2 PATHS</strong><p>真实LLM已进入本地QA与工单主链。</p></article>
          </div>
        </section>

        <section className="boundary-banner shell">
          <div><span>PUBLIC DELIVERY STATUS</span><strong>公开部署候选 · 实时能力独立开关</strong></div>
          <p>网站与API可独立保持在线。真实调用关闭、额度耗尽或状态未知时，预设回放继续可用；自由输入不会被伪装成模型生成。</p>
          <Link href="/app">查看诚实降级如何工作 →</Link>
        </section>
      </main>
      <SiteFooter />
    </div>
  );
}
