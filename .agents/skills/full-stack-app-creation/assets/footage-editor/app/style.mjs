// Recording style panel: learn the open video's style, keep a library of
// styles, and toggle the loaded video into one of them. Progress and results
// arrive on the shared /events stream (see app/style_routes.py).
import {onStatus, progressBar} from "./status.mjs";

const $ = id => document.getElementById(id);
const learn = $("style-learn");
if (learn) setup();

function setup() {
  const cancel = $("style-cancel"), status = $("style-status"), name = $("style-name");
  const choice = $("style-choice"), toggle = $("style-apply"), applyStatus = $("style-apply-status");
  const list = $("style-list"), empty = $("style-empty");
  const result = $("style-result"), video = $("style-video"), home = $("style-preview-home");
  const match = $("style-match"), groups = $("style-groups").tBodies[0], clear = $("style-clear");
  const exportButton = $("style-export"), exportStatus = $("style-export-status");
  let exporting = false;
  const originalVideo = $("source"), picture = $("stage-content"), stage = picture?.parentElement;
  const bar = progressBar(status, "Recording style progress");
  const labels = {format: "Format and encoding", color: "Colour grade", texture: "Grain and sharpness",
    vignette: "Vignette", motion: "Camera motion", audio: "Sound", deep: "Deep look (CNN statistics)"};
  const remembered = "footage-editor-style-choice";
  let state = null, shownReport = null, libraryKey = "", requested = null;

  const post = async (path, headers = {}) => {
    const response = await fetch(path, {method: "POST", headers});
    const text = await response.text();
    if (!response.ok) throw new Error(text);
    return text;
  };
  const say = text => { status.textContent = text; };
  const busy = () => state && state.phase !== "idle";
  const report = () => state?.report;
  const ready = () => report() && report().style_id === choice.value;
  const inStage = () => video.parentElement === stage;

  // The styled video takes the editor stage's place while the toggle is on,
  // starting at the editor's playhead; turning it off returns to the editor there.
  function showInStage(visible) {
    if (!stage) return;
    if (visible && !inStage()) {
      if (stage.dataset.facePreview) $("face-stage-display").click();
      originalVideo?.pause();
      const time = originalVideo?.currentTime || 0;
      picture.hidden = true;
      stage.append(video);
      stage.dataset.stylePreview = "true";
      const seek = () => { if (inStage()) video.currentTime = Math.min(time, Math.max(0, (video.duration || time) - .01)); };
      if (video.readyState >= 1) seek();
      else video.addEventListener("loadedmetadata", seek, {once: true});
    } else if (!visible && inStage()) {
      video.pause();
      const time = video.currentTime;
      picture.hidden = false;
      delete stage.dataset.stylePreview;
      home.append(video);
      if (window.movementReview?.seekSeconds) window.movementReview.seekSeconds(time);
    }
  }

  async function render_style() {
    if (!toggle.checked || !choice.value) return;
    if (ready()) {
      applyStatus.textContent = `Showing the loaded video in “${choiceName()}”. Turn the switch off for the original.`;
      showInStage(true);
      return;
    }
    showInStage(false);
    if (busy()) {
      applyStatus.textContent = "Waiting for the current style task to finish.";
      return;
    }
    if (requested === choice.value) return;
    requested = choice.value;
    try {
      await post("/style/apply", {"X-Style-Id": choice.value});
      applyStatus.textContent = `Rendering the loaded video in “${choiceName()}”. The picture switches when it is ready.`;
    } catch (error) {
      applyStatus.textContent = error.message;
      requested = null;
    }
  }
  const choiceName = () => choice.selectedOptions[0]?.textContent || "";

  learn.addEventListener("click", async () => {
    learn.disabled = true;
    try {
      say(await post("/style/learn", {"X-Style-Name": encodeURIComponent(name.value).slice(0, 400)}));
    } catch (error) {
      say(error.message);
      learn.disabled = false;
    }
  });
  cancel.addEventListener("click", () => post("/style/cancel").catch(error => say(error.message)));
  clear.addEventListener("click", () => post("/style/clear").then(() => {
    toggle.checked = false;
    showInStage(false);
    applyStatus.textContent = "";
  }).catch(error => say(error.message)));
  toggle.addEventListener("change", () => {
    if (toggle.checked) render_style();
    else {
      showInStage(false);
      applyStatus.textContent = "Showing the original video.";
    }
  });
  choice.addEventListener("change", () => {
    try { localStorage.setItem(remembered, choice.value); } catch {}
    requested = null;
    if (toggle.checked) render_style();
  });

  exportButton.addEventListener("click", async () => {
    exporting = true;
    exportButton.disabled = true;
    exportStatus.textContent = "";
    try {
      const url = "/style/styles.zip", suggestedName = "footage-styles.zip";
      if (window.showSaveFilePicker) {
        const file = await window.showSaveFilePicker({suggestedName,
          types: [{description: "Saved recording styles", accept: {"application/zip": [".zip"]}}]});
        const response = await fetch(url);
        if (!response.ok) throw new Error("Could not export the saved styles. Refresh the library and retry.");
        const writable = await file.createWritable();
        await response.body.pipeTo(writable);
        exportStatus.textContent = "Saved " + file.name + ".";
      } else {
        const link = document.createElement("a");
        link.href = url;
        link.download = suggestedName;
        link.click();
        exportStatus.textContent = "Download requested. Your browser’s download settings control the destination.";
      }
    } catch (error) {
      exportStatus.textContent = error.name === "AbortError" ? "Export cancelled." : error.message;
    } finally {
      exporting = false;
      exportButton.disabled = !state?.library?.length;
    }
  });

  function outcomeText(outcome) {
    if (!outcome) return "";
    switch (outcome.kind) {
      case "duplicate":
        return `We already have this ability: it matches “${outcome.name}” at ${outcome.match.toFixed(1)}% ` +
          `(${state.threshold}% or more counts as the same style), so nothing new was added.`;
      case "added":
        return `Learned “${outcome.name}”. ` + (outcome.closest ?
          `Closest existing style: “${outcome.closest.name}” at ${outcome.closest.match.toFixed(1)}%.` :
          "It is the first style in the library.");
      case "rendered":
        return `Rendered in “${outcome.name}”: the result measures ${outcome.match.toFixed(1)}% like the style.`;
      case "cancelled":
        return "Cancelled.";
      default:
        return outcome.message || "The style task failed.";
    }
  }

  function renderLibrary(library) {
    const key = JSON.stringify(library) + busy();
    if (key === libraryKey) return;
    libraryKey = key;
    let saved = choice.value;
    if (!saved) try { saved = localStorage.getItem(remembered) || ""; } catch {}
    choice.replaceChildren(...(library.length ? library.map(entry => new Option(entry.name, entry.id)) :
      [new Option("No saved styles", "")]));
    choice.value = library.some(entry => entry.id === saved) ? saved : library[0]?.id || "";
    exportButton.disabled = exporting || !library.length;
    choice.disabled = toggle.disabled = !library.length;
    if (!library.length && toggle.checked) {
      toggle.checked = false;
      showInStage(false);
    }
    list.replaceChildren(...library.map(entry => {
      const item = document.createElement("li");
      const title = document.createElement("span");
      title.className = "style-name";
      title.textContent = entry.name;
      const summary = document.createElement("span");
      summary.className = "style-summary";
      summary.textContent = entry.summary;
      const row = document.createElement("div");
      row.className = "row";
      const use = document.createElement("button");
      use.type = "button";
      use.textContent = "Apply to loaded video";
      use.disabled = busy();
      use.addEventListener("click", () => {
        choice.value = entry.id;
        choice.dispatchEvent(new Event("change"));
        if (!toggle.checked) {
          toggle.checked = true;
          toggle.dispatchEvent(new Event("change"));
        }
      });
      const remove = document.createElement("button");
      remove.type = "button";
      remove.textContent = "Delete";
      remove.disabled = busy();
      remove.addEventListener("click", async () => {
        if (!window.confirm(`Delete the learned style “${entry.name}”?`)) return;
        try {
          say(await post("/style/delete", {"X-Style-Id": entry.id}));
        } catch (error) {
          say(error.message);
        }
      });
      row.append(use, remove);
      item.append(title, summary, row);
      return item;
    }));
    empty.hidden = library.length > 0;
  }

  function renderReport(current) {
    result.hidden = !current;
    if (!current) {
      showInStage(false);
      if (shownReport) video.removeAttribute("src");
      shownReport = null;
      return;
    }
    const key = JSON.stringify(current);
    if (key === shownReport) return;
    shownReport = key;
    // A query string makes the browser fetch the new result after a re-render.
    video.src = "/style/result.mp4?" + encodeURIComponent(current.style_id + "-" + current.frames + "-" + Date.now());
    match.textContent = `Rendered in “${current.style}”: ${current.width}×${current.height}, ` +
      `${Number(current.fps).toFixed(3).replace(/\.?0+$/, "")} fps, ${current.frames} frames` +
      `${current.audio ? ", with sound" : ""}. Measured against the style: ${current.match.toFixed(1)}%.`;
    groups.replaceChildren(...Object.entries(current.groups).filter(([, value]) => value !== null).map(([group, value]) => {
      const row = document.createElement("tr");
      const label = document.createElement("td"), score = document.createElement("td");
      label.textContent = labels[group] || group;
      score.textContent = value.toFixed(1) + "%";
      row.append(label, score);
      return row;
    }));
  }

  function render() {
    if (!state) return;
    const running = busy();
    learn.disabled = running;
    cancel.hidden = !running;
    if (running) {
      bar.show(state, state.progress || (state.phase === "learning" ? "Learning the style" :
        state.phase === "rendering" ? "Rendering in the style" : "Cancelling"));
    } else {
      bar.hide();
      if (state.outcome) say(outcomeText(state.outcome));
      if (state.outcome?.kind === "error" || state.outcome?.kind === "cancelled") requested = null;
    }
    renderLibrary(state.library || []);
    renderReport(report());
    if (toggle.checked) {
      if (ready()) render_style();
      else if (inStage()) showInStage(false);
      else if (!running && requested !== choice.value) render_style();
    }
  }

  onStatus(({style}) => {
    if (!style) return;
    state = style;
    render();
  });
}
