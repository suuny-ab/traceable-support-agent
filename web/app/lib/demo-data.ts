import liveCaseData from "./live-cases.json";
import replayData from "./replay-presets.json";

export type DemoMode = "qa" | "ticket";

export type DemoResult = {
  mode: "verified_replay" | "live" | "handoff";
  outcome: "candidate" | "handoff";
  title: string;
  answer: string;
  actionSteps?: string[];
  obligations: string[];
  evidence: Array<{ id: string; source: string; text: string }>;
  gates: Array<{ label: string; pass: boolean }>;
  note: string;
  handoff_reason?: string;
  provider_call_count?: number;
};

export type DemoExample = {
  id: string;
  caseId?: string;
  taskType: DemoMode;
  label: string;
  model: "CZ-R1" | "CZ-R2";
  input: string;
  stopStageIndex?: number;
  replayOnly?: boolean;
  result: DemoResult;
};

export type LiveCase = {
  id: string;
  caseId?: string;
  kind: "default" | "boundary";
  taskType: DemoMode;
  label: string;
  model: "CZ-R1" | "CZ-R2";
  input: string;
  summary: string;
  replayPresetId?: string;
};

export type SuggestedQuestion = {
  taskType: DemoMode;
  model: "CZ-R1" | "CZ-R2";
  text: string;
};

export const replayPresets: readonly DemoExample[] =
  replayData.presets as unknown as DemoExample[];

/** Default live cases; every click creates a new run through the real chain. */
export const liveCases: readonly LiveCase[] =
  liveCaseData.cases as unknown as LiveCase[];

/** Recommended questions for the constrained free exploration, all inside the synthetic sandbox. */
export const suggestedQuestions: readonly SuggestedQuestion[] =
  liveCaseData.suggested_questions as unknown as SuggestedQuestion[];
