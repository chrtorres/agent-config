import {onStatus, progressBar} from "./status.mjs";

// Start (or join) the 4K build and resolve when it is verified. Progress arrives on the
// shared status stream; the build request returns immediately instead of being re-sent.
export async function ensureUhd(onProgress = () => {}) {
  if ((await fetch("/4k.mp4", {method:"HEAD"})).ok) return;
  const response = await fetch("/prepare-4k", {method:"POST"});
  if (response.status === 200) return;
  if (response.status !== 202) throw new Error(await response.text());
  // Ignore snapshots from before this request, such as an earlier failed attempt.
  const attempt = Number(response.headers.get("X-Footage-Attempt"));
  await new Promise((resolve, reject) => {
    const stop = onStatus(({uhd}) => {
      if (uhd.attempt < attempt) return;
      if (uhd.phase === "building") {
        onProgress(uhd);
      } else if (uhd.phase === "ready") {
        stop();
        resolve();
      } else {
        // Failed, or idle because the session was cleared during this attempt.
        stop();
        reject(new Error(uhd.message || "4K preparation stopped. Retry 4K."));
      }
    });
  });
}

const video = document.querySelector("#uhd-video");
if (video) {
  const status = document.querySelector("#uhd-status");
  const retry = document.querySelector("#uhd-retry");
  const bar = progressBar(status, "4K build progress");
  async function prepare() {
    status.textContent = "Preparing and verifying 4K playback…";
    retry.hidden = true;
    bar.show(null);
    try {
      await ensureUhd(progress => bar.show(progress));
      video.src = "/4k.mp4";
      document.querySelector("#uhd-download").hidden = false;
      status.textContent = "";
    } catch (error) {
      status.textContent = error.message;
      retry.hidden = false;
    } finally {
      bar.hide();
    }
  }
  retry.addEventListener("click", prepare);
  prepare();
}
