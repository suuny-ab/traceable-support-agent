/**
 * Live-first routing: runs are only created against the real service.
 * Replay is never an automatic substitute; it is a separate explicit action.
 *
 * @param {{
 *   availability: "checking" | "available" | "unavailable" | "unknown",
 *   preflightOnly?: boolean,
 * }} input
 * @returns {"live" | "blocked"}
 */
export function selectRunRoute({ availability, preflightOnly = false }) {
  if (availability === "available") return "live";
  // Deterministic preflight handoffs (e.g. unsupported claims) are persisted
  // before the live gate, so they stay runnable when live is off.
  if (preflightOnly) return "live";
  return "blocked";
}
