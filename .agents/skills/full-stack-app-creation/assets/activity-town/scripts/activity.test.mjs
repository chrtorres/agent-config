import assert from 'node:assert/strict';
import { randomUUID } from 'node:crypto';
import { mkdtemp, mkdir, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { test } from 'node:test';
import { createActivityReader } from './activity.mjs';

async function fixture(t) {
  const now = new Date();
  const year = String(now.getFullYear());
  const month = String(now.getMonth() + 1).padStart(2, '0');
  const day = String(now.getDate()).padStart(2, '0');
  const home = await mkdtemp(join(tmpdir(), 'activity-town-activity-'));
  t.after(() => rm(home, { recursive: true, force: true }));
  const workspace = join(home, 'workspace');
  const logs = join(home, 'sessions', year, month, day);
  await mkdir(logs, { recursive: true });
  const date = [year, month, day].join('-');
  const id = randomUUID();

  function event(type, payload) {
    return JSON.stringify({ timestamp: now.toISOString(), type, payload }) + '\n';
  }

  function writeSession(session, cwd, filenameTime, extra = '') {
    return writeFile(join(logs, `rollout-${date}T${filenameTime}-${session}.jsonl`),
      event('session_meta', { id: session, cwd }) +
      event('event_msg', { type: 'task_started' }) +
      event('response_item', { type: 'function_call', name: 'image_gen' }) +
      extra);
  }

  return { home, workspace, id, event, writeSession };
}

test('A large tool output preserves the preceding activity on relay startup', async (t) => {
  const { home, workspace, id, event, writeSession } = await fixture(t);
  await writeSession(id, workspace, '10-00-00',
    event('response_item', { type: 'function_call_output', output: 'x'.repeat(640 * 1024) }));
  const read = createActivityReader({ codexHome: home, workspace, sessionId: id });
  const result = await read();
  assert.equal(result.source, 'live');
  assert.equal(result.session.state, 'working');
  assert.equal(result.session.location, 'pictures');
  assert.equal(Object.hasOwn(result.session, 'output'), false);
});

test('Newer log filenames from another workspace cannot hide the active session', async (t) => {
  const { home, workspace, id, writeSession } = await fixture(t);
  await writeSession(id, workspace, '08-00-00');
  await Promise.all(Array.from({ length: 53 }, () =>
    writeSession(randomUUID(), join(home, 'unrelated'), '10-00-00')
  ));
  const read = createActivityReader({ codexHome: home, workspace, sessionId: '' });
  const result = await read();
  assert.equal(result.source, 'live');
  assert.equal(result.session.location, 'pictures');
});
