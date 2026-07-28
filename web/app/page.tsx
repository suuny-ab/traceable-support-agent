import Link from "next/link";
import { SiteFooter, SiteHeader } from "./components/SiteChrome";

const outcomes = [
  ["每个事实可回读", "客户可见结论绑定批准来源，主管能回到原始证据。"],
  ["不确定就转人工", "证据不足、型号冲突或运行异常不会被包装成成功。"],
  ["决定权留给团队", "系统给出候选与检查结果，但不发送、不退款、不结单。"],
];

const stages = [
  ["01", "检索", "在型号边界内融合稀疏与语义候选。"],
  ["02", "规划", "生成前枚举本次必须覆盖的业务义务。"],
  ["03", "生成", "只用批准来源组织客户可见候选。"],
  ["04", "检查", "来源、结构或完整性失败立即停止。"],
  ["05", "决定", "主管批准、编辑或拒绝，不自动执行。"],
];

export default function Home() {
  return (
    <div className="site-frame">
      <SiteHeader />
      <main>
        <section className="hero shell">
          <div className="hero-copy">
            <p className="eyebrow"><span>公开 Beta</span> 可追溯客服决策支持</p>
            <h1>让客服 AI 的结论<br /><em>有证据，能退出。</em></h1>
            <p className="hero-lede">
              Traceable Support Agent 把检索证据、业务义务、质量门和人工决定放进一条可检查
              的工作流。团队得到的是可信候选，不是一个无法解释的答案框。
            </p>
            <div className="hero-actions">
              <Link className="button button-primary" href="/app">体验工作台 <span>→</span></Link>
              <Link className="button button-secondary" href="/design">查看工程证据</Link>
            </div>
            <ul className="trust-line" aria-label="核心边界">
              <li>只用合成数据</li>
              <li>失败关闭</li>
              <li>人工最终决定</li>
            </ul>
          </div>

          <aside className="decision-preview" aria-label="一次可追溯决定预览">
            <div className="preview-topline">
              <span className="status-pill status-success">证据检查通过</span>
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

        <section className="proof-section shell">
          <div className="proof-copy">
            <p className="section-kicker">当前公开能力</p>
            <h2>把边界讲清楚，<br />比把 Demo 说大更重要。</h2>
            <p>当前公网体验以已验证回放为主，Provider 关闭。唯一的例外是固定边界挑战：它在模型
              调用前由确定性规则转人工，Provider 调用为 0。真实模型主链已在本地固定场景验证，
              但不据此宣称生产级高可用、SLA 或 product/0.1.0 已发布。</p>
            <Link className="text-link" href="/privacy">查看完整运行边界 →</Link>
          </div>
          <div className="proof-grid">
            <article><span>产品路径</span><strong>QA + 工单</strong><p>两条主链共用证据合同、失败关闭和人工决定。</p></article>
            <article><span>当前公网</span><strong>Replay only</strong><p>回放与实时路径明确区分，不伪造模型生成。</p></article>
            <article><span>自动动作</span><strong>0</strong><p>批准只记录决定，不发送回复或改变业务系统。</p></article>
            <article><span>公开 API</span><strong>4</strong><p>运行、轮询、人工决定和健康接口保持稳定。</p></article>
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
