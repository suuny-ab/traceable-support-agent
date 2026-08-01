import type { Metadata } from "next";
import { SiteFooter, SiteHeader } from "../components/SiteChrome";
import retrievalCheckup from "../lib/retrieval-checkup-v1.json";

export const metadata: Metadata = {
  title: "设计与工程证据",
  description: "可追溯客服 LLM 工作流的架构、失败关闭与工程证据。",
};

const principles = [
  ["宿主拥有停止权", "检索、预算、来源校验、持久化和重试都由确定性宿主控制，模型没有工具权。"],
  ["先规划，再生成", "先枚举必须覆盖的业务义务，再生成客户正文，让遗漏在交付前暴露。"],
  ["结构不冒充语义", "来源绑定通过只证明结构；事实完整仍需语义检查和人工判断。"],
  ["失败是正式结果", "证据不足、型号冲突或运行异常都转人工，不包装成成功回答。"],
];

const flow = [
  ["输入预检", "合成 QA 或工单", "先检查长度、敏感内容、型号和安全边界。"],
  ["混合检索", "型号感知的证据候选", "BM25、BGE 与 RRF 由宿主运行，模型不自行搜索。"],
  ["义务规划", "先说明必须回答什么", "第一轮模型只规划义务及证据，不写最终回复。"],
  ["证据生成", "形成客户可见候选", "第二轮只在批准来源与义务范围内组织正文。"],
  ["机械门", "通过或明确停止", "来源、结构和完整性失败就 handoff；通过也只等待人工决定。"],
];

const retrievalCases = new Map(
  retrievalCheckup.cases.map((item) => [item.case_id, item]),
);

const retrievalLabels = new Map(
  retrievalCheckup.retrievers.map((item) => [item.retriever_id, item.label]),
);

export default function DesignPage() {
  const baselineRetrievers = retrievalCheckup.retrievers.slice(0, 2);
  const fusedRetriever = retrievalCheckup.retrievers[2];

  return (
    <div className="site-frame">
      <SiteHeader />
      <main className="shell inner-page evidence-page">
        <header className="page-intro design-intro evidence-intro">
          <p className="eyebrow"><span>工程证据</span> Architecture · Retrieval · Failure</p>
          <h1>三个工程问题，<br /><em>证明这不只是聊天框 Demo。</em></h1>
          <p>模型被放在什么边界里，RAG 是否真的找回必需来源，失败又怎样改变产品——
            下面先给结论，需要时再展开完整证据。</p>
        </header>

        <nav className="evidence-index" aria-label="三项核心工程证据">
          <a href="#architecture-proof">
            <span>01 · 系统</span><strong>模型如何被约束？</strong><p>宿主管理检索、预算、状态和停止。</p><em>看架构 ↓</em>
          </a>
          <a href="#retrieval-proof">
            <span>02 · RAG</span><strong>检索真的更好吗？</strong><p>冻结问题的 Top-5 全覆盖从 {baselineRetrievers[0].full_coverage_at_5.passed_cases}/{baselineRetrievers[0].full_coverage_at_5.total_cases} 提升到 {fusedRetriever.full_coverage_at_5.passed_cases}/{fusedRetriever.full_coverage_at_5.total_cases}。</p><em>看结果 ↓</em>
          </a>
          <a href="#failure-proof">
            <span>03 · 失败</span><strong>系统何时会停手？</strong><p>机械通过不冒充业务完整，失败正式转人工。</p><em>看演进 ↓</em>
          </a>
        </nav>

        <section id="architecture-proof" className="evidence-story">
          <div className="story-heading">
            <div><span>01</span><p>系统边界</p></div>
            <div><h2>模型负责组织候选，<br />宿主负责控制风险。</h2><p>生产依赖方向固定，评测与历史实验不能反向进入产品。</p></div>
          </div>

          <div className="architecture-card architecture-summary">
            <div>
              <span>依赖方向</span>
              <h3>HTTP API → Product → Retrieval / Generation / Provider</h3>
              <p>公开回放无需模型、凭据或 live 依赖即可启动；实时能力只有在开关、runner、依赖、凭据和健康门同时就绪时可用。</p>
            </div>
            <ul>
              <li><strong>公开调用方不受信任</strong><span>精确 CORS、16 KiB 请求上限、随机 run ID、队列与预算门。</span></li>
              <li><strong>失败必须有明确状态</strong><span>来源、结构或完整性失败就停止，不生成虚假成功。</span></li>
              <li><strong>人工批准不触发动作</strong><span>决定被记录，但不发送、不退款、不换新、不结单。</span></li>
            </ul>
          </div>

          <details className="evidence-details">
            <summary><span>展开设计细节</span><strong>四项原则与五步工作流</strong><em>展开</em></summary>
            <div className="evidence-details-body">
              <section className="principle-grid" aria-label="四项设计原则">
                {principles.map(([title, copy], index) => (
                  <article key={title}><span>0{index + 1}</span><h3>{title}</h3><p>{copy}</p></article>
                ))}
              </section>
              <section className="design-flow">
                <div className="section-heading">
                  <p>一次候选如何形成</p>
                  <div><h3>模型只负责它擅长的部分。</h3><p>身份、状态、预算和门由宿主掌握。</p></div>
                </div>
                <div className="flow-rows">
                  {flow.map(([label, title, copy], index) => (
                    <article key={label}><b>{String(index + 1).padStart(2, "0")}</b><span>{label}</span><h3>{title}</h3><p>{copy}</p></article>
                  ))}
                </div>
              </section>
            </div>
          </details>
        </section>

        <section id="retrieval-proof" className="evidence-story retrieval-story" aria-labelledby="retrieval-checkup-title">
          <div className="story-heading">
            <div><span>02</span><p>RAG 体检</p></div>
            <div>
              <h2 id="retrieval-checkup-title">两种单路各漏两题，<br />混合检索补回 Top 5。</h2>
              <p>同一批冻结合成问题、同一套必需来源标签，不换题、不调参。</p>
            </div>
          </div>

          <div className="retrieval-spotlight">
            <div className="retrieval-change">
              <span>Top-5 必需来源全覆盖</span>
              <div>
                <b>{baselineRetrievers[0].full_coverage_at_5.passed_cases}/{baselineRetrievers[0].full_coverage_at_5.total_cases}</b>
                <i>+</i>
                <b>{baselineRetrievers[1].full_coverage_at_5.passed_cases}/{baselineRetrievers[1].full_coverage_at_5.total_cases}</b>
                <i>→</i>
                <strong>{fusedRetriever.full_coverage_at_5.passed_cases}/{fusedRetriever.full_coverage_at_5.total_cases}</strong>
              </div>
              <p>BM25 与 BGE 各自漏出 Top 5 的来源，被 BM25 + BGE + RRF 补回。</p>
            </div>
            <dl>
              <div><dt>冻结问题</dt><dd>{retrievalCheckup.dataset.case_count}</dd></div>
              <div><dt>有效章节覆盖</dt><dd>{retrievalCheckup.dataset.section_count}/{retrievalCheckup.dataset.section_count}</dd></div>
              <div><dt>错误型号来源</dt><dd>{fusedRetriever.wrong_model_hits_at_10}</dd></div>
            </dl>
          </div>
          <p className="evidence-limit"><strong>结论边界：</strong>这不是线上成功率，不评回答是否正确，也不是未见 HOLDOUT；全程没有调用 Provider。</p>

          <details className="evidence-details">
            <summary><span>展开评测细节</span><strong>范围、完整表格与成功/失败案例</strong><em>展开</em></summary>
            <div className="evidence-details-body">
              <div className="checkup-scope" aria-label="评测范围">
                <article><strong>{retrievalCheckup.dataset.case_count}</strong><span>个冻结合成问题</span></article>
                <article><strong>{retrievalCheckup.dataset.model_split["CZ-R1"]} + {retrievalCheckup.dataset.model_split["CZ-R2"]}</strong><span>R1 / R2 各半</span></article>
                <article><strong>{retrievalCheckup.dataset.section_count} / {retrievalCheckup.dataset.section_count}</strong><span>当前有效章节被标签覆盖</span></article>
                <article><strong>{retrievalCheckup.dataset.multi_source_case_count}</strong><span>个多来源问题</span></article>
              </div>

              <div className="checkup-table-wrap">
                <table className="checkup-table">
                  <caption>每个数字表示“全部必需来源都进入该范围”的题数，不是单个来源命中率。</caption>
                  <thead>
                    <tr><th scope="col">检索方式</th><th scope="col">Top 5 全部命中</th><th scope="col">Top 10 全部命中</th><th scope="col">错误型号来源</th></tr>
                  </thead>
                  <tbody>
                    {retrievalCheckup.retrievers.map((item) => (
                      <tr key={item.retriever_id}>
                        <th scope="row">{item.label}</th>
                        <td><strong>{item.full_coverage_at_5.passed_cases} / {item.full_coverage_at_5.total_cases}</strong></td>
                        <td>{item.full_coverage_at_10.passed_cases} / {item.full_coverage_at_10.total_cases}</td>
                        <td>{item.wrong_model_hits_at_10}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div className="checkup-examples" aria-label="一条成功和两条失败">
                {retrievalCheckup.public_examples.map((example) => {
                  const item = retrievalCases.get(example.case_id);
                  if (!item) return null;
                  const retrieval = item.retrievals[example.retriever_id as keyof typeof item.retrievals];
                  return (
                    <article key={`${example.role}-${example.case_id}`} className={example.role === "success" ? "example-success" : "example-failure"}>
                      <span>{example.role === "success" ? "成功样例" : "失败样例"} · {retrievalLabels.get(example.retriever_id)}</span>
                      <h3>{example.case_id}</h3>
                      <p>{item.query}</p>
                      <dl>
                        <div><dt>必需来源</dt><dd>{item.required_source_sections.join("；")}</dd></div>
                        <div>
                          <dt>Top 5 结果</dt>
                          <dd>{example.role === "success"
                            ? "全部进入 Top 5。"
                            : example.missing_at_5.map((source) => `${source} 只排到第 ${retrieval.required_source_ranks[source as keyof typeof retrieval.required_source_ranks]} 名`).join("；")}
                          </dd>
                        </div>
                      </dl>
                    </article>
                  );
                })}
              </div>

              <aside className="checkup-boundary">
                <strong>这组数字能证明什么？</strong>
                <p>它只说明：在 16 个公开合成问题上，混合 RRF 把 BM25 和 BGE 各自漏出 Top 5 的来源补了回来。它不代表线上成功率，不评回答是否正确，也不是未见 HOLDOUT；全程没有调用 Provider。</p>
                <code>PYTHONPATH=api/src python tools/retrieval_checkup.py --check</code>
              </aside>
            </div>
          </details>
        </section>

        <section id="failure-proof" className="evidence-story failure-story">
          <div className="story-heading">
            <div><span>03</span><p>失败演进</p></div>
            <div><h2>绿色检查不够，<br />产品必须知道何时失败。</h2><p>一次“结构全过但正文漏项”的失败，促成了先规划义务、再生成正文的两阶段链路。</p></div>
          </div>

          <div className="failure-spotlight">
            <article><span>发现问题</span><strong>6 / 6 ≠ PASS</strong><p>结构门全过，但正文只覆盖 11 / 15 项关键义务。</p></article>
            <div aria-hidden="true">→</div>
            <article><span>进入产品</span><strong>Plan → Text</strong><p>先规划必须覆盖的义务，再用机械映射阻止静默漏项。</p></article>
          </div>

          <details className="evidence-details">
            <summary><span>展开失败记录</span><strong>四次关键发现与产品变化</strong><em>展开</em></summary>
            <div className="evidence-details-body">
              <div className="ledger-table">
                <div><span>Formal B1</span><strong>27 / 36</strong><p>安全护栏未达冻结门，候选正式失败。</p></div>
                <div><span>Top-10 v3</span><strong>6 / 6 ≠ PASS</strong><p>结构门全过，但正文只覆盖 11 / 15 项关键义务。</p></div>
                <div><span>Two-step</span><strong>Plan → Text</strong><p>把遗漏上移到义务规划，再以机械映射阻止静默漏项。</p></div>
                <div><span>Public beta</span><strong>绑定式溯源</strong><p>真实 Provider 已启用；每条结论绑定存在的证据与义务，回放独立标记。</p></div>
              </div>
            </div>
          </details>
        </section>
      </main>
      <SiteFooter />
    </div>
  );
}
