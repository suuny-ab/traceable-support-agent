/**
 * @param {{
 *   availability: "checking" | "available" | "unavailable" | "unknown",
 *   isPreset: boolean,
 *   replayOnly?: boolean,
 * }} input
 * @returns {"live" | "replay" | "blocked"}
 */
export function selectRunRoute({ availability, isPreset, replayOnly = false }) {
  if (isPreset && (replayOnly || availability !== "available")) return "replay";
  if (availability === "available") return "live";
  return "blocked";
}
