export function shouldScrollResult(options: {
  panelTop: number;
  viewportWidth: number;
  viewportHeight: number;
}): boolean;

export function revealResultPanel(
  panel: HTMLElement | null,
  options?: {
    windowImpl?: Pick<Window, "innerWidth" | "innerHeight" | "matchMedia">;
  },
): void;
