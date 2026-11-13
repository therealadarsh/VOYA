"""Browser walkthrough of the private preview. Opt-in: VOYA_BROWSER=1.

Install once: `uv run --with playwright playwright install chromium`.
"""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(
    os.environ.get("VOYA_BROWSER") != "1",
    reason="set VOYA_BROWSER=1 to run the browser flow",
)


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_until(url: str, timeout: float = 20) -> None:
    import urllib.request

    deadline = time.time() + timeout
    last = ""
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1) as response:
                if response.status == 200:
                    return
        except Exception as exc:  # noqa: BLE001 - server still booting
            last = str(exc)
            time.sleep(0.2)
    raise RuntimeError(f"server did not start: {last}")


def test_preview_flow(tmp_path: Path) -> None:
    sync_playwright = pytest.importorskip("playwright.sync_api").sync_playwright
    port = _free_port()
    env = os.environ.copy()
    env.update(
        {
            "VOYA_ENV": "development",
            "VOYA_DEV_SIGNIN": "1",
            "VOYA_DB": str(tmp_path / "voya.db"),
            "VOYA_PREVIEW_LABEL": "1",
        }
    )
    env.pop("VOYA_INVITE_CODE", None)
    server = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "voya.api:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
        ],
        env=env,
        cwd=Path(__file__).resolve().parents[2],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    base = f"http://127.0.0.1:{port}"
    try:
        _wait_until(base + "/healthz")
        with sync_playwright() as playwright:
            launch_args = {"headless": True, "args": ["--no-sandbox", "--disable-dev-shm-usage"]}
            try:
                browser = playwright.chromium.launch(channel="chrome", **launch_args)
            except Exception:
                browser = playwright.chromium.launch(**launch_args)
            page = browser.new_page(viewport={"width": 390, "height": 844})
            page.goto(base + "/")
            page.get_by_text("Preview", exact=True).wait_for()
            page.locator("#f-dest option").first.wait_for(state="attached")
            page.wait_for_function("() => document.querySelector('#f-date').value")
            page.locator("#plan-form").get_by_role("spinbutton", name="Budget (USD)").fill("300")
            page.locator("#f-adults").fill("2")
            page.get_by_role("button", name="Some wiggle room").click()
            page.get_by_role("button", name="Plan my trip").click()
            page.get_by_text("Demo prices").wait_for()
            page.get_by_role("button", name="Show me another").wait_for()
            first_idea = page.locator("#ideas h3").first.inner_text()
            page.get_by_role("button", name="Show me another").click()
            page.wait_for_function(
                "(first) => document.querySelector('#ideas h3').textContent !== first",
                arg=first_idea,
            )
            page.locator(".headline .big").wait_for()
            assert "est." in page.locator(".headline .big").inner_text()
            page.get_by_role("button", name="Feedback").click()
            page.locator("#fb-message").fill("Browser flow feedback")
            page.get_by_role("button", name="Send").click()
            page.get_by_text("Thanks. The note is saved").wait_for()
            page.locator("#feedback-close").click()
            page.get_by_role("button", name="Save trip").click()
            page.locator("#si-email").fill("preview@example.com")
            page.locator("#si-adult").check()
            page.get_by_role("button", name="Continue").click()
            page.get_by_text("Trip saved").wait_for()
            browser.close()
    finally:
        server.terminate()
        try:
            server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server.kill()
