import {downloadVideo, saveMedia} from "./media-download.mjs";
import {onStatus, progressBar} from "./status.mjs";

const byId = id => document.getElementById(id);
const picker = byId("upload-file");
const review = byId("quick-review");
const video = byId("quick-video");
const image = byId("quick-image");
const transport = review.querySelector(".quick-transport");
const frame = review.querySelector("[data-view-frame]");
const seekRow = review.querySelector(".quick-seek");
const upload = byId("upload-button");
const play = byId("quick-play");
const seek = byId("quick-seek");
const status = byId("quick-status");
const speed = byId("quick-speed");
const original = byId("quick-original");
const [zoom, light, contrast, color] = ["zoom", "light", "contrast", "color"].map(id => byId("quick-" + id));
const sliders = [zoom, light, contrast, color];
let url;

function apply() {
  const comparison = original.getAttribute("aria-pressed") === "true";
  for (const media of [video, image]) {
    media.style.transform = comparison ? "" : `scale(${zoom.valueAsNumber / 100})`;
    media.style.filter = comparison ? "" :
      `brightness(${light.value}%) contrast(${contrast.value}%) saturate(${color.value}%)`;
  }
}

function reset() {
  for (const control of sliders) control.value = "100";
  speed.value = "1";
  video.playbackRate = 1;
  original.setAttribute("aria-pressed", "false");
  original.textContent = "Show original";
  apply();
}

function release() {
  video.pause();
  video.removeAttribute("src");
  image.removeAttribute("src");
  video.load();
  if (url) URL.revokeObjectURL(url);
  url = undefined;
  seek.max = seek.value = "0";
  frame.style.removeProperty("--media-aspect");
  frame.removeAttribute("data-media-size");
  byId("quick-time").value = "";
  status.hidden = true;
  review.hidden = true;
}

function setMediaAspect(width, height) {
  if (!width || !height) return;
  frame.style.setProperty("--media-aspect", width / height);
  frame.setAttribute("data-media-size", "");
}
video.addEventListener("loadedmetadata", () => setMediaAspect(video.videoWidth, video.videoHeight));
image.addEventListener("load", () => setMediaAspect(image.naturalWidth, image.naturalHeight));

function showError(message) {
  status.textContent = message;
  status.hidden = false;
}

picker.addEventListener("change", () => {
  release();
  reset();
  const file = picker.files[0];
  upload.hidden = false;
  if (!file) return;
  // The preview reads the selected file directly in the browser. Only the separate preparation form uploads it.
  url = URL.createObjectURL(file);
  const still = file.type.startsWith("image/") || /\.(avif|bmp|gif|jpe?g|png|svg|webp)$/i.test(file.name);
  image.hidden = !still;
  video.hidden = transport.hidden = seekRow.hidden = upload.hidden = still;
  (still ? image : video).src = url;
  review.hidden = false;
});
byId("quick-clear").addEventListener("click", () => {
  picker.value = "";
  picker.dispatchEvent(new Event("change"));
});
document.getElementById("upload-form").addEventListener("submit", () => video.pause());
window.addEventListener("pagehide", release);

play.addEventListener("click", () => {
  if (video.paused) video.play().catch(() => showError("This video could not play in the local preview."));
  else video.pause();
});
function clock(seconds) {
  if (!Number.isFinite(seconds)) return "0:00";
  return Math.floor(seconds / 60) + ":" + String(Math.floor(seconds % 60)).padStart(2, "0");
}
function sync() {
  seek.max = Number.isFinite(video.duration) ? video.duration : 0;
  seek.value = video.currentTime;
  byId("quick-time").value = `${clock(video.currentTime)} / ${clock(video.duration)}`;
  play.textContent = video.paused ? "Play preview" : "Pause preview";
}
for (const event of ["loadedmetadata", "durationchange", "timeupdate", "play", "pause"]) {
  video.addEventListener(event, sync);
}
video.addEventListener("error", () => {
  if (url) {
    showError("This browser could not play this video. Footage Editor supports MP4 (H.264) videos.");
  }
});
image.addEventListener("error", () => {
  if (url && !image.hidden) showError("This image could not load in the local preview.");
});
seek.addEventListener("input", () => { video.currentTime = seek.valueAsNumber; });
for (const [id, offset] of [["back", -5], ["forward", 5]]) {
  byId("quick-" + id).addEventListener("click", () => {
    if (Number.isFinite(video.duration)) video.currentTime = Math.max(0, Math.min(video.duration, video.currentTime + offset));
  });
}
speed.addEventListener("change", () => { video.playbackRate = Number(speed.value); });
for (const control of sliders) control.addEventListener("input", apply);
original.addEventListener("click", () => {
  const show = original.getAttribute("aria-pressed") !== "true";
  original.setAttribute("aria-pressed", String(show));
  original.textContent = show ? "Show adjustments" : "Show original";
  apply();
});
byId("quick-reset").addEventListener("click", reset);

const download = byId("quick-download");
download.addEventListener("click", async () => {
  const selected = picker.files[0];
  if (!selected) return;
  const changes = sliders.map(control => control.valueAsNumber / 100);
  download.disabled = true;
  showError("Preparing download…");
  const bar = progressBar(status, "Download progress");
  const stop = onStatus(({export: job}) => { if (job.phase === "rendering") bar.show(job, "Rendering edits"); });
  try {
    if (!image.hidden) {
      if (!image.naturalWidth || !image.naturalHeight) throw new Error("Wait for the image to finish loading.");
      const canvas = document.createElement("canvas");
      const width = canvas.width = image.naturalWidth, height = canvas.height = image.naturalHeight;
      const context = canvas.getContext("2d");
      const [scale, brightness, contrast, saturation] = changes;
      context.filter = `brightness(${brightness}) contrast(${contrast}) saturate(${saturation})`;
      context.drawImage(image, (1-scale)*width/2, (1-scale)*height/2, scale*width, scale*height);
      const png = await new Promise(resolve => canvas.toBlob(resolve, "image/png"));
      if (!png) throw new Error("Could not encode the image.");
      saveMedia(png, "footage-edited.png");
    } else {
      await downloadVideo("/export-preview", selected, {"X-Footage-Adjustments": JSON.stringify(changes)});
    }
    status.hidden = true;
  } catch (error) {
    if (picker.files[0] === selected) showError(error.message);
  } finally {
    stop();
    bar.remove();
    download.disabled = false;
  }
});
