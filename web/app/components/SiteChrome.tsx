"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";

const links = [
  ["/", "产品"],
  ["/design", "设计与证据"],
  ["/app", "在线工作台"],
  ["/privacy", "隐私与边界"],
] as const;

export function SiteHeader() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);

  return (
    <header className="site-header">
      <div className="shell header-inner">
        <Link className="brand" href="/" aria-label="Traceable Support Agent 产品主页" onClick={() => setOpen(false)}>
          <span className="brand-mark" aria-hidden="true"><i /><i /><i /></span>
          <span>
            <strong>Traceable Support Agent</strong>
            <small>Evidence-led support decisions</small>
          </span>
        </Link>

        <button
          className="mobile-menu-button"
          type="button"
          aria-expanded={open}
          aria-controls="site-navigation"
          aria-label={open ? "关闭主导航" : "打开主导航"}
          onClick={() => setOpen((value) => !value)}
        >
          <span aria-hidden="true" />
          <span aria-hidden="true" />
          <span aria-hidden="true" />
        </button>

        <nav id="site-navigation" className={open ? "site-navigation navigation-open" : "site-navigation"} aria-label="主导航">
          {links.map(([href, label]) => (
            <Link
              href={href}
              key={href}
              aria-current={pathname === href ? "page" : undefined}
              onClick={() => setOpen(false)}
            >
              {label}
            </Link>
          ))}
          <a
            className="github-link"
            href="https://github.com/suuny-ab/traceable-support-agent"
            target="_blank"
            rel="noreferrer"
          >
            GitHub <span aria-hidden="true">↗</span>
          </a>
        </nav>

        <div className="deploy-status" aria-label="公开体验状态">
          <i aria-hidden="true" />
          <span><strong>公开 Beta</strong><small>实时运行 + 回放</small></span>
        </div>
      </div>
    </header>
  );
}

export function SiteFooter() {
  return (
    <footer className="site-footer">
      <div className="shell footer-inner">
        <div>
          <strong>Traceable Support Agent</strong>
          <span>RAG · 受控生成 · 失败关闭 · AI 应用工程作品</span>
        </div>
        <nav aria-label="页脚导航">
          <Link href="/design">设计与证据</Link>
          <Link href="/app">在线工作台</Link>
          <Link href="/privacy">隐私与边界</Link>
          <a href="https://github.com/suuny-ab/traceable-support-agent" target="_blank" rel="noreferrer">GitHub ↗</a>
        </nav>
        <p>合成数据 · 无自动外部动作 · product/0.1.0 尚未发布</p>
      </div>
    </footer>
  );
}
