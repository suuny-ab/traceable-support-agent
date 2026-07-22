const RUN_ID_PATTERN = /^[A-Za-z0-9_-]{20,100}$/;
const ACTIVE_STATUSES = new Set([
  "queued",
  "retrieving",
  "planning",
  "generating",
  "validating",
]);
const TERMINAL_STATUSES = new Set(["completed", "handoff"]);

export function apiUrl(path, baseUrl = "") {
  return `${baseUrl.replace(/\/$/, "")}${path}`;
}

function isObject(value) {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

async function safeJson(response) {
  try {
    return await response.json();
  } catch {
    return null;
  }
}

export function parseHealth(value) {
  if (!isObject(value) || value.status !== "ok") return "unknown";
  if (value.live_experience === "available") return "available";
  if (value.live_experience === "replay_only") return "unavailable";
  return "unknown";
}

export async function checkLiveAvailability({ fetchImpl = globalThis.fetch, baseUrl = "" } = {}) {
  try {
    const response = await fetchImpl(apiUrl("/api/v1/health", baseUrl), {
      method: "GET",
      headers: { accept: "application/json" },
      cache: "no-store",
    });
    if (!response.ok) return { state: "unknown", reason: `health_http_${response.status}` };
    const state = parseHealth(await safeJson(response));
    return state === "unknown"
      ? { state, reason: "health_contract_invalid" }
      : { state, reason: null };
  } catch {
    return { state: "unknown", reason: "health_connection_failed" };
  }
}

export function isDemoResult(value) {
  if (!isObject(value)) return false;
  if (!["verified_replay", "live", "handoff"].includes(value.mode)) return false;
  if (!["candidate", "handoff"].includes(value.outcome)) return false;
  if (!["title", "answer", "note"].every((key) => typeof value[key] === "string")) return false;
  if (!Array.isArray(value.obligations) || !value.obligations.every((item) => typeof item === "string")) return false;
  if (!Array.isArray(value.evidence) || !value.evidence.every((item) =>
    isObject(item) && ["id", "source", "text"].every((key) => typeof item[key] === "string"))) return false;
  if (!Array.isArray(value.gates) || !value.gates.every((gate) =>
    isObject(gate) && typeof gate.label === "string" && typeof gate.pass === "boolean")) return false;
  if (value.actionSteps !== undefined &&
      (!Array.isArray(value.actionSteps) || !value.actionSteps.every((item) => typeof item === "string"))) return false;
  return true;
}

function terminalResult(status, result) {
  if (!isDemoResult(result)) return null;
  if (status === "completed" && (result.outcome !== "candidate" || result.mode !== "live")) return null;
  if (status === "handoff" && (result.outcome !== "handoff" || result.mode !== "handoff")) return null;
  return result;
}

export async function pollLiveRun({
  runId,
  fetchImpl = globalThis.fetch,
  delayImpl = (milliseconds) => new Promise((resolve) => globalThis.setTimeout(resolve, milliseconds)),
  nowImpl = () => Date.now(),
  baseUrl = "",
  onStatus = () => {},
  pollWindowMs = 240_000,
  pollIntervalMs = 2_500,
}) {
  if (!RUN_ID_PATTERN.test(runId)) return { kind: "protocol_error", reason: "run_id_invalid" };
  const deadline = nowImpl() + pollWindowMs;
  while (nowImpl() < deadline) {
    await delayImpl(pollIntervalMs);
    let response;
    try {
      response = await fetchImpl(apiUrl(`/api/v1/runs/${encodeURIComponent(runId)}`, baseUrl), {
        method: "GET",
        headers: { accept: "application/json" },
        cache: "no-store",
      });
    } catch {
      return { kind: "protocol_error", runId, reason: "run_status_connection_lost" };
    }
    if (!response.ok) return { kind: "protocol_error", runId, reason: `run_status_http_${response.status}` };
    const body = await safeJson(response);
    if (!isObject(body) || typeof body.status !== "string") {
      return { kind: "protocol_error", runId, reason: "run_status_contract_invalid" };
    }
    if (!ACTIVE_STATUSES.has(body.status) && !TERMINAL_STATUSES.has(body.status)) {
      return { kind: "protocol_error", runId, reason: "run_status_unknown" };
    }
    if (TERMINAL_STATUSES.has(body.status)) {
      const result = terminalResult(body.status, body.result);
      if (!result) return { kind: "protocol_error", runId, reason: "terminal_result_invalid" };
      onStatus(body.status);
      return { kind: "terminal", runId, status: body.status, result };
    }
    onStatus(body.status);
  }
  return { kind: "timeout", runId };
}

export async function requestLiveRun({
  taskType,
  inputMode,
  text,
  productModel,
  fetchImpl = globalThis.fetch,
  delayImpl,
  nowImpl,
  baseUrl = "",
  onStatus = () => {},
  pollWindowMs,
  pollIntervalMs,
}) {
  let response;
  try {
    response = await fetchImpl(apiUrl("/api/v1/runs", baseUrl), {
      method: "POST",
      headers: { "content-type": "application/json", accept: "application/json" },
      body: JSON.stringify({
        task_type: taskType,
        input_mode: inputMode,
        text,
        product_model: productModel,
        consent: true,
      }),
    });
  } catch {
    return { kind: "protocol_error", reason: "run_create_connection_failed" };
  }
  const body = await safeJson(response);
  if (!response.ok) {
    const error = isObject(body) && isObject(body.error) ? body.error : null;
    if (error && error.replay_available === true && typeof error.code === "string") {
      return { kind: "unavailable", reason: error.code };
    }
    return { kind: "protocol_error", reason: `run_create_http_${response.status}` };
  }
  if (!isObject(body) || typeof body.run_id !== "string" || !RUN_ID_PATTERN.test(body.run_id)) {
    return { kind: "protocol_error", reason: "run_create_contract_invalid" };
  }
  onStatus("queued");
  return pollLiveRun({
    runId: body.run_id,
    fetchImpl,
    delayImpl,
    nowImpl,
    baseUrl,
    onStatus,
    pollWindowMs,
    pollIntervalMs,
  });
}

export async function submitHumanDecision({
  runId,
  decision,
  decisionText = "",
  fetchImpl = globalThis.fetch,
  baseUrl = "",
}) {
  if (!RUN_ID_PATTERN.test(runId)) return { ok: false, reason: "run_id_invalid" };
  const payload = decision === "edit"
    ? { decision, decision_text: decisionText }
    : { decision };
  try {
    const response = await fetchImpl(
      apiUrl(`/api/v1/runs/${encodeURIComponent(runId)}/decision`, baseUrl),
      {
        method: "POST",
        headers: { "content-type": "application/json", accept: "application/json" },
        body: JSON.stringify(payload),
      },
    );
    const body = await safeJson(response);
    if (!response.ok || !isObject(body) || body.status !== "recorded" || body.decision !== decision) {
      return { ok: false, reason: `decision_http_${response.status}` };
    }
    return { ok: true };
  } catch {
    return { ok: false, reason: "decision_connection_failed" };
  }
}
