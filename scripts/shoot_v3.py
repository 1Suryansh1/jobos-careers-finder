"""Fresh UI screenshots: results, market pulse, why-match, tracker (uses cached sources; no new agent spend)."""
import asyncio
from playwright.async_api import async_playwright
async def m():
  async with async_playwright() as p:
    b = await p.chromium.launch(); pg = await b.new_page(viewport={"width": 1440, "height": 960})
    await pg.goto("http://localhost:8300"); await pg.wait_for_timeout(1500)
    await pg.click("#go"); await pg.wait_for_timeout(3000)
    await pg.wait_for_function("document.querySelector('#go').textContent.includes('Find')", timeout=600000)
    await pg.wait_for_timeout(2500); await pg.screenshot(path="artifacts/v3_results.png")
    await (await pg.query_selector("#pulse")).screenshot(path="artifacts/v3_pulse.png")
    await pg.click("article.job details summary"); await pg.wait_for_timeout(600)
    await (await pg.query_selector("article.job")).screenshot(path="artifacts/v3_why_expanded.png")
    await pg.screenshot(path="artifacts/v3_results_full.png", full_page=True)
    for i in range(4):
        await pg.locator("article.job [onclick^='save']").nth(i).click(); await pg.wait_for_timeout(500)
    await pg.click("#nav [data-v=track]"); await pg.evaluate("window.scrollTo(0,0)"); await pg.wait_for_timeout(1200)
    await pg.screenshot(path="artifacts/v3_tracker_board.png"); await b.close()
asyncio.run(m())
