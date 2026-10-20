"""Bake src/eclipse.html (WebGL) into assets/eclipse.webp — GitHub READMEs can't run JS, but they play animated WebP.

Usage: python src/render.py [frames] [preview_t]
"""
import io
import sys
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
FRAMES = int(sys.argv[1]) if len(sys.argv) > 1 else 120
LOOP_MS = 8000

with sync_playwright() as pw:
    browser = pw.chromium.launch(channel="chrome", headless=True,
                                 args=["--use-angle=swiftshader", "--enable-unsafe-swiftshader"])
    page = browser.new_page(viewport={"width": 1200, "height": 420})
    page.goto((ROOT / "src" / "eclipse.html").as_uri())
    page.wait_for_function("window.renderAt && document.fonts.status === 'loaded'")
    stage = page.locator("#stage")
    if len(sys.argv) > 2:  # single still for checking the look
        page.evaluate(f"renderAt({sys.argv[2]})")
        stage.screenshot(path=str(ROOT / "src" / "preview.png"))
        sys.exit()
    frames = []
    for i in range(FRAMES):
        page.evaluate(f"renderAt({i / FRAMES})")
        frames.append(Image.open(io.BytesIO(stage.screenshot())).convert("RGB"))
    browser.close()

out = ROOT / "assets" / "eclipse.webp"
frames[0].save(out, save_all=True, append_images=frames[1:], duration=LOOP_MS // FRAMES,
               loop=0, quality=82, method=6)
print(f"{out.name}: {len(frames)} frames, {out.stat().st_size / 1e6:.2f} MB")
