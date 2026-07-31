import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { access, readFile } from "node:fs/promises";
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
  ["/", /让客服 AI 的结论/],
  ["/design", /把模型放进一条/],
  ["/app", /从输入到决定/],
  ["/privacy", /这里不是客服入口/],
];

for (const [pathname, expected] of routes) {
  test(`standalone renders ${pathname}`, async () => {
    const response = await fetch(`${baseUrl}${pathname}`);
    assert.equal(response.status, 200);
    assert.match(response.headers.get("content-type") ?? "", /^text\/html\b/i);
    const html = await response.text();
    assert.match(html, expected);
    assert.match(html, /https:\/\/github\.com\/suuny-ab\/traceable-support-agent/);
    assert.match(html, /打开主导航/);
    assert.match(html, /产品|设计与证据|在线工作台|隐私与边界/);
    assert.doesNotMatch(html, /react-loading-skeleton|Your site is taking shape/);
  });
}

test("renders explicit live-health and replay choices", async () => {
  const response = await fetch(`${baseUrl}/app`);
  const html = await response.text();
  assert.match(html, /正在检测实时服务/);
  assert.match(html, /创建新运行/);
  assert.match(html, /受约束自由探索/);
  assert.match(html, /已验证回放/);
  assert.match(html, /GEN-DEV-IE-001/);
  assert.match(html, /唯一的例外是固定边界挑战/);
  assert.match(html, /Provider 调用为 0/);
  assert.doesNotMatch(html, /不可用时不能创建新运行/);
});

test("homepage preview answer matches the verified replay and approved clause", async () => {
  const replayData = JSON.parse(await readFile(
    new URL("../app/lib/replay-presets.json", import.meta.url),
    "utf8",
  ));
  const preset = replayData.presets.find((item) => item.id === "qa-local-clean");
  const response = await fetch(`${baseUrl}/`);
  const html = await response.text();
  // 首页预览标记 VERIFIED REPLAY，同一客户问题的建议回复必须与已验证回放逐字一致，
  // 并且与批准来源 KB-CZR1-014 的动作（长按三秒）保持同一语义。
  assert.ok(html.includes(preset.input));
  assert.ok(html.includes(preset.result.answer));
  assert.match(html, /KB-CZR1-014/);
  assert.match(preset.result.answer, /长按清扫键三秒/);
  assert.match(preset.result.evidence[0].text, /长按三秒/);
  assert.doesNotMatch(html, /短按局部清扫键/);
});

test("design page renders the frozen retrieval checkup and its limits", async () => {
  const response = await fetch(`${baseUrl}/design`);
  const html = await response.text();
  assert.match(html, /RAG 体检/);
  assert.match(html, /BM25 \+ BGE \+ RRF/);
  assert.match(html, /Top 5 全部命中/);
  assert.match(html, /Top 10 全部命中/);
  assert.match(html, /错误型号来源/);
  assert.match(html, /成功样例/);
  assert.match(html, /失败样例/);
  assert.match(html, /不代表线上成功率/);
  assert.match(html, /没有调用 Provider/);
});
