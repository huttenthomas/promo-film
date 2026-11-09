#!/usr/bin/env python3
"""Capture crisp UI screenshots of a running (or static) web app for promo shots.

    python capture.py --url http://localhost:3000 --device phone --out screens/home.png
    python capture.py --static ./dist --path /settings --device browser --out screens/settings.png
    python capture.py --url ... --keys ArrowUp,ArrowLeft --click "text=Get started" --wait 800 --out ...

--device phone   -> 390x844 viewport @3x  (1170 px wide, sharp enough for macro close-ups)
--device tablet  -> 820x1180 @2x
--device browser -> 1440x900 @2x
--full-page captures the whole scrollable page (use with a shot's "scroll" to pan down it).
--dark asks the page for prefers-color-scheme: dark.
"""
import argparse, functools, http.server, socketserver, threading, time
from pathlib import Path

DEVICES = {"phone": ((390, 844), 3, True), "tablet": ((820, 1180), 2, True), "browser": ((1440, 900), 2, False)}


def serve(directory):
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a): pass
    handler = functools.partial(Quiet, directory=str(directory))
    httpd = socketserver.TCPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, f"http://127.0.0.1:{httpd.server_address[1]}"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--url"); src.add_argument("--static", help="directory to serve (index.html inside)")
    ap.add_argument("--path", default="/")
    ap.add_argument("--device", choices=DEVICES, default="phone")
    ap.add_argument("--out", required=True)
    ap.add_argument("--full-page", action="store_true")
    ap.add_argument("--dark", action="store_true")
    ap.add_argument("--wait", type=int, default=600, help="ms to wait after load/actions")
    ap.add_argument("--keys", default="", help="comma-separated keys to press, e.g. ArrowUp,Enter")
    ap.add_argument("--click", action="append", default=[], help="selector to click (repeatable)")
    ap.add_argument("--type", dest="type_", nargs=2, metavar=("SELECTOR", "TEXT"), action="append", default=[])
    ap.add_argument("--hide", action="append", default=[], help="selector to hide (cookie banners, dev overlays)")
    a = ap.parse_args()

    from playwright.sync_api import sync_playwright
    httpd = None
    url = a.url
    if a.static:
        httpd, base = serve(Path(a.static).resolve()); url = base + a.path
    (vw, vh), scale, mobile = DEVICES[a.device]
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        ctx = b.new_context(viewport={"width": vw, "height": vh}, device_scale_factor=scale, is_mobile=mobile,
                            has_touch=mobile, color_scheme="dark" if a.dark else "light")
        page = ctx.new_page()
        page.goto(url, wait_until="networkidle")
        for sel, text in a.type_: page.fill(sel, text)
        for sel in a.click: page.click(sel); time.sleep(0.25)
        for k in filter(None, a.keys.split(",")): page.keyboard.press(k.strip()); time.sleep(0.18)
        for sel in a.hide: page.add_style_tag(content=f"{sel}{{display:none!important}}")
        page.wait_for_timeout(a.wait)
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=a.out, full_page=a.full_page)
        b.close()
    if httpd: httpd.shutdown()
    print("captured", a.out)


if __name__ == "__main__":
    main()
