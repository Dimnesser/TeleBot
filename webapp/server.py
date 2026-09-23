"""aiohttp-сервер Mini App: отдаёт статику (SPA) и API из webapp/api.py.

Запускается в том же процессе и event loop'е, что и long-polling бот (см.
bot/app.py) — оба используют один и тот же async_session/engine.
"""
from __future__ import annotations

import logging
import subprocess
from pathlib import Path

from aiogram import Bot
from aiohttp import web

from bot.config import config
from bot.database.engine import async_session
from bot.database.repo.users import get_or_create_user
from webapp.api import routes
from webapp.auth import InitDataError, WebAppUser, validate_init_data

logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).parent / "static"


def _build_version() -> str:
    """Версия для cache-busting query-параметров у статики.

    Telegram WebView кэширует HTML/JS/CSS мини-аппа по URL очень агрессивно
    (сильнее обычного мобильного браузера) — без версии в URL пользователь
    после редеплоя продолжает видеть старый JS/CSS, пока сам не почистит
    кэш Telegram. git-хэш меняется на каждый коммит, что и нужно."""
    try:
        return subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=Path(__file__).resolve().parent.parent,
            capture_output=True,
            text=True,
            timeout=5,
        ).stdout.strip() or "0"
    except Exception:
        return "0"


BUILD_VERSION = _build_version()


def _extract_init_data(request: web.Request) -> str:
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("tma "):
        return auth_header[4:]
    return request.headers.get("X-Telegram-Init-Data", "")


@web.middleware
async def auth_middleware(request: web.Request, handler):
    if not request.path.startswith("/api/"):
        return await handler(request)

    init_data = _extract_init_data(request)
    tg_user: WebAppUser | None = None

    if init_data:
        try:
            tg_user = validate_init_data(init_data, config.bot_token)
        except InitDataError as exc:
            return web.json_response({"error": f"invalid_init_data: {exc}"}, status=401)
    elif config.webapp_allow_dev_auth and "dev_tg_id" in request.query:
        tg_user = WebAppUser(
            tg_id=int(request.query["dev_tg_id"]),
            username=request.query.get("dev_username"),
            first_name=request.query.get("dev_first_name", "Dev"),
        )

    if tg_user is None:
        return web.json_response({"error": "unauthorized"}, status=401)

    async with async_session() as session:
        user = await get_or_create_user(session, tg_user.tg_id, tg_user.username, tg_user.first_name)
        request["session"] = session
        request["user"] = user
        return await handler(request)


def create_app(bot: Bot) -> web.Application:
    app = web.Application(middlewares=[auth_middleware])
    app["bot"] = bot
    app.add_routes(routes)
    app.router.add_static("/static/", STATIC_DIR, show_index=False)

    index_html = (STATIC_DIR / "index.html").read_text(encoding="utf-8")
    index_html = index_html.replace(
        'href="/static/css/app.css"', f'href="/static/css/app.css?v={BUILD_VERSION}"'
    ).replace(
        'src="/static/js/character-art.js"',
        f'src="/static/js/character-art.js?v={BUILD_VERSION}"',
    ).replace(
        'src="/static/js/app.js"', f'src="/static/js/app.js?v={BUILD_VERSION}"'
    )

    async def index(_request: web.Request) -> web.Response:
        return web.Response(
            text=index_html,
            content_type="text/html",
            headers={"Cache-Control": "no-store, must-revalidate"},
        )

    app.router.add_get("/", index)
    app.router.add_get("/webapp", index)
    app.router.add_get("/webapp/", index)
    return app


async def run_webapp(bot: Bot) -> None:
    app = create_app(bot)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, config.webapp_host, config.webapp_port)
    await site.start()
    logger.info("Mini App запущен на http://%s:%s", config.webapp_host, config.webapp_port)
