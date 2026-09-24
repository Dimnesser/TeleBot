// Рендерит модели кейсов: node drive.js <specs.json> <out_dir> [code ...]
// Поднимает локальный статик-сервер (render.html, three из node_modules,
// рендеры брейнротов из webapp/static/assets/brainrots) и снимает PNG
// с window.renderCase(spec) в headless Chromium (WebGL через SwiftShader).
const http = require('http');
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

const HERE = __dirname;
const ASSETS = path.resolve(HERE, '../../webapp/static/assets/brainrots');
const TYPES = { '.html': 'text/html', '.js': 'text/javascript', '.webp': 'image/webp', '.png': 'image/png' };

function serve() {
  const server = http.createServer((req, res) => {
    const url = decodeURIComponent(req.url.split('?')[0]);
    const file = url.startsWith('/brainrots/') ? path.join(ASSETS, url.slice('/brainrots/'.length)) : path.join(HERE, url);
    fs.readFile(file, (err, data) => {
      if (err) { res.writeHead(404); res.end(); return; }
      res.writeHead(200, { 'Content-Type': TYPES[path.extname(file)] || 'application/octet-stream' });
      res.end(data);
    });
  });
  return new Promise((resolve) => server.listen(0, '127.0.0.1', () => resolve(server)));
}

(async () => {
  const [specsPath, outDir, ...only] = process.argv.slice(2);
  const specs = JSON.parse(fs.readFileSync(specsPath, 'utf8')).filter((s) => !only.length || only.includes(s.code));
  const server = await serve();
  const browser = await chromium.launch({
    executablePath: process.env.CHROMIUM_PATH || undefined,
    args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'],
  });
  const page = await browser.newPage({ viewport: { width: 720, height: 600 } });
  page.on('pageerror', (e) => console.error('pageerror', e.message));
  await page.goto(`http://127.0.0.1:${server.address().port}/render.html`);
  await page.waitForFunction(() => window.ready === true, null, { timeout: 30000 });
  fs.mkdirSync(outDir, { recursive: true });
  for (const spec of specs) {
    const dataUrl = await page.evaluate((s) => window.renderCase(s), spec);
    fs.writeFileSync(path.join(outDir, `${spec.code}.png`), Buffer.from(dataUrl.split(',')[1], 'base64'));
    console.log('rendered', spec.code);
  }
  await browser.close();
  server.close();
})();
