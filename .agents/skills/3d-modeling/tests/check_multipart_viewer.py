"""Smoke-test an assembled and exploded GLB review in an isolated Chrome session."""

import argparse
import functools
import http.server
import io
import json
import shutil
import subprocess
import tempfile
import threading
import time
from base64 import b64decode
from pathlib import Path
from urllib.request import urlopen

import websocket
from PIL import Image, ImageChops


VIEWER_FILES = ("index.html", "viewer.js", "styles.css")


def wait_for(probe):
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        value = probe()
        if value:
            return value
        time.sleep(0.08)
    raise RuntimeError(f"Timed out: {probe}")


class Browser:
    def __init__(self, socket):
        self.socket = socket
        self.sequence = 0

    def call(self, name, **args):
        self.sequence += 1
        self.socket.send(json.dumps({"id": self.sequence, "method": name, "params": args}))
        while True:
            message = json.loads(self.socket.recv())
            if message.get("id") == self.sequence:
                if "error" in message:
                    raise RuntimeError(message["error"])
                return message["result"]

    def evaluate(self, code):
        response = self.call("Runtime.evaluate", expression=code, awaitPromise=True, returnByValue=True)
        if "exceptionDetails" in response:
            raise RuntimeError(response["exceptionDetails"])
        return response["result"].get("value")

    def open(self, url, width=1350, height=960):
        self.call("Emulation.setDeviceMetricsOverride", width=width, height=height,
                  deviceScaleFactor=1, mobile=False)
        self.call("Page.navigate", url=url)
        wait_for(lambda: self.evaluate(
            f"location.href === {json.dumps(url)} && !!document.querySelector('#loading.hidden')"))
        # Observe the rendered scene from the test only. No test hooks ship in the viewer.
        self.evaluate("""(async () => {
          const three = await import("three");
          const updateScene = three.Scene.prototype.updateMatrixWorld;
          three.Scene.prototype.updateMatrixWorld = function (...args) {
            window.renderedModel = this.children.find((node) => node.isGroup);
            return updateScene.apply(this, args);
          };
          const updateCamera = three.PerspectiveCamera.prototype.updateMatrixWorld;
          three.PerspectiveCamera.prototype.updateMatrixWorld = function (...args) {
            window.renderedCamera = this;
            return updateCamera.apply(this, args);
          };
          window.reviewThree = three;
        })()""")
        wait_for(lambda: self.evaluate("!!window.renderedModel && !!window.renderedCamera"))

    def click(self, selector):
        x, y = self.evaluate(f"""(() => {{
          const button = document.querySelector({json.dumps(selector)});
          button.scrollIntoView({{block: "nearest"}});
          const rect = button.getBoundingClientRect();
          return [rect.x + rect.width / 2, rect.y + rect.height / 2];
        }})()""")
        for action in ("mousePressed", "mouseReleased"):
            self.call("Input.dispatchMouseEvent", type=action, x=x, y=y, button="left", clickCount=1)

    def canvas_center(self):
        return self.evaluate("""(() => {
          const rect = document.querySelector("#viewer canvas").getBoundingClientRect();
          return [rect.x + rect.width / 2, rect.y + rect.height / 2];
        })()""")

    def drag(self, button):
        x, y = self.canvas_center()
        buttons = 1 if button == "left" else 2
        self.call("Input.dispatchMouseEvent", type="mousePressed", x=x, y=y, button=button, buttons=buttons)
        self.call("Input.dispatchMouseEvent", type="mouseMoved", x=x + 90, y=y + 32, buttons=buttons)
        self.call("Input.dispatchMouseEvent", type="mouseReleased", x=x + 90, y=y + 32, button=button)

    def screenshot(self, path=None):
        content = b64decode(self.call("Page.captureScreenshot", format="png")["data"])
        if path is not None:
            path.write_bytes(content)
        return Image.open(io.BytesIO(content)).convert("RGB")


def assert_visible(browser, screenshot):
    rect = browser.evaluate("""(() => {
      const { left, top, right, bottom } = document.querySelector("#viewer canvas").getBoundingClientRect();
      return [left, top, right, bottom].map(Math.round);
    })()""")
    browser.evaluate("window.renderedModel.visible = false")
    browser.evaluate("new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))")
    background = browser.screenshot()
    browser.evaluate("window.renderedModel.visible = true")
    difference = ImageChops.difference(screenshot.crop(rect), background.crop(rect))
    bounds = difference.getbbox()
    width, height = difference.size
    assert bounds and min(*bounds[:2], width - bounds[2], height - bounds[3]) > 4, bounds
    assert (bounds[2] - bounds[0]) * (bounds[3] - bounds[1]) > width * height * 0.03, bounds


def model_state(browser):
    return browser.evaluate("""window.renderedModel.children.map(node => ({
      name: node.name,
      visible: node.visible,
      position: node.position.toArray()
    }))""")


def perform_checks(browser, base_url, sandbox, check):
    for file in (*VIEWER_FILES, "model.glb", "metadata.json"):
        with urlopen(f"{base_url}/review/{file}", timeout=5) as response:
            check(response.status == 200 and bool(response.read()), f"{file} served over HTTP")

    url = f"{base_url}/review/"
    browser.open(url)
    start = model_state(browser)
    layout = browser.evaluate("""fetch("metadata.json").then(r => r.json()).then(m =>
      m.parts.map(part => ({ ...part, node: window.reviewThree.PropertyBinding.sanitizeNodeName(part.node) })))""")
    parts = {part["node"]: part for part in layout}
    names = [node["name"] for node in start]
    check(len(parts) >= 2 and len(parts) == len(layout) and all(names.count(name) == 1 for name in parts),
          "GLB exposes each declared part exactly once")
    check(all(node["visible"] for node in start if node["name"] in parts), "assembled parts are visible")
    check(browser.evaluate('document.querySelector("#part-inspection").hidden && !document.querySelector("#explode").disabled'),
          "Explode is available with the picker hidden")
    assert_visible(browser, browser.screenshot(sandbox / "assembled.png"))
    check(True, "assembled geometry is visibly rendered and framed")

    browser.click("#explode")
    explosive = []
    for node in start:
        part = parts.get(node["name"])
        explosive.append({
            **node,
            "visible": part is not None,
            "position": [a + b for a, b in zip(node["position"], part["offset"])] if part else node["position"],
        })
    wait_for(lambda: model_state(browser) == explosive)
    check(True, "all parts move to the configured offsets and guides disappear")
    check(browser.evaluate('document.querySelector("#explode").textContent === "Reassemble" && document.querySelector("#explode").ariaPressed === "true"'),
          "exploded button label and accessible state update")
    labels = browser.evaluate('Array.from(document.querySelector("#part").options, option => option.textContent)')
    check(labels == ["All parts", *(part["label"] for part in layout)], "picker lists the configured part labels in order")
    assert_visible(browser, browser.screenshot(sandbox / "exploded.png"))
    check(True, "all parts render within the exploded viewport")

    for index, part in enumerate(layout):
        browser.evaluate(f"""(() => {{
          const picker = document.querySelector("#part");
          picker.value = "{index}";
          picker.dispatchEvent(new Event("change"));
        }})()""")
        visible = [node["name"] for node in model_state(browser) if node["visible"]]
        check(visible == [part["node"]], f"{part['label']} can be isolated")
        assert_visible(browser, browser.screenshot(sandbox / f"isolated-{index + 1}.png"))
        check(True, f"{part['label']} is visible and framed in isolation")

    camera_position = lambda: browser.evaluate("window.renderedCamera.position.toArray()")
    before = camera_position()
    browser.click("#autoRotate")
    wait_for(lambda: camera_position() != before)
    browser.click("#autoRotate")
    check(True, "auto-rotate moves the camera around the isolated part")
    browser.click("#wireframe")
    check(browser.evaluate("""(() => {
      const renderedMaterials = [];
      window.renderedModel.traverseVisible((node) => {
        if (node.isMesh) renderedMaterials.push(...[node.material].flat());
      });
      return renderedMaterials.length > 0 && renderedMaterials.every(material => material.wireframe);
    })()"""), "wireframe updates the isolated meshes")
    browser.click("#wireframe")
    browser.click("#reset")
    check(len([node for node in model_state(browser) if node["visible"]]) == 1, "reset retains the selected part")
    before = camera_position()
    browser.drag("left")
    wait_for(lambda: camera_position() != before)
    check(True, "drag orbits the isolated part")
    browser.click("#reset")
    before = camera_position()
    browser.drag("right")
    wait_for(lambda: camera_position() != before)
    check(True, "right-drag pans the isolated view")
    browser.click("#reset")
    distance = lambda: browser.evaluate("""(() => {
      const visible = window.renderedModel.children.find(node => node.visible);
      const center = new window.reviewThree.Box3().setFromObject(visible).getCenter(new window.reviewThree.Vector3());
      return window.renderedCamera.position.distanceTo(center);
    })()""")
    before = distance()
    x, y = browser.canvas_center()
    browser.call("Input.dispatchMouseEvent", type="mouseWheel", x=x, y=y, deltaX=0, deltaY=-120)
    wait_for(lambda: distance() < before * 0.99)
    check(True, "scroll zooms into the isolated part")
    browser.click("#reset")
    browser.evaluate('document.querySelector("#part").selectedIndex = 0; document.querySelector("#part").dispatchEvent(new Event("change"))')
    check(model_state(browser) == explosive, "All parts restores the exploded overview")

    for cycle in range(3):
        browser.click("#explode")
        wait_for(lambda: model_state(browser) == start)
        check(True, f"reassembly {cycle + 1} restores every position and guide exactly")
        if cycle < 2:
            browser.click("#explode")
            wait_for(lambda: model_state(browser) == explosive)
    check(browser.evaluate('document.querySelector("#part-inspection").hidden && document.querySelector("#explode").ariaPressed === "false"'),
          "reassembly resets the controls")

    browser.call("Emulation.setEmulatedMedia", features=[{"name": "prefers-reduced-motion", "value": "reduce"}])
    browser.open(f"{url}?narrow", width=510, height=940)
    browser.click("#explode")
    check(model_state(browser) == explosive, "narrow viewport and reduced motion reach the exploded layout immediately")
    assert_visible(browser, browser.screenshot(sandbox / "exploded-narrow.png"))
    check(True, "exploded geometry is framed in the narrow viewport")



def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--review", required=True, type=Path)
    parser.add_argument("--sandbox", required=True, type=Path)
    parser.add_argument("--chrome")
    args = parser.parse_args()
    sandbox = args.sandbox.resolve()
    source = args.review.resolve()
    target = sandbox / "review"
    if source == sandbox or source in sandbox.parents:
        parser.error("Keep the smoke-test sandbox outside the source review")
    target.mkdir(parents=True)
    for file in (*VIEWER_FILES, "model.glb", "metadata.json"):
        shutil.copy2(source / file, target / file)
    chrome_path = args.chrome or next((path for name in ("google-chrome", "chromium", "chromium-browser")
                                       if (path := shutil.which(name))), None)
    if not chrome_path:
        parser.error("A Chromium-compatible browser is required")
    lines = []

    def check(condition, label):
        assert condition, label
        lines.append(f"PASS {len(lines) + 1} {label}")

    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=sandbox)
    with http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler) as server, tempfile.TemporaryDirectory() as profile:
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        with (sandbox / "chrome.log").open("w") as chrome_log:
            chrome = subprocess.Popen([
                chrome_path, "--headless", "--no-sandbox", "--use-angle=swiftshader",
                "--enable-unsafe-swiftshader", "--disable-background-timer-throttling",
                "--remote-debugging-port=0", f"--user-data-dir={profile}", "about:blank",
            ], stdout=chrome_log, stderr=chrome_log)
            try:
                marker = Path(profile) / "DevToolsActivePort"
                wait_for(marker.is_file)
                port = marker.read_text().splitlines()[0]
                with urlopen(f"http://127.0.0.1:{port}/json/list", timeout=5) as response:
                    target = next(tab for tab in json.load(response) if tab["type"] == "page")
                socket = websocket.create_connection(target["webSocketDebuggerUrl"], timeout=20, suppress_origin=True)
                try:
                    perform_checks(Browser(socket), f"http://127.0.0.1:{server.server_port}", sandbox, check)
                    check(len(lines) >= 20, "minimum of 20 checks passed")
                finally:
                    socket.close()
            except Exception as error:
                lines.append(f"FAIL {type(error).__name__}: {error}")
                raise
            finally:
                chrome.terminate()
                chrome.wait(timeout=10)
                server.shutdown()
                (sandbox / "viewer-results.txt").write_text("\n".join(lines) + "\n")
    print(f"TOTAL_PASS={len(lines)}")


if __name__ == "__main__":
    main()
