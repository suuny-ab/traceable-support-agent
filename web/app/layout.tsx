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
      default: "Traceable Support Agent｜可追溯客服决策支持",
      template: "%s｜Traceable Support Agent",
    },
    description: "让客服 AI 的每个结论有证据、有退出机制，并把最终决定留给团队。",
    openGraph: {
      type: "website",
      title: "Traceable Support Agent",
      description: "让客服 AI 的每个结论有证据、有退出机制。",
      images: [{ url: "/og.png", width: 1672, height: 941, alt: "Traceable Support Agent evidence console" }],
    },
    twitter: {
      card: "summary_large_image",
      title: "Traceable Support Agent",
      description: "让客服 AI 的每个结论有证据、有退出机制。",
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
