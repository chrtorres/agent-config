import '@fontsource-variable/dm-sans';
import './style.css';
import { icon, renderInterface } from './interface.js';
import { places } from './places.js';
import { createTown } from './town.js';

const root = document.querySelector('#app');
renderInterface(root);

const testId = (name) => root.querySelector(`[data-testid="${name}"]`);
const sourceBadge = testId('status-source');
const status = testId('agent-status');
const locationLabel = testId('agent-location');
const activityMessage = root.querySelector('#activity-message');
const playback = testId('demo-play');
const follow = testId('follow-camera');
const overview = testId('overview-camera');
const heightInput = testId('camera-height');
const floor = testId('floor-view');
const cameraMenu = testId('camera-menu');
const buildingButtons = [...root.querySelectorAll('[data-building]')];
const markers = Object.fromEntries([...root.querySelectorAll('[data-marker]')].map((element) => [element.dataset.marker, element]));
const demoTasks = {
  office: 'Planning at Town Hall',
  documents: 'Reviewing project documents',
  pictures: 'Organizing reference images',
  workshop: 'Running a development task'
};
const demoOrder = Object.keys(demoTasks);
const floorModes = [['both', 'Both floors'], ['ground', 'Ground floor'], ['upper', 'Upper floor']];

let town;
let source = 'pending';
let arriving = false;
let destination = 'office';
let latestActivity = { state: 'idle', location: 'office', label: 'Waiting for activity' };
let demoPlaying = true;
let demoTimer;
let demoIndex = 0;
let floorIndex = 0;

function refreshStatus() {
  locationLabel.textContent = arriving ? `To ${places[destination].name}` : places[destination].name;
  const working = latestActivity.state === 'working';
  status.textContent = source === 'offline' ? 'Last known location' : arriving ? 'Traveling' : working ? 'Working' : 'Idle';
  status.dataset.working = String(source !== 'offline' && (working || arriving));
  activityMessage.textContent = source === 'offline' ? 'Waiting for the local activity feed' : latestActivity.label;
  for (const button of buildingButtons) {
    if (button.dataset.building === destination) button.setAttribute('aria-current', 'location');
    else button.removeAttribute('aria-current');
  }
  town?.setWorking(working && source !== 'offline');
}

function transition(activity) {
  if (activity.location !== destination) {
    destination = activity.location;
    arriving = town?.sendTo(destination) ?? false;
  }
  latestActivity = activity;
  refreshStatus();
}

function arrived(place) {
  if (place === destination) {
    arriving = false;
    refreshStatus();
  }
}

try {
  town = createTown(testId('town-canvas'), heightInput, markers, testId('agent-marker'), arrived);
} catch (error) {
  console.error('Could not display the 3D town.', error);
  root.querySelector('#render-error').hidden = false;
}

function queueDemo() {
  clearTimeout(demoTimer);
  if (source === 'demo' && demoPlaying) {
    demoTimer = setTimeout(() => {
      demoIndex = (demoIndex + 1) % demoOrder.length;
      selectDemoPlace(demoOrder[demoIndex]);
    }, 19_000);
  }
}

function selectDemoPlace(place) {
  demoIndex = demoOrder.indexOf(place);
  transition({ state: 'working', location: place, label: demoTasks[place] });
  queueDemo();
}

function setSource(next) {
  if (source === next) return;
  source = next;
  const demo = next === 'demo';
  sourceBadge.dataset.source = next;
  const label = {
    demo: ['Demo activity', 'Showing sample tasks from a local demo'],
    live: ['Live session', 'Following a local Codex session'],
    offline: ['Activity feed offline', 'Showing the last known destination']
  }[next];
  sourceBadge.innerHTML = `<i></i>${label[0]}`;
  sourceBadge.title = label[1];
  playback.hidden = !demo;
  if (demo) {
    if (demoPlaying) selectDemoPlace('office');
    else transition({ state: 'idle', location: 'office', label: 'Demo activity paused' });
  } else if (next === 'offline') refreshStatus();
  queueDemo();
}

async function pollActivity() {
  try {
    const response = await fetch('/api/activity', { cache: 'no-store', signal: AbortSignal.timeout(3000) });
    if (!response.ok) throw new Error('Activity source unavailable');
    const activity = await response.json();
    if (activity.source === 'live' && Object.hasOwn(places, activity.session?.location)) {
      setSource('live');
      transition(activity.session);
    } else if (activity.source === 'demo') setSource('demo');
    else throw new Error('Activity source returned an unexpected status');
  } catch {
    if (source === 'live') setSource('offline');
    else if (source === 'pending') setSource('demo');
  } finally {
    setTimeout(pollActivity, 1550);
  }
}

function setCamera(mode, place) {
  const tracking = mode === 'follow';
  follow.setAttribute('aria-pressed', String(tracking));
  overview.setAttribute('aria-pressed', String(!tracking));
  if (place) town?.showPlace(place);
  else town?.setCamera(mode);
}

function selectPlace(place) {
  if (source === 'demo') selectDemoPlace(place);
  else setCamera('overview', place);
}

function setPlayback(value) {
  demoPlaying = value;
  const label = value ? 'Pause demo activity' : 'Play demo activity';
  playback.setAttribute('aria-label', label);
  playback.title = label;
  playback.innerHTML = icon(value ? 'pause' : 'play', 18);
}

for (const button of buildingButtons) {
  button.addEventListener('click', () => selectPlace(button.dataset.building));
}
for (const [place, button] of Object.entries(markers)) {
  button.addEventListener('click', () => selectPlace(place));
}
playback.addEventListener('click', () => {
  setPlayback(!demoPlaying);
  if (demoPlaying) selectDemoPlace(destination);
  else transition({ state: 'idle', location: destination, label: 'Demo activity paused' });
  queueDemo();
});
floor.addEventListener('click', () => {
  floorIndex = (floorIndex + 1) % floorModes.length;
  const [mode, label] = floorModes[floorIndex];
  floor.querySelector('span').textContent = label;
  town?.setFloor(mode);
});
follow.addEventListener('click', () => setCamera('follow'));
overview.addEventListener('click', () => setCamera('overview'));
heightInput.addEventListener('input', () => town?.setHeight(Number(heightInput.value)));
testId('camera-zoom-in').addEventListener('click', () => town?.zoom(true));
testId('camera-zoom-out').addEventListener('click', () => town?.zoom(false));
testId('camera-reset').addEventListener('click', () => town?.resetCamera());
cameraMenu.addEventListener('click', () => {
  cameraMenu.setAttribute('aria-expanded', String(cameraMenu.getAttribute('aria-expanded') !== 'true'));
});

setPlayback(demoPlaying);
refreshStatus();
pollActivity();
