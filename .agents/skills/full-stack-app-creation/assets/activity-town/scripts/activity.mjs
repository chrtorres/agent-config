import { createHash } from 'node:crypto';
import { constants } from 'node:fs';
import { open, readdir, stat } from 'node:fs/promises';
import { homedir } from 'node:os';
import { basename, dirname, isAbsolute, join, relative, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const projectRoot = fileURLToPath(new URL('../', import.meta.url));
const metadataLimit = 256 * 1024;
const eventLimit = 8 * 1024 * 1024;
const discoveryDays = 7;
const discoveryInterval = 2500;
const autoSessionLifetime = 30 * 60 * 1000;
const workTimeout = 5 * 60 * 1000;
const idleState = { state: 'idle', location: 'office', label: 'At Town Hall' };
const workingState = { state: 'working', location: 'office', label: 'Working at Town Hall' };

function defaultWorkspace() {
  const project = resolve(projectRoot);
  const creations = dirname(dirname(project));
  if (/^version-\d+$/.test(basename(project)) && basename(creations) === 'creations') {
    return dirname(creations);
  }
  return project;
}

function logDirectory(root, date) {
  const year = String(date.getFullYear());
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return join(root, 'sessions', year, month, day);
}

async function findLogs(root, now, sessionId) {
  const directories = new Set();
  const date = new Date(now);
  for (let day = 0; day < discoveryDays; day++) {
    directories.add(logDirectory(root, date));
    date.setDate(date.getDate() - 1);
  }

  // UUIDv7 session identifiers also encode the rollout's start date.
  if (sessionId && /^[a-f\d]{8}-[a-f\d]{4}-7[a-f\d]{3}-(?:[a-f\d]{4}-)[a-f\d]{12}$/i.test(sessionId)) {
    const started = new Date(Number.parseInt(sessionId.slice(0, 13).replace('-', ''), 16));
    for (const offset of [-1, 0, 1]) {
      const adjacent = new Date(started);
      adjacent.setDate(adjacent.getDate() + offset);
      directories.add(logDirectory(root, adjacent));
    }
  }

  const results = await Promise.all([...directories].map(async (directory) => {
    const entries = await readdir(directory, { withFileTypes: true }).catch(() => []);
    const names = entries.filter((entry) => entry.isFile())
      .map((entry) => entry.name)
      .filter((name) => /^rollout-[\dTZ:.-]+-[\da-f-]+\.jsonl$/i.test(name))
      .filter((name) => !sessionId || name.endsWith(`-${sessionId}.jsonl`));
    return Promise.all(names.map(async (name) => {
      const path = join(directory, name);
      const details = await stat(path).catch(() => null);
      return details?.isFile() ? { path, modified: details.mtimeMs } : null;
    }));
  }));
  return results.flat().filter(Boolean)
    .filter(({ modified }) => sessionId || now - modified < autoSessionLifetime)
    .sort((left, right) => right.modified - left.modified);
}

async function readBytes(file, length, start) {
  const buffer = Buffer.alloc(length);
  const { bytesRead } = await file.read(buffer, 0, length, start);
  return buffer.subarray(0, bytesRead);
}

function parseLine(line) {
  try {
    return JSON.parse(line);
  } catch {
    return null;
  }
}

function withinWorkspace(workspace, cwd) {
  if (typeof cwd !== 'string' || !isAbsolute(cwd)) return false;
  const fromWorkspace = relative(workspace, cwd);
  return !isAbsolute(fromWorkspace) && fromWorkspace.split(/[\\/]/)[0] !== '..';
}

async function readMetadata(file, size, workspace, requestedId) {
  const buffer = await readBytes(file, Math.min(size, metadataLimit), 0);
  const end = buffer.indexOf(10);
  if (end === -1) return null;
  const entry = parseLine(buffer.toString('utf8', 0, end));
  const meta = entry?.type === 'session_meta' ? entry.payload : null;
  const id = meta?.id ?? meta?.session_id;
  if (typeof id !== 'string' || !withinWorkspace(workspace, meta?.cwd)) return null;
  if (requestedId) return id === requestedId ? id : null;
  if (meta.parent_thread_id || meta.source?.subagent ||
      (meta.agent_path && meta.agent_path !== '/root')) return null;
  return id;
}

function toolState(tool) {
  const name = typeof tool.name === 'string' ? tool.name : '';
  if (/^(?:image_gen|imagegen|image_query|view_image|mcp__codex_apps__.*__image_\w+)$/.test(name) ||
      (tool.namespace === 'image_gen' && name === 'imagegen')) {
    return { state: 'working', location: 'pictures', label: 'Working with images' };
  }
  if (/^mcp__codex_apps__(?:codex_document_control|microsoft_outlook_email|sharepoint|google_drive)__/.test(name) ||
      /^(?:read_document|search_documents|edit_document)$/.test(name)) {
    return { state: 'working', location: 'documents', label: 'Working with documents' };
  }
  if (/^(?:exec|exec_command|apply_patch|write_stdin)$/.test(name)) {
    return { state: 'working', location: 'workshop', label: 'Running development tools' };
  }
  return null;
}

function readActivity(entry, previous, now) {
  const observed = Date.parse(entry?.timestamp);
  if (!Number.isFinite(observed) || observed > now + 30_000 ||
      observed < (previous?.observed ?? 0)) return previous;
  const type = entry.payload?.type;
  let state;
  if (entry.type === 'event_msg') {
    if (type === 'task_started' || type === 'turn_started') state = workingState;
    if (type === 'task_complete' || type === 'turn_completed' || type === 'turn_aborted') state = idleState;
  } else if (entry.type === 'response_item') {
    if (type === 'function_call' || type === 'custom_tool_call') {
      state = toolState(entry.payload) ?? (previous?.state === 'working' ? previous : workingState);
    }
    if (previous?.state === 'working' &&
        (type === 'function_call_output' || type === 'custom_tool_call_output' || type === 'reasoning')) {
      state = previous;
    }
  }
  return state ? { ...state, observed } : previous;
}

async function updateLog(file, size, fileState, now) {
  const remembered = size < fileState.offset ? { ...fileState, offset: 0, activity: null } : fileState;
  const minimum = Math.max(0, size - eventLimit);
  const start = Math.max(remembered.offset, minimum);
  if (start >= size) return remembered;

  // Rollouts are appended during a turn. Preserve incomplete records for the next poll.
  const startsOnRecord = start === remembered.offset;
  const readStart = startsOnRecord ? start : start - 1;
  const buffer = await readBytes(file, size - readStart, readStart);
  const first = startsOnRecord ? 0 : buffer.indexOf(10) + 1;
  const last = buffer.lastIndexOf(10);
  if ((!startsOnRecord && first === 0) || last < first) return remembered;
  let activity = remembered.activity;
  for (const line of buffer.toString('utf8', first, last).split('\n')) {
    activity = readActivity(parseLine(line), activity, now);
  }
  return { ...remembered, offset: readStart + last + 1, activity };
}

export function createActivityReader({
  codexHome = process.env.ACTIVITY_TOWN_CODEX_HOME || process.env.CODEX_HOME || join(homedir(), '.codex'),
  workspace = process.env.ACTIVITY_TOWN_WORKSPACE || defaultWorkspace(),
  sessionId = process.env.ACTIVITY_TOWN_SESSION_ID ??
    (process.env.ACTIVITY_TOWN_CODEX_HOME ? undefined : process.env.CODEX_SESSION_ID),
  clock = Date.now,
} = {}) {
  const workspacePath = resolve(workspace);
  const root = resolve(codexHome);
  let selected = null;
  let lastDiscovery = -Infinity;
  let reading = null;

  async function inspect(path, now, cached = null) {
    let file;
    try {
      const flags = constants.O_RDONLY | (constants.O_NOFOLLOW ?? 0) | (constants.O_NONBLOCK ?? 0);
      file = await open(path, flags);
      const details = await file.stat();
      if (!details.isFile() || (!sessionId && now - details.mtimeMs >= autoSessionLifetime)) return null;
      const remembered = cached?.identity === details.ino ? cached : null;
      const id = remembered?.id ?? await readMetadata(file, details.size, workspacePath, sessionId);
      if (!id) return null;
      return await updateLog(file, details.size, remembered ?? {
        path,
        id,
        identity: details.ino,
        offset: 0,
        activity: null,
      }, now);
    } catch {
      return null;
    } finally {
      await file?.close();
    }
  }

  async function snapshot() {
    const now = clock();
    if (selected) selected = await inspect(selected.path, now, selected);
    const currentActivity = selected?.activity?.observed ?? 0;
    // A pinned session stays selected. In automatic mode, only newer activity can take over.
    if (!selected?.activity || (!sessionId && now - lastDiscovery >= discoveryInterval)) {
      lastDiscovery = now;
      for (const candidate of await findLogs(root, now, sessionId)) {
        if (candidate.modified < currentActivity) break;
        if (candidate.path === selected?.path) continue;
        const alternative = await inspect(candidate.path, now);
        if (alternative?.activity && alternative.activity.observed > currentActivity) {
          selected = alternative;
          break;
        }
      }
    }
    if (!selected?.activity) return { source: 'demo' };
    const { observed, ...state } = selected.activity;
    const expired = state.state === 'working' && now - observed > workTimeout;
    // Expose classified activity only. The session record stays on the server.
    return {
      source: 'live',
      session: {
        id: createHash('sha256').update(selected.id).digest('hex').slice(0, 12),
        ...(expired ? idleState : state),
        updatedAt: new Date(expired ? observed + workTimeout : observed).toISOString(),
      },
    };
  }

  return async function read() {
    reading ??= snapshot().finally(() => { reading = null; });
    return reading;
  };
}

export function isLoopbackHost(host) {
  return /^(?:localhost|127\.0\.0\.1|\[::1\])(?::\d+)?$/i.test(host ?? '');
}

export function createActivityHandler(options) {
  const read = createActivityReader(options);
  return async function activityHandler(request, response, next) {
    if (request.url?.split('?')[0] !== '/api/activity') return next();
    const headers = {
      'Cache-Control': 'no-store',
      'Content-Type': 'application/json; charset=utf-8',
      'Cross-Origin-Resource-Policy': 'same-origin',
      'X-Content-Type-Options': 'nosniff',
    };
    const protocol = request.socket.encrypted ? 'https' : 'http';
    const { host, origin } = request.headers;
    if (!isLoopbackHost(host) || (origin && origin !== `${protocol}://${host}`)) {
      response.writeHead(403, headers).end('{"error":"Local access required"}');
      return;
    }
    if (request.method !== 'GET') {
      response.writeHead(405, { ...headers, Allow: 'GET' }).end('{"error":"Method not allowed"}');
      return;
    }
    const activity = await read().catch(() => ({ source: 'demo' }));
    response.writeHead(200, headers).end(JSON.stringify(activity));
  };
}
