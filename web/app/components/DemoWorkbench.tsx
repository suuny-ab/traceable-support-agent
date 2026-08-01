"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import {
  DemoMode,
  DemoResult,
  LiveCase,
  liveCases,
  replayPresets,
  suggestedQuestions,
} from "../lib/demo-data";
import {
  checkLiveAvailability,
  pollLiveRun,
  requestLiveRun,
  submitHumanDecision,
} from "../lib/live-api.mjs";
import { selectRunRoute } from "../lib/replay-routing.mjs";
import { revealResultPanel } from "../lib/result-visibility.mjs";

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
      answer: "额度、队列或实时开关阻止了这次运行。系统没有用预设答案替换输入；你仍可查看已验证回放。",
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

function providerCallCopy(result: DemoResult): string {
  if (result.mode === "verified_replay") return "回放不调用模型";
  const count = result.provider_call_count;
  if (typeof count === "number") {
    return count === 0 ? "0 次 · 模型调用前停止" : `${count} 次 · 零自动重试`;
  }
  return "未知";
}

export function DemoWorkbench() {
  const operationRef = useRef(0);
  const outputRef = useRef<HTMLElement>(null);
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
  const [freeTaskType, setFreeTaskType] = useState<DemoMode>("qa");
  const [freeModel, setFreeModel] = useState<"CZ-R1" | "CZ-R2">("CZ-R1");
  const [freeInput, setFreeInput] = useState("");
  const freeCount = useMemo(() => Array.from(freeInput).length, [freeInput]);
  const inputLocked = running || decisionState === "submitting";
  const liveReady = availability === "available";
  const visibleSuggestions = suggestedQuestions.filter((item) => item.taskType === freeTaskType);
  const recommendedLiveCase = liveCases[0];
  const additionalLiveCases = liveCases.slice(1);
  const recommendedReplay = replayPresets[0];

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

  function revealOutput() {
    window.requestAnimationFrame(() => revealResultPanel(outputRef.current));
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

  async function startLiveRun({ taskType, inputMode, text, productModel }: {
    taskType: DemoMode;
    inputMode: "preset" | "free_text";
    text: string;
    productModel: "CZ-R1" | "CZ-R2";
  }) {
    const operation = ++operationRef.current;
    setRunning(true);
    clearRun();
    revealOutput();
    const outcome = await requestLiveRun({
      taskType,
      inputMode,
      text,
      productModel,
      baseUrl: API_BASE,
      onStatus: (status) => {
        if (operation === operationRef.current) showLiveStatus(status);
      },
    });
    if (operation !== operationRef.current) return;
    applyLiveOutcome(outcome);
    setRunning(false);
  }

  async function runCase(liveCase: LiveCase) {
    if (inputLocked) return;
    const route = selectRunRoute({
      availability,
      preflightOnly: liveCase.kind === "boundary",
    });
    if (route !== "live") return;
    await startLiveRun({
      taskType: liveCase.taskType,
      inputMode: "preset",
      text: liveCase.input,
      productModel: liveCase.model,
    });
  }

  async function submitFree() {
    const text = freeInput.trim();
    if (inputLocked || !text || freeCount > 500 || !liveReady) return;
    if (freeTaskType === "ticket" && Array.from(text).length < 8) return;
    await startLiveRun({
      taskType: freeTaskType,
      inputMode: "free_text",
      text,
      productModel: freeModel,
    });
  }

  async function showReplay(presetId: string) {
    if (inputLocked) return;
    const preset = replayPresets.find((item) => item.id === presetId);
    if (!preset) return;
    const operation = ++operationRef.current;
    setRunning(true);
    clearRun();
    revealOutput();
    const stopIndex = preset.stopStageIndex ?? stageNames.length - 1;
    for (let index = 0; index <= stopIndex; index += 1) {
      if (operation !== operationRef.current) return;
      setTrace(stageNames.map((_, itemIndex) => itemIndex < index ? "pass" : itemIndex === index ? "run" : "wait"));
      await delay(180);
    }
    if (operation !== operationRef.current) return;
    setTrace(preset.result.outcome === "handoff"
      ? stageNames.map((_, index) => index < stopIndex ? "pass" : index === stopIndex ? "stop" : "wait")
      : stageNames.map(() => "pass"));
    setResult(preset.result);
    setRunning(false);
  }

  async function continuePolling() {
    if (!runId || running) return;
    const operation = ++operationRef.current;
    setRunning(true);
    setCanContinue(false);
    revealOutput();
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

  function applySuggestion(text: string, model: "CZ-R1" | "CZ-R2") {
    if (inputLocked) return;
    operationRef.current += 1;
    setFreeInput(text);
    setFreeModel(model);
    clearRun();
  }

  function startRecommended() {
    if (inputLocked || availability === "checking") return;
    if (liveReady && recommendedLiveCase) {
      void runCase(recommendedLiveCase);
      return;
    }
    if (recommendedReplay) void showReplay(recommendedReplay.id);
  }

  const availabilityCopy = availability === "checking"
    ? "正在检测实时服务"
    : availability === "available"
      ? "实时体验可用 · 点击后创建新的运行"
      : availability === "unavailable"
        ? "实时服务不可用 · 推荐案例将打开已验证回放"
        : "实时状态未知 · 推荐案例将打开已验证回放";
  const freeTooShort = freeTaskType === "ticket" && freeInput.trim().length > 0 && Array.from(freeInput.trim()).length < 8;
  const canSubmitFree = !inputLocked && liveReady && Boolean(freeInput.trim()) && freeCount <= 500 && !freeTooShort;

  return (
    <div className="workbench">
      <div className="live-status" role="status">
        <span className={`live-dot live-${availability}`} aria-hidden="true" />
        <strong>{availabilityCopy}</strong>
        {availabilityReason && <code>{availabilityReason}</code>}
        <button type="button" onClick={refreshAvailability} disabled={availability === "checking" || inputLocked}>重新检测</button>
      </div>

      <div className="guided-grid">
        <section className="guided-case" aria-labelledby="guided-case-title">
          <div className="guided-case-kicker"><span>01</span> 推荐案例 · 约 30 秒</div>
          <h2 id="guided-case-title">CZ-R1 局部清扫</h2>
          <p className="guided-question">{recommendedLiveCase?.input}</p>
          <button className="guided-run-button" type="button" disabled={inputLocked || availability === "checking"} onClick={startRecommended}>
            {availability === "checking" ? "正在确认实时状态…" : liveReady ? "运行推荐案例" : "查看已验证回放"}<span>→</span>
          </button>
          <small className="guided-boundary">{liveReady ? "将创建一次新的真实运行；自动重试为 0。" : "实时不可用，不会用回放冒充新运行。"}</small>
          <p className="guided-summary">不用先理解所有设置。运行后按顺序查看四件事：</p>
          <ol className="guided-proof-list">
            <li><span>1</span>客户可见回答</li>
            <li><span>2</span>绑定的批准来源</li>
            <li><span>3</span>质量门检查结果</li>
            <li><span>4</span>等待人工决定</li>
          </ol>
        </section>

        <section ref={outputRef} className="output-panel guided-output" aria-live="polite" aria-label="运行结果" tabIndex={-1}>
          <div className="panel-heading"><span>RUN RESULT</span><strong>{result ? result.title : "等待推荐案例"}</strong></div>
          {runId && <div className="run-id"><span>RUN ID</span><code>{runId}</code>{canContinue && <button type="button" disabled={running} onClick={continuePolling}>继续查询同一运行</button>}</div>}
          <ol className="progress-list">
            {stageNames.map((name, index) => <li className={`trace-${trace[index]}`} key={name}><b>{String(index + 1).padStart(2, "0")}</b><span>{name}</span><em>{trace[index].toUpperCase()}</em></li>)}
          </ol>
          {!result && <div className="result-placeholder"><strong>点击左侧按钮开始</strong><p>结果会在这里依次展示回答、来源、质量门和人工决定，而不是只给出一个无法检查的答案。</p></div>}
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

      <details className="experience-options">
        <summary><span>更多体验</span><strong>其他实时案例、自由提问与已验证回放</strong><em>展开</em></summary>
        <div className="input-panel experience-options-content" aria-label="更多运行输入">
          <div className="panel-heading"><span>MORE LIVE CASES</span><strong>其他案例 · 每次创建新运行</strong></div>
          <div className="case-list">
            {additionalLiveCases.map((liveCase) => {
              const runnable = selectRunRoute({ availability, preflightOnly: liveCase.kind === "boundary" }) === "live";
              return (
                <article className={`case-card${liveCase.kind === "boundary" ? " case-boundary" : ""}`} key={liveCase.id}>
                  <div className="case-card-head">
                    <span>{liveCase.label}{liveCase.caseId ? ` · ${liveCase.caseId}` : ""}</span>
                    <code>{liveCase.model}</code>
                  </div>
                  <p className="case-question">{liveCase.input}</p>
                  <p className="case-summary">{liveCase.summary}</p>
                  <button
                    type="button"
                    disabled={inputLocked || !runnable}
                    onClick={() => runCase(liveCase)}
                  >
                    {running ? "正在运行…" : "创建新运行"}
                  </button>
                </article>
              );
            })}
          </div>

          <div className="free-explore">
            <div className="panel-heading"><span>FREE EXPLORATION</span><strong>受约束自由探索</strong></div>
            <div className="workbench-tabs free-tabs" role="tablist" aria-label="自由探索类型">
              <button role="tab" aria-selected={freeTaskType === "qa"} disabled={inputLocked} onClick={() => { if (!inputLocked) { operationRef.current += 1; setFreeTaskType("qa"); clearRun(); } }}>QA 带来源问答</button>
              <button role="tab" aria-selected={freeTaskType === "ticket"} disabled={inputLocked} onClick={() => { if (!inputLocked) { operationRef.current += 1; setFreeTaskType("ticket"); clearRun(); } }}>工单处理建议</button>
            </div>
            <div className="suggestion-chips" aria-label="推荐问法">
              {visibleSuggestions.map((item) => (
                <button type="button" key={item.text} disabled={inputLocked} onClick={() => applySuggestion(item.text, item.model)}>{item.text}</button>
              ))}
            </div>
            <label htmlFor="free-model">产品型号</label>
            <select id="free-model" value={freeModel} disabled={inputLocked} onChange={(event) => { operationRef.current += 1; setFreeModel(event.target.value as "CZ-R1" | "CZ-R2"); clearRun(); }}>
              <option value="CZ-R1">CZ-R1</option><option value="CZ-R2">CZ-R2</option>
            </select>
            <label htmlFor="free-input">合成问题或工单（限虚构 CZ-R1 / CZ-R2 支持范围）</label>
            <textarea id="free-input" maxLength={500} value={freeInput} disabled={inputLocked} placeholder="输入一个合成客服问题，或点击上方推荐问法。" onChange={(event) => { operationRef.current += 1; setFreeInput(event.target.value); clearRun(); }} />
            <div className="input-meta">
              <span className={freeCount > 500 ? "danger-text" : ""}>{freeCount} / 500</span>
              <span>请勿输入个人信息、公司机密或生产数据{freeTaskType === "ticket" ? "；工单至少 8 字" : ""}</span>
            </div>
            <button className="run-button" type="button" disabled={!canSubmitFree} onClick={submitFree}>
              {running ? "正在运行检查链…" : liveReady ? "创建新运行" : "实时服务不可用，不能创建新运行"}<span>→</span>
            </button>
            <p className="input-boundary">每次运行最多 2 次模型调用、自动重试 0；敏感、越界或证据不足的输入在模型调用前失败关闭。</p>
          </div>

          <div className="replay-section">
            <div className="panel-heading"><span>VERIFIED REPLAY</span><strong>已验证回放 · 不创建新运行</strong></div>
            <p className="replay-hint">已验证回放不调用模型，也绝不冒充本次运行。</p>
            <ul className="replay-list">
              {replayPresets.map((preset) => (
                <li key={preset.id}>
                  <span>{preset.label}{preset.caseId ? ` · ${preset.caseId}` : ""}</span>
                  <button type="button" disabled={inputLocked} onClick={() => showReplay(preset.id)}>查看回放</button>
                </li>
              ))}
            </ul>
            <p className="input-boundary">运行边界：普通运行不可用时不会创建。唯一的例外是固定边界挑战 GEN-DEV-IE-001；实时不可用时，它仍会创建一次 Provider 调用为 0 的确定性转人工运行。</p>
          </div>
        </div>
      </details>
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
      <div className="run-meta">
        <span className={`mode-badge ${result.outcome === "handoff" ? "badge-handoff" : ""}`}>{modeLabel}</span>
        <span className="provider-calls">Provider 调用：{providerCallCopy(result)}</span>
        {result.handoff_reason && <code className="handoff-reason">handoff: {result.handoff_reason}</code>}
      </div>
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
