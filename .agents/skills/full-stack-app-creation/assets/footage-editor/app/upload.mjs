import {onStatus, progressBar} from "./status.mjs";

const form = document.querySelector("#upload-form");
const picker = document.querySelector("#upload-file");
const button = document.querySelector("#upload-button");
const status = document.querySelector("#upload-status");
const clearPreview = document.querySelector("#quick-clear");
const job = document.querySelector("#upload-job");
const cancel = document.querySelector("#cancel-preparation");
const thumbnail = document.querySelector("#upload-thumbnail");
const placeholder = document.querySelector("#upload-thumbnail-placeholder");
const preview = document.querySelector("#quick-video");
let requestActive = false;
let uploading = false;
let phase = "idle";
const bar = progressBar(job, "Preparation progress");

function drawThumbnail() {
  if (!requestActive || preview.readyState < 2 || !preview.videoWidth) return;
  const scale = Math.min(thumbnail.width / preview.videoWidth, thumbnail.height / preview.videoHeight);
  const width = preview.videoWidth * scale;
  const height = preview.videoHeight * scale;
  thumbnail.getContext("2d").drawImage(preview, (thumbnail.width-width)/2, (thumbnail.height-height)/2, width, height);
  thumbnail.hidden = false;
  placeholder.hidden = true;
}
preview.addEventListener("loadeddata", drawThumbnail);

function renderJob() {
  const busy = phase !== "idle";
  picker.disabled = button.disabled = clearPreview.disabled = requestActive || busy;
  job.hidden = !requestActive && !busy;
  cancel.disabled = !busy || phase === "cancelling";
  if (job.hidden) {
    thumbnail.width = thumbnail.width;
    thumbnail.hidden = true;
    placeholder.hidden = false;
  }
}

function showProgress(preparation) {
  if (uploading) return;
  if (phase === "preparing") bar.show(preparation, preparation.stage && preparation.stage !== "Receiving video" ?
    preparation.stage : "Preparing video");
  else bar.hide();
}

// Preparation status arrives on the shared event stream rather than by polling.
onStatus(({preparation}) => {
  const next = preparation.phase;
  if (next === "cancelling") status.textContent = "Cancelling preparation…";
  else if (next === "preparing") {
    if (!requestActive && !uploading) status.textContent = "A previous upload is still preparing.";
    else if (!uploading) status.textContent = "Preparing video for editing. Keep this page open.";
  }
  else if (next === "idle" && phase !== "idle" && !requestActive)
    status.textContent = "Ready for a video.";
  phase = next;
  showProgress(preparation);
  renderJob();
});

cancel.addEventListener("click", async () => {
  phase = "cancelling";
  renderJob();
  status.textContent = "Cancelling preparation…";
  try {
    const response = await fetch("/cancel", {method:"POST"});
    if (!response.ok) throw new Error("Could not cancel preparation. Try again.");
  } catch (error) {
    status.textContent = error.message;
  }
});

picker.addEventListener("change", () => { status.textContent = ""; });

form.addEventListener("submit", event => {
  event.preventDefault();
  const file = picker.files[0];
  if (!file || button.disabled || button.hidden) return;

  requestActive = true;
  renderJob();
  drawThumbnail();
  status.textContent = "Uploading video…";
  const request = new XMLHttpRequest();
  request.open("POST", "/upload");
  request.setRequestHeader("Content-Type", "application/octet-stream");
  uploading = true;
  request.upload.addEventListener("progress", event => {
    if (event.lengthComputable) bar.show({percent: 100 * event.loaded / event.total, eta: null}, "Uploading video");
  });
  request.upload.addEventListener("load", () => {
    uploading = false;
    status.textContent = "Preparing video for editing. Keep this page open.";
    bar.show(null, "Preparing video");
  });

  function retry(message) {
    requestActive = uploading = false;
    phase = "idle";
    status.textContent = message;
    bar.hide();
    renderJob();
  }

  request.addEventListener("load", () => {
    if (request.status === 200) {
      window.location.replace("/");
    } else {
      if (request.status === 409 && request.responseText.startsWith("Preparation cancelled.")) {
        picker.value = "";
        picker.dispatchEvent(new Event("change"));
      }
      retry(request.responseText || "Upload failed. Try again.");
      if (request.getResponseHeader("X-Footage-Mode") === "preview") {
        document.querySelector("#quick-heading").focus({preventScroll:true});
      }
    }
  });
  request.addEventListener("error", () => retry("Connection lost. Reload the page to check your session."));
  request.send(file);
});
