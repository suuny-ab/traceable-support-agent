const STACKED_WORKBENCH_WIDTH = 1100;
const SAFE_HEADER_TOP = 80;
const SAFE_HEADER_BOTTOM = 160;

export function shouldScrollResult({ panelTop, viewportWidth, viewportHeight }) {
  return viewportWidth <= STACKED_WORKBENCH_WIDTH
    || panelTop < SAFE_HEADER_TOP
    || panelTop > viewportHeight - SAFE_HEADER_BOTTOM;
}

export function revealResultPanel(panel, { windowImpl = globalThis.window } = {}) {
  if (!panel || !windowImpl) return;

  panel.focus({ preventScroll: true });
  const { top } = panel.getBoundingClientRect();
  if (!shouldScrollResult({
    panelTop: top,
    viewportWidth: windowImpl.innerWidth,
    viewportHeight: windowImpl.innerHeight,
  })) return;

  const reducedMotion = windowImpl.matchMedia("(prefers-reduced-motion: reduce)").matches;
  panel.scrollIntoView({
    block: "start",
    behavior: reducedMotion ? "auto" : "smooth",
  });
}
