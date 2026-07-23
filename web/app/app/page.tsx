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
            <p>页面会先检测实时服务。当前公网固定为已验证回放；自由输入不会被预设答案冒充，
              也不会执行任何外部业务动作。</p>
            <div className="beta-notice"><strong>REPLAY ONLY</strong><span>Provider disabled · 合成数据</span></div>
          </div>
        </header>
        <DemoWorkbench />
      </main>
      <SiteFooter />
    </div>
  );
}
