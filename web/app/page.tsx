import Link from "next/link";
import { SiteFooter, SiteHeader } from "./components/SiteChrome";

const outcomes = [
  ["真实运行", "公网接入真实模型，同时保留明确标记的已验证回放。"],
  ["结论有据", "每条客户可见结论都绑定批准来源，可以回到原文。"],
  ["失败有出口", "证据不足或越界时停止生成，把最终决定交还给人。"],
];

const stages = [
  ["01", "检索", "在型号边界内融合稀疏与语义候选。"],
  ["02", "规划", "生成前枚举本次必须覆盖的业务义务。"],
  ["03", "生成", "只用批准来源组织客户可见候选。"],
  ["04", "检查", "来源、结构或完整性失败立即停止。"],
  ["05", "决定", "主管批准、编辑或拒绝，不自动执行。"],
];

const portfolioProofs = [
  ["AI 应用", "RAG + 受控生成", "检索、义务规划和生成分工清楚，每条客户可见结论绑定批准来源。"],
  ["工程交付", "API + SQLite + 容器", "异步运行、人工决定、持久化、预算门和发布身份形成完整闭环。"],
  ["质量边界", "评测 + 失败关闭", "公开评测可重复，证据不足、越界或状态未知都不会被包装成成功。"],
];

export default function Home() {
  return (
    <div className="site-frame">
      <SiteHeader />
      <main>
        <section className="hero shell">
          <div className="hero-copy">
            <p className="eyebrow"><span>AI 应用工程作品</span> RAG · Guardrails · Full-stack</p>
            <h1>客服 AI 不只回答，<br /><em>有证据，也会停手。</em></h1>
            <p className="hero-lede">
              真实模型负责生成，RAG 为结论绑定来源；证据不足或越界时立即停止，
              最终决定始终留给人工。
            </p>
            <div className="hero-actions">
              <Link className="button button-primary" href="/app">运行推荐案例 <span>→</span></Link>
              <Link className="hero-detail-link" href="/design">两分钟查看架构与评测 →</Link>
            </div>
            <ul className="trust-line" aria-label="核心工程证据">
              <li>真实模型运行</li>
              <li>来源可以回读</li>
              <li>失败时转人工</li>
            </ul>
          </div>

          <aside className="decision-preview" aria-label="一次可追溯决定预览">
            <div className="preview-topline">
              <span className="status-pill status-success">已验证结果</span>
              <code>RUN · VERIFIED REPLAY</code>
            </div>
            <div className="customer-question">
              <span>客户问题</span>
              <h2>CZ-R1 怎么开始局部清扫？</h2>
            </div>
            <div className="preview-answer">
              <span>建议回复</span>
              <p>请在主机停止状态下长按清扫键三秒，CZ-R1 会围绕当前位置清扫约两平方米后停止。如果需要提前结束，可再次短按清扫键暂停。</p>
            </div>
            <div className="preview-evidence">
              <div><span>批准来源</span><strong>KB-CZR1-014 · 清扫模式</strong></div>
              <div><span>义务覆盖</span><strong>3 / 3</strong></div>
              <div><span>外部动作</span><strong>0</strong></div>
            </div>
            <div className="preview-decision">
              <span>等待主管决定</span>
              <div><b>批准</b><b>编辑</b><b>拒绝</b></div>
            </div>
          </aside>
        </section>

        <section className="outcome-strip">
          <div className="shell outcome-grid">
            {outcomes.map(([title, copy], index) => (
              <article key={title}>
                <span>0{index + 1}</span>
                <div><h2>{title}</h2><p>{copy}</p></div>
              </article>
            ))}
          </div>
        </section>

        <section className="system-section shell">
          <div className="section-heading">
            <p>工作方式</p>
            <div><h2>从输入到人工决定，<br />每一步都有责任边界。</h2><p>模型负责组织候选；宿主负责证据、预算、状态和停止。</p></div>
          </div>
          <div className="pipeline">
            {stages.map(([index, title, copy]) => (
              <article className="pipeline-stage" key={index}>
                <span>{index}</span><h3>{title}</h3><p>{copy}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="portfolio-section shell">
          <div className="portfolio-heading">
            <p className="section-kicker">求职展示重点</p>
            <h2>这份作品证明的，<br />不只是会调用模型。</h2>
            <p>它覆盖了 AI 应用从检索、生成、控制面到部署验证的完整链路，同时诚实保留公开 Beta 的能力边界。</p>
            <div className="portfolio-links">
              <Link className="text-link" href="/design">查看架构与评测 →</Link>
              <Link className="text-link" href="/privacy">查看运行边界 →</Link>
            </div>
          </div>
          <div className="portfolio-proof-list">
            {portfolioProofs.map(([label, title, copy], index) => (
              <article key={label}>
                <span>{String(index + 1).padStart(2, "0")} · {label}</span>
                <strong>{title}</strong>
                <p>{copy}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="cta-panel shell">
          <div><span>从真实交互开始</span><h2>亲自查看一次候选如何形成、停止和等待决定。</h2></div>
          <Link className="button button-primary" href="/app">打开在线工作台 <span>→</span></Link>
        </section>
      </main>
      <SiteFooter />
    </div>
  );
}
