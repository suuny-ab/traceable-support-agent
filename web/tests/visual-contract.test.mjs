import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { test } from "node:test";

test("light SaaS palette and responsive accessibility contracts are local", async () => {
  const css = await readFile(new URL("../app/globals.css", import.meta.url), "utf8");
  assert.match(css, /--canvas:\s*#f7f7f3/);
  assert.match(css, /--navy:\s*#0b2742/);
  assert.match(css, /--blue:\s*#2563eb/);
  assert.match(css, /--teal:\s*#0f8f83/);
  assert.match(css, /--amber:\s*#a65306/);
  assert.match(css, /\.mobile-menu-button[\s\S]*width:\s*44px[\s\S]*height:\s*44px/);
  assert.match(css, /@media \(prefers-reduced-motion: reduce\)/);
  assert.match(css, /overflow-x:\s*clip/);
  assert.doesNotMatch(css, /url\((?:https?:)?\/\//);
});

test("mobile navigation exposes keyboard state and the real repository", async () => {
  const source = await readFile(
    new URL("../app/components/SiteChrome.tsx", import.meta.url),
    "utf8",
  );
  assert.match(source, /aria-expanded=\{open\}/);
  assert.match(source, /aria-controls="site-navigation"/);
  assert.match(source, /aria-current=\{pathname === href \? "page"/);
  assert.match(source, /https:\/\/github\.com\/suuny-ab\/traceable-support-agent/);
  assert.match(source, /target="_blank"/);
  assert.match(source, /rel="noreferrer"/);
});

test("core text palette meets WCAG AA contrast", () => {
  function luminance(hex) {
    const channels = hex.match(/../g).map((value) => Number.parseInt(value, 16) / 255);
    const linear = channels.map((value) =>
      value <= 0.03928 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4);
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2];
  }
  function contrast(foreground, background) {
    const first = luminance(foreground);
    const second = luminance(background);
    return (Math.max(first, second) + 0.05) / (Math.min(first, second) + 0.05);
  }
  for (const [foreground, background] of [
    ["0b2742", "f7f7f3"],
    ["18344f", "ffffff"],
    ["5d7184", "f7f7f3"],
    ["5f7183", "f7f7f3"],
    ["2563eb", "f7f7f3"],
    ["a65306", "fff6df"],
  ]) {
    assert.ok(contrast(foreground, background) >= 4.5);
  }
});
