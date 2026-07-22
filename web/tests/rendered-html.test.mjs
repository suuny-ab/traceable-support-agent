import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { access } from "node:fs/promises";
import { after, before, test } from "node:test";

const port = 32000 + (process.pid % 1000);
const baseUrl = `http://127.0.0.1:${port}`;
let server;
let stderr = "";

async function waitUntilReady() {
  const deadline = Date.now() + 20_000;
  while (Date.now() < deadline) {
    try {
      const response = await fetch(`${baseUrl}/`);
      if (response.ok) return;
    } catch {
      // Standalone server is still starting.
    }
    await new Promise((resolve) => setTimeout(resolve, 100));
  }
  throw new Error(`standalone server did not start: ${stderr}`);
}

before(async () => {
  await access(new URL("../.next/standalone/server.js", import.meta.url));
  server = spawn(process.execPath, [".next/standalone/server.js"], {
    cwd: new URL("..", import.meta.url),
    env: {
      ...process.env,
      HOSTNAME: "127.0.0.1",
      PORT: String(port),
      NEXT_TELEMETRY_DISABLED: "1",
    },
    stdio: ["ignore", "pipe", "pipe"],
  });
  server.stderr.on("data", (chunk) => {
    stderr += chunk.toString();
  });
  await waitUntilReady();
});

after(() => {
  server?.kill();
});

const routes = [
  ["/", /让每个 LLM 结论都有/],
  ["/design", /设计的重点不是让模型/],
  ["/app", /实际体验候选、来源、义务与失败边界/],
  ["/privacy", /这是合成数据演示/],
];

for (const [pathname, expected] of routes) {
  test(`standalone renders ${pathname}`, async () => {
    const response = await fetch(`${baseUrl}${pathname}`);
    assert.equal(response.status, 200);
    assert.match(response.headers.get("content-type") ?? "", /^text\/html\b/i);
    const html = await response.text();
    assert.match(html, expected);
    assert.doesNotMatch(html, /react-loading-skeleton|Your site is taking shape/);
  });
}

test("renders explicit live-health and replay choices", async () => {
  const response = await fetch(`${baseUrl}/app`);
  const html = await response.text();
  assert.match(html, /正在检测实时服务/);
  assert.match(html, /实时路径最多两次 Provider 请求/);
  assert.match(html, /运行已验证回放/);
  assert.match(html, /CZ-R1 证据不足转人工/);
});
