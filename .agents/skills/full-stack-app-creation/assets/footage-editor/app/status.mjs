// One shared server-sent event stream per page carries the status of every background task.
// It replaces per-feature polling: the server pushes a snapshot only when something changes.
const listeners = new Set();
let source;
let latest;

function connect() {
  if (source || document.hidden || !listeners.size) return;
  source = new EventSource("/events");
  source.onmessage = event => {
    try {
      latest = JSON.parse(event.data);
    } catch {
      return;
    }
    for (const listener of listeners) listener(latest);
  };
  // EventSource reconnects by itself after errors, using the server's retry interval.
}

function disconnect() {
  source?.close();
  source = undefined;
}

// Background tabs release their connection and catch up when shown again.
document.addEventListener("visibilitychange", () => (document.hidden ? disconnect() : connect()));
window.addEventListener("pagehide", disconnect);

export function onStatus(listener) {
  listeners.add(listener);
  if (latest) queueMicrotask(() => listeners.has(listener) && listener(latest));
  connect();
  return () => {
    listeners.delete(listener);
    if (!listeners.size) disconnect();
  };
}

export function formatDuration(seconds) {
  if (!Number.isFinite(seconds)) return "";
  const total = Math.max(1, Math.round(seconds));
  if (total < 60) return `${total} s`;
  const minutes = Math.floor(total / 60);
  if (minutes < 60) return `${minutes} min${total % 60 ? ` ${total % 60} s` : ""}`;
  return `${Math.floor(minutes / 60)} h ${minutes % 60} min`;
}

export function describeProgress(info) {
  if (!info || !Number.isFinite(info.percent)) return "";
  const parts = [`${Math.floor(info.percent)}%`];
  if (info.percent >= 100) return parts[0];
  parts.push(Number.isFinite(info.eta) ? `about ${formatDuration(info.eta)} left` : "estimating time left");
  return parts.join(" · ");
}

// A labeled progress bar placed after `anchor`. Unknown progress shows an indeterminate bar.
export function progressBar(anchor, label) {
  const wrapper = document.createElement("div");
  wrapper.className = "job-progress";
  wrapper.hidden = true;
  const bar = document.createElement("progress");
  bar.max = 100;
  bar.setAttribute("aria-label", label);
  const text = document.createElement("span");
  text.className = "job-progress-text";
  wrapper.append(bar, text);
  anchor.after(wrapper);
  return {
    show(info, stage = "") {
      wrapper.hidden = false;
      if (info && Number.isFinite(info.percent)) bar.value = info.percent;
      else bar.removeAttribute("value");
      const detail = describeProgress(info);
      text.textContent = [stage, detail].filter(Boolean).join(" — ");
    },
    hide() {
      wrapper.hidden = true;
      bar.removeAttribute("value");
      text.textContent = "";
    },
    remove() {
      wrapper.remove();
    },
  };
}
