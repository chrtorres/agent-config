export function setupViewers() {
  for (const viewer of document.querySelectorAll("[data-viewer]")) {
    const frame = viewer.querySelector("[data-view-frame]");
    const fit = viewer.querySelector("[data-view-fit]");
    const width = viewer.querySelector("[data-view-width]");
    const height = viewer.querySelector("[data-view-height]");
    const canvas = frame.querySelector("canvas");
    const fullscreen = viewer.querySelector("[data-view-fullscreen]");

    function layoutCanvas() {
      if (!canvas || !frame.clientWidth || !frame.clientHeight) return;
      const horizontal = frame.clientWidth / canvas.width;
      const vertical = frame.clientHeight / canvas.height;
      const scale = fit.value === "center" ? Math.min(1, horizontal, vertical) :
        (fit.value === "fill" ? Math.max : Math.min)(horizontal, vertical);
      const mediaWidth = fit.value === "stretch" ? frame.clientWidth : canvas.width * scale;
      const mediaHeight = fit.value === "stretch" ? frame.clientHeight : canvas.height * scale;
      // Keep the canvas box on the displayed pixels so picking and the feature marker use the same geometry.
      canvas.style.width = `${mediaWidth}px`;
      canvas.style.height = `${mediaHeight}px`;
      const content = canvas.parentElement;
      content.style.left = `${(frame.clientWidth - mediaWidth) / 2}px`;
      content.style.top = `${(frame.clientHeight - mediaHeight) / 2}px`;
    }

    function apply() {
      frame.dataset.fit = fit.value;
      frame.toggleAttribute("data-manual-height", Boolean(height.dataset.changed));
      frame.style.setProperty("--view-width", width.value + "%");
      if (height.dataset.changed) frame.style.setProperty("--view-height", height.value + "dvh");
      else frame.style.removeProperty("--view-height");
      layoutCanvas();
    }

    fit.addEventListener("change", apply);
    width.addEventListener("input", apply);
    height.addEventListener("input", () => {
      height.dataset.changed = "true";
      apply();
    });
    viewer.querySelector("[data-view-reset]").addEventListener("click", () => {
      width.value = width.defaultValue;
      height.value = height.defaultValue;
      delete height.dataset.changed;
      apply();
    });
    if (canvas) {
      new ResizeObserver(layoutCanvas).observe(frame);
      new MutationObserver(layoutCanvas).observe(canvas, {attributes:true, attributeFilter:["width", "height"]});
    }
    fullscreen.hidden = !document.fullscreenEnabled;
    fullscreen.addEventListener("click", () => {
      const action = document.fullscreenElement ? document.exitFullscreen() : viewer.requestFullscreen();
      action.catch(() => {});
    });
    document.addEventListener("fullscreenchange", () => {
      fullscreen.textContent = document.fullscreenElement === viewer ? "Exit full screen" : "Full screen";
    });
    apply();
  }
}
