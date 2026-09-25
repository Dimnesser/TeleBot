// Рендер баннера приветствия: node render.js → bot/assets/welcome.jpg (через PNG).
// Героя (Kraken) берёт в полном разрешении с Steal a Brainrot Wiki, шрифт
// Oswald лежит рядом. Нужен playwright (см. tools/case_renders/package.json).
const http = require('http');
const fs = require('fs');
const path = require('path');
const { execFileSync } = require('child_process');
const { chromium } = require('playwright');

const HERE = __dirname;
const HERO_URL = 'https://static.wikia.nocookie.net/stealabr/images/d/d3/Kraken.png/revision/latest?cb=20260616235047';
// node render.js          → bot/assets/welcome.jpg (баннер /start, 1280×656)
// node render.js avatar   → bot/assets/avatar.png (аватарка бота, 640×640) + favicon Mini App
// node render.js news     → bot/assets/news_logo.png (аватарка новостного канала, 640×640)
const MODE = ['avatar', 'news'].includes(process.argv[2]) ? process.argv[2] : 'welcome';
const OUT = path.resolve(HERE, {
  avatar: '../../bot/assets/avatar.png', news: '../../bot/assets/news_logo.png', welcome: '../../bot/assets/welcome.jpg',
}[MODE]);
const FAVICON = path.resolve(HERE, '../../webapp/static/assets/favicon.png');
const SIZE = MODE === 'welcome' ? { width: 1280, height: 656 } : { width: 640, height: 640 };

(async () => {
  const hero = path.join(HERE, 'kraken_crop.png');
  if (!fs.existsSync(hero)) {
    const raw = path.join(HERE, 'kraken.png');
    execFileSync('curl', ['-sL', '-A', 'Mozilla/5.0', '-o', raw, HERO_URL]);
    execFileSync('python3', ['-c', `from PIL import Image; im=Image.open(${JSON.stringify(raw)}); im.crop(im.getbbox()).save(${JSON.stringify(hero)})`]);
  }
  const server = http.createServer((req, res) => {
    fs.readFile(path.join(HERE, decodeURIComponent(req.url.split('?')[0])), (err, data) => {
      if (err) { res.writeHead(404); res.end(); return; }
      res.end(data);
    });
  });
  await new Promise((r) => server.listen(0, '127.0.0.1', r));
  const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH || undefined });
  const page = await browser.newPage({ viewport: SIZE });
  await page.goto(`http://127.0.0.1:${server.address().port}/${MODE}.html`, { waitUntil: 'networkidle' });
  await page.evaluate(() => document.fonts.ready);
  const png = path.join(HERE, `${MODE}.png`);
  await page.screenshot({ path: png });
  await browser.close();
  server.close();
  if (MODE === 'avatar') {
    execFileSync('python3', ['-c', `from PIL import Image; im=Image.open(${JSON.stringify(png)}).convert('RGB'); im.save(${JSON.stringify(OUT)}); im.resize((192,192), Image.LANCZOS).save(${JSON.stringify(FAVICON)})`]);
  } else if (MODE === 'news') {
    execFileSync('python3', ['-c', `from PIL import Image; Image.open(${JSON.stringify(png)}).convert('RGB').save(${JSON.stringify(OUT)})`]);
  } else {
    execFileSync('python3', ['-c', `from PIL import Image; Image.open(${JSON.stringify(png)}).convert('RGB').save(${JSON.stringify(OUT)}, 'JPEG', quality=90, optimize=True)`]);
  }
  console.log('saved', OUT);
})();
