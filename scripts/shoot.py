import sys, asyncio
from playwright.async_api import async_playwright
async def main(url, out, wait=4, click=None):
    async with async_playwright() as p:
        b = await p.chromium.launch(); pg = await b.new_page(viewport={"width": 1600, "height": 1000})
        await pg.goto(url); await pg.wait_for_timeout(wait * 1000)
        if click: await pg.click(click); await pg.wait_for_timeout(2500)
        await pg.screenshot(path=out, full_page=True); await b.close()
a = sys.argv; asyncio.run(main(a[1], a[2], int(a[3]) if len(a) > 3 else 4, a[4] if len(a) > 4 else None))
