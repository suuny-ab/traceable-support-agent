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
            <p className="eyebrow"><span>在线体验</span> Product workbench</p>
            <h1>从输入到决定，<br /><em>看见完整证据链。</em></h1>
          </div>
          <div className="workbench-intro-copy">
            <p>先选一个默认案例，看检索、义务、生成、机械门和来源如何形成候选或转人工。
              普通案例只在实时可用时创建新运行；回放不创建运行。唯一的例外是固定边界挑战：
              实时不可用时仍会创建一次 Provider 调用为 0 的确定性转人工运行。</p>
            <div className="beta-notice"><strong>合成数据 · 不执行客服动作</strong><span>实时状态现场检测 · 回放不调用模型</span></div>
          </div>
        </header>
        <DemoWorkbench />
      </main>
      <SiteFooter />
    </div>
  );
}
