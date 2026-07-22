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

const presets = replayData.presets as unknown as DemoExample[];

export const examples: Record<DemoMode, readonly DemoExample[]> = {
  qa: presets.filter((preset) => preset.taskType === "qa"),
  ticket: presets.filter((preset) => preset.taskType === "ticket"),
};
