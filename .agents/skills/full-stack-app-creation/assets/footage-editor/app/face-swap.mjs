import {setupMediaDrops} from "./workspace.mjs";
import {onStatus, progressBar} from "./status.mjs";

const base = "/face-swap/";
const mount = document.getElementById("face-swap-mount");
const panel = await fetch(base + "panel.html");
if (panel.ok && mount) {
  mount.innerHTML = await panel.text();
  setupMediaDrops(mount);
  setup();
}

function setup() {
  const $ = id => document.getElementById(id);
  const tools = $("face-swap");
  const form = $("face-form");
  const source = $("face-portrait");
  const sourceIndex = $("face-source-index");
  const submit = $("face-run");
  const cancel = $("face-cancel");
  const clear = $("face-clear");
  const status = $("face-status");
  const section = $("face-result");
  const video = $("face-video");
  const display = $("face-display");
  const stageDisplay = $("face-stage-display");
  const monitor = $("face-monitor");
  const home = $("face-preview-home");
  const picker = $("upload-file");
  const originalVideo = $("source") || $("quick-video");
  const originalPicture = $("stage-content") || document.querySelector(".quick-picture");
  const stage = originalPicture?.parentElement;
  const prepared = $("stage-content") ? Symbol("prepared video") : null;
  const tab = $("tab-face");
  const targetPicker = $("face-target-picker");
  const targetPicture = $("face-target-picture");
  const zoomControl = $("face-zoom");
  const zoomReset = $("face-zoom-reset");
  const targetVideo = $("face-target-video");
  const targetImage = $("face-target-image");
  const resultImage = $("face-image-result");
  const targetTime = $("face-target-time");
  const marker = $("face-target-marker");
  const mask = $("face-target-mask");
  const curvature = $("face-curvature");
  const layers = $("face-depth-layers");
  const layerOptions = $("face-depth-options");
  const depthStatus = $("face-depth-status");
  let targetMedia;
  let targetUrl;
  let selected;
  let maskUrl;
  let selectedFrame;
  let loadingDepth = false;
  let selectionVersion = 0;
  let checkingMask = false;
  let cursor = [.5,.5];
  let displayedTime;
  let selectingDisabled = false;
  let zoom = 1;
  let pan = [0, 0];
  let drag;
  let suppressPick = false;
  const sourceVideo = $("face-source-video");
  const sourceControls = $("face-source-controls");
  const capture = $("face-capture");
  const still = $("face-still");
  let portrait;
  let sourceUrl;
  let stillUrl;
  let sending = false;
  let state = {phase:"idle"};
  let intendedTarget;
  let captureVersion = 0;
  const bar = progressBar(status, "Face Swap progress");
  let shownPhase = "idle";

  const isImage = file => Boolean(file && file !== prepared &&
    (file.type?.startsWith("image/") || /\.(avif|bmp|gif|jpe?g|png|webp|tiff?)$/i.test(file.name ?? "")));

  // The target is the editor's prepared video, or the video or still image open in Quick Review.
  function target() {
    if (prepared) return prepared;
    const file = picker?.files[0];
    return file && (isImage(file) || file.type.startsWith("video/") || /\.(mp4|m4v)$/i.test(file.name)) ? file : null;
  }

  // The element currently showing the target, and whether it has a decodable picture.
  const targetElement = () => (isImage(targetMedia) ? targetImage : targetVideo);
  const targetReady = () => isImage(targetMedia) ? targetImage.complete && targetImage.naturalWidth > 0 :
    !targetVideo.seeking && targetVideo.readyState >= 2;

  function paintMarker(point) {
    marker.style.left = (point[0] * 100) + "%";
    marker.style.top = (point[1] * 100) + "%";
    marker.hidden = false;
  }

  function paintZoom() {
    pan = pan.map(value => Math.max(1 - zoom, Math.min(0, value)));
    targetPicture.style.transform = `translate(${pan[0]*100}%, ${pan[1]*100}%) scale(${zoom})`;
    targetPicture.style.setProperty("--face-zoom", zoom);
    targetPicker.classList.toggle("is-zoomed", zoom > 1);
    zoomControl.value = zoom;
    $("face-zoom-value").value = zoom + "×";
    zoomReset.disabled = selectingDisabled || zoom === 1;
  }

  function resetZoom() {
    zoom = 1;
    pan = [0, 0];
    paintZoom();
  }

  function inCrop(point) {
    return point.map((value,index) => Math.min((1-pan[index])/zoom,Math.max(-pan[index]/zoom,value)));
  }

  zoomControl.addEventListener("input", () => {
    const next = zoomControl.valueAsNumber;
    const anchor = selected ? selected.slice(1) : [.5,.5].map((center,index) => (center-pan[index])/zoom);
    pan = pan.map((value,index) => value + (zoom-next)*anchor[index]);
    zoom = next;
    paintZoom();
  });
  zoomReset.addEventListener("click", resetZoom);

  function clearSelection() {
    selectionVersion++;
    selected = undefined;
    selectedFrame = undefined;
    loadingDepth = false;
    curvature.open = false;
    curvature.hidden = true;
    layers.replaceChildren();
    layers.hidden = true;
    layerOptions.replaceChildren();
    depthStatus.value = "";
    mask.hidden = true;
    mask.removeAttribute("src");
    if (maskUrl) URL.revokeObjectURL(maskUrl);
    maskUrl = undefined;
    marker.hidden = true;
    $("face-target-pick-status").value = "";
  }

  function setTargetMedia(media) {
    if (media === targetMedia) return;
    if (targetUrl) URL.revokeObjectURL(targetUrl);
    targetMedia = media;
    targetUrl = media && media !== prepared ? URL.createObjectURL(media) : null;
    clearSelection();
    displayedTime = undefined;
    cursor = [.5,.5];
    resetZoom();
    targetTime.value = "0";
    $("face-target-pick-status").value = "";
    marker.hidden = true;
    const still = isImage(media);
    targetImage.hidden = !still;
    targetVideo.hidden = still;
    $("face-target-frame").hidden = still;
    if (still) {
      targetVideo.removeAttribute("src");
      targetVideo.load();
      targetImage.src = targetUrl;
    } else if (media) {
      targetImage.removeAttribute("src");
      targetVideo.src = media === prepared ? "/video.mp4" : targetUrl;
    } else {
      targetImage.removeAttribute("src");
      targetVideo.removeAttribute("src");
      targetVideo.load();
    }
  }

  async function selectTarget(point) {
    if (selectingDisabled || checkingMask || !targetReady()) return;
    clearSelection();
    const id = selectionVersion;
    const still = isImage(targetMedia);
    const seconds = still ? 0 : displayedTime ?? targetVideo.currentTime;
    const position = [...point];
    paintMarker(point);
    $("face-target-pick-status").value = "Checking the selected face…";
    checkingMask = true;
    render();
    try {
      const canvas = document.createElement("canvas");
      const picture = targetElement();
      canvas.width = still ? picture.naturalWidth : picture.videoWidth;
      canvas.height = still ? picture.naturalHeight : picture.videoHeight;
      canvas.getContext("2d").drawImage(picture, 0, 0);
      const frame = await new Promise(resolve => canvas.toBlob(resolve,"image/png"));
      if (!frame || id !== selectionVersion) return;
      const response = await fetch(base + "mask", {
        method:"POST", headers:{"Content-Type":"image/png","X-Target-Point":JSON.stringify(position)}, body:frame,
      });
      if (!response.ok) throw new Error(await response.text());
      const overlay = await response.blob();
      if (id !== selectionVersion) return;
      maskUrl = URL.createObjectURL(overlay);
      mask.src = maskUrl;
      mask.hidden = false;
      selected = [seconds,...position];
      selectedFrame = frame;
      curvature.hidden = false;
      $("face-target-pick-status").value = still ? "Target face selected." : `Target face selected at ${seconds.toFixed(2)} s.`;
    } catch (error) {
      if (id === selectionVersion) $("face-target-pick-status").value = error.message || "Unable to preview the selected face.";
    } finally {
      checkingMask = false;
      render();
    }
  }

  function showDepth() {
    const visible = curvature.open && layers.childElementCount > 0;
    layers.hidden = !visible;
    mask.hidden = !maskUrl || visible;
  }

  curvature.addEventListener("toggle", async () => {
    showDepth();
    if (!curvature.open || !selectedFrame || loadingDepth || layers.childElementCount) return;
    const id = selectionVersion;
    loadingDepth = true;
    depthStatus.value = "Estimating facial curvature…";
    try {
      const response = await fetch(base + "mask", {
        method:"POST", body:selectedFrame,
        headers:{"Content-Type":"image/png","X-Face-Mask":"curvature",
                 "X-Target-Point":JSON.stringify(selected.slice(1))},
      });
      if (!response.ok) throw new Error(await response.text());
      const {width,height,bounds,bands} = await response.json();
      if (id !== selectionVersion) return;
      const [left,top,boxWidth,boxHeight] = bounds;
      for (const [index, png] of bands.entries()) {
        const image = document.createElement("img");
        image.alt = "";
        image.src = "data:image/png;base64," + png;
        image.style.left = `${100*left/width}%`;
        image.style.top = `${100*top/height}%`;
        image.style.width = `${100*boxWidth/width}%`;
        image.style.height = `${100*boxHeight/height}%`;
        layers.append(image);
        const label = document.createElement("label");
        const control = document.createElement("input");
        control.type = "checkbox";
        control.checked = true;
        control.addEventListener("change", () => { image.hidden = !control.checked; });
        label.append(control, String(index+1));
        control.setAttribute("aria-label", `Depth band ${index+1}`);
        layerOptions.append(label);
      }
      selectedFrame = undefined;
      depthStatus.value = "";
      showDepth();
    } catch (error) {
      if (id === selectionVersion) depthStatus.value = error.message || "Could not estimate facial curvature.";
    } finally {
      if (id === selectionVersion) loadingDepth = false;
    }
  });

  targetVideo.addEventListener("loadedmetadata", () => {
    targetTime.max = Number.isFinite(targetVideo.duration) ? targetVideo.duration : 0;
  });
  targetVideo.addEventListener("error", () => {
    if (targetMedia && !isImage(targetMedia)) $("face-target-pick-status").value = "Could not load the target video for face selection.";
  });
  targetImage.addEventListener("error", () => {
    if (isImage(targetMedia)) $("face-target-pick-status").value = "Could not load the target image for face selection.";
  });
  targetImage.addEventListener("load", render);
  if (targetVideo.requestVideoFrameCallback) {
    const trackFrame = (_, frame) => {
      displayedTime = frame.mediaTime;
      targetVideo.requestVideoFrameCallback(trackFrame);
    };
    targetVideo.requestVideoFrameCallback(trackFrame);
  }
  targetTime.addEventListener("input", () => {
    if (selectingDisabled || targetVideo.readyState < 1) return;
    displayedTime = undefined;
    clearSelection();
    render();
    targetVideo.currentTime = Math.min(targetTime.valueAsNumber, Math.max(0, targetVideo.duration-.02));
  });
  targetPicker.addEventListener("click", event => {
    if (suppressPick) {
      suppressPick = false;
      return;
    }
    const box = targetElement().getBoundingClientRect();
    if (!box.width || !box.height) return;
    const point = [(event.clientX-box.left)/box.width,(event.clientY-box.top)/box.height];
    if (point.every(value => value >= 0 && value <= 1)) {
      cursor = point;
      selectTarget(cursor);
    }
  });
  targetPicker.addEventListener("pointerdown", event => {
    if (!event.isPrimary || event.button !== 0) return;
    suppressPick = false;
    if (zoom > 1 && !selectingDisabled) {
      drag = {id:event.pointerId,x:event.clientX,y:event.clientY,start:[...pan],moved:false};
    }
  });
  targetPicker.addEventListener("pointermove", event => {
    if (drag?.id !== event.pointerId) return;
    const dx = event.clientX - drag.x, dy = event.clientY - drag.y;
    if (!drag.moved && Math.hypot(dx,dy) < 5) return;
    if (!drag.moved) targetPicker.setPointerCapture(event.pointerId);
    drag.moved = true;
    pan = [drag.start[0]+dx/targetPicker.clientWidth,drag.start[1]+dy/targetPicker.clientHeight];
    paintZoom();
  });
  for (const name of ["pointerup","pointercancel","lostpointercapture"]) {
    targetPicker.addEventListener(name, event => {
      if (drag?.id !== event.pointerId) return;
      suppressPick = drag.moved;
      drag = undefined;
    });
  }
  targetPicker.addEventListener("keydown", event => {
    if (selectingDisabled) return;
    const directions = {ArrowLeft:[-.02,0],ArrowRight:[.02,0],ArrowUp:[0,-.02],ArrowDown:[0,.02]};
    if (directions[event.key]) {
      event.preventDefault();
      event.stopPropagation();
      if (event.altKey) {
        pan = pan.map((value,index)=>value-directions[event.key][index]*4);
        paintZoom();
      } else {
        // Keep keyboard selection inside the visible crop at every zoom level.
        cursor = inCrop(cursor.map((value,index)=>value+directions[event.key][index]/zoom));
        paintMarker(cursor);
      }
    } else if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      event.stopPropagation();
      selectTarget(inCrop(cursor));
    }
  });

  function releaseSource() {
    captureVersion++;
    sourceVideo.pause();
    sourceVideo.removeAttribute("src");
    sourceVideo.load();
    still.removeAttribute("src");
    still.hidden = true;
    sourceControls.hidden = true;
    if (sourceUrl) URL.revokeObjectURL(sourceUrl);
    if (stillUrl) URL.revokeObjectURL(stillUrl);
    sourceUrl = stillUrl = portrait = undefined;
    $("face-capture-status").value = "";
  }

  const imageResult = () => state.report?.kind === "image";
  const previewShown = () => !(imageResult() ? resultImage : video).hidden;

  function canCompare() {
    if (prepared) return !imageResult() && state.report?.prepared_target !== false;
    return intendedTarget && target() === intendedTarget && !$("quick-review").hidden;
  }

  // Both views share a decoder and playhead. The small sidebar canvas only
  // copies presented frames while the comparison is visible.
  function paintMonitor() {
    if (monitor.hidden) return;
    const media = imageResult() ? resultImage : video;
    const width = media.videoWidth || media.naturalWidth;
    const height = media.videoHeight || media.naturalHeight;
    if (!width || !height || (media === video && media.readyState < 2)) return;
    const scale = Math.min(1, 440 / Math.max(width, height));
    const w = Math.max(1, Math.round(width * scale)), h = Math.max(1, Math.round(height * scale));
    if (monitor.width !== w || monitor.height !== h) {
      monitor.width = w;
      monitor.height = h;
    }
    monitor.getContext("2d").drawImage(media, 0, 0, w, h);
  }
  let frameCallback;
  function nextFrame() {
    paintMonitor();
    if (!monitor.hidden && video.parentElement === stage)
      frameCallback = video.requestVideoFrameCallback?.(nextFrame);
  }
  for (const event of ["loadeddata", "seeked", "timeupdate"]) video.addEventListener(event, paintMonitor);
  resultImage.addEventListener("load", paintMonitor);

  function showPreview(visible) {
    const media = imageResult() || resultImage.parentElement === stage ? resultImage : video;
    if (frameCallback !== undefined) video.cancelVideoFrameCallback(frameCallback);
    frameCallback = undefined;
    if (visible) {
      if (canCompare()) {
        const style = $("style-apply");
        if (style?.checked) style.click();
        originalVideo.pause();
        originalPicture.hidden = true;
        stage.append(media);
        stage.dataset.facePreview = "true";
        if (media === video) {
          const seek = () => {
            if (video.parentElement === stage) video.currentTime = originalVideo.currentTime;
          };
          if (video.readyState >= 1) seek();
          else video.addEventListener("loadedmetadata", seek, {once:true});
        }
      }
      if (!media.hasAttribute("src")) media.src = base + (media === video ? "preview.mp4" : "result.png");
    } else {
      video.pause();
      if (media.parentElement === stage) {
        if (media === video && video.readyState >= 2) {
          if (prepared) window.movementReview?.seekSeconds(video.currentTime);
          else if (originalVideo.readyState >= 1) originalVideo.currentTime = video.currentTime;
        }
        originalPicture.hidden = false;
        delete stage.dataset.facePreview;
        home.append(media);
      }
    }
    media.hidden = !visible;
    monitor.hidden = !(visible && media.parentElement === stage);
    if (!monitor.hidden) nextFrame();
    for (const button of [display, stageDisplay]) {
      button.setAttribute("aria-pressed", String(visible));
      button.textContent = visible ? "Show original" : "Show swap";
    }
  }

  function render() {
    const ready = state.phase === "ready";
    const active = sending || state.phase === "processing" || state.phase === "cancelling";
    const media = target();
    selectingDisabled = active || ready;
    if (!active && !ready && (media === targetMedia || (tools.open && !mount.hidden) || !media))
      setTargetMedia(media);
    if (ready) setTargetMedia(null);
    $("face-target-controls").hidden = !media;
    targetTime.disabled = selectingDisabled;
    zoomControl.disabled = selectingDisabled;
    zoomReset.disabled = selectingDisabled || zoom === 1;
    targetPicker.tabIndex = selectingDisabled ? -1 : 0;
    for (const indicator of [$("face-tab-status"),$("face-inline-status")].filter(Boolean)) {
      indicator.hidden = !active && !ready;
      indicator.textContent = active ? "Running" : ready ? "Ready" : "";
    }
    $("face-inputs").hidden = ready;
    submit.hidden = ready;
    for (const input of [source, sourceIndex]) input.disabled = active || ready;
    submit.disabled = active || ready || checkingMask || !media || !portrait || !selected;
    capture.disabled = active || ready || sourceVideo.seeking || sourceVideo.readyState < 2;
    cancel.hidden = !active;
    cancel.disabled = state.phase !== "processing";
    clear.hidden = !ready;
    section.hidden = !ready;
    stageDisplay.hidden = !ready || !canCompare();
    $("face-target-status").textContent = media ?
      (prepared ? "Target: the current editor video." :
        isImage(media) ? "Target: the image in Quick Review." : "Target: the video selected in Quick Review.") :
      (ready ? "" : "Open an MP4 or an image to use Face Swap.");
    const download = $("face-download");
    if (ready) {
      const result = state.report;
      const still = result.kind === "image";
      download.href = base + (still ? "result.png" : "result.mp4");
      download.download = still ? "face-swap.png" : "face-swap.mp4";
      download.textContent = still ? "Download lossless PNG" : "Download lossless MP4";
      $("face-report").textContent = still ? "Face swapped. Lossless PNG verified." :
        `${result.swapped} of ${result.frames} frames modified. Lossless export verified.`;
      status.textContent = "";
    } else {
      if (video.hasAttribute("src") || resultImage.hasAttribute("src")) showPreview(false);
      if (resultImage.hasAttribute("src")) {
        resultImage.hidden = true;
        resultImage.removeAttribute("src");
      }
      if (video.hasAttribute("src")) {
        video.removeAttribute("src");
        video.load();
      }
    }
    if (state.phase === "processing") {
      // Announce the run once so later redraws keep any newer message.
      if (shownPhase !== "processing") status.textContent = "Face Swap is running. You can keep using the other tools.";
      bar.show(state, state.progress || "Preparing Face Swap");
    } else bar.hide();
    shownPhase = state.phase;
    if (state.phase === "cancelling") status.textContent = "Cancelling Face Swap…";
  }

  // Job progress arrives on the shared status stream. After a user action, one request
  // refreshes the state immediately instead of waiting for the next pushed snapshot.
  let generation = 0;
  async function update() {
    const request = ++generation;
    try {
      const response = await fetch(base + "status", {cache:"no-store"});
      if (!response.ok || request !== generation) return;
      state = await response.json();
      render();
    } catch {
      if (request === generation) status.textContent = "Connection lost. Reopen Face Swap to check the job.";
    }
  }
  onStatus(({face}) => {
    if (!face) return;
    ++generation;
    state = face;
    render();
  });

  source.addEventListener("change", () => {
    releaseSource();
    const file = source.files[0];
    if (file && (file.type.startsWith("video/") || /\.(mp4|m4v|mov|webm)$/i.test(file.name))) {
      sourceUrl = URL.createObjectURL(file);
      sourceVideo.src = sourceUrl;
      sourceControls.hidden = false;
    } else if (file) {
      portrait = file;
      stillUrl = URL.createObjectURL(file);
      still.src = stillUrl;
      still.hidden = false;
    }
    render();
  });
  for (const event of ["loadeddata", "seeking", "seeked"]) sourceVideo.addEventListener(event, render);
  sourceVideo.addEventListener("error", () => {
    if (sourceUrl) $("face-capture-status").value = "This source video could not be decoded in the browser.";
  });
  capture.addEventListener("click", () => {
    sourceVideo.pause();
    const version = ++captureVersion;
    const time = sourceVideo.currentTime;
    const canvas = document.createElement("canvas");
    canvas.width = sourceVideo.videoWidth;
    canvas.height = sourceVideo.videoHeight;
    canvas.getContext("2d").drawImage(sourceVideo, 0, 0);
    canvas.toBlob(blob => {
      if (!blob || version !== captureVersion) return;
      if (stillUrl) URL.revokeObjectURL(stillUrl);
      portrait = blob;
      stillUrl = URL.createObjectURL(blob);
      still.src = stillUrl;
      still.hidden = false;
      $("face-capture-status").value = `Frame selected at ${time.toFixed(2)} s`;
      render();
    }, "image/png");
  });
  picker?.addEventListener("change", () => {
    if (previewShown()) showPreview(false);
    render();
  });
  tools.addEventListener("toggle", () => {
    if (tools.open) update();
    else {
      if (!stage.dataset.facePreview) showPreview(false);
      sourceVideo.pause();
    }
  });
  if (tab) {
    tools.querySelector(":scope > summary").hidden = true;
    new MutationObserver(() => {
      if (!mount.hidden) update();
      else {
        if (!stage.dataset.facePreview) showPreview(false);
        sourceVideo.pause();
      }
    }).observe(mount,{attributeFilter:["hidden"]});
  }
  for (const button of [display, stageDisplay]) {
    button.addEventListener("click", () => showPreview(!previewShown()));
  }
  video.addEventListener("error", () => {
    if (video.hasAttribute("src")) status.textContent = "Playback preview unavailable. The verified download is still available.";
  });

  form.addEventListener("submit", async event => {
    event.preventDefault();
    const media = target();
    if (submit.disabled || !media || !portrait || !selected) return;
    sourceVideo.pause();
    originalVideo?.pause();
    intendedTarget = media;
    sending = true;
    render();
    status.textContent = "Sending files to the local editor…";
    const headers = {
      "Content-Type":"application/octet-stream",
      "X-Portrait-Bytes":String(portrait.size),
      "X-Source-Index":String(sourceIndex.valueAsNumber - 1),
      "X-Target-Index":"0",
      "X-Target-Selection":JSON.stringify(selected),
    };
    if (media === prepared) headers["X-Footage-Target"] = "prepared";
    if (isImage(media)) headers["X-Target-Kind"] = "image";
    const response = fetch(base + "run", {
      method:"POST", headers, body:media === prepared ? portrait : new Blob([portrait, media]),
    });
    update();
    try {
      const result = await response;
      status.textContent = await result.text();
      if (result.ok) releaseSource();
    } catch {
      status.textContent = "Connection lost. Check the job before retrying.";
    } finally {
      sending = false;
      update();
    }
  });

  async function act(action, button) {
    button.disabled = true;
    try {
      const response = await fetch(base + action, {method:"POST"});
      if (response.ok && action === "clear") {
        showPreview(false);
        form.reset();
        releaseSource();
        intendedTarget = undefined;
      }
      status.textContent = await response.text();
    } catch {
      status.textContent = "Connection lost. Reopen Face Swap and try again.";
    } finally {
      button.disabled = false;
      update();
    }
  }

  cancel.addEventListener("click", () => act("cancel", cancel));
  clear.addEventListener("click", () => act("clear", clear));
  window.addEventListener("pagehide", () => {
    releaseSource();
    setTargetMedia(null);
  });
  function openTools() {
    if (location.hash === "#face-swap" && tab) tab.click();
    else if (location.hash === "#face-swap") tools.open = true;
  }
  window.addEventListener("hashchange", () => {
    openTools();
  });
  if (tab) tools.open = true;
  else mount.hidden = false;
  openTools();
  render();
  update();
}
