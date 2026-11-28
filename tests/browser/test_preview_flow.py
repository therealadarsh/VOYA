"""Browser walkthrough of the private preview. Opt-in: VOYA_BROWSER=1.

Run: `make e2e` (installs Chromium if needed, then this file).
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

_WIDTHS = [360, 1280]
_SERIOUS = {"serious", "critical"}


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
        except Exception as exc:
            last = str(exc)
            time.sleep(0.2)
    raise RuntimeError(f"server did not start: {last}")


class _Server:
    def __init__(self, tmp_path: Path, extra: dict[str, str] | None = None) -> None:
        self.port = _free_port()
        env = os.environ.copy()
        for key in ("OPENROUTER_API_KEY", "FOURSQUARE_API_KEY"):
            env.pop(key, None)
        env.update(
            {
                "VOYA_ENV": "development",
                "VOYA_DEV_SIGNIN": "1",
                "VOYA_DB": str(tmp_path / "voya.db"),
                "VOYA_PREVIEW_LABEL": "1",
            }
        )
        env.pop("VOYA_INVITE_CODE", None)
        if extra:
            env.update(extra)
        self.base = f"http://127.0.0.1:{self.port}"
        self._proc = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "voya.api:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(self.port),
            ],
            env=env,
            cwd=Path(__file__).resolve().parents[2],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )

    def wait(self) -> None:
        _wait_until(self.base + "/healthz")

    def stop(self) -> None:
        self._proc.terminate()
        try:
            self._proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self._proc.kill()


def _watch(page) -> list[str]:
    errors: list[str] = []
    page.on("pageerror", lambda exc: errors.append(f"pageerror: {exc}"))

    def _console(msg) -> None:
        if msg.type == "error":
            errors.append(f"console: {msg.text}")

    page.on("console", _console)
    return errors


def _quiet(errors: list[str]) -> None:
    assert not errors, "\n".join(errors)


def _axe(page) -> None:
    from axe_playwright_python.sync_playwright import Axe

    results = Axe().run(page)
    bad = [
        item for item in results.response.get("violations", []) if item.get("impact") in _SERIOUS
    ]
    if not bad:
        return
    lines = [f"{len(bad)} serious or critical axe violation(s):"]
    for item in bad:
        lines.append(f"- {item.get('impact')} {item.get('id')}: {item.get('help')}")
        for node in item.get("nodes", [])[:4]:
            lines.append(f"    {node.get('target')}")
    raise AssertionError("\n".join(lines))


def _browser(playwright):
    launch_args = {"headless": True, "args": ["--no-sandbox", "--disable-dev-shm-usage"]}
    try:
        return playwright.chromium.launch(channel="chrome", **launch_args)
    except Exception:
        return playwright.chromium.launch(**launch_args)


def _plan_nyc(page, base: str) -> None:
    page.goto(base)
    page.get_by_text("Preview", exact=True).wait_for()
    page.locator("#f-dest option").first.wait_for(state="attached")
    page.locator("#f-dest").select_option("new-york")
    page.wait_for_function("() => document.querySelector('#f-date').value")
    page.locator("#plan-form").get_by_role("spinbutton", name="Budget (USD)").fill("800")
    page.locator("#f-adults").fill("1")
    page.locator("#f-days").fill("1")
    page.get_by_role("button", name="Some wiggle room").click()
    page.get_by_role("button", name="Plan my trip").click()
    page.get_by_role("heading", name="Classic picks").wait_for()
    assert "Demo prices" in page.locator("#demo-banner").inner_text()
    assert "est." in page.locator("#plan-view .headline .big").inner_text()


@pytest.mark.parametrize("width", _WIDTHS)
def test_preview_flow(tmp_path: Path, width: int) -> None:
    sync_playwright = pytest.importorskip("playwright.sync_api").sync_playwright
    server = _Server(tmp_path)
    try:
        server.wait()
        with sync_playwright() as playwright:
            browser = _browser(playwright)
            page = browser.new_page(viewport={"width": width, "height": 800})
            page.emulate_media(color_scheme="light")
            errors = _watch(page)
            _plan_nyc(page, server.base)
            _axe(page)
            morning = page.locator("[data-idea='1:morning']")
            before = morning.inner_text()
            afternoon = page.locator("[data-idea='1:afternoon']").inner_text()
            evening = page.locator("[data-idea='1:evening']").inner_text()
            another = page.get_by_role("button", name="Another morning idea for day 1")
            another.evaluate("el => el.scrollIntoView({block: 'center'})")
            another.click()
            page.wait_for_function(
                "(first) => document.querySelector(\"[data-idea='1:morning']\").textContent !== first",
                arg=before,
            )
            assert page.locator("[data-idea='1:afternoon']").inner_text() == afternoon
            assert page.locator("[data-idea='1:evening']").inner_text() == evening
            page.get_by_role("button", name="Save trip").click()
            page.get_by_role("heading", name="Sign in to keep this trip").wait_for()
            _axe(page)
            page.locator("#si-email").fill("preview@example.com")
            page.locator("#si-adult").check()
            page.get_by_role("button", name="Continue").click()
            page.get_by_text("Trip saved").wait_for()
            page.get_by_role("button", name="Track spend").click()
            page.get_by_role("heading", name="Log spend").wait_for()
            _axe(page)
            before_spent = page.locator("#trip-view .big").inner_text()
            page.locator("#s-amt").fill("12.50")
            page.get_by_role("button", name="Log it").click()
            page.wait_for_function(
                "() => { const el = document.querySelector('#trip-view .big');"
                " return el && el.textContent.includes('12.50'); }"
            )
            assert page.locator("#trip-view .big").inner_text() != before_spent
            page.get_by_role("tab", name="Plan").click()
            page.get_by_role("button", name="Ask VOYA").click()
            page.get_by_role("button", name="Make it $20 cheaper").click()
            page.get_by_text("Built-in helper").wait_for()
            page.locator("#sheet-close").click()
            page.get_by_role("button", name="Feedback").click()
            page.locator("#fb-message").fill("Browser flow feedback")
            page.get_by_role("button", name="Send").click()
            page.get_by_text("Thanks. The note is saved").wait_for()
            page.locator("#feedback-close").click()
            page.get_by_role("link", name="Privacy").click()
            page.get_by_role("heading", name="Privacy").wait_for()
            assert "contact address" in page.locator("main").inner_text()
            _axe(page)
            page.get_by_role("link", name="Terms").click()
            page.get_by_role("heading", name="Terms").wait_for()
            _quiet(errors)
            browser.close()
    finally:
        server.stop()


@pytest.mark.parametrize("width", _WIDTHS)
def test_invite_code_gate(tmp_path: Path, width: int) -> None:
    sync_playwright = pytest.importorskip("playwright.sync_api").sync_playwright
    server = _Server(tmp_path, extra={"VOYA_INVITE_CODE": "browser-invite"})
    try:
        server.wait()
        with sync_playwright() as playwright:
            browser = _browser(playwright)
            page = browser.new_page(viewport={"width": width, "height": 800})
            page.emulate_media(color_scheme="light")
            errors = _watch(page)
            page.goto(server.base + "/")
            page.get_by_role("heading", name="Invite code").wait_for()
            _axe(page)
            _quiet(errors)
            page.locator("#invite-code").fill("wrong-code")
            page.get_by_role("button", name="Continue").click()
            page.get_by_text("That invite code is not valid.").wait_for()
            # The refused code is a 401. Chromium logs that failed fetch.
            assert errors and all("401" in item for item in errors)
            errors.clear()
            page.locator("#invite-code").fill("browser-invite")
            page.get_by_role("button", name="Continue").click()
            page.get_by_role("heading", name="Where, when, and how much?").wait_for()
            _quiet(errors)
            browser.close()
    finally:
        server.stop()
