import asyncio, sys
from playwright.async_api import async_playwright
async def m():
  async with async_playwright() as p:
    b = await p.chromium.launch(); pg = await b.new_page(viewport={"width": 1440, "height": 960})
    await pg.goto("http://localhost:8300"); await pg.wait_for_timeout(1500)
    await pg.click("#go"); await pg.wait_for_timeout(2500); await pg.screenshot(path="artifacts/v2_loading.png")
    await pg.wait_for_timeout(30000); await pg.screenshot(path="artifacts/v2_partial_live.png")
    await pg.wait_for_function("document.querySelector('#go').textContent.includes('Find')", timeout=600000)
    await pg.wait_for_timeout(2500); await pg.screenshot(path="artifacts/v2_results.png")
    await pg.click("details summary"); await pg.wait_for_timeout(600)
    el = await pg.query_selector("article.job"); await el.screenshot(path="artifacts/v2_why_expanded.png")
    await pg.screenshot(path="artifacts/v2_results_full.png", full_page=True)
    m = await b.new_page(viewport={"width": 390, "height": 844}); await m.goto("http://localhost:8300"); await m.wait_for_timeout(2000)
    await m.screenshot(path="artifacts/v2_mobile.png", full_page=False); await b.close()
asyncio.run(m())
