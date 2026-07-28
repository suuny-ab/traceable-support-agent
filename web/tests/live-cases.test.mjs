import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const liveCaseData = JSON.parse(await readFile(
  new URL("../app/lib/live-cases.json", import.meta.url),
  "utf8",
));
const replayData = JSON.parse(await readFile(
  new URL("../app/lib/replay-presets.json", import.meta.url),
  "utf8",
));
const publicRegression = JSON.parse(await readFile(
  new URL("../../evals/public-regression-v1.json", import.meta.url),
  "utf8",
));

test("live case inventory has three defaults and one boundary challenge", () => {
  assert.equal(liveCaseData.schema_version, "live-workbench-cases-v1");
  assert.equal(liveCaseData.cases.length, 4);
  assert.equal(liveCaseData.cases.filter((item) => item.kind === "default").length, 3);
  assert.equal(liveCaseData.cases.filter((item) => item.kind === "boundary").length, 1);
  assert.equal(new Set(liveCaseData.cases.map((item) => item.id)).size, 4);
  for (const item of liveCaseData.cases) {
    assert.ok(["qa", "ticket"].includes(item.taskType));
    assert.ok(["CZ-R1", "CZ-R2"].includes(item.model));
    assert.ok(item.input.length > 0 && item.input.length <= 500);
    if (item.replayPresetId) {
      assert.ok(replayData.presets.some((preset) => preset.id === item.replayPresetId));
    }
  }
});

test("boundary challenge matches the public mechanical expectation", () => {
  const boundary = liveCaseData.cases.find((item) => item.kind === "boundary");
  const expected = publicRegression.cases.find((item) => item.case_id === "GEN-DEV-IE-001");
  assert.equal(boundary.caseId, "GEN-DEV-IE-001");
  assert.equal(boundary.taskType, expected.task_type);
  assert.equal(boundary.model, expected.product_model);
  assert.equal(boundary.input, expected.input);
});

test("the three default cases cover QA, ticket, and fault handling", () => {
  const defaults = liveCaseData.cases.filter((item) => item.kind === "default");
  assert.deepEqual(defaults.map((item) => item.id), [
    "qa-local-clean",
    "ticket-carpet-risk",
    "qa-e310-fault",
  ]);
  assert.equal(defaults.filter((item) => item.taskType === "qa").length, 2);
  assert.equal(defaults.filter((item) => item.taskType === "ticket").length, 1);
  assert.match(defaults[2].input, /E310/);
});

test("boundary challenge copy declares the live-off exception honestly", async () => {
  const boundary = liveCaseData.cases.find((item) => item.kind === "boundary");
  assert.match(boundary.summary, /Provider 调用为 0/);
  assert.match(boundary.summary, /实时不可用时仍可创建/);

  const workbenchSource = await readFile(
    new URL("../app/components/DemoWorkbench.tsx", import.meta.url),
    "utf8",
  );
  // 实时不可用 / 未知时，状态行必须同时说明普通运行不可用和边界挑战例外，
  // 不得再笼统声称“不能创建新运行”。
  assert.match(workbenchSource, /普通运行不可用；边界挑战仍创建 0 次模型调用的确定性转人工/);
  assert.doesNotMatch(workbenchSource, /不能创建新运行，可查看已验证回放/);

  const pageSource = await readFile(
    new URL("../app/app/page.tsx", import.meta.url),
    "utf8",
  );
  assert.match(pageSource, /唯一的例外是固定边界挑战/);
  assert.match(pageSource, /Provider 调用为 0/);
  assert.doesNotMatch(pageSource, /不可用时不能创建新运行/);

  // 规格不得再保留两处旧概括原文（实时不可用时不能创建任何新运行）。
  const specSource = await readFile(
    new URL("../../docs/work/active/portfolio-live-experience/spec.md", import.meta.url),
    "utf8",
  );
  assert.doesNotMatch(specSource, /只明确说明不能创建新的运行/);
  assert.doesNotMatch(specSource, /不能创建新运行，明示原因/);
  assert.match(specSource, /固定边界挑战/);
});

test("suggested questions stay inside the synthetic sandbox and input limits", () => {
  assert.ok(liveCaseData.suggested_questions.length >= 4);
  for (const item of liveCaseData.suggested_questions) {
    assert.ok(["qa", "ticket"].includes(item.taskType));
    assert.ok(["CZ-R1", "CZ-R2"].includes(item.model));
    assert.ok(item.text.includes("CZ-R"));
    assert.ok(item.text.length <= 500);
    if (item.taskType === "ticket") {
      assert.ok(item.text.length >= 8);
    }
  }
});
