import type { Metadata } from "next";
import { DemoWorkbench } from "../components/DemoWorkbench";
import { SiteFooter, SiteHeader } from "../components/SiteChrome";

export const metadata: Metadata = {
  title: "在线工作台",
  description: "体验可追溯 QA 与工单工作流的输入、轨迹、证据和人工决定。",
};

export default function AppPage() {
  return (
    <div className="site-frame">
      <SiteHeader />
      <main className="shell inner-page app-page">
        <header className="page-intro compact-intro">
          <div>
            <p className="eyebrow"><span>引导演示</span> Guided product demo</p>
            <h1>运行一个案例，<br /><em>看懂整个系统。</em></h1>
          </div>
          <div className="workbench-intro-copy">
            <p>从推荐案例开始。一次运行会依次展示回答、批准来源、质量门和人工决定；
              其他案例、自由提问与回放都收在“更多体验”里。</p>
            <div className="beta-notice"><strong>点击后才创建运行</strong><span>只用合成数据 · 不执行客服动作</span></div>
          </div>
        </header>
        <DemoWorkbench />
      </main>
      <SiteFooter />
    </div>
  );
}
