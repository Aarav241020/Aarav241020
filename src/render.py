"""Bake src/eclipse.html (WebGL) into assets/eclipse.webp — GitHub READMEs can't run JS, but they play animated WebP.

The sequence (diamond ring -> totality -> diamond ring, sky drifting) isn't periodic, so the last FADE frames
dissolve into the first ones; the seam lands inside the glare of third/second contact where it's invisible.

Usage: python src/render.py            full render
       python src/render.py still 0.3  one frame at u=0.3 -> src/preview.png
"""
import shutil
import sys
from pathlib import Path

from PIL import Image, WebPImagePlugin, _webp
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
TMP = ROOT / "src" / "_frames"
FRAMES, FADE, MS = 240, 24, 16000 // 240


def open_page(pw):
    browser = pw.chromium.launch(channel="chrome", headless=True,
                                 args=["--use-angle=swiftshader", "--enable-unsafe-swiftshader"])
    page = browser.new_page(viewport={"width": 1200, "height": 420})
    page.goto((ROOT / "src" / "eclipse.html").as_uri())
    page.wait_for_function("!!window.renderAt")
    return browser, page


with sync_playwright() as pw:
    if sys.argv[1:2] == ["still"]:
        browser, page = open_page(pw)
        page.evaluate(f"renderAt({sys.argv[2]}, 1)")
        page.screenshot(path=str(ROOT / "src" / "preview.png"))
        sys.exit()
    TMP.mkdir(exist_ok=True)
    total = FRAMES + FADE
    for i in range(total):
        if i % 60 == 0:  # software GL leaks over hundreds of screenshots; a fresh browser per chunk stays stable
            if i:
                browser.close()
            browser, page = open_page(pw)
        page.evaluate(f"renderAt({i / (total - 1)}, {i * 7.31})")
        page.screenshot(path=str(TMP / f"{i:04d}.png"))
    browser.close()


def frame(i):
    with Image.open(TMP / f"{i:04d}.png") as a:
        a = a.convert("RGB")
    if i >= FADE:
        return a
    with Image.open(TMP / f"{FRAMES + i:04d}.png") as b:
        return Image.blend(b.convert("RGB"), a, i / FADE)


# ponytail: Pillow's private streaming encoder, one frame in RAM at a time (save_all holds them all and hit
# this machine's commit limit); if a Pillow upgrade breaks it, go back to frames[0].save(..., save_all=True)
enc = _webp.WebPAnimEncoder((1200, 420), 0xFF000000, 0, False, 3, 5, False, False)
for i in range(FRAMES):
    enc.add(WebPImagePlugin._convert_frame(frame(i)).getim(), i * MS, False, 80, 100, 4)
enc.add(None, FRAMES * MS, False, 80, 100, 0)
out = ROOT / "assets" / "eclipse.webp"
out.write_bytes(enc.assemble("", "", ""))
shutil.rmtree(TMP)
print(f"{out.name}: {FRAMES} frames, {out.stat().st_size / 1e6:.2f} MB")
