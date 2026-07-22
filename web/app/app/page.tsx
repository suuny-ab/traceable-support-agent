import type { Metadata } from "next";
import { DemoWorkbench } from "../components/DemoWorkbench";
import { SiteFooter, SiteHeader } from "../components/SiteChrome";

export const metadata: Metadata = { title: "在线体验", description: "体验可追溯QA与工单处理工作流的真实运行、已验证回放和失败关闭。" };

export default function AppPage() {
  return <div className="site-frame"><SiteHeader /><main className="shell inner-page app-page">
    <header className="page-intro compact-intro"><p className="eyebrow"><span>03</span> Product Workbench</p><h1>实际体验候选、来源、义务与失败边界</h1><p>页面会现场检测实时服务。实时关闭或状态未知时，预设案例仍可使用阶段11已验证回放；两条路径不会混淆。</p><div className="beta-notice"><strong>DEPLOYMENT CANDIDATE</strong><span>不会把回放伪装成实时生成，也不会执行任何外部业务动作。</span></div></header>
    <DemoWorkbench />
  </main><SiteFooter /></div>;
}
