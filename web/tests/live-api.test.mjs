import assert from "node:assert/strict";
import test from "node:test";

import {
  apiUrl,
  checkLiveAvailability,
  parseHealth,
  pollLiveRun,
  requestLiveRun,
  submitHumanDecision,
} from "../app/lib/live-api.mjs";

const runId = "R".repeat(24);
const candidate = {
  mode: "live",
  outcome: "candidate",
  title: "带来源QA候选",
  answer: "通过来源约束的答案。",
  obligations: ["绑定来源"],
  evidence: [{ id: "E1", source: "DOC · 章节", text: "证据原文" }],
  gates: [{ label: "来源绑定", pass: true }],
  note: "等待人工决定。",
  provider_call_count: 2,
};

function response(status, body) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

test("empty API base keeps same-origin relative URLs", () => {
  assert.equal(apiUrl("/api/v1/health"), "/api/v1/health");
  assert.equal(apiUrl("/api/v1/health", "https://api.example/"), "https://api.example/api/v1/health");
});

test("health distinguishes available, replay-only, and unknown", async () => {
  assert.equal(parseHealth({ status: "ok", live_experience: "available" }), "available");
  assert.equal(parseHealth({ status: "ok", live_experience: "replay_only" }), "unavailable");
  assert.equal(parseHealth({ status: "ok", live_experience: true }), "unknown");
  const unknown = await checkLiveAvailability({ fetchImpl: async () => { throw new Error("offline"); } });
  assert.deepEqual(unknown, { state: "unknown", reason: "health_connection_failed" });
});

test("preset live run posts preset mode and preserves terminal provenance", async () => {
  const calls = [];
  const replies = [
    response(202, { run_id: runId, status: "queued", estimated_wait_seconds: 120 }),
    response(200, { run_id: runId, status: "retrieving" }),
    response(200, { run_id: runId, status: "completed", result: candidate }),
  ];
  const statuses = [];
  const result = await requestLiveRun({
    taskType: "qa",
    inputMode: "preset",
    text: "CZ-R1 怎么开始局部清扫？",
    productModel: "CZ-R1",
    fetchImpl: async (url, init) => {
      calls.push({ url, init });
      return replies.shift();
    },
    delayImpl: async () => {},
    onStatus: (status) => statuses.push(status),
  });
  assert.equal(result.kind, "terminal");
  assert.equal(result.result.mode, "live");
  assert.deepEqual(statuses, ["queued", "retrieving", "completed"]);
  assert.equal(JSON.parse(calls[0].init.body).input_mode, "preset");
  assert.equal(calls.filter((call) => call.init.method === "POST").length, 1);
});

test("handoff cannot be relabeled as LIVE MODEL", async () => {
  const invalidHandoff = { ...candidate, mode: "live", outcome: "handoff" };
  const statuses = [];
  const result = await pollLiveRun({
    runId,
    fetchImpl: async () => response(200, { run_id: runId, status: "handoff", result: invalidHandoff }),
    delayImpl: async () => {},
    onStatus: (status) => statuses.push(status),
  });
  assert.deepEqual(result, { kind: "protocol_error", runId, reason: "terminal_result_invalid" });
  assert.deepEqual(statuses, []);
});

test("240-second observation timeout keeps run id and never resubmits", async () => {
  let now = 0;
  let postCount = 0;
  const result = await requestLiveRun({
    taskType: "qa",
    inputMode: "free_text",
    text: "CZ-R1 如何回充？",
    productModel: "CZ-R1",
    fetchImpl: async (_url, init) => {
      if (init.method === "POST") {
        postCount += 1;
        return response(202, { run_id: runId, status: "queued", estimated_wait_seconds: 120 });
      }
      return response(200, { run_id: runId, status: "queued" });
    },
    nowImpl: () => now,
    delayImpl: async (milliseconds) => { now += milliseconds; },
    pollWindowMs: 240_000,
    pollIntervalMs: 60_000,
  });
  assert.deepEqual(result, { kind: "timeout", runId });
  assert.equal(postCount, 1);
});

test("explicit replay-capable refusal is unavailable, not a fake terminal run", async () => {
  const result = await requestLiveRun({
    taskType: "qa",
    inputMode: "preset",
    text: "CZ-R1 如何回充？",
    productModel: "CZ-R1",
    fetchImpl: async () => response(503, {
      error: { code: "live_experience_unavailable", replay_available: true },
    }),
  });
  assert.deepEqual(result, { kind: "unavailable", reason: "live_experience_unavailable" });
});

test("human decision posts once with edited text", async () => {
  const calls = [];
  const result = await submitHumanDecision({
    runId,
    decision: "edit",
    decisionText: "编辑后的正文",
    fetchImpl: async (url, init) => {
      calls.push({ url, init });
      return response(200, { status: "recorded", decision: "edit" });
    },
  });
  assert.deepEqual(result, { ok: true });
  assert.equal(calls.length, 1);
  assert.deepEqual(JSON.parse(calls[0].init.body), {
    decision: "edit",
    decision_text: "编辑后的正文",
  });
});
