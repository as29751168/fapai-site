from playwright.sync_api import sync_playwright
import os
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 1200, "height": 630})
    pg.goto("file://" + os.path.abspath("og.html"))
    os.makedirs("site", exist_ok=True)
    pg.screenshot(path="site/og.jpg", type="jpeg", quality=90)
    b.close()
