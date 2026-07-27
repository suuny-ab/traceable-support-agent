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
            <p>每次点击都会创建一次新的运行：检索、义务规划、生成和机械门都发生在服务端，
              结果只有候选或转人工两种。实时状态由页面检测；普通运行和自由探索只在实时
              可用时创建，不可用时只能查看明确标记的已验证回放。唯一的例外是固定边界挑战：
              它在模型调用前由确定性规则停止，即使实时不可用也会创建一次 Provider 调用为 0
              的确定性转人工运行，用于演示证据不足如何失败关闭。</p>
            <div className="beta-notice"><strong>合成数据 · 零业务动作</strong><span>实时状态由工作台检测显示，不用回放冒充新运行</span></div>
          </div>
        </header>
        <DemoWorkbench />
      </main>
      <SiteFooter />
    </div>
  );
}
