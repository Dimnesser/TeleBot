"""Обработчики Telegram: команды, текст, фото, файлы, ошибки."""

from __future__ import annotations

import asyncio
import base64
import logging
from collections import defaultdict
from typing import Any

from telegram import Message, Update
from telegram.constants import ChatType
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from .config import Config
from .types import ModelError, Reply
from .history import HistoryStore, image_block, text_block
from .prompts import HELP_MESSAGE, START_MESSAGE, build_system_prompt
from .reply import ReplyStreamer, keep_typing

logger = logging.getLogger(__name__)

SUPPORTED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
TEXT_DOCUMENT_HINTS = (
    ".txt", ".md", ".csv", ".json", ".yaml", ".yml", ".py", ".js", ".ts",
    ".html", ".css", ".java", ".c", ".cpp", ".cs", ".go", ".rs", ".sql",
    ".sh", ".ini", ".toml", ".log", ".xml",
)

BUSY_MESSAGE = "Секунду, я ещё отвечаю на прошлый вопрос."
DENIED_MESSAGE = "Извини, у меня ограниченный доступ — этот чат не в списке разрешённых."
UNSUPPORTED_MESSAGE = (
    "Пока я понимаю только текст и картинки. "
    "Опиши вопрос словами или пришли скриншот."
)
EMPTY_QUESTION = "Напиши вопрос текстом — и я отвечу."
TOO_BIG_IMAGE = "Картинка слишком большая. Пришли файл поменьше или сожми его."
TOO_BIG_DOCUMENT = "Файл слишком большой. Пришли фрагмент текста или файл поменьше."
UNREADABLE_DOCUMENT = "Не смог прочитать файл как текст. Пришли .txt, .md или код."


class BotRuntime:
    """Связывает конфигурацию, историю и клиента модели."""

    def __init__(self, config: Config, claude: Any, history: HistoryStore) -> None:
        self.config = config
        self.claude = claude
        self.history = history
        self.system_prompt = build_system_prompt(web_search_enabled=config.web_search)
        self._locks: dict[int, asyncio.Lock] = defaultdict(asyncio.Lock)

    def lock_for(self, chat_id: int) -> asyncio.Lock:
        return self._locks[chat_id]


def _runtime(context: ContextTypes.DEFAULT_TYPE) -> BotRuntime:
    runtime = context.application.bot_data.get("runtime")
    if runtime is None:  # pragma: no cover — защита от неверной сборки приложения
        raise RuntimeError("BotRuntime не зарегистрирован в bot_data")
    return runtime


def _is_private(message: Message) -> bool:
    return message.chat.type == ChatType.PRIVATE


def should_answer(message: Message, bot_username: str | None) -> bool:
    """В группах отвечаем только на упоминание или ответ на наше сообщение."""
    if _is_private(message):
        return True
    reply_to = message.reply_to_message
    if reply_to is not None and reply_to.from_user and reply_to.from_user.is_bot:
        if bot_username and reply_to.from_user.username == bot_username:
            return True
    text = message.text or message.caption or ""
    if bot_username and f"@{bot_username}".lower() in text.lower():
        return True
    return False


def strip_mention(text: str, bot_username: str | None) -> str:
    if not bot_username:
        return text.strip()
    cleaned = text.replace(f"@{bot_username}", " ").replace(f"@{bot_username.lower()}", " ")
    return " ".join(cleaned.split())


async def _guard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> BotRuntime | None:
    """Проверяет доступ пользователя; отвечает отказом, если он закрыт."""
    runtime = _runtime(context)
    user = update.effective_user
    if runtime.config.is_allowed(user.id if user else None):
        return runtime
    if update.effective_message:
        await update.effective_message.reply_text(DENIED_MESSAGE)
    logger.info("Отказано в доступе пользователю %s", user.id if user else "?")
    return None


# --- команды ----------------------------------------------------------


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if await _guard(update, context) is None or update.effective_message is None:
        return
    await update.effective_message.reply_text(START_MESSAGE)


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if await _guard(update, context) is None or update.effective_message is None:
        return
    await update.effective_message.reply_text(HELP_MESSAGE, parse_mode="HTML")


async def cmd_reset(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    runtime = await _guard(update, context)
    if runtime is None or update.effective_message is None or update.effective_chat is None:
        return
    existed = await runtime.history.reset(update.effective_chat.id)
    await update.effective_message.reply_text(
        "Контекст очищен — начинаем с чистого листа."
        if existed
        else "История и так пустая. Спрашивай!"
    )


async def cmd_about(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    runtime = await _guard(update, context)
    if runtime is None or update.effective_message is None:
        return
    chats, messages = await runtime.history.stats()
    text = (
        "<b>Настройки бота</b>\n"
        f"{runtime.config.describe()}\n"
        f"Активных диалогов: <code>{chats}</code>, сообщений в памяти: <code>{messages}</code>"
    )
    await update.effective_message.reply_text(text, parse_mode="HTML")


# --- сообщения --------------------------------------------------------


async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    runtime = await _guard(update, context)
    message = update.effective_message
    if runtime is None or message is None:
        return
    if not should_answer(message, context.bot.username):
        return

    question = strip_mention(message.text or "", context.bot.username)
    if not question:
        await message.reply_text(EMPTY_QUESTION)
        return

    await _respond(runtime, update, context, [text_block(question)])


async def on_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    runtime = await _guard(update, context)
    message = update.effective_message
    if runtime is None or message is None or not message.photo:
        return
    if not should_answer(message, context.bot.username):
        return

    photo = message.photo[-1]
    if photo.file_size and photo.file_size > runtime.config.max_image_bytes:
        await message.reply_text(TOO_BIG_IMAGE)
        return

    try:
        telegram_file = await context.bot.get_file(photo.file_id)
        payload = bytes(await telegram_file.download_as_bytearray())
    except Exception:  # noqa: BLE001 — сеть Telegram
        logger.exception("Не удалось скачать фото")
        await message.reply_text("Не получилось скачать картинку. Попробуй прислать ещё раз.")
        return

    if len(payload) > runtime.config.max_image_bytes:
        await message.reply_text(TOO_BIG_IMAGE)
        return

    caption = strip_mention(message.caption or "", context.bot.username)
    blocks = [
        image_block("image/jpeg", base64.standard_b64encode(payload).decode("ascii")),
        text_block(caption or "Что на этом изображении? Помоги разобраться."),
    ]
    await _respond(runtime, update, context, blocks)


async def on_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    runtime = await _guard(update, context)
    message = update.effective_message
    document = message.document if message else None
    if runtime is None or message is None or document is None:
        return
    if not should_answer(message, context.bot.username):
        return

    mime = (document.mime_type or "").lower()
    name = document.file_name or "файл"
    is_image = mime in SUPPORTED_IMAGE_TYPES
    is_textual = mime.startswith("text/") or name.lower().endswith(TEXT_DOCUMENT_HINTS)

    if not is_image and not is_textual:
        await message.reply_text(UNSUPPORTED_MESSAGE)
        return

    limit = runtime.config.max_image_bytes if is_image else runtime.config.max_document_bytes
    if document.file_size and document.file_size > limit:
        await message.reply_text(TOO_BIG_IMAGE if is_image else TOO_BIG_DOCUMENT)
        return

    try:
        telegram_file = await context.bot.get_file(document.file_id)
        payload = bytes(await telegram_file.download_as_bytearray())
    except Exception:  # noqa: BLE001 — сеть Telegram
        logger.exception("Не удалось скачать документ")
        await message.reply_text("Не получилось скачать файл. Попробуй ещё раз.")
        return

    if len(payload) > limit:
        await message.reply_text(TOO_BIG_IMAGE if is_image else TOO_BIG_DOCUMENT)
        return

    caption = strip_mention(message.caption or "", context.bot.username)

    if is_image:
        blocks = [
            image_block(mime, base64.standard_b64encode(payload).decode("ascii")),
            text_block(caption or "Что на этом изображении? Помоги разобраться."),
        ]
    else:
        try:
            content = payload.decode("utf-8")
        except UnicodeDecodeError:
            await message.reply_text(UNREADABLE_DOCUMENT)
            return
        prompt = caption or "Разбери этот файл и скажи, что в нём важного."
        blocks = [text_block(f"{prompt}\n\nФайл «{name}»:\n```\n{content}\n```")]

    await _respond(runtime, update, context, blocks)


async def on_unsupported(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    runtime = await _guard(update, context)
    message = update.effective_message
    if runtime is None or message is None:
        return
    if not should_answer(message, context.bot.username):
        return
    await message.reply_text(UNSUPPORTED_MESSAGE)


# --- ядро ответа ------------------------------------------------------


async def _respond(
    runtime: BotRuntime,
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    blocks: list[dict[str, Any]],
) -> None:
    chat = update.effective_chat
    message = update.effective_message
    if chat is None or message is None:
        return

    lock = runtime.lock_for(chat.id)
    if lock.locked():
        await message.reply_text(BUSY_MESSAGE)
        return

    async with lock:
        history = await runtime.history.get(chat.id)
        conversation = history + [{"role": "user", "content": blocks}]

        streamer = ReplyStreamer(
            context.bot,
            chat.id,
            reply_to_message_id=None if _is_private(message) else message.message_id,
            interval=runtime.config.stream_edit_interval,
        )
        await streamer.start()

        stop_typing = asyncio.Event()
        typing_task = asyncio.create_task(keep_typing(context.bot, chat.id, stop_typing))

        reply: Reply | None = None
        error_text = ""
        try:
            reply = await runtime.claude.complete(
                runtime.system_prompt, conversation, on_delta=streamer.push
            )
        except ModelError as exc:
            error_text = exc.user_message
        except Exception:  # noqa: BLE001 — не роняем бота из-за одного чата
            logger.exception("Непредвиденная ошибка при генерации ответа")
            error_text = "Что-то сломалось на моей стороне. Попробуй ещё раз."
        finally:
            stop_typing.set()
            await typing_task

        if reply is None:
            await streamer.fail(error_text)
            return

        await streamer.finalize(reply.text, footer=build_footer(reply))

        if not reply.refused:
            await runtime.history.replace(
                chat.id,
                conversation + [{"role": "assistant", "content": [text_block(reply.text)]}],
            )


def build_footer(reply: Reply) -> str:
    """Подпись под ответом: источники поиска и пометка об обрыве."""
    parts: list[str] = []
    if reply.sources:
        links = [f"[{_short(title)}]({url})" for title, url in reply.sources[:5]]
        parts.append("Источники: " + ", ".join(links))
    elif reply.used_search:
        parts.append("Использован веб-поиск.")
    if reply.truncated:
        parts.append("_Ответ получился длинным и был обрезан. Напиши «продолжи», если нужно дальше._")
    return "\n".join(parts)


def _short(title: str, limit: int = 40) -> str:
    title = " ".join(title.split())
    clean = title.replace("[", "(").replace("]", ")")
    return clean if len(clean) <= limit else clean[: limit - 1] + "…"


async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Логирует всё, что не поймали обработчики."""
    logger.exception("Ошибка при обработке обновления", exc_info=context.error)
    if isinstance(update, Update) and update.effective_message is not None:
        try:
            await update.effective_message.reply_text(
                "Произошла ошибка. Попробуй повторить запрос."
            )
        except Exception:  # noqa: BLE001 — сообщение об ошибке не критично
            logger.debug("Не удалось сообщить пользователю об ошибке")


def register(application: Application, runtime: BotRuntime) -> None:
    """Подключает все обработчики к приложению."""
    application.bot_data["runtime"] = runtime

    application.add_handler(CommandHandler("start", cmd_start))
    application.add_handler(CommandHandler("help", cmd_help))
    application.add_handler(CommandHandler("reset", cmd_reset))
    application.add_handler(CommandHandler(["about", "status"], cmd_about))

    application.add_handler(MessageHandler(filters.PHOTO, on_photo))
    application.add_handler(MessageHandler(filters.Document.ALL, on_document))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
    application.add_handler(
        MessageHandler(
            filters.VOICE | filters.AUDIO | filters.VIDEO | filters.VIDEO_NOTE | filters.Sticker.ALL,
            on_unsupported,
        )
    )

    application.add_error_handler(on_error)


__all__ = [
    "BotRuntime",
    "build_footer",
    "register",
    "should_answer",
    "strip_mention",
]
