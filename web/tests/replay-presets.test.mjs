import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

import { selectRunRoute } from "../app/lib/replay-routing.mjs";


const replayData = JSON.parse(await readFile(
  new URL("../app/lib/replay-presets.json", import.meta.url),
  "utf8",
));
const publicRegression = JSON.parse(await readFile(
  new URL("../../evals/public-regression-v1.json", import.meta.url),
  "utf8",
));


test("replay inventory has two QA presets and one ticket preset", () => {
  assert.equal(replayData.schema_version, "verified-replay-presets-v1");
  assert.equal(replayData.presets.length, 3);
  assert.equal(new Set(replayData.presets.map((item) => item.id)).size, 3);
  assert.equal(replayData.presets.filter((item) => item.taskType === "qa").length, 2);
  assert.equal(replayData.presets.filter((item) => item.taskType === "ticket").length, 1);
});


test("GEN-DEV-IE-001 replay matches the public mechanical expectation", () => {
  const replay = replayData.presets.find((item) => item.caseId === "GEN-DEV-IE-001");
  const expected = publicRegression.cases.find((item) => item.case_id === "GEN-DEV-IE-001");
  assert.ok(replay);
  assert.ok(expected);
  assert.equal(replay.taskType, expected.task_type);
  assert.equal(replay.model, expected.product_model);
  assert.equal(replay.input, expected.input);
  assert.equal(replay.result.outcome, expected.expected.outcome);
  assert.equal(replay.result.handoff_reason, expected.expected.handoff_reason);
  assert.equal(replay.result.provider_call_count, expected.expected.provider_call_count);
  assert.deepEqual(expected.expected.source_sections, []);
  assert.deepEqual(replay.result.evidence, []);
});


test("insufficient evidence replay stops before planning or generation", () => {
  const replay = replayData.presets.find((item) => item.id === "qa-insufficient-evidence");
  assert.equal(replay.stopStageIndex, 0);
  assert.equal(replay.replayOnly, true);
  assert.match(replay.result.answer, /不足以确认/);
  assert.match(replay.result.answer, /转交人工/);
  assert.equal(replay.result.gates.find((gate) => gate.label === "批准来源").pass, false);
  assert.equal(replay.result.gates.find((gate) => gate.label === "Provider 调用前拦截").pass, true);
});


test("live-first routing never auto-substitutes replay", () => {
  assert.equal(selectRunRoute({ availability: "available" }), "live");
  assert.equal(selectRunRoute({ availability: "unavailable" }), "blocked");
  assert.equal(selectRunRoute({ availability: "unknown" }), "blocked");
  assert.equal(selectRunRoute({ availability: "checking" }), "blocked");
  // Deterministic preflight handoffs stay runnable without live: they are
  // persisted before the live gate and never reach a Provider call.
  assert.equal(selectRunRoute({ availability: "unavailable", preflightOnly: true }), "live");
  assert.equal(selectRunRoute({ availability: "unknown", preflightOnly: true }), "live");
});
