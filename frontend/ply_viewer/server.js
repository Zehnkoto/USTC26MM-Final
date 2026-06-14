import fs from 'node:fs';
import http from 'node:http';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createServer as createViteServer } from 'vite';
import { buildPresetList, PRESET_PATHS } from './server/presets.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const port = Number(process.env.PORT || 5178);
const host = '127.0.0.1';
const isPreview = process.argv.includes('--preview');

function sendJson(res, statusCode, payload) {
  res.writeHead(statusCode, { 'Content-Type': 'application/json; charset=utf-8' });
  res.end(JSON.stringify(payload));
}

function sendPly(req, res) {
  const requestUrl = new URL(req.url, `http://${req.headers.host}`);
  const targetPath = requestUrl.searchParams.get('path');

  if (!targetPath || !PRESET_PATHS.includes(targetPath)) {
    sendJson(res, 403, { error: 'Only configured preset PLY paths can be loaded through this API.' });
    return;
  }

  if (!fs.existsSync(targetPath)) {
    sendJson(res, 404, { error: 'Preset PLY file does not exist on this machine.' });
    return;
  }

  res.writeHead(200, {
    'Content-Type': 'application/octet-stream',
    'Content-Disposition': `inline; filename="${path.basename(targetPath)}"`
  });
  fs.createReadStream(targetPath).pipe(res);
}

async function main() {
  const vite = await createViteServer({
    root: __dirname,
    server: { middlewareMode: true },
    appType: 'spa'
  });

  const server = http.createServer(async (req, res) => {
    try {
      if (req.url?.startsWith('/api/presets')) {
        sendJson(res, 200, buildPresetList(fs.existsSync));
        return;
      }

      if (req.url?.startsWith('/api/ply')) {
        sendPly(req, res);
        return;
      }

      if (isPreview) {
        const staticPath = path.join(__dirname, 'dist', req.url === '/' ? 'index.html' : decodeURIComponent(req.url || ''));
        if (staticPath.startsWith(path.join(__dirname, 'dist')) && fs.existsSync(staticPath) && fs.statSync(staticPath).isFile()) {
          fs.createReadStream(staticPath).pipe(res);
          return;
        }
      }

      vite.middlewares(req, res);
    } catch (error) {
      sendJson(res, 500, { error: error instanceof Error ? error.message : String(error) });
    }
  });

  server.listen(port, host, () => {
    console.log(`SfM/MVS point cloud viewer: http://${host}:${port}`);
  });
}

main();
