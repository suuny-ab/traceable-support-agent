export type LiveHealthState = "available" | "unavailable" | "unknown";

export interface ApiDemoResult {
  mode: "verified_replay" | "live" | "handoff";
  outcome: "candidate" | "handoff";
  title: string;
  answer: string;
  obligations: string[];
  evidence: Array<{ id: string; source: string; text: string }>;
  gates: Array<{ label: string; pass: boolean }>;
  note: string;
  actionSteps?: string[];
  handoff_reason?: string | null;
  handoff_type?: string | null;
  provider_call_count?: number | null;
}

export type RunOutcome =
  | { kind: "terminal"; runId: string; status: "completed" | "handoff"; result: ApiDemoResult }
  | { kind: "timeout"; runId: string }
  | { kind: "unavailable"; reason: string }
  | { kind: "protocol_error"; reason: string; runId?: string };

interface PollOptions {
  runId: string;
  fetchImpl?: typeof fetch;
  delayImpl?: (milliseconds: number) => Promise<void>;
  nowImpl?: () => number;
  baseUrl?: string;
  onStatus?: (status: string) => void;
  pollWindowMs?: number;
  pollIntervalMs?: number;
}

interface RequestOptions extends Omit<PollOptions, "runId"> {
  taskType: "qa" | "ticket";
  inputMode: "preset" | "free_text";
  text: string;
  productModel: "CZ-R1" | "CZ-R2";
}

export function apiUrl(path: string, baseUrl?: string): string;
export function parseHealth(value: unknown): LiveHealthState;
export function checkLiveAvailability(options?: {
  fetchImpl?: typeof fetch;
  baseUrl?: string;
}): Promise<{ state: LiveHealthState; reason: string | null }>;
export function isDemoResult(value: unknown): value is ApiDemoResult;
export function pollLiveRun(options: PollOptions): Promise<RunOutcome>;
export function requestLiveRun(options: RequestOptions): Promise<RunOutcome>;
export function submitHumanDecision(options: {
  runId: string;
  decision: "approve" | "edit" | "reject";
  decisionText?: string;
  fetchImpl?: typeof fetch;
  baseUrl?: string;
}): Promise<{ ok: boolean; reason?: string }>;
