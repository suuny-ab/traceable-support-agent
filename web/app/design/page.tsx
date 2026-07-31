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
  return (
    <div className="site-frame">
      <SiteHeader />
      <main className="shell inner-page">
        <header className="page-intro design-intro">
          <p className="eyebrow"><span>架构</span> Design & evidence</p>
          <h1>把模型放进一条<br /><em>可检查、可停止的业务链。</em></h1>
          <p>这里展示的是已经进入代码、测试或真实运行回执的设计。重点不是让模型更自由，
            而是让团队知道结论从哪里来、何时应停止、最后由谁决定。</p>
        </header>

        <section className="principle-grid" aria-label="四项设计原则">
          {principles.map(([title, copy], index) => (
            <article key={title}><span>0{index + 1}</span><h2>{title}</h2><p>{copy}</p></article>
          ))}
        </section>

        <section className="design-flow">
          <div className="section-heading">
            <p>一次候选如何形成</p>
            <div><h2>模型只负责它擅长的部分。</h2><p>身份、状态、预算和门由宿主掌握。</p></div>
          </div>
          <div className="flow-rows">
            {flow.map(([label, title, copy], index) => (
              <article key={label}><b>{String(index + 1).padStart(2, "0")}</b><span>{label}</span><h3>{title}</h3><p>{copy}</p></article>
            ))}
          </div>
        </section>

        <section className="architecture-card">
          <div>
            <span>依赖方向</span>
            <h2>HTTP API → Product → Retrieval / Generation / Provider</h2>
            <p>评测只能调用产品，产品不能反向依赖评测、脚本或历史实验。公开回放无需模型、凭据或 live 依赖即可启动。</p>
          </div>
          <ul>
            <li><strong>公开调用方不受信任</strong><span>精确 CORS、16 KiB 请求上限、随机 run ID、队列与预算门。</span></li>
            <li><strong>实时能力不是默认值</strong><span>开关、runner、依赖、凭据和健康门必须同时就绪。</span></li>
            <li><strong>人工批准不触发动作</strong><span>决定被记录，但不发送、不退款、不换新、不结单。</span></li>
          </ul>
        </section>

        <section className="retrieval-checkup" aria-labelledby="retrieval-checkup-title">
          <div className="section-heading">
            <p>RAG 体检</p>
            <div>
              <h2 id="retrieval-checkup-title">同一组问题，三种现有检索各自找回了什么。</h2>
              <p>第一次冻结运行，结果不用于换题、调参或包装线上成功率。</p>
            </div>
          </div>

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
        </section>

        <section className="failure-ledger">
          <div className="section-heading">
            <p>工程证据</p>
            <div><h2>失败如何改变了产品。</h2><p>机械通过不等于业务完整，真实运行也不能被静态复核替代。</p></div>
          </div>
          <div className="ledger-table">
            <div><span>Formal B1</span><strong>27 / 36</strong><p>安全护栏未达冻结门，候选正式失败。</p></div>
            <div><span>Top-10 v3</span><strong>6 / 6 ≠ PASS</strong><p>结构门全过，但正文只覆盖 11 / 15 项关键义务。</p></div>
            <div><span>Two-step</span><strong>Plan → Text</strong><p>把遗漏上移到义务规划，再以机械映射阻止静默漏项。</p></div>
            <div><span>Public beta</span><strong>绑定式溯源</strong><p>真实 Provider 已启用；每条结论绑定存在的证据与义务，回放独立标记。</p></div>
          </div>
        </section>
      </main>
      <SiteFooter />
    </div>
  );
}
