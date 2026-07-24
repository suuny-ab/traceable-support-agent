"""Drive the live-first workbench in Edge and capture acceptance screenshots."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from playwright.async_api import async_playwright

BASE = "http://localhost:3100"


async def main(out: Path) -> None:
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(channel="msedge", headless=True)
        page = await browser.new_page(viewport={"width": 1280, "height": 900})
        errors: list[str] = []
        page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
        page.on("pageerror", lambda exc: errors.append(str(exc)))

        await page.goto(f"{BASE}/app", wait_until="networkidle")
        await page.wait_for_timeout(1500)
        status = await page.locator(".live-status strong").inner_text()
        print("status:", status)
        await page.screenshot(path=str(out / "01-workbench-idle.png"), full_page=True)

        # Case 1: QA local clean -> live candidate
        await page.locator(".case-card", has_text="局部清扫").locator("button").click()
        await page.wait_for_selector(".mode-badge", timeout=60_000)
        await page.wait_for_timeout(500)
        print("case1 badge:", await page.locator(".mode-badge").inner_text())
        print("case1 calls:", await page.locator(".provider-calls").inner_text())
        await page.screenshot(path=str(out / "02-case-qa-candidate.png"), full_page=True)

        # Human decision approve
        await page.get_by_role("button", name="批准", exact=True).click()
        await page.wait_for_selector(".decision-note", timeout=15_000)
        print("decision:", await page.locator(".decision-note").inner_text())

        # Boundary challenge -> 0-call handoff
        await page.locator(".case-card", has_text="边界挑战").locator("button").click()
        await page.wait_for_selector(".mode-badge", timeout=30_000)
        await page.wait_for_timeout(500)
        print("boundary badge:", await page.locator(".mode-badge").inner_text())
        print("boundary calls:", await page.locator(".provider-calls").inner_text())
        print("boundary reason:", await page.locator(".handoff-reason").inner_text())
        await page.screenshot(path=str(out / "03-boundary-handoff.png"), full_page=True)

        # Free exploration with a suggested question
        await page.locator(".suggestion-chips button", has_text="尘盒和滤网").click()
        await page.locator(".run-button").click()
        await page.wait_for_selector(".mode-badge", timeout=60_000)
        await page.wait_for_timeout(500)
        print("free badge:", await page.locator(".mode-badge").inner_text())
        await page.screenshot(path=str(out / "04-free-explore.png"), full_page=True)

        # Explicit verified replay
        await page.locator(".replay-list li", has_text="地毯风险").locator("button").click()
        await page.wait_for_selector(".mode-badge", timeout=15_000)
        await page.wait_for_timeout(800)
        print("replay badge:", await page.locator(".mode-badge").inner_text())
        print("replay calls:", await page.locator(".provider-calls").inner_text())
        await page.screenshot(path=str(out / "05-verified-replay.png"), full_page=True)

        # Ticket case
        await page.locator(".case-card", has_text="地毯风险").locator("button").click()
        await page.wait_for_selector(".mode-badge", timeout=60_000)
        await page.wait_for_timeout(500)
        print("ticket badge:", await page.locator(".mode-badge").inner_text())
        await page.screenshot(path=str(out / "06-ticket-candidate.png"), full_page=True)

        # Mobile viewport
        await page.set_viewport_size({"width": 390, "height": 844})
        await page.goto(f"{BASE}/app", wait_until="networkidle")
        await page.wait_for_timeout(1200)
        overflow = await page.evaluate("document.documentElement.scrollWidth")
        print("mobile scrollWidth:", overflow)
        await page.screenshot(path=str(out / "07-mobile.png"), full_page=True)

        print("console errors:", errors if errors else "none")
        await browser.close()


if __name__ == "__main__":
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("private-artifacts/visual")
    out.mkdir(parents=True, exist_ok=True)
    asyncio.run(main(out))
