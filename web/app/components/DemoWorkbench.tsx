"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { DemoMode, DemoResult, examples } from "../lib/demo-data";
import {
  checkLiveAvailability,
  pollLiveRun,
  requestLiveRun,
  submitHumanDecision,
} from "../lib/live-api.mjs";
import { selectRunRoute } from "../lib/replay-routing.mjs";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ?? "";
const stageNames = ["检索证据", "规划义务", "生成候选", "执行质量门"];
type TraceState = "wait" | "run" | "pass" | "stop";
type LiveAvailability = "checking" | "available" | "unavailable" | "unknown";
type Decision = "approve" | "edit" | "reject";
type DecisionState = "idle" | "editing" | "submitting" | "recorded" | "failed";

function emptyTrace(): TraceState[] {
  return stageNames.map(() => "wait");
}

function delay(milliseconds: number) {
  return new Promise((resolve) => window.setTimeout(resolve, milliseconds));
}

function uncertainResult(kind: string, reason: string): DemoResult {
  if (kind === "unavailable") {
    return {
      mode: "handoff",
      outcome: "handoff",
      title: "实时体验当前未接收运行",
      answer: "额度、队列或实时开关阻止了这次运行。系统没有用预设答案替换自由输入；你仍可查看已验证回放。",
      obligations: ["在调用前检查预算与容量", "不伪造实时生成", "保留回放降级"],
      evidence: [],
      gates: [{ label: "运行准入", pass: false }, { label: "失败关闭", pass: true }],
      note: `后端明确拒绝创建本次运行（${reason}）；页面没有自动重试。`,
    };
  }
  if (kind === "timeout") {
    return {
      mode: "handoff",
      outcome: "handoff",
      title: "240 秒观察窗口已结束",
      answer: "当前结果仍然未知。页面没有重新提交请求，避免重复调用和重复费用；可以继续查询同一个 run。",
      obligations: ["保留原 run_id", "不自动重提", "不把超时包装成失败或成功"],
      evidence: [],
      gates: [{ label: "观察窗口", pass: false }, { label: "零自动重试", pass: true }],
      note: "超时只表示浏览器停止轮询，不证明后端已经停止，也不证明 Provider 是否调用。",
    };
  }
  return {
    mode: "handoff",
    outcome: "handoff",
    title: "连接中断，运行状态未知",
    answer: "页面无法证明本次运行是否创建或完成，因此没有展示候选，也没有自动重试。预设回放仍可独立查看。",
    obligations: ["不推断 Provider 调用状态", "不自动重提", "未知结果不冒充转人工完成态"],
    evidence: [],
    gates: [{ label: "状态合同", pass: false }, { label: "失败关闭", pass: true }],
    note: `运行状态未知（${reason}）。这不等于“没有调用模型”。`,
  };
}

export function DemoWorkbench() {
  const initialExample = examples.qa[0];
  const operationRef = useRef(0);
  const [mode, setMode] = useState<DemoMode>("qa");
  const [selectedPresetId, setSelectedPresetId] = useState(initialExample.id);
  const [input, setInput] = useState(initialExample.input);
  const [model, setModel] = useState<"CZ-R1" | "CZ-R2">(initialExample.model);
  const [trace, setTrace] = useState<TraceState[]>(emptyTrace);
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<DemoResult | null>(null);
  const [runId, setRunId] = useState<string | null>(null);
  const [canContinue, setCanContinue] = useState(false);
  const [availability, setAvailability] = useState<LiveAvailability>("checking");
  const [availabilityReason, setAvailabilityReason] = useState<string | null>(null);
  const [decision, setDecision] = useState<Decision | null>(null);
  const [decisionState, setDecisionState] = useState<DecisionState>("idle");
  const [decisionText, setDecisionText] = useState("");
  const modeExamples = examples[mode];
  const selectedExample = modeExamples.find((example) => example.id === selectedPresetId) ?? modeExamples[0];
  const isPreset = input.trim() === selectedExample.input && model === selectedExample.model;
  const inputCount = useMemo(() => Array.from(input).length, [input]);
  const inputLocked = running || decisionState === "submitting";

  useEffect(() => {
    let active = true;
    checkLiveAvailability({ baseUrl: API_BASE }).then((receipt) => {
      if (!active) return;
      setAvailability(receipt.state as LiveAvailability);
      setAvailabilityReason(receipt.reason);
    });
    return () => { active = false; };
  }, []);

  function clearRun() {
    setResult(null);
    setRunId(null);
    setCanContinue(false);
    setDecision(null);
    setDecisionState("idle");
    setDecisionText("");
    setTrace(emptyTrace());
  }

  function changeMode(next: DemoMode) {
    if (inputLocked) return;
    operationRef.current += 1;
    const nextExample = examples[next][0];
    setMode(next);
    setSelectedPresetId(nextExample.id);
    setInput(nextExample.input);
    setModel(nextExample.model);
    clearRun();
  }

  function changePreset(presetId: string) {
    if (inputLocked) return;
    const nextExample = modeExamples.find((example) => example.id === presetId);
    if (!nextExample) return;
    operationRef.current += 1;
    setSelectedPresetId(nextExample.id);
    setInput(nextExample.input);
    setModel(nextExample.model);
    clearRun();
  }

  function resetExample() {
    if (inputLocked) return;
    operationRef.current += 1;
    setInput(selectedExample.input);
    setModel(selectedExample.model);
    clearRun();
  }

  async function refreshAvailability() {
    setAvailability("checking");
    setAvailabilityReason(null);
    const receipt = await checkLiveAvailability({ baseUrl: API_BASE });
    setAvailability(receipt.state as LiveAvailability);
    setAvailabilityReason(receipt.reason);
  }

  function showLiveStatus(status: string) {
    const activeIndex = status === "retrieving" ? 0 : status === "planning" ? 1 : status === "generating" ? 2 : status === "validating" ? 3 : -1;
    if (status === "completed") {
      setTrace(stageNames.map(() => "pass"));
      return;
    }
    if (status === "handoff") {
      setTrace((current) => current.map((item, index) =>
        item === "run" || (index === 0 && current.every((value) => value === "wait")) ? "stop" : item));
      return;
    }
    if (activeIndex >= 0) {
      setTrace(stageNames.map((_, index) => index < activeIndex ? "pass" : index === activeIndex ? "run" : "wait"));
    }
  }

  async function showReplay() {
    if (running || !isPreset) return;
    const operation = ++operationRef.current;
    setRunning(true);
    clearRun();
    const stopIndex = selectedExample.stopStageIndex ?? stageNames.length - 1;
    for (let index = 0; index <= stopIndex; index += 1) {
      if (operation !== operationRef.current) return;
      setTrace(stageNames.map((_, itemIndex) => itemIndex < index ? "pass" : itemIndex === index ? "run" : "wait"));
      await delay(180);
    }
    if (operation !== operationRef.current) return;
    setTrace(selectedExample.result.outcome === "handoff"
      ? stageNames.map((_, index) => index < stopIndex ? "pass" : index === stopIndex ? "stop" : "wait")
      : stageNames.map(() => "pass"));
    setResult(selectedExample.result);
    setRunning(false);
  }

  function applyLiveOutcome(outcome: Awaited<ReturnType<typeof requestLiveRun>>) {
    if (outcome.kind === "terminal") {
      setRunId(outcome.runId);
      setResult(outcome.result as DemoResult);
      setCanContinue(false);
      return;
    }
    const nextRunId = "runId" in outcome && typeof outcome.runId === "string" ? outcome.runId : null;
    setRunId(nextRunId);
    setCanContinue(Boolean(nextRunId) && (outcome.kind === "timeout" || outcome.kind === "protocol_error"));
    setResult(uncertainResult(outcome.kind, "reason" in outcome ? outcome.reason : "poll_timeout"));
    setTrace((current) => {
      const activeIndex = current.indexOf("run");
      const stopIndex = activeIndex >= 0 ? activeIndex : stageNames.length - 1;
      return current.map((item, index) => index === stopIndex ? "stop" : item);
    });
  }

  async function run() {
    if (running || !input.trim() || inputCount > 500) return;
    const route = selectRunRoute({
      availability,
      isPreset,
      replayOnly: selectedExample.replayOnly,
    });
    if (route === "replay") {
      await showReplay();
      return;
    }
    if (route === "blocked") {
      return;
    }
    const operation = ++operationRef.current;
    setRunning(true);
    clearRun();
    const outcome = await requestLiveRun({
      taskType: mode,
      inputMode: isPreset ? "preset" : "free_text",
      text: input.trim(),
      productModel: model,
      baseUrl: API_BASE,
      onStatus: (status) => {
        if (operation === operationRef.current) showLiveStatus(status);
      },
    });
    if (operation !== operationRef.current) return;
    applyLiveOutcome(outcome);
    setRunning(false);
  }

  async function continuePolling() {
    if (!runId || running) return;
    const operation = ++operationRef.current;
    setRunning(true);
    setCanContinue(false);
    const outcome = await pollLiveRun({
      runId,
      baseUrl: API_BASE,
      onStatus: (status) => {
        if (operation === operationRef.current) showLiveStatus(status);
      },
    });
    if (operation !== operationRef.current) return;
    applyLiveOutcome(outcome);
    setRunning(false);
  }

  async function chooseDecision(next: Decision) {
    if (!result || result.outcome !== "candidate" || decisionState === "submitting" || decisionState === "recorded") return;
    setDecision(next);
    if (next === "edit") {
      setDecisionText(result.answer);
      setDecisionState("editing");
      return;
    }
    if (!runId) {
      setDecisionState("recorded");
      return;
    }
    const operation = ++operationRef.current;
    setDecisionState("submitting");
    const receipt = await submitHumanDecision({ runId, decision: next, baseUrl: API_BASE });
    if (operation !== operationRef.current) return;
    setDecisionState(receipt.ok ? "recorded" : "failed");
  }

  async function submitEdit() {
    if (decision !== "edit" || !decisionText.trim() || decisionState === "submitting") return;
    if (!runId) {
      setDecisionState("recorded");
      return;
    }
    const operation = ++operationRef.current;
    setDecisionState("submitting");
    const receipt = await submitHumanDecision({
      runId,
      decision: "edit",
      decisionText: decisionText.trim(),
      baseUrl: API_BASE,
    });
    if (operation !== operationRef.current) return;
    setDecisionState(receipt.ok ? "recorded" : "failed");
  }

  const availabilityCopy = availability === "checking"
    ? "正在检测实时服务"
    : availability === "available"
      ? "实时体验可用"
      : availability === "unavailable"
        ? "实时调用关闭 · 回放可用"
        : "实时状态未知 · 回放可用";
  const selectedRoute = selectRunRoute({
    availability,
    isPreset,
    replayOnly: selectedExample.replayOnly,
  });
  const canRunPrimary = !inputLocked && Boolean(input.trim()) && inputCount <= 500 && selectedRoute !== "blocked";

  return (
    <div className="workbench">
      <div className="workbench-tabs" role="tablist" aria-label="体验类型">
        <button role="tab" aria-selected={mode === "qa"} disabled={inputLocked} onClick={() => changeMode("qa")}>QA 带来源问答</button>
        <button role="tab" aria-selected={mode === "ticket"} disabled={inputLocked} onClick={() => changeMode("ticket")}>工单处理建议</button>
      </div>

      <div className="live-status" role="status">
        <span className={`live-dot live-${availability}`} aria-hidden="true" />
        <strong>{availabilityCopy}</strong>
        {availabilityReason && <code>{availabilityReason}</code>}
        <button type="button" onClick={refreshAvailability} disabled={availability === "checking" || inputLocked}>重新检测</button>
      </div>

      <div className="workbench-grid">
        <section className="input-panel" aria-label="体验输入">
          <div className="panel-heading"><span>INPUT CONTRACT</span><strong>{mode === "qa" ? "提问" : "工单描述"}</strong></div>
          <label htmlFor="product-model">产品型号</label>
          <select id="product-model" value={model} disabled={inputLocked} onChange={(event) => { operationRef.current += 1; setModel(event.target.value as "CZ-R1" | "CZ-R2"); clearRun(); }}>
            <option value="CZ-R1">CZ-R1</option><option value="CZ-R2">CZ-R2</option>
          </select>
          <label htmlFor="demo-preset">已验证预设</label>
          <select id="demo-preset" value={selectedExample.id} disabled={inputLocked} onChange={(event) => changePreset(event.target.value)}>
            {modeExamples.map((example) => <option value={example.id} key={example.id}>{example.label}{example.caseId ? ` · ${example.caseId}` : ""}</option>)}
          </select>
          <div className="preset-line"><span>当前预设：{selectedExample.label}{selectedExample.caseId ? ` · ${selectedExample.caseId}` : ""}</span><button type="button" disabled={inputLocked} onClick={resetExample}>恢复预设</button></div>
          <label htmlFor="demo-input">合成问题或工单</label>
          <textarea id="demo-input" maxLength={500} value={input} disabled={inputLocked} onChange={(event) => { operationRef.current += 1; setInput(event.target.value); clearRun(); }} />
          <div className="input-meta"><span className={inputCount > 500 ? "danger-text" : ""}>{inputCount} / 500</span><span>请勿输入个人信息、公司机密或生产数据</span></div>
          <button className="run-button" type="button" disabled={!canRunPrimary} onClick={run}>
            {running ? "正在运行检查链…" : selectedRoute === "live" ? "运行实时模型" : selectedRoute === "replay" ? "运行已验证回放" : "实时服务尚未确认"}<span>→</span>
          </button>
          {selectedRoute === "live" && isPreset && <button className="replay-button" type="button" disabled={running} onClick={showReplay}>不调用模型，查看已验证回放</button>}
          <p className="input-boundary">实时路径最多两次 Provider 请求且零自动重试；回放路径不调用模型。两者在结果标签中明确区分。</p>
        </section>

        <section className="output-panel" aria-live="polite" aria-label="运行结果">
          <div className="panel-heading"><span>RUN TRACE</span><strong>{result ? result.title : "等待运行"}</strong></div>
          {runId && <div className="run-id"><span>RUN ID</span><code>{runId}</code>{canContinue && <button type="button" disabled={running} onClick={continuePolling}>继续查询同一运行</button>}</div>}
          <ol className="progress-list">
            {stageNames.map((name, index) => <li className={`trace-${trace[index]}`} key={name}><b>{String(index + 1).padStart(2, "0")}</b><span>{name}</span><em>{trace[index].toUpperCase()}</em></li>)}
          </ol>
          {!result && <div className="result-placeholder"><strong>选择真实运行或已验证回放</strong><p>结果会展示客户可见正文、证据、义务和机械门，而不是只有一个答案框。</p></div>}
          {result && <ResultView
            result={result}
            runId={runId}
            decision={decision}
            decisionState={decisionState}
            decisionText={decisionText}
            onDecision={chooseDecision}
            onDecisionText={setDecisionText}
            onSubmitEdit={submitEdit}
          />}
        </section>
      </div>
    </div>
  );
}

function ResultView({
  result,
  runId,
  decision,
  decisionState,
  decisionText,
  onDecision,
  onDecisionText,
  onSubmitEdit,
}: {
  result: DemoResult;
  runId: string | null;
  decision: Decision | null;
  decisionState: DecisionState;
  decisionText: string;
  onDecision: (value: Decision) => void;
  onDecisionText: (value: string) => void;
  onSubmitEdit: () => void;
}) {
  const decisionLocked = decisionState === "submitting" || decisionState === "recorded";
  const modeLabel = result.mode === "live"
    ? "LIVE MODEL"
    : result.mode === "verified_replay"
      ? result.outcome === "handoff" ? "VERIFIED REPLAY · HANDOFF" : "VERIFIED REPLAY"
      : "HONEST HANDOFF";
  return (
    <div className="result-view">
      <div className={`mode-badge ${result.outcome === "handoff" ? "badge-handoff" : ""}`}>{modeLabel}</div>
      <div className="answer-card"><span>CUSTOMER-VISIBLE RESULT</span><p>{result.answer}</p></div>
      {result.actionSteps && <div className="result-block"><h3>处理步骤</h3><ol>{result.actionSteps.map((item) => <li key={item}>{item}</li>)}</ol></div>}
      <div className="result-columns">
        <div className="result-block"><h3>义务清单</h3><ul>{result.obligations.map((item) => <li key={item}>{item}</li>)}</ul></div>
        <div className="result-block"><h3>机械门</h3><ul className="gate-list">{result.gates.map((gate) => <li key={gate.label}><span>{gate.label}</span><b className={gate.pass ? "gate-pass" : "gate-fail"}>{gate.pass ? "PASS" : "STOP"}</b></li>)}</ul></div>
      </div>
      {result.evidence.length > 0 && <div className="result-block"><h3>批准来源</h3>{result.evidence.map((item) => <blockquote key={item.id}><code>{item.id}</code><strong>{item.source}</strong><p>{item.text}</p></blockquote>)}</div>}
      <p className="result-note">{result.note}</p>
      {result.outcome === "candidate" && <>
        <div className="decision-row" aria-label="人工决定">
          {([ ["approve", "批准"], ["edit", "编辑后批准"], ["reject", "拒绝"] ] as Array<[Decision, string]>).map(([value, label]) =>
            <button className={decision === value ? "selected" : ""} disabled={decisionLocked} type="button" key={value} onClick={() => onDecision(value)}>{label}</button>)}
        </div>
        {decision === "edit" && decisionState !== "recorded" && <div className="decision-editor">
          <label htmlFor="decision-edit">编辑后的客户可见正文</label>
          <textarea id="decision-edit" maxLength={1000} value={decisionText} onChange={(event) => onDecisionText(event.target.value)} />
          <button type="button" disabled={!decisionText.trim() || decisionState === "submitting"} onClick={onSubmitEdit}>{decisionState === "submitting" ? "正在记录…" : "提交编辑后批准"}</button>
        </div>}
      </>}
      {decisionState === "recorded" && <p className="decision-note">{runId ? "服务器已记录人工决定。" : "仅在当前页面完成回放演练。"}未发送回复，也未改变任何外部工单。</p>}
      {decisionState === "failed" && <p className="decision-note decision-failed">人工决定未能写入服务器，请勿把它视为已记录。</p>}
    </div>
  );
}
