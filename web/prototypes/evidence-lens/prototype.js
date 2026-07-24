const canvas = document.querySelector("#evidence-lens");
const forcedReduced = new URLSearchParams(window.location.search).get("motion") === "reduce";
const forcedFallback = new URLSearchParams(window.location.search).get("fallback") === "1";
const motionQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
const compactQuery = window.matchMedia("(max-width: 760px)");

const state = {
  context: null,
  width: 0,
  height: 0,
  dpr: 1,
  frame: 0,
  startedAt: 0,
  visible: true,
  pageVisible: document.visibilityState === "visible",
  reduced: forcedReduced || motionQuery.matches,
  compact: compactQuery.matches,
  animationFrame: 0,
};

const word = "TRACEABLE";

function clamp(value, minimum, maximum) {
  return Math.min(maximum, Math.max(minimum, value));
}

function easeOutCubic(value) {
  return 1 - Math.pow(1 - clamp(value, 0, 1), 3);
}

function setPrototypeState(value) {
  document.documentElement.dataset.prototypeState = value;
}

function configureCanvas() {
  if (!canvas || forcedFallback) return false;
  const context = canvas.getContext("2d", { alpha: true });
  if (!context) return false;

  state.context = context;
  const bounds = canvas.getBoundingClientRect();
  state.width = Math.max(1, bounds.width);
  state.height = Math.max(1, bounds.height);
  state.dpr = Math.min(window.devicePixelRatio || 1, state.compact ? 1.35 : 1.7);
  canvas.width = Math.round(state.width * state.dpr);
  canvas.height = Math.round(state.height * state.dpr);
  context.setTransform(state.dpr, 0, 0, state.dpr, 0, 0);
  setPrototypeState(state.reduced ? "reduced" : "active");
  return true;
}

function lensGeometry(intro = 1) {
  const finalRadius = state.compact
    ? Math.min(state.width * 0.31, 125)
    : Math.min(state.width * 0.095, 120);
  const radius = Math.max(72, finalRadius * easeOutCubic(intro));
  return {
    centerX: state.width * 0.5,
    centerY: state.height * 0.51,
    radius,
  };
}

function typography() {
  return {
    size: state.compact
      ? clamp(state.width * 0.2, 68, 82)
      : clamp(state.width * 0.086, 88, 122),
    speed: state.compact ? 48 : 64,
  };
}

function prepareType(context, fontSize) {
  context.font = `760 ${fontSize}px "Segoe UI", "PingFang SC", Arial, sans-serif`;
  context.textBaseline = "middle";
  context.textAlign = "left";
  if ("letterSpacing" in context) context.letterSpacing = "-0.065em";
}

function drawRepeatedWord(context, elapsed, centerY, channelOffset = 0) {
  const { size, speed } = typography();
  prepareType(context, size);
  const wordWidth = Math.max(1, context.measureText(word).width);
  const gap = size * (state.compact ? 0.66 : 0.8);
  const cycle = wordWidth + gap;
  const travel = state.reduced ? cycle * 0.28 : ((elapsed * speed) / 1000) % cycle;
  let x = -cycle - travel + channelOffset;

  while (x < state.width + cycle * 2) {
    context.fillText(word, x, centerY);
    x += cycle;
  }
}

function drawBackground(intro) {
  const context = state.context;
  const { centerX, centerY, radius } = lensGeometry(intro);
  context.clearRect(0, 0, state.width, state.height);

  const ambient = context.createRadialGradient(
    centerX,
    centerY,
    radius * 0.2,
    centerX,
    centerY,
    radius * 2.6,
  );
  ambient.addColorStop(0, `rgba(255, 255, 255, ${0.025 * intro})`);
  ambient.addColorStop(0.52, `rgba(10, 13, 14, ${0.18 * intro})`);
  ambient.addColorStop(1, "rgba(3, 4, 5, 0)");
  context.fillStyle = ambient;
  context.fillRect(0, 0, state.width, state.height);
}

function drawRollingBand(elapsed, intro) {
  const context = state.context;
  const { centerY } = lensGeometry(intro);

  context.save();
  context.globalCompositeOperation = "screen";

  context.filter = `blur(${state.compact ? 2.5 : 3.6}px)`;
  context.globalAlpha = 0.34 * intro;
  context.fillStyle = "rgba(236, 240, 239, 0.78)";
  drawRepeatedWord(context, elapsed, centerY);

  context.filter = `blur(${state.compact ? 3 : 4.2}px)`;
  context.globalAlpha = 0.105 * intro;
  context.fillStyle = "rgba(85, 220, 228, 0.9)";
  drawRepeatedWord(context, elapsed, centerY, -4);

  context.globalAlpha = 0.09 * intro;
  context.fillStyle = "rgba(239, 157, 80, 0.88)";
  drawRepeatedWord(context, elapsed, centerY, 4);
  context.restore();
}

function drawLensInterior(elapsed, intro) {
  const context = state.context;
  const { centerX, centerY, radius } = lensGeometry(intro);

  context.save();
  context.beginPath();
  context.arc(centerX, centerY, radius, 0, Math.PI * 2);
  context.clip();

  const disc = context.createRadialGradient(
    centerX - radius * 0.24,
    centerY - radius * 0.18,
    radius * 0.08,
    centerX,
    centerY,
    radius,
  );
  disc.addColorStop(0, "rgba(10, 12, 13, 0.98)");
  disc.addColorStop(0.72, "rgba(3, 4, 5, 0.99)");
  disc.addColorStop(1, "rgba(0, 0, 0, 1)");
  context.fillStyle = disc;
  context.fillRect(centerX - radius, centerY - radius, radius * 2, radius * 2);

  const beam = context.createLinearGradient(
    centerX - radius,
    centerY,
    centerX + radius,
    centerY,
  );
  beam.addColorStop(0, "rgba(226, 244, 241, 0)");
  beam.addColorStop(0.42, `rgba(226, 244, 241, ${0.07 * intro})`);
  beam.addColorStop(0.5, `rgba(255, 255, 255, ${0.14 * intro})`);
  beam.addColorStop(0.58, `rgba(226, 244, 241, ${0.07 * intro})`);
  beam.addColorStop(1, "rgba(226, 244, 241, 0)");
  context.fillStyle = beam;
  context.fillRect(centerX - radius, centerY - radius * 0.22, radius * 2, radius * 0.44);

  const compression = state.compact ? 0.34 : 0.31;
  context.translate(centerX, centerY);
  context.scale(compression, 1);
  context.translate(-centerX, -centerY);

  context.globalCompositeOperation = "screen";
  context.filter = `blur(${state.compact ? 1.5 : 2}px)`;
  context.globalAlpha = 0.54 * intro;
  context.fillStyle = "rgba(238, 242, 241, 0.84)";
  drawRepeatedWord(context, elapsed, centerY);

  context.globalAlpha = 0.14 * intro;
  context.fillStyle = "rgba(85, 220, 228, 0.9)";
  drawRepeatedWord(context, elapsed, centerY, -5 / compression);
  context.fillStyle = "rgba(239, 157, 80, 0.8)";
  drawRepeatedWord(context, elapsed, centerY, 5 / compression);
  context.restore();

  drawScanlines(intro);
}

function drawScanlines(intro) {
  const context = state.context;
  const { centerX, centerY, radius } = lensGeometry(intro);
  context.save();
  context.beginPath();
  context.arc(centerX, centerY, radius, 0, Math.PI * 2);
  context.clip();
  context.globalAlpha = 0.08 * intro;
  context.strokeStyle = "rgba(242, 247, 246, 0.48)";
  context.lineWidth = 0.6;
  const gap = state.compact ? 5 : 4;
  for (let y = centerY - radius; y <= centerY + radius; y += gap) {
    context.beginPath();
    context.moveTo(centerX - radius, y + 0.5);
    context.lineTo(centerX + radius, y + 0.5);
    context.stroke();
  }
  context.restore();
}

function drawCrescent(elapsed, intro) {
  const context = state.context;
  const { centerX, centerY, radius } = lensGeometry(intro);
  const motion = state.reduced ? 0.18 : Math.sin(elapsed * 0.00022) * 0.42;
  const start = Math.PI * (0.08 + motion);
  const end = start + Math.PI * 1.22;

  context.save();
  context.globalCompositeOperation = "screen";
  context.lineCap = "round";

  context.strokeStyle = `rgba(238, 247, 246, ${0.44 * intro})`;
  context.lineWidth = state.compact ? 7 : 6;
  context.filter = `blur(${state.compact ? 12 : 10}px)`;
  context.beginPath();
  context.arc(centerX, centerY, radius * 1.012, start, end);
  context.stroke();

  context.filter = "none";
  context.strokeStyle = `rgba(246, 250, 249, ${0.86 * intro})`;
  context.lineWidth = 1.4;
  context.beginPath();
  context.arc(centerX, centerY, radius, start, end);
  context.stroke();

  context.strokeStyle = `rgba(168, 182, 182, ${0.15 * intro})`;
  context.lineWidth = 0.8;
  context.beginPath();
  context.arc(centerX, centerY, radius, end, start + Math.PI * 2);
  context.stroke();

  const hotX = centerX + Math.cos(end) * radius;
  const hotY = centerY + Math.sin(end) * radius;
  context.fillStyle = `rgba(255, 255, 255, ${0.92 * intro})`;
  context.filter = "blur(3px)";
  context.beginPath();
  context.arc(hotX, hotY, state.compact ? 3.5 : 3, 0, Math.PI * 2);
  context.fill();
  context.restore();
}

function render(timestamp) {
  if (!state.context) return;
  if (!state.startedAt) state.startedAt = timestamp;
  const elapsed = state.reduced ? 5200 : timestamp - state.startedAt;
  const intro = easeOutCubic((elapsed - 480) / 1550);
  state.frame += 1;

  drawBackground(intro);
  drawRollingBand(elapsed, intro);
  drawLensInterior(elapsed, intro);
  drawCrescent(elapsed, intro);

  canvas.dataset.renderState = state.reduced ? "static" : "animated";
  canvas.dataset.frame = String(state.frame);

  if (!state.reduced && state.visible && state.pageVisible) {
    state.animationFrame = window.requestAnimationFrame(render);
  }
}

function restart() {
  window.cancelAnimationFrame(state.animationFrame);
  if (!state.context) return;
  if (state.reduced) {
    render(5200);
    return;
  }
  if (state.visible && state.pageVisible) {
    state.animationFrame = window.requestAnimationFrame(render);
  }
}

function handleResize() {
  state.compact = compactQuery.matches;
  configureCanvas();
  restart();
}

function handleMotionChange() {
  state.reduced = forcedReduced || motionQuery.matches;
  setPrototypeState(state.reduced ? "reduced" : "active");
  restart();
}

function start() {
  if (!configureCanvas()) {
    document.documentElement.classList.add("no-canvas");
    setPrototypeState("fallback");
    return;
  }

  const hero = document.querySelector(".lens-hero");
  const observer = new IntersectionObserver(
    ([entry]) => {
      state.visible = entry.isIntersecting;
      restart();
    },
    { threshold: 0.04 },
  );
  observer.observe(hero);

  document.addEventListener("visibilitychange", () => {
    state.pageVisible = document.visibilityState === "visible";
    restart();
  });
  window.addEventListener("resize", handleResize, { passive: true });
  motionQuery.addEventListener("change", handleMotionChange);
  compactQuery.addEventListener("change", handleResize);
  restart();
}

try {
  start();
} catch (error) {
  console.error("evidence_lens_prototype_failed", error);
  document.documentElement.classList.add("no-canvas");
  setPrototypeState("fallback");
}
