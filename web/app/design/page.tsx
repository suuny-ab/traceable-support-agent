import type { Metadata } from "next";
import { SiteFooter, SiteHeader } from "../components/SiteChrome";

export const metadata: Metadata = { title: "设计说明", description: "可追溯客服LLM工作流的设计亮点、失败边界与证据。" };

const principles = [
  ["宿主拥有停止权", "检索、预算、来源校验、持久化和重试都由确定性宿主控制，模型没有工具权。"],
  ["先规划，再生成", "先枚举回答必须覆盖的业务义务，再生成客户正文，把遗漏变成可以观察的失败。"],
  ["结构不冒充语义", "claim与来源绑定通过，只能证明结构；正文事实完整仍需独立语义和人工门。"],
  ["失败也是结果", "证据不足、型号冲突、Provider异常或门失败都转人工，不包装成一次成功回答。"],
];

export default function DesignPage() {
  return <div className="site-frame"><SiteHeader /><main className="shell inner-page">
    <header className="page-intro"><p className="eyebrow"><span>02</span> Design Notes</p><h1>设计的重点不是让模型<br />更自由，而是让结果更可检查</h1><p>这是一次从确定性Demo、失败候选到两步法产品主链的演进。设计说明只展示已经进入代码、测试或真实运行证据的取舍。</p></header>
    <section className="principle-grid">{principles.map(([title, copy], index) => <article key={title}><span>0{index + 1}</span><h2>{title}</h2><p>{copy}</p></article>)}</section>
    <section className="design-flow"><div className="section-heading"><p>01 / DATA FLOW</p><h2>一次候选如何形成</h2></div><div className="flow-rows">
      <article><b>INPUT</b><h3>合成QA或工单</h3><p>前置检查型号、范围和安全输入；高风险内容在生成前停止。</p></article>
      <article><b>RETRIEVAL</b><h3>型号感知的混合检索</h3><p>宿主使用BM25、BGE与RRF形成候选，来源原文不会由模型自行搜索。</p></article>
      <article><b>PLAN</b><h3>义务枚举</h3><p>第一轮模型只规划必须回答的内容及证据，不直接生成最终回复。</p></article>
      <article><b>GENERATE</b><h3>证据约束正文</h3><p>第二轮生成QA回复或工单建议，每条claim绑定批准来源与义务。</p></article>
      <article><b>GATES</b><h3>机械门与人工决定</h3><p>失败则handoff；通过后也只等待人工批准、编辑或拒绝。</p></article>
    </div></section>
    <section className="failure-ledger"><div className="section-heading"><p>02 / FAILURE LEDGER</p><h2>失败怎样改变架构</h2></div><div className="ledger-table">
      <div><span>Formal B1</span><strong>27 / 36</strong><p>安全护栏未达冻结门，候选正式失败，不能接产品。</p></div>
      <div><span>Top-10 v3</span><strong>6 / 6 ≠ PASS</strong><p>结构与来源机械门全部通过，但正文只覆盖11/15项关键义务。</p></div>
      <div><span>Two-step</span><strong>PLAN → TEXT</strong><p>把遗漏从最终正文上移到义务规划，并用机械映射阻止静默漏项。</p></div>
      <div><span>Stage 11</span><strong>QA + TICKET</strong><p>两条本地主链完成真实调用、SQLite决定和描述性效率统计。</p></div>
    </div></section>
    <section className="tradeoff-grid"><article><span>选择</span><h2>保留完整Top-10上下文</h2><p>不让未经证明的启发式证据选择器静默丢失关键事实；代价是上下文更长，生成链必须承担更严格的义务门。</p></article><article><span>选择</span><h2>不做开放式Agent</h2><p>模型不调用工具、不写库、不决定重试。当前求职项目证明的是受控LLM Workflow，不是自主执行平台。</p></article><article><span>限制</span><h2>当前仍是Beta</h2><p>Stage 12全新未见评测尚未执行；公开部署流程跑通不等于`product/0.1.0`发布。</p></article></section>
  </main><SiteFooter /></div>;
}
