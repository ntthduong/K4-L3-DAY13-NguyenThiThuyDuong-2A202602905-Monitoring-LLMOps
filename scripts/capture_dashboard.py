from __future__ import annotations

import argparse
import asyncio
import base64
import json
import shutil
import subprocess
import tempfile
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

import websockets


CHROME_CANDIDATES = (
    Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
    Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
)


def find_browser() -> Path:
    for candidate in CHROME_CANDIDATES:
        if candidate.exists():
            return candidate
    raise FileNotFoundError("Không tìm thấy Chrome hoặc Edge")


def wait_for_debugger(port: int, timeout: float = 10.0) -> None:
    deadline = time.monotonic() + timeout
    url = f"http://127.0.0.1:{port}/json/version"
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1):
                return
        except OSError:
            time.sleep(0.2)
    raise TimeoutError("Chrome DevTools không khởi động kịp")


def create_page(port: int, url: str) -> str:
    request = urllib.request.Request(
        f"http://127.0.0.1:{port}/json/new?{urllib.parse.quote(url, safe=':/?=&')}",
        method="PUT",
    )
    with urllib.request.urlopen(request, timeout=5) as response:
        payload = json.load(response)
    return str(payload["webSocketDebuggerUrl"])


class CdpClient:
    def __init__(self, websocket: Any) -> None:
        self.websocket = websocket
        self.next_id = 1

    async def call(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        request_id = self.next_id
        self.next_id += 1
        await self.websocket.send(json.dumps({"id": request_id, "method": method, "params": params or {}}))
        while True:
            message = json.loads(await self.websocket.recv())
            if message.get("id") != request_id:
                continue
            if "error" in message:
                raise RuntimeError(f"CDP {method}: {message['error']}")
            return message.get("result", {})


async def capture(
    websocket_url: str,
    output: Path,
    wait_seconds: float,
    full_page: bool,
    scroll_position: str,
) -> None:
    async with websockets.connect(websocket_url, max_size=20 * 1024 * 1024) as websocket:
        cdp = CdpClient(websocket)
        await cdp.call("Page.enable")
        await cdp.call("Runtime.enable")
        await asyncio.sleep(wait_seconds)

        # Streamlit renders charts lazily. Visit the bottom once, then return to
        # the top before capturing so all six panels exist in the page.
        scroll_target = (
            "document.querySelector('[data-testid=\"stMain\"]') || "
            "document.querySelector('[data-testid=\"stAppViewContainer\"]') || document.scrollingElement"
        )
        await cdp.call("Runtime.evaluate", {"expression": f"({scroll_target}).scrollTop = ({scroll_target}).scrollHeight"})
        await asyncio.sleep(2)
        if scroll_position == "top":
            expression = f"({scroll_target}).scrollTop = 0"
        else:
            expression = f"({scroll_target}).scrollTop = ({scroll_target}).scrollHeight"
        await cdp.call("Runtime.evaluate", {"expression": expression})
        await asyncio.sleep(1)

        params: dict[str, Any] = {"format": "png", "captureBeyondViewport": full_page}
        if full_page:
            metrics = await cdp.call("Page.getLayoutMetrics")
            size = metrics["cssContentSize"]
            params["clip"] = {
                "x": 0,
                "y": 0,
                "width": min(float(size["width"]), 1920),
                "height": min(float(size["height"]), 5000),
                "scale": 1,
            }
        result = await cdp.call("Page.captureScreenshot", params)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(base64.b64decode(result["data"]))


def main() -> None:
    parser = argparse.ArgumentParser(description="Capture a fully rendered Streamlit dashboard")
    parser.add_argument("--url", default="http://127.0.0.1:8501")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--wait-seconds", type=float, default=6.0)
    parser.add_argument("--full-page", action="store_true")
    parser.add_argument("--scroll-position", choices=("top", "bottom"), default="top")
    parser.add_argument("--port", type=int, default=9237)
    args = parser.parse_args()

    browser = find_browser()
    profile = Path(tempfile.mkdtemp(prefix="day13-dashboard-"))
    creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    process = subprocess.Popen(
        [
            str(browser),
            "--headless=new",
            "--disable-gpu",
            "--hide-scrollbars",
            "--no-first-run",
            "--remote-allow-origins=*",
            f"--remote-debugging-port={args.port}",
            f"--user-data-dir={profile}",
            "--window-size=1920,1080",
            "about:blank",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=creation_flags,
    )
    try:
        wait_for_debugger(args.port)
        websocket_url = create_page(args.port, args.url)
        asyncio.run(
            capture(
                websocket_url,
                args.output,
                args.wait_seconds,
                args.full_page,
                args.scroll_position,
            )
        )
        print(f"Saved dashboard screenshot: {args.output}")
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
        shutil.rmtree(profile, ignore_errors=True)


if __name__ == "__main__":
    main()
