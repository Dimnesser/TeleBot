"""aiohttp-сервер Mini App: отдаёт статику (SPA) и API из webapp/api.py.

Запускается в том же процессе и event loop'е, что и long-polling бот (см.
bot/app.py) — оба используют один и тот же async_session/engine.
"""
from __future__ import annotations

import logging
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

    async def index(_request: web.Request) -> web.FileResponse:
        return web.FileResponse(STATIC_DIR / "index.html")

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
