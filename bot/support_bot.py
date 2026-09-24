"""Отдельный бот поддержки: запускается в том же процессе, что и основной.

Токен админ вставляет в Mini App (админка → «Бот поддержки»); он хранится в
настройках и подхватывается на старте. Смена токена перезапускает бота без
перезапуска сервера.
"""
from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from bot.database.engine import async_session
from bot.handlers.support import make_router
from bot.services import settings_service

logger = logging.getLogger(__name__)

_bot: Bot | None = None
_dp: Dispatcher | None = None
_task: asyncio.Task | None = None


class BadToken(Exception):
    pass


async def check_token(token: str) -> str:
    """username бота по токену или BadToken."""
    try:
        probe = Bot(token=token)
    except Exception as exc:  # noqa: BLE001 — неверный формат токена
        raise BadToken from exc
    try:
        return (await probe.get_me()).username
    except Exception as exc:  # noqa: BLE001 — токен отозван/не существует
        raise BadToken from exc
    finally:
        await probe.session.close()


async def stop() -> None:
    global _bot, _dp, _task
    if _dp is not None:
        try:
            await _dp.stop_polling()
        except Exception:  # noqa: BLE001 — поллинг мог ещё не стартовать
            pass
    if _task is not None:
        _task.cancel()
    if _bot is not None:
        await _bot.session.close()
    _bot = _dp = _task = None


async def start(token: str) -> None:
    global _bot, _dp, _task
    await stop()
    _bot = Bot(token=token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    _dp = Dispatcher()
    _dp.include_router(make_router(standalone=True))
    await _bot.delete_webhook(drop_pending_updates=False)
    _task = asyncio.create_task(_dp.start_polling(_bot, handle_signals=False))
    logger.info("Бот поддержки @%s запущен", (await _bot.get_me()).username)


async def start_from_settings() -> None:
    async with async_session() as session:
        token = await settings_service.get_setting(session, settings_service.SUPPORT_BOT_TOKEN)
    if not token:
        return
    try:
        await start(token)
    except Exception:  # noqa: BLE001 — основной бот должен работать и без поддержки
        logger.warning("Не удалось запустить бота поддержки", exc_info=True)


async def support_username() -> str | None:
    async with async_session() as session:
        return await settings_service.get_setting(session, settings_service.SUPPORT_BOT_USERNAME)
