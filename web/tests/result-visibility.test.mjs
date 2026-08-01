import assert from "node:assert/strict";
import { test } from "node:test";

import {
  revealResultPanel,
  shouldScrollResult,
} from "../app/lib/result-visibility.mjs";

test("stacked workbench always brings the result start into view", () => {
  assert.equal(shouldScrollResult({ panelTop: 590, viewportWidth: 390, viewportHeight: 844 }), true);
  assert.equal(shouldScrollResult({ panelTop: 120, viewportWidth: 1000, viewportHeight: 900 }), true);
});

test("wide workbench scrolls only when the result header is outside the safe viewport", () => {
  assert.equal(shouldScrollResult({ panelTop: 436, viewportWidth: 1440, viewportHeight: 900 }), false);
  assert.equal(shouldScrollResult({ panelTop: -976, viewportWidth: 1440, viewportHeight: 900 }), true);
  assert.equal(shouldScrollResult({ panelTop: 780, viewportWidth: 1440, viewportHeight: 900 }), true);
});

test("result reveal focuses once and respects reduced motion", () => {
  const calls = [];
  const panel = {
    focus: (options) => calls.push(["focus", options]),
    getBoundingClientRect: () => ({ top: 590 }),
    scrollIntoView: (options) => calls.push(["scroll", options]),
  };
  revealResultPanel(panel, {
    windowImpl: {
      innerWidth: 390,
      innerHeight: 844,
      matchMedia: () => ({ matches: true }),
    },
  });
  assert.deepEqual(calls, [
    ["focus", { preventScroll: true }],
    ["scroll", { block: "start", behavior: "auto" }],
  ]);
});

test("a visible wide result receives focus without moving the page", () => {
  const calls = [];
  const panel = {
    focus: (options) => calls.push(["focus", options]),
    getBoundingClientRect: () => ({ top: 436 }),
    scrollIntoView: (options) => calls.push(["scroll", options]),
  };
  revealResultPanel(panel, {
    windowImpl: {
      innerWidth: 1440,
      innerHeight: 900,
      matchMedia: () => ({ matches: false }),
    },
  });
  assert.deepEqual(calls, [["focus", { preventScroll: true }]]);
});
