export function saveMedia(blob, filename) {
  const link = document.createElement("a");
  const url = URL.createObjectURL(blob);
  link.href = url;
  link.download = filename;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 15000);
}

export async function renderVideo(route, body, headers) {
  const response = await fetch(route, {method: "POST", headers, body});
  if (!response.ok) throw new Error(await response.text());
  return response.blob();
}

export async function downloadVideo(route, body, headers) {
  saveMedia(await renderVideo(route, body, headers), "footage-edited.mp4");
}
