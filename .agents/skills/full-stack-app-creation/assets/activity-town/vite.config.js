import { fileURLToPath } from 'node:url';
import { defineConfig } from 'vite';
import { createActivityHandler } from './scripts/activity.mjs';

export default defineConfig({
  envPrefix: [],
  publicDir: false,
  server: {
    host: '127.0.0.1',
    cors: false,
    fs: {
      allow: [fileURLToPath(new URL('.', import.meta.url))],
      deny: ['.env', '.env.*', '*.{crt,key,pem,p12,pfx,jsonl}', '**/.git/**', '**/review/**']
    }
  },
  preview: { host: '127.0.0.1', cors: false },
  plugins: [{
    name: 'activity-town-activity',
    configureServer(server) {
      server.middlewares.use(createActivityHandler());
    },
    configurePreviewServer(server) {
      server.middlewares.use(createActivityHandler());
    }
  }]
});
