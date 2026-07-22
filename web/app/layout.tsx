import type { Metadata } from "next";
import { headers } from "next/headers";
import "./globals.css";

export async function generateMetadata(): Promise<Metadata> {
  const requestHeaders = await headers();
  const host = requestHeaders.get("host") ?? "traceable-support-agent.local";
  const forwardedProto = requestHeaders.get("x-forwarded-proto");
  const protocol = forwardedProto === "http" || forwardedProto === "https"
    ? forwardedProto
    : host.includes("localhost") || host.endsWith(".local") ? "http" : "https";
  const metadataBase = new URL(`${protocol}://${host}`);

  return {
    metadataBase,
    title: {
      default: "Traceable Support Agent｜可追溯客服智能体",
      template: "%s｜Traceable Support Agent",
    },
    description: "以混合检索、义务规划、机械质量门和人工决定构成的可追溯客服LLM工作流。",
    openGraph: {
      type: "website",
      title: "Traceable Support Agent",
      description: "让每个LLM结论都有证据，让每次失败诚实停止。",
      images: [{ url: "/og.png", width: 1672, height: 941, alt: "Traceable Support Agent evidence console" }],
    },
    twitter: {
      card: "summary_large_image",
      title: "Traceable Support Agent",
      description: "让每个LLM结论都有证据，让每次失败诚实停止。",
      images: ["/og.png"],
    },
  };
}

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
