import { places } from './places.js';

const paths = {
  logo: '<path d="m12 2.5 9 5v9l-9 5-9-5v-9l9-5Z"/><path d="m3.5 7.8 8.5 4.8 8.5-4.8M12 12.6V21m-4.4-16 8.7 4.8"/>',
  bot: '<rect x="4" y="7" width="16" height="13" rx="5"/><path d="M12 7V4m-2-1h4M2 12v4m20-4v4m-13-2h.01m6 0h.01"/>',
  office: '<path d="M3 21h18M6 21V5l10-2v18m0-13h3v13M9 8h3m-3 4h3m-3 4h3"/>',
  folder: '<path d="M3 17V7a2 2 0 0 1 2-2h5l2 2h7a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2Z"/><path d="M3 10h18"/>',
  picture: '<rect x="3" y="4" width="18" height="16" rx="3"/><circle cx="9" cy="9" r="1.4"/><path d="m4 17 4-4 3.2 2.8 4.2-5 5.1 4.7"/>',
  tool: '<path d="M14.7 6.3a4.7 4.7 0 0 0-6.5 5.8l-5 5a2.1 2.1 0 0 0 3 3l5-5a4.7 4.7 0 0 0 5.8-6.5l-2.8 2.8-2.1-2.1 2.6-3Z"/><path d="M18 3v3m1.5-1.5h-3m3 10v3m1.5-1.5h-3"/>',
  arrow: '<path d="m9 6 6 6-6 6"/>',
  down: '<path d="m6 9 6 6 6-6"/>',
  layers: '<path d="m12 3 9 5-9 5-9-5 9-5Zm-9 9 9 5 9-5M3 16l9 5 9-5"/>',
  follow: '<circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/><path d="M12 2v3m0 14v3M2 12h3m14 0h3"/>',
  overview: '<path d="m3 6 6-3 6 3 6-3v15l-6 3-6-3-6 3V6Zm6-3v15m6-12v15"/>',
  reset: '<path d="M4 11a8 8 0 1 1 2.7 7m-2.7-7V5m0 6h6"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  minus: '<path d="M5 12h14"/>',
  pin: '<path d="M19 10c0 5-7 10-7 10s-7-5-7-10a7 7 0 0 1 14 0Z"/><circle cx="12" cy="10" r="2"/>',
  play: '<path fill="currentColor" stroke="none" d="M8 4.8v14.4L20 12 8 4.8Z"/>',
  pause: '<path d="M9 5v14m6-14v14"/>',
  mouse: '<rect x="6" y="3" width="12" height="18" rx="6"/><path d="M12 7v3"/>',
  sliders: '<path d="M4 7h5m4 0h7M4 17h9m4 0h3"/><circle cx="11" cy="7" r="2"/><circle cx="15" cy="17" r="2"/>',
  compass: '<circle cx="12" cy="12" r="9"/><path d="m15.5 8.5-2 5-5 2 2-5 5-2Z"/>'
};

export function icon(name, size = 20) {
  return `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${paths[name]}</svg>`;
}

function buildingRow([key, place]) {
  return `<button class="building-row" data-testid="building-${key}" data-building="${key}" type="button">
    <span class="place-icon ${place.color}">${icon(place.icon, 20)}</span>
    <span class="building-text"><strong>${place.name}</strong><small>${place.detail}</small></span>
    <span class="place-arrow">${icon('arrow', 16)}</span>
  </button>`;
}

function marker([key, place]) {
  return `<button type="button" class="building-marker ${place.color}" data-marker="${key}" aria-label="View ${place.name}" hidden>
    ${icon(place.icon, 14)}<span>${place.name}</span>
  </button>`;
}

export function renderInterface(root) {
  root.innerHTML = `
    <header class="top-bar">
      <div class="brand">
        <span class="brand-icon">${icon('logo', 25)}</span>
        <div><span class="brand-name">Activity Town</span><span class="brand-tagline">Your workspace in 3D</span></div>
      </div>
      <span class="source" data-testid="status-source" data-source="pending"><i></i>Connecting</span>
    </header>

    <main class="workspace" aria-label="Activity Town">
      <aside class="sidebar" aria-label="Agent and buildings">
        <section class="agent-section" aria-labelledby="agent-heading">
          <h2 id="agent-heading">Your agent</h2>
          <div class="agent-card">
            <div class="agent-identity">
              <div class="avatar">${icon('bot', 27)}</div>
              <div class="agent-name"><strong>Codex</strong><small><i></i><span data-testid="agent-status">Ready</span></small></div>
              <button data-testid="demo-play" class="icon-button playback" type="button" aria-label="Play demo activity" title="Play demo activity" hidden>${icon('play', 18)}</button>
            </div>
            <div class="agent-location">${icon('pin', 16)}<span data-testid="agent-location">Town Hall</span></div>
          </div>
        </section>
        <section class="buildings-section" aria-labelledby="buildings-heading">
          <h2 id="buildings-heading">Buildings</h2>
          <div class="building-list">${Object.entries(places).map(buildingRow).join('')}</div>
        </section>
        <section class="activity-section" aria-labelledby="activity-heading">
          <h2 id="activity-heading">Current activity</h2>
          <div class="activity-summary"><span class="activity-dot"></span><p id="activity-message">Waiting for activity</p></div>
        </section>
      </aside>

      <section class="stage" data-testid="town-view" aria-labelledby="stage-heading">
        <canvas class="town-canvas" data-testid="town-canvas" tabindex="0" aria-label="Interactive 3D town. Use arrow keys to pan."></canvas>
        <div class="scene-markers">
          ${Object.entries(places).map(marker).join('')}
          <span class="agent-marker" data-testid="agent-marker" hidden><i></i>Codex</span>
        </div>
        <div class="stage-header">
          <div class="stage-heading"><span>${icon('compass', 16)} AERIAL VIEW</span><h1 id="stage-heading">Town view</h1></div>
          <button data-testid="floor-view" type="button" class="floor-button" title="Cycle the Town Hall floor view">
            ${icon('layers', 17)}<span>Both floors</span>${icon('down', 13)}
          </button>
        </div>
        <div id="render-error" class="render-error" role="alert" hidden>Activity Town needs WebGL 2 to display the scene.</div>
        <div class="stage-footer">
          <div class="view-hint">${icon('mouse', 17)} <span>Drag to orbit <b>·</b> Scroll to zoom</span></div>
          <button data-testid="camera-menu" class="camera-toggle" type="button" aria-expanded="false" aria-controls="view-menu">${icon('sliders', 16)} Camera</button>
          <div class="camera-panel" data-testid="view-menu" id="view-menu">
            <div class="camera-modes" aria-label="Camera view">
              <button data-testid="follow-camera" type="button" aria-pressed="true">${icon('follow', 16)} Follow agent</button>
              <button data-testid="overview-camera" type="button" aria-pressed="false">${icon('overview', 15)} Overview</button>
            </div>
            <div class="camera-adjust">
              <label class="height-control"><span>Height</span><input data-testid="camera-height" type="range" min="19" max="79" value="42" aria-label="Camera height" /></label>
              <div class="zoom-controls" aria-label="Zoom and reset">
                <button class="icon-button" data-testid="camera-zoom-out" type="button" aria-label="Zoom out" title="Zoom out">${icon('minus', 16)}</button>
                <button class="icon-button" data-testid="camera-zoom-in" type="button" aria-label="Zoom in" title="Zoom in">${icon('plus', 16)}</button>
                <button class="icon-button" data-testid="camera-reset" type="button" aria-label="Reset camera" title="Reset camera">${icon('reset', 16)}</button>
              </div>
            </div>
          </div>
        </div>
      </section>
    </main>
  `;
}
