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
