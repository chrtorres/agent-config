import {setupViewers} from "./viewer-size.mjs";

function hasFiles(event) {
  return Array.from(event.dataTransfer?.types ?? []).includes("Files");
}

export function setupMediaDrops(root = document) {
  for (const zone of root.querySelectorAll("[data-media-drop]")) {
    const input = zone.querySelector("input");
    const title = zone.querySelector("[data-drop-title]");
    const hint = zone.querySelector("[data-drop-hint]");
    const status = zone.parentElement.querySelector("[data-drop-status]");
    const emptyTitle = title.textContent;
    const update = () => {
      title.textContent = input.files[0]?.name || emptyTitle;
      hint.textContent = input.files.length ? "Choose a different file" : "or choose a file";
      status.textContent = "";
    };
    input.addEventListener("change", update);
    input.form.addEventListener("reset", () => queueMicrotask(update));
    zone.addEventListener("dragover", event => {
      if (!hasFiles(event)) return;
      event.preventDefault();
      zone.classList.toggle("is-dragging", !input.disabled);
      event.dataTransfer.dropEffect = input.disabled ? "none" : "copy";
    });
    zone.addEventListener("dragleave", event => {
      if (!(event.relatedTarget instanceof Node) || !zone.contains(event.relatedTarget))
        zone.classList.remove("is-dragging");
    });
    zone.addEventListener("drop", event => {
      zone.classList.remove("is-dragging");
      if (!hasFiles(event)) return;
      event.preventDefault();
      if (input.disabled) return;
      const files = event.dataTransfer.files;
      if (files.length !== 1) {
        status.textContent = "Drop one video or image.";
        return;
      }
      const file = files[0];
      const media = /^(image|video)\//i.test(file.type) ||
        /\.(apng|avif|bmp|gif|3gp|asf|avi|flv|heic|heif|ico|jpe?g|m2ts|m3u8?|m4v|mkv|mov|mp4|mpe?g|mts|mxf|nut|ogv|png|svg|tiff?|ts|vob|webm|webp|wmv)$/i.test(file.name);
      if (!media) {
        status.textContent = "Choose a video or image file.";
        return;
      }
      // The editor no longer converts other containers, so its upload zone takes MP4 videos only.
      const video = /^video\//i.test(file.type) || !/^image\//i.test(file.type) && !/\.(apng|avif|bmp|gif|heic|heif|ico|jpe?g|png|svg|tiff?|webp)$/i.test(file.name);
      if ("mp4Only" in zone.dataset && video && !(/^video\/mp4$/i.test(file.type) || /\.(mp4|m4v)$/i.test(file.name))) {
        status.textContent = "Choose an MP4 video. Other video formats are not converted.";
        return;
      }
      // Reuse the same change handlers as the file dialog, including local preview and cleanup.
      input.files = files;
      input.dispatchEvent(new Event("change", {bubbles:true}));
    });
  }
}

for (const type of ["dragover", "drop"]) {
  document.addEventListener(type, event => {
    if (hasFiles(event)) event.preventDefault();
  });
}
setupMediaDrops();
setupViewers();
const theme = document.querySelector("#theme");
const systemDark = matchMedia("(prefers-color-scheme: dark)");
const themeKey = "footage-editor-theme";

function applyTheme() {
  document.documentElement.dataset.theme = theme.value === "system"
    ? (systemDark.matches ? "dark" : "light")
    : theme.value;
}

const saved = localStorage.getItem(themeKey);
theme.value = [...theme.options].some(option => option.value === saved) ? saved : "dark";
applyTheme();
systemDark.addEventListener("change", applyTheme);
theme.addEventListener("change", () => {
  localStorage.setItem(themeKey, theme.value);
  applyTheme();
});

const tabs = [...document.querySelectorAll('[role="tab"]')];
function selectTab(selected) {
  for (const tab of tabs) {
    const active = tab === selected;
    tab.setAttribute("aria-selected", active);
    tab.tabIndex = active ? 0 : -1;
    document.getElementById(tab.getAttribute("aria-controls")).hidden = !active;
  }
}

for (const [index, tab] of tabs.entries()) {
  tab.addEventListener("click", () => selectTab(tab));
  tab.addEventListener("keydown", event => {
    const next = {ArrowLeft: (index + tabs.length - 1) % tabs.length,
      ArrowRight: (index + 1) % tabs.length, Home: 0, End: tabs.length - 1}[event.key];
    if (next === undefined) return;
    event.preventDefault();
    selectTab(tabs[next]);
    tabs[next].focus();
  });
}

const clear = document.querySelector("#clear-video");
if (clear) {
  fetch("/clear", {method: "HEAD"}).then(response => {
    clear.hidden = !response.ok;
  }).catch(() => {});
  const channel = new BroadcastChannel("footage-editor-session");
  const returnToUpload = () => window.location.replace("/");
  channel.addEventListener("message", returnToUpload);
  clear.addEventListener("click", async () => {
    if (!window.confirm("Clear the current video and discard its edits?")) return;
    clear.disabled = true;
    try {
      const response = await fetch("/clear", {method: "POST"});
      if (!response.ok) throw new Error(await response.text());
      channel.postMessage("cleared");
      returnToUpload();
    } catch (error) {
      const status = document.querySelector("#workspace-status");
      status.textContent = error.message;
      status.hidden = false;
      clear.disabled = false;
    }
  });
}
