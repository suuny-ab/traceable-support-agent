import Link from "next/link";

export function SiteHeader() {
  return (
    <header className="site-header shell">
      <Link className="brand" href="/" aria-label="Traceable Support Agent 产品主页">
        <span className="brand-mark" aria-hidden="true"><i /><i /></span>
        <span><strong>Traceable Support Agent</strong><small>可追溯客服智能体</small></span>
      </Link>
      <nav aria-label="主导航">
        <Link href="/">产品主页</Link>
        <Link href="/design">设计说明</Link>
        <Link href="/app">在线体验</Link>
        <span aria-label="源码仓库将在公开检查点开放">GitHub · 准备中</span>
      </nav>
      <div className="deploy-status"><i /> DEPLOYMENT CANDIDATE · REPLAY READY</div>
    </header>
  );
}

export function SiteFooter() {
  return (
    <footer className="site-footer shell">
      <div><strong>Traceable Support Agent</strong><span>AI Application Engineering Portfolio</span></div>
      <nav aria-label="页脚导航"><Link href="/design">设计说明</Link><Link href="/app">在线体验</Link><Link href="/privacy">隐私与边界</Link></nav>
      <p>合成数据 · 无自动外部动作 · product/0.1.0 尚未发布</p>
    </footer>
  );
}
