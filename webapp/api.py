"""REST API Mini App'а — тонкий HTTP-слой поверх тех же bot.database.repo и
bot.services, что использует long-polling бот. Игровая логика НЕ дублируется:
каждый хендлер здесь — прямой аналог соответствующего callback-хендлера в
bot/handlers/*.py, просто с JSON вместо edit_text/inline-кнопок.
"""
from __future__ import annotations

import random
import time
from datetime import datetime, timedelta
from pathlib import Path

from aiogram.types import LabeledPrice
from aiohttp import web
from sqlalchemy import select

from bot.config import config, is_admin, is_owner, set_granted_admins
from bot import support_bot
from bot.data.brainrot_roster import (
    RARITY_COLOR,
    RARITY_LABEL,
    RARITY_ORDER,
    ROSTER,
    ROSTER_BY_NAME,
    WIKI_SNAPSHOT_DATE,
    Rarity,
    rarity_for,
    slugify,
)
from bot.data.coins import COIN_RARITY, coin_amount
from bot.data.market import (
    COLD_DEMAND,
    HOT_DEMAND,
    MARKET_SNAPSHOT_DATE,
    MARKET_SOURCES,
    market_info,
    names_with_demand,
)
from bot.data.seed_cases import CASE_THEMES, SEED_CASES_BY_CODE
from bot.data.referral_tiers import next_tier_for_count, tier_for_count
from bot.database.models import (
    Case,
    CaseCategory,
    CaseItem,
    Giveaway,
    GiveawayStatus,
    InventoryItem,
    Quest,
    StakePosition,
    StakeStatus,
    User,
)
from bot.database.models import (
    AdminGrant,
    DepositCategory,
    DepositRequest,
    DepositRequestStatus,
    PromoKind,
    StarsDeposit,
    WithdrawRequest,
    WithdrawStatus,
)
from bot.database.repo import cases as cases_repo
from bot.database.repo import deposit_items as deposit_items_repo
from bot.database.repo import deposit_requests as deposit_requests_repo
from bot.database.repo import rewards as rewards_repo
from bot.database.repo import giveaways as giveaways_repo
from bot.database.repo import inventory as inventory_repo
from bot.database.repo import quests as quests_repo
from bot.database.repo import staking as staking_repo
from bot.database.repo.known_items import list_known_items
from bot.database.repo.users import get_user_by_tg_id
from bot.database.repo.users import add_balance, count_referrals, find_user
from bot.services import deposit_moderation, partner_service, quest_service, settings_service, stars_service, withdraw_service
from bot.services.deposit_service import cart_is_valid
from bot.services.battle_service import run_battle
from bot.services.cases_service import REEL_REVEAL_INDEX, build_reel, draw_items, total_cost
from bot.services.dice_service import COLORS, MATCH_PAYOUT_TABLE, resolve_roll
from bot.services.giveaway_service import resolve_all_expired
from bot.services.staking_service import MIN_STAKE_AMOUNT, STAKE_TIERS, is_matured, payout_amount, tier_by_term
from bot.services.upgrader_service import chance_percent, lucky_chance, roll_success
from bot.utils.texts import FAQ_ENTRIES
from webapp import crash_runtime as crash_rt

routes = web.RouteTableDef()


# ---------------------------------------------------------------- сериализация


BRAINROT_ASSETS_DIR = Path(__file__).parent / "static" / "assets" / "brainrots"
# Какие официальные рендеры реально лежат в ассетах — для остальных фронтенд
# рисует явный плейсхолдер «нет ассета», а не случайную картинку.
AVAILABLE_BRAINROT_IMAGES = {p.stem for p in BRAINROT_ASSETS_DIR.glob("*.webp")}
# 3D-рендеры моделей кейсов (tools/case_renders) — по коду кейса.
CASE_RENDERS_DIR = Path(__file__).parent / "static" / "assets" / "cases"
AVAILABLE_CASE_RENDERS = {p.stem for p in CASE_RENDERS_DIR.glob("*.webp")}

COLLECTIONS = [
    {"key": CaseCategory.STARTER.value, "title": "Кейсы", "categories": [CaseCategory.STARTER]},
    {"key": "free", "title": "Бесплатные кейсы", "categories": [CaseCategory.FREE, CaseCategory.REFERRAL]},
    {"key": CaseCategory.APEX.value, "title": "All-in", "categories": [CaseCategory.APEX]},
]


def free_case_wait_seconds(user, cooldown_hours: float) -> int:
    """Сколько ждать до следующего бесплатного открытия (0 — можно сейчас)."""
    if user.free_case_at is None:
        return 0
    ready = user.free_case_at + timedelta(hours=cooldown_hours)
    return max(0, int((ready - datetime.utcnow()).total_seconds()))


async def _free_case_state(request: web.Request) -> dict:
    """Кулдаун и обязательный канал бесплатного кейса (настраиваются админом)."""
    session = request["session"]
    hours = await settings_service.free_case_cooldown_hours(session)
    channel = await settings_service.required_channel(session)
    return {
        "free_wait_seconds": free_case_wait_seconds(request["user"], hours),
        "free_cooldown_hours": hours,
        "required_channel": channel,
        "required_channel_url": settings_service.channel_url(channel),
    }


def _brainrot_image_url(name: str) -> str | None:
    slug = slugify(name)
    return f"/static/assets/brainrots/{slug}.webp" if slug in AVAILABLE_BRAINROT_IMAGES else None


def _case_json(case: Case) -> dict:
    best = Rarity(case.best_rarity) if case.best_rarity else Rarity.COMMON
    theme = CASE_THEMES.get(case.code)
    return {
        "id": case.id,
        "code": case.code,
        "category": case.category.value,
        "name": case.name,
        "price_tokens": case.price_tokens,
        "item_count_label": case.item_count_label,
        "note": case.note,
        "is_openable": case.is_openable,
        "top_item_name": case.top_item_name,
        "top_item_image_url": _brainrot_image_url(case.top_item_name) if case.top_item_name else None,
        "image_url": f"/static/assets/cases/{case.code}.webp" if case.code in AVAILABLE_CASE_RENDERS else None,
        "best_rarity": best.value,
        "best_rarity_label": RARITY_LABEL[best],
        "best_rarity_color": RARITY_COLOR[best][0],
        "best_rarity_color_accent": RARITY_COLOR[best][1],
        # Герои кейса — два самых дорогих брейнрота, они сидят в модели кейса.
        "heroes": [
            {"name": i.name, "image_url": _brainrot_image_url(i.name)}
            for i in (SEED_CASES_BY_CODE[case.code].items if case.code in SEED_CASES_BY_CODE else ())
            if i.rarity != COIN_RARITY
        ][:2],
        "theme": {
            "filling": theme.filling,
            "aura": theme.aura,
            "shell": list(theme.shell),
            "accent": theme.accent,
            "colors": [theme.accent, theme.shell[0], theme.shell[1]],
        } if theme else None,
    }


def _brainrot_json(name: str, value: int, rarity: str | None = None) -> dict:
    if (coins := coin_amount(name)) is not None:
        return {
            "name": f"{coins} B", "value": coins, "coins": True, "rarity": COIN_RARITY, "rarity_rank": -1,
            "rarity_label": "Монеты", "rarity_color": "#ffd24d", "rarity_color_accent": "#b8861a",
            "slug": "coins", "image_url": None, "game": None, "market": None,
        }
    roster_entry = ROSTER_BY_NAME.get(name)
    # Реальный тир из ростера важнее сохранённого: старые записи инвентаря
    # получали rarity угадыванием по ценности.
    try:
        tier = rarity_for(name, value) if roster_entry or not rarity else Rarity(rarity)
    except ValueError:  # неизвестный тир в старой записи — не роняем весь ответ
        tier = rarity_for(name, value)
    color = RARITY_COLOR[tier]
    return {
        "name": name,
        "value": value,
        "rarity": tier.value,
        "rarity_rank": RARITY_ORDER.index(tier),
        "rarity_label": RARITY_LABEL[tier],
        "rarity_color": color[0],
        "rarity_color_accent": color[1],
        "slug": slugify(name),
        "image_url": _brainrot_image_url(name),
        "market": market_info(name),
        "game": {
            "cost": roster_entry.cost,
            "income": roster_entry.income,
            "wiki_url": roster_entry.wiki_url,
            "as_of": WIKI_SNAPSHOT_DATE,
        } if roster_entry else None,
    }


def _case_item_json(item: CaseItem) -> dict:
    return _brainrot_json(item.name, item.value, item.rarity)


def _inventory_item_json(item: InventoryItem) -> dict:
    payload = _brainrot_json(item.item_name, item.value, item.rarity)
    payload.update(
        {
            "id": item.id,
            "case_id": item.case_id,
            "case_name": item.case_name,
            "obtained_at": item.obtained_at.isoformat(),
        }
    )
    return payload


def _quest_json(quest: Quest, progress_count: int, claimed: bool, reset_label: str) -> dict:
    return {
        "id": quest.id,
        "scope": quest.scope.value,
        "title": quest.title,
        "description": quest.description,
        "target_count": quest.target_count,
        "reward_tokens": quest.reward_tokens,
        "progress_count": progress_count,
        "claimed": claimed,
        "claimable": (not claimed) and progress_count >= quest.target_count,
        "reset_label": reset_label,
    }


def _stake_json(position: StakePosition) -> dict:
    return {
        "id": position.id,
        "amount": position.amount,
        "term_days": position.term_days,
        "bonus_percent": position.bonus_percent,
        "matures_at": position.matures_at.isoformat(),
        "status": position.status.value,
        "matured": is_matured(position),
        "payout": payout_amount(position),
    }


def _giveaway_json(giveaway: Giveaway, joined: bool, entries: int) -> dict:
    return {
        "id": giveaway.id,
        "title": giveaway.title,
        "prize_description": giveaway.prize_description,
        "ends_at": giveaway.ends_at.isoformat(),
        "entries": entries,
        "joined": joined,
    }


async def _user_json(request: web.Request) -> dict:
    user = request["user"]
    session = request["session"]
    referral_count = await count_referrals(session, user)
    return {
        "is_admin": is_admin(user.tg_id),
        "is_owner": is_owner(user.tg_id),
        "design": await settings_service.ui_design(session),
        "case_credits": await rewards_repo.case_credits(session, user),
        "partner_percent": user.partner_percent,
        "deposit_bonus_percent": user.deposit_bonus_percent,
        "partner_code": pc.code if (pc := await partner_service.get_partner_code_of(session, user)) and pc.is_active else None,
        "tg_id": user.tg_id,
        "username": user.username,
        "first_name": user.first_name,
        "balance": user.balance,
        "referral_code": user.referral_code,
        "referral_count": referral_count,
        "referral_earned_total": user.referral_earned_total,
    }


# --------------------------------------------------------------------- профиль


@routes.get("/api/me")
async def get_me(request: web.Request) -> web.Response:
    return web.json_response(await _user_json(request))


@routes.get("/api/inventory")
async def get_inventory(request: web.Request) -> web.Response:
    session, user = request["session"], request["user"]
    limit = int(request.query.get("limit", "20"))
    items = await inventory_repo.list_all(session, user)
    return web.json_response([_inventory_item_json(i) for i in items[:limit]])


SELL_RATE = 1.0  # без комиссии: продажа по полной цене (кейсы и так с RTP < 100%)


@routes.post("/api/inventory/{item_id}/sell")
async def post_inventory_sell(request: web.Request) -> web.Response:
    session, user = request["session"], request["user"]
    item = await inventory_repo.get_by_id(session, int(request.match_info["item_id"]))
    if item is None or item.user_id != user.id:
        return web.json_response({"error": "not_found"}, status=404)

    payout = round(item.value * SELL_RATE)
    name = item.item_name
    await inventory_repo.delete(session, item)
    user = await add_balance(session, user, payout)

    return web.json_response({"sold_name": name, "payout": payout, "balance": user.balance})


@routes.get("/api/recent-wins")
async def get_recent_wins(request: web.Request) -> web.Response:
    session = request["session"]
    limit = int(request.query.get("limit", "20"))
    rows = await inventory_repo.list_recent_global(session, limit=limit)
    payload = []
    for item, owner in rows:
        entry = _brainrot_json(item.item_name, item.value, item.rarity)
        entry["player"] = f"@{owner.username}" if owner.username else (owner.first_name or "игрок")
        entry["case_name"] = item.case_name
        entry["obtained_at"] = item.obtained_at.isoformat()
        payload.append(entry)
    return web.json_response(payload)


@routes.get("/api/market")
async def get_market(_request: web.Request) -> web.Response:
    """Рыночный пульс: самые востребованные и самые неликвидные брейнроты
    ростера по снимку bot.data.market (источники — в MARKET_SOURCES)."""
    def pack(levels):
        names = sorted(names_with_demand(levels), key=lambda n: -ROSTER_BY_NAME[n].value)
        return [_brainrot_json(n, ROSTER_BY_NAME[n].value) for n in names]

    return web.json_response({
        "hot": pack(HOT_DEMAND),
        "cold": pack(COLD_DEMAND),
        "as_of": MARKET_SNAPSHOT_DATE,
        "sources": list(MARKET_SOURCES),
    })


# ------------------------------------------------------------------- пополнение
# Честные пополнения: брейнроты и гирсы — место в очереди, трейды строго по
# одному, B зачисляет модератор (та же очередь, что в чате: bot/handlers/deposit),
# Stars — счёт Telegram; B зачисляет bot/handlers/deposit/stars.py по
# successful_payment. Mini App сам баланс не начисляет.

DEPOSIT_STATUS_LABEL = {
    DepositRequestStatus.PENDING: "На проверке",
    DepositRequestStatus.QUEUED: "В очереди",
    DepositRequestStatus.APPROVED: "Зачислено",
    DepositRequestStatus.REJECTED: "Отклонено",
    DepositRequestStatus.CANCELLED: "Отменено",
}


GEAR_ASSETS_DIR = Path(__file__).parent / "static" / "assets" / "gears"
AVAILABLE_GEAR_IMAGES = {p.stem for p in GEAR_ASSETS_DIR.glob("*.webp")}


def _gear_image_url(name: str) -> str | None:
    slug = slugify(name)
    return f"/static/assets/gears/{slug}.webp" if slug in AVAILABLE_GEAR_IMAGES else None


def _deposit_item_json(item) -> dict:
    return {
        "id": item.id, "name": item.name, "emoji": item.emoji, "price_b": item.price_b,
        "min_qty": item.min_qty, "hot_stock_left": item.hot_stock_left,
        "image_url": _brainrot_image_url(item.name) if item.category == DepositCategory.BRAINROT else _gear_image_url(item.name),
    }


@routes.get("/api/deposit/catalog")
async def get_deposit_catalog(request: web.Request) -> web.Response:
    session = request["session"]
    return web.json_response({
        "brainrot": [_deposit_item_json(i) for i in await deposit_items_repo.list_items(session, DepositCategory.BRAINROT)],
        "hirsy": [_deposit_item_json(i) for i in await deposit_items_repo.list_items(session, DepositCategory.HIRSY)],
        "stars": {
            "rate": await stars_service.rate(session), "code_bonus_percent": await stars_service.code_bonus(session),
            "min": config.min_stars_amount, "max": None,
        },
    })


@routes.post("/api/deposit/request")
async def post_deposit_request(request: web.Request) -> web.Response:
    """Встать в очередь на пополнение брейнротами/гирсами (строго по одному,
    см. bot.services.deposit_moderation)."""
    session, user = request["session"], request["user"]
    body = await request.json()
    try:
        category = DepositCategory(body.get("category"))
        cart = {int(k): int(v) for k, v in (body.get("items") or {}).items() if int(v) > 0}
    except (ValueError, TypeError):
        return web.json_response({"error": "bad_request", "message": "Неверная заявка"}, status=400)
    nickname = str(body.get("nickname") or "").strip()
    if not 2 <= len(nickname) <= 32:
        return web.json_response({"error": "bad_nickname", "message": "Ник в игре: от 2 до 32 символов"}, status=400)
    items = await deposit_items_repo.list_items(session, category)
    if not cart_is_valid(items, cart):
        return web.json_response({"error": "bad_cart", "message": "Выбери предметы (учитывай «от N шт»)"}, status=400)
    try:
        deposit, position = await deposit_moderation.submit_deposit(
            session, request.app["bot"], user, category, cart, nickname, items, code=body.get("code"),
        )
    except stars_service.BadCode:
        return web.json_response({"error": "bad_code", "message": "Такого кода нет"}, status=400)
    except deposit_moderation.DepositAlreadyOpen as exc:
        return web.json_response({
            "error": "already_open", "request_id": exc.request.id,
            "message": f"У тебя уже есть заявка #{exc.request.id} в очереди — дождись её",
        }, status=400)
    await deposit_moderation.notify_submitted(request.app["bot"], user, deposit, position)
    return web.json_response({"request": _deposit_request_json(deposit, {i.id: i for i in items}, position), "queue_position": position})


@routes.post("/api/deposit/requests/{request_id}/cancel")
async def post_deposit_cancel(request: web.Request) -> web.Response:
    try:
        r = await deposit_moderation.cancel_by_user(
            request["session"], request.app["bot"], request["user"], int(request.match_info["request_id"])
        )
    except deposit_moderation.DepositAlreadyResolved:
        return web.json_response({"error": "already_resolved", "message": "Заявку уже нельзя отменить"}, status=400)
    return web.json_response({"id": r.id, "status": r.status.value})


def _deposit_request_json(req: DepositRequest, items_by_id: dict, position: int | None = None) -> dict:
    status_label = DEPOSIT_STATUS_LABEL[req.status]
    if position == 1:
        status_label = "Твоя очередь — жди трейд"
    elif position:
        status_label = f"В очереди: {position}-й"
    return {
        "id": req.id,
        "category": req.category.value,
        "total_b": req.total_b,
        "status": req.status.value,
        "status_label": status_label,
        "queue_position": position,
        "promo_code": req.promo_code,
        "bonus_b": deposit_moderation.bonus_amount(req.total_b, req.bonus_percent),
        "nickname": req.game_nickname,
        "items": [
            {"name": items_by_id[int(i)].name if int(i) in items_by_id else "?", "qty": q}
            for i, q in req.items.items()
        ],
        "created_at": req.created_at.isoformat() if req.created_at else None,
    }


@routes.get("/api/deposit/requests")
async def get_deposit_requests(request: web.Request) -> web.Response:
    session, user = request["session"], request["user"]
    rows = (await session.execute(
        select(DepositRequest).where(DepositRequest.user_id == user.id).order_by(DepositRequest.id.desc()).limit(10)
    )).scalars().all()
    ids = {int(i) for r in rows for i in r.items}
    items_by_id = {i: v for i in ids if (v := await deposit_items_repo.get_item(session, i))}
    result = []
    for r in rows:
        position = await deposit_moderation.queue_position(session, r) if r.status in deposit_moderation.OPEN_STATUSES else None
        result.append(_deposit_request_json(r, items_by_id, position))
    return web.json_response(result)


async def _stars_quote(request: web.Request, body: dict):
    try:
        amount = int(body.get("amount"))
    except (TypeError, ValueError):
        amount = 0
    if amount < config.min_stars_amount:
        return None, web.json_response({"error": "bad_amount", "message": "Минимум 1 ⭐"}, status=400)
    try:
        q = await stars_service.quote(request["session"], request["user"], amount, body.get("code"))
    except stars_service.BadCode:
        return None, web.json_response({"error": "bad_code", "message": "Такого кода нет"}, status=400)
    return q, None


@routes.get("/api/deposit/code")
async def get_deposit_code(request: web.Request) -> web.Response:
    """Проверка кода для пополнения (Stars/брейнроты/гирсы) — бонус в %."""
    try:
        code, bonus = await stars_service.code_bonus_percent(request["session"], request["user"], request.query.get("code"))
    except stars_service.BadCode:
        return web.json_response({"error": "bad_code", "message": "Такого кода нет"}, status=400)
    return web.json_response({"code": code, "bonus_percent": bonus})


@routes.post("/api/deposit/stars/quote")
async def post_deposit_stars_quote(request: web.Request) -> web.Response:
    q, err = await _stars_quote(request, await request.json())
    if err is not None:
        return err
    return web.json_response({"stars": q.stars, "rate": q.rate, "bonus_percent": q.bonus_percent, "code": q.code, "credited": q.credited})


@routes.post("/api/deposit/stars")
async def post_deposit_stars(request: web.Request) -> web.Response:
    """Счёт Telegram Stars для Mini App (tg.openInvoice). Сумма зачисления
    фиксируется здесь (курс + бонус за код), зачисляет её
    bot/handlers/deposit/stars.py по successful_payment."""
    q, err = await _stars_quote(request, await request.json())
    if err is not None:
        return err
    deposit = await stars_service.create_deposit(request["session"], request["user"], q)
    try:
        link = await request.app["bot"].create_invoice_link(
            title="Пополнение баланса BrainCore",
            description=f"Начисление {q.credited} B на баланс",
            payload=deposit.payload,
            currency="XTR",
            prices=[LabeledPrice(label="Пополнение баланса", amount=q.stars)],
        )
    except Exception as exc:  # noqa: BLE001 — лимиты самого Telegram на сумму счёта
        return web.json_response({"error": "invoice_failed", "message": f"Telegram не принял счёт: {exc}"}, status=400)
    return web.json_response({"invoice_url": link, "credited": q.credited, "bonus_percent": q.bonus_percent})


# ----------------------------------------------------------------------- вывод
# Вывод брейнротов через сток админа (bot/services/withdraw_service.py).


def _withdraw_request_json(r: WithdrawRequest, owner: User | None = None, position: int | None = None) -> dict:
    label = {"queued": "В очереди", "pending": "Ждёт трейда", "done": "Выдано", "cancelled": "Отменено"}[r.status.value]
    if position == 1:
        label = "Твоя очередь — жди трейд"
    elif position:
        label = f"В очереди: {position}-й"
    data = {
        "id": r.id,
        "item": _brainrot_json(r.item_name, r.item_value, r.item_rarity),
        "payout": [{**_brainrot_json(p["name"], p["value"]), "qty": p["qty"]} for p in r.payout],
        "topup_b": r.topup_b,
        "nickname": r.game_nickname,
        "status": r.status.value,
        "status_label": label,
        "queue_position": position,
    }
    if owner is not None:
        data["player"] = f"@{owner.username}" if owner.username else (owner.first_name or str(owner.tg_id))
    return data


@routes.get("/api/withdraw/stock")
async def get_withdraw_stock(request: web.Request) -> web.Response:
    stock = await withdraw_service.stock(request["session"])
    items = [{**_brainrot_json(n, withdraw_service.stock_value(n)), "count": c} for n, c in stock.items() if withdraw_service.stock_value(n)]
    return web.json_response(sorted(items, key=lambda i: -i["value"]))


@routes.get("/api/withdraw/options/{item_id}")
async def get_withdraw_options(request: web.Request) -> web.Response:
    session, user = request["session"], request["user"]
    item = await inventory_repo.get_by_id(session, int(request.match_info["item_id"]))
    if item is None or item.user_id != user.id:
        return web.json_response({"error": "item_gone", "message": "Этого брейнрота уже нет в инвентаре"}, status=404)
    exchange = request.query.get("exchange") == "1"
    options = withdraw_service.options_for(item.item_name, item.value, await withdraw_service.stock(session), exchange=exchange)
    return web.json_response({
        "item": _brainrot_json(item.item_name, item.value, item.rarity),
        "options": [{
            "key": o.key, "direct": o.items[0][0] == item.item_name, "topup_b": o.topup,
            "items": [{**_brainrot_json(n, v), "qty": q} for n, v, q in o.items],
        } for o in options],
    })


@routes.post("/api/withdraw")
async def post_withdraw(request: web.Request) -> web.Response:
    session, user = request["session"], request["user"]
    body = await request.json()
    nickname = str(body.get("nickname") or "").strip()
    if not 2 <= len(nickname) <= 32:
        return web.json_response({"error": "bad_nickname", "message": "Ник в игре: от 2 до 32 символов"}, status=400)
    try:
        item = await inventory_repo.get_by_id(session, int(body.get("item_id")))
    except (TypeError, ValueError):
        item = None
    if item is None:
        return web.json_response({"error": "item_gone", "message": "Этого брейнрота уже нет в инвентаре"}, status=404)
    try:
        req, position = await withdraw_service.create_request(
            session, request.app["bot"], user, item, str(body.get("option_key") or ""), nickname,
            exchange=bool(body.get("exchange")),
        )
    except withdraw_service.WithdrawError as exc:
        return web.json_response({"error": exc.code, "message": exc.message}, status=400)
    return web.json_response(_withdraw_request_json(req, position=position))


@routes.post("/api/withdraw/{request_id}/cancel")
async def post_withdraw_cancel(request: web.Request) -> web.Response:
    try:
        r = await withdraw_service.resolve(
            request["session"], request.app["bot"], int(request.match_info["request_id"]),
            done=False, admin_tg_id=request["user"].tg_id, by_user=request["user"],
        )
    except withdraw_service.WithdrawError as exc:
        return web.json_response({"error": exc.code, "message": exc.message}, status=400)
    return web.json_response(_withdraw_request_json(r))


@routes.get("/api/withdraw/requests")
async def get_withdraw_requests(request: web.Request) -> web.Response:
    session, user = request["session"], request["user"]
    rows = (await session.execute(
        select(WithdrawRequest).where(WithdrawRequest.user_id == user.id).order_by(WithdrawRequest.id.desc()).limit(10)
    )).scalars().all()
    result = []
    for r in rows:
        pos = await withdraw_service.queue_position(session, r) if r.status in withdraw_service.OPEN else None
        result.append(_withdraw_request_json(r, position=pos))
    return web.json_response(result)


@routes.get("/api/admin/stock")
async def get_admin_stock(request: web.Request) -> web.Response:
    """Все брейнроты ростера с количеством в стоке (0 — нет)."""
    if (denied := _require_admin(request)) is not None:
        return denied
    stock = await withdraw_service.stock(request["session"])
    items = [{"name": b.name, "value": b.value, "count": stock.get(b.name, 0), "image_url": _brainrot_image_url(b.name)} for b in ROSTER]
    return web.json_response(sorted(items, key=lambda i: (i["count"] == 0, -i["value"])))


@routes.post("/api/admin/stock")
async def post_admin_stock(request: web.Request) -> web.Response:
    if (denied := _require_admin(request)) is not None:
        return denied
    body = await request.json()
    name = body.get("name")
    if name not in ROSTER_BY_NAME:
        return web.json_response({"error": "unknown_brainrot"}, status=400)
    try:
        delta = int(body.get("delta", 0))
    except (TypeError, ValueError):
        delta = 0
    count = await withdraw_service.add_stock(request["session"], name, delta)
    await request["session"].commit()
    return web.json_response({"name": name, "count": count})


@routes.get("/api/admin/withdrawals")
async def get_admin_withdrawals(request: web.Request) -> web.Response:
    if (denied := _require_admin(request)) is not None:
        return denied
    session = request["session"]
    rows = (await session.execute(
        select(WithdrawRequest).where(WithdrawRequest.status.in_(withdraw_service.OPEN)).order_by(WithdrawRequest.id)
    )).scalars().all()
    return web.json_response([
        _withdraw_request_json(r, await session.get(User, r.user_id), await withdraw_service.queue_position(session, r))
        for r in rows
    ])


@routes.post("/api/admin/withdrawals/{request_id}")
async def post_admin_withdrawal(request: web.Request) -> web.Response:
    if (denied := _require_admin(request)) is not None:
        return denied
    body = await request.json()
    try:
        r = await withdraw_service.resolve(
            request["session"], request.app["bot"], int(request.match_info["request_id"]),
            done=body.get("action") == "done", admin_tg_id=request["user"].tg_id,
        )
    except withdraw_service.WithdrawError as exc:
        return web.json_response({"error": exc.code, "message": exc.message}, status=400)
    return web.json_response(_withdraw_request_json(r))


# ----------------------------------------------------------------------- кейсы


@routes.get("/api/cases")
async def get_cases(request: web.Request) -> web.Response:
    """Без ?category — весь каталог по коллекциям (главная Mini App)."""
    session = request["session"]
    if "category" in request.query:
        try:
            category = CaseCategory(request.query["category"])
        except ValueError:
            return web.json_response({"error": "unknown_category"}, status=400)
        cases = await cases_repo.list_cases(session, category)
        return web.json_response({"category": category.value, "cases": [_case_json(c) for c in cases]})

    collections = []
    for meta in COLLECTIONS:
        cases = []
        for category in meta["categories"]:
            cases.extend(await cases_repo.list_cases(session, category))
        collections.append({"key": meta["key"], "title": meta["title"], "cases": [_case_json(c) for c in cases]})
    return web.json_response({"collections": collections, **await _free_case_state(request)})


@routes.get("/api/cases/by-code/{code}")
async def get_case_by_code(request: web.Request) -> web.Response:
    case = await cases_repo.get_case_by_code(request["session"], request.match_info["code"])
    if case is None:
        return web.json_response({"error": "not_found"}, status=404)
    return web.json_response(_case_json(case))


@routes.get("/api/cases/{case_id}")
async def get_case_detail(request: web.Request) -> web.Response:
    session = request["session"]
    case = await cases_repo.get_case(session, int(request.match_info["case_id"]))
    if case is None:
        return web.json_response({"error": "not_found"}, status=404)
    items = await cases_repo.list_case_items(session, case.id)
    # Шансы наружу не отдаются — только состав кейса.
    payload = _case_json(case)
    payload["items"] = [_case_item_json(i) for i in items]
    return web.json_response(payload)


@routes.post("/api/cases/{case_id}/open")
async def post_case_open(request: web.Request) -> web.Response:
    session, user = request["session"], request["user"]
    body = await request.json()
    qty = int(body.get("qty", 1))
    if qty not in (1, 3, 5):
        return web.json_response({"error": "invalid_qty"}, status=400)

    case = await cases_repo.get_case(session, int(request.match_info["case_id"]))
    if case is None:
        return web.json_response({"error": "not_found"}, status=404)
    if not case.is_openable:
        return web.json_response({"error": "not_openable"}, status=400)

    cost = total_cost(case, qty)
    if cost is None:
        return web.json_response({"error": "no_price"}, status=400)
    # Бесплатные открытия (от админа/промокода) тратятся первыми, целиком на qty.
    free = bool(body.get("use_credits")) and await rewards_repo.use_case_credits(session, user, case.code, qty)
    if case.category == CaseCategory.FREE and not free:
        state = await _free_case_state(request)
        wait = state["free_wait_seconds"]
        if qty != 1:
            return web.json_response({"error": "free_single", "message": "Бесплатный — по одному"}, status=400)
        channel = state["required_channel"]
        if channel and not await settings_service.is_subscribed(request.app["bot"], channel, user.tg_id):
            return web.json_response({
                "error": "subscribe_required", "message": f"Подпишись на {channel}",
                "channel": channel, "channel_url": state["required_channel_url"],
            }, status=400)
        if wait > 0:
            return web.json_response({"error": "free_cooldown", "wait_seconds": wait, "message": "Ещё рано"}, status=400)
        user.free_case_at = datetime.utcnow()
        free, cost = True, 0
    if free:
        cost = 0
    elif case.category == CaseCategory.REFERRAL:
        return web.json_response({"error": "referral_only", "message": "Этот кейс только выдаётся"}, status=400)
    elif user.balance < cost:
        return web.json_response({"error": "not_enough_tokens", "message": f"Нужно {cost} B, у тебя {user.balance} B", "cost": cost, "balance": user.balance}, status=400)

    items = await cases_repo.list_case_items(session, case.id)
    # Результат определяется ЗДЕСЬ, на сервере, до какой-либо анимации —
    # клиент получает уже готовый won[] и декоративные ленты reels[] (по
    # одной на каждый выигрыш) с результатом на фиксированной позиции
    # REEL_REVEAL_INDEX, см. bot.services.cases_service.build_reel.
    won = draw_items(items, qty, luck=user.luck, case_price=case.price_tokens)

    user.balance -= cost
    await session.commit()
    await session.refresh(user)

    # Монеты — сразу на баланс B; брейнроты — в инвентарь.
    coins_won = sum(coin_amount(i.name) or 0 for i in won)
    if coins_won:
        user = await add_balance(session, user, coins_won)
    brainrots = [i for i in won if coin_amount(i.name) is None]
    entries = iter(await inventory_repo.add_items(
        session, user, case.name, [(i.name, i.value) for i in brainrots], case_id=case.id
    ))
    await quest_service.record_progress(session, user, f"open_case:{case.code}")

    won_payload = []
    for item in won:
        data = _case_item_json(item)
        if data.get("coins"):
            data["inventory_id"], data["sell_payout"] = None, 0
        else:
            data["inventory_id"] = next(entries).id
            data["sell_payout"] = round(item.value * SELL_RATE)
        won_payload.append(data)

    reels = [[_case_item_json(i) for i in build_reel(items, w)] for w in won]
    response = {
        "won": won_payload,
        "cost": cost,
        "free": free,
        "credits_left": (await rewards_repo.case_credits(session, user)).get(case.code, 0),
        "free_wait_seconds": (await _free_case_state(request))["free_wait_seconds"],
        "balance": user.balance,
        "reels": reels,
        "reveal_index": REEL_REVEAL_INDEX,
    }
    if qty == 1:
        response["reel"] = reels[0]  # старое поле, на него ещё смотрят тесты/старые клиенты
    return web.json_response(response)


# -------------------------------------------------------------------- апгрейдер


@routes.get("/api/upgrader/targets")
async def get_upgrader_targets(request: web.Request) -> web.Response:
    session = request["session"]
    min_value = int(request.query.get("min_value", "0"))
    exclude_name = request.query.get("exclude_name")
    items = await list_known_items(session)
    # Только брейнроты ростера: в «известных предметах» есть ещё гирсы из
    # обменника (Santas Sleigh и т.п.) — они не персонажи и без картинок.
    # Цели — брейнроты ростера с честным шансом от 75% вниз до 1%:
    # цель дороже вклада минимум в 100/75 раза и максимум в 100 раз.
    if min_value:
        low, high = min_value * 100 / config.upgrader_max_target_chance_percent, min_value * 100
    else:
        low, high = 0, float("inf")
    eligible = [
        i for i in items
        if i.value > min_value and low <= i.value <= high and i.name != exclude_name and i.name in ROSTER_BY_NAME
    ]
    payload = []
    for i in eligible:
        entry = _brainrot_json(i.name, i.value)
        entry["chance_percent"] = chance_percent(min_value, i.value) if min_value else None
        payload.append(entry)
    return web.json_response(payload)


UPGRADER_MAX_STAKE_ITEMS = 5


@routes.post("/api/upgrader/spin")
async def post_upgrader_spin(request: web.Request) -> web.Response:
    """Вклад — от 1 до 5 брейнротов инвентаря (ценность — их сумма); при
    любом исходе вклад сгорает, при успехе выдаётся цель."""
    session, user = request["session"], request["user"]
    body = await request.json()
    raw_ids = body.get("contribution_item_ids") or ([body["contribution_item_id"]] if body.get("contribution_item_id") else [])
    target_name = body.get("target_name")
    try:
        ids = list(dict.fromkeys(int(i) for i in raw_ids))
    except (TypeError, ValueError):
        ids = []
    if not ids or not target_name:
        return web.json_response({"error": "missing_fields"}, status=400)
    if len(ids) > UPGRADER_MAX_STAKE_ITEMS:
        return web.json_response({"error": "too_many_items", "message": f"Не больше {UPGRADER_MAX_STAKE_ITEMS} брейнротов"}, status=400)

    items = [await inventory_repo.get_by_id(session, i) for i in ids]
    if any(it is None or it.user_id != user.id for it in items):
        return web.json_response({"error": "item_gone"}, status=404)
    stake_value = sum(it.value for it in items)

    # Ценность цели берётся из каталога, а не из запроса: иначе клиент мог
    # бы сам назначить цели любую цену.
    known = {i.name: i.value for i in await list_known_items(session) if i.name in ROSTER_BY_NAME}
    if target_name not in known or known[target_name] <= stake_value:
        return web.json_response({"error": "invalid_target"}, status=400)
    raw_chance = stake_value * 100 / known[target_name]
    if not 1 <= raw_chance <= config.upgrader_max_target_chance_percent:
        return web.json_response({"error": "target_out_of_range"}, status=400)
    target_value = known[target_name]

    chance = chance_percent(stake_value, target_value)
    # Подкрутка админа меняет реальный шанс; игроку показывается честный.
    success = roll_success(lucky_chance(chance, user.luck))
    # Точка остановки стрелки (0..100): внутри зоны шанса при успехе, вне — при
    # проигрыше. Чисто визуальная, исход уже решён выше.
    roll_point = random.uniform(0, chance) if success else random.uniform(chance, 100)

    contributions = [_brainrot_json(it.item_name, it.value, it.rarity) for it in items]
    for it in items:
        await inventory_repo.delete(session, it)
    won_item = None
    if success:
        won_item = _brainrot_json(target_name, int(target_value))
        await inventory_repo.add_items(session, user, "Апгрейдер", [(target_name, int(target_value))])
    await quest_service.record_progress(session, user, "upgrader_spin")

    return web.json_response(
        {
            "success": success,
            "chance": chance,
            "roll_point": round(roll_point, 2),
            "stake_value": stake_value,
            "contribution": contributions[0],
            "contributions": contributions,
            "won_item": won_item,
        }
    )


# ------------------------------------------------------------------------ краш


def _crash_payload(round_) -> dict:
    """Состояние краша для клиента. Точка взрыва раскрывается только после
    того, как раунд завершился."""
    payload = {
        "history": crash_rt.history(),
        "growth_per_sec": crash_rt.growth_per_sec(),
        "max_multiplier": config.crash_max_multiplier,
        "active": False,
    }
    if round_ is None:
        return payload
    payload["stake"] = _brainrot_json(round_.item_name, round_.item_value)
    payload["ladder"] = [
        {**_brainrot_json(step["name"], step["value"]), "at": step["at"]}
        for step in crash_rt.prize_ladder(round_.item_name, round_.item_value)
    ]
    if round_.outcome is None:
        payload["active"] = True
        payload["elapsed"] = round(round_.elapsed, 3)
    else:
        payload["result"] = {
            "outcome": round_.outcome,
            "multiplier": round_.final_multiplier,
            "crash_point": round_.crash_point,
            "prize": _brainrot_json(*round_.prize) if round_.prize else None,
        }
    return payload


@routes.get("/api/crash/state")
async def get_crash_state(request: web.Request) -> web.Response:
    return web.json_response(_crash_payload(crash_rt.poll(request["user"].tg_id)))


@routes.post("/api/crash/start")
async def post_crash_start(request: web.Request) -> web.Response:
    session, user = request["session"], request["user"]
    body = await request.json()
    item_id = body.get("item_id")
    if not item_id:
        return web.json_response({"error": "missing_item"}, status=400)
    if crash_rt.is_flying(user.tg_id):
        return web.json_response({"error": "already_running"}, status=400)

    item = await inventory_repo.get_by_id(session, int(item_id))
    if item is None or item.user_id != user.id:
        return web.json_response({"error": "item_gone"}, status=404)

    item_name, item_value = item.item_name, item.value
    await inventory_repo.delete(session, item)
    round_ = crash_rt.start_round(user.tg_id, item_name, item_value)
    return web.json_response(_crash_payload(round_))


@routes.post("/api/crash/cashout")
async def post_crash_cashout(request: web.Request) -> web.Response:
    session, user = request["session"], request["user"]
    round_ = crash_rt.cashout(user.tg_id)
    if round_ is None:
        return web.json_response(
            {"error": "no_active_round_or_crashed", **_crash_payload(crash_rt.poll(user.tg_id))}, status=400
        )
    prize_name, prize_value = round_.prize
    await inventory_repo.add_items(session, user, "Краш", [(prize_name, prize_value)])
    return web.json_response(_crash_payload(round_))


# ----------------------------------------------------------------------- дайсы


@routes.get("/api/dice/rules")
async def get_dice_rules(_request: web.Request) -> web.Response:
    return web.json_response(
        {
            "colors": COLORS,
            "payout_table": {str(k): v for k, v in MATCH_PAYOUT_TABLE.items()},
            "bonus_chance_percent": config.dice_bonus_chance_percent,
            "bonus_multiplier": config.dice_bonus_multiplier,
        }
    )


@routes.post("/api/dice/roll")
async def post_dice_roll(request: web.Request) -> web.Response:
    session, user = request["session"], request["user"]
    body = await request.json()
    item_id = body.get("item_id")
    color = body.get("color")
    if not item_id or color not in COLORS:
        return web.json_response({"error": "missing_fields"}, status=400)

    item = await inventory_repo.get_by_id(session, int(item_id))
    if item is None or item.user_id != user.id:
        return web.json_response({"error": "item_gone"}, status=404)

    item_name, item_value = item.item_name, item.value
    result = resolve_roll(color)
    await inventory_repo.delete(session, item)

    won_item = None
    if result.is_win:
        winnings = round(item_value * result.multiplier)
        won_item = _brainrot_json(item_name, winnings)
        await inventory_repo.add_items(session, user, "Дайсы", [(item_name, winnings)])

    return web.json_response(
        {
            "dice": result.dice,
            "match_count": result.match_count,
            "bonus": result.bonus,
            "win": result.is_win,
            "multiplier": result.multiplier,
            "stake": _brainrot_json(item_name, item_value),
            "won_item": won_item,
        }
    )


# ---------------------------------------------------------------------- батл


@routes.get("/api/battle/cases")
async def get_battle_cases(request: web.Request) -> web.Response:
    session = request["session"]
    openable = []
    for category in (CaseCategory.STARTER, CaseCategory.APEX):
        cases = await cases_repo.list_cases(session, category)
        openable.extend(c for c in cases if c.is_openable and c.price_tokens is not None)
    return web.json_response([_case_json(c) for c in openable])


@routes.post("/api/battle/start")
async def post_battle_start(request: web.Request) -> web.Response:
    session, user = request["session"], request["user"]
    body = await request.json()
    case_id = body.get("case_id")

    case = await cases_repo.get_case(session, int(case_id) if case_id else 0)
    if case is None or not case.is_openable or case.price_tokens is None:
        return web.json_response({"error": "case_unavailable"}, status=400)

    cost = case.price_tokens
    if user.balance < cost:
        return web.json_response({"error": "not_enough_tokens", "message": f"Нужно {cost} B, у тебя {user.balance} B", "cost": cost, "balance": user.balance}, status=400)

    user.balance -= cost
    await session.commit()
    await session.refresh(user)

    items = await cases_repo.list_case_items(session, case.id)
    result = run_battle(items, luck=user.luck, case_price=case.price_tokens)

    if result.winner == "player":
        await inventory_repo.add_items(
            session,
            user,
            f"Батл: {case.name}",
            [(result.player_item.name, result.player_item.value), (result.bot_item.name, result.bot_item.value)],
            case_id=case.id,
        )
    elif result.winner == "tie":
        await add_balance(session, user, cost)

    return web.json_response(
        {
            "winner": result.winner,
            "player_item": _case_item_json(result.player_item),
            "bot_item": _case_item_json(result.bot_item),
            "balance": user.balance,
        }
    )


# --------------------------------------------------------------------- квесты


@routes.get("/api/quests")
async def get_quests(request: web.Request) -> web.Response:
    session, user = request["session"], request["user"]
    all_quests = await quests_repo.list_quests(session)

    payload = []
    for quest in all_quests:
        key = quest_service.period_key(quest.scope)
        progress = await quests_repo.get_progress(session, user, quest, key)
        progress_count = progress.progress_count if progress else 0
        claimed = progress.claimed if progress else False
        reset_label = quest_service.format_timedelta(quest_service.time_until_reset(quest.scope))
        payload.append(_quest_json(quest, progress_count, claimed, reset_label))

    return web.json_response(payload)


@routes.post("/api/quests/{quest_id}/claim")
async def post_quest_claim(request: web.Request) -> web.Response:
    session, user = request["session"], request["user"]
    quest = await session.get(Quest, int(request.match_info["quest_id"]))
    if quest is None:
        return web.json_response({"error": "not_found"}, status=404)

    key = quest_service.period_key(quest.scope)
    progress = await quests_repo.get_progress(session, user, quest, key)
    if progress is None or progress.progress_count < quest.target_count:
        return web.json_response({"error": "not_ready"}, status=400)
    if progress.claimed:
        return web.json_response({"error": "already_claimed"}, status=400)

    progress.claimed = True
    await session.commit()
    user = await add_balance(session, user, quest.reward_tokens)

    return web.json_response({"reward": quest.reward_tokens, "balance": user.balance})


# -------------------------------------------------------------------- бонусы


@routes.get("/api/referral")
async def get_referral(request: web.Request) -> web.Response:
    session, user = request["session"], request["user"]
    bot = request.app["bot"]
    referral_count = await count_referrals(session, user)
    tier = tier_for_count(referral_count)
    next_tier = next_tier_for_count(referral_count)

    me = await bot.get_me()
    return web.json_response(
        {
            "code": user.referral_code,
            "link": f"https://t.me/{me.username}?start=ref_{user.referral_code}",
            "tier": (
                {"name": "Партнёр", "commission_percent": user.partner_percent}
                if user.partner_percent is not None
                else {"name": tier.name, "commission_percent": tier.commission_percent}
            ),
            "next_tier": (
                {"name": next_tier.name, "remaining": next_tier.min_referrals - referral_count}
                if next_tier
                else None
            ),
            "referral_count": referral_count,
            "earned_total": user.referral_earned_total,
        }
    )


@routes.get("/api/staking")
async def get_staking(request: web.Request) -> web.Response:
    session, user = request["session"], request["user"]
    active = await staking_repo.get_active_position(session, user)
    completed = await staking_repo.list_completed(session, user)
    all_positions = await staking_repo.list_all_for_user(session, user)

    return web.json_response(
        {
            "tiers": [{"term_days": t.term_days, "bonus_percent": t.bonus_percent, "label": t.label} for t in STAKE_TIERS],
            "min_amount": MIN_STAKE_AMOUNT,
            "balance": user.balance,
            "active": _stake_json(active) if active else None,
            "total_frozen": sum(p.amount for p in all_positions),
            "total_bonus": sum(payout_amount(p) - p.amount for p in completed),
            "completed_count": len(completed),
        }
    )


@routes.post("/api/staking/start")
async def post_staking_start(request: web.Request) -> web.Response:
    session, user = request["session"], request["user"]
    body = await request.json()
    term_days = body.get("term_days")
    amount = body.get("amount")

    tier = tier_by_term(int(term_days)) if term_days else None
    if tier is None:
        return web.json_response({"error": "invalid_tier"}, status=400)
    if not isinstance(amount, int) or not (MIN_STAKE_AMOUNT <= amount <= user.balance):
        return web.json_response({"error": "invalid_amount", "min_amount": MIN_STAKE_AMOUNT, "balance": user.balance}, status=400)

    active = await staking_repo.get_active_position(session, user)
    if active is not None:
        return web.json_response({"error": "already_active"}, status=400)

    user.balance -= amount
    await session.commit()
    position = await staking_repo.create_position(session, user, amount, tier.term_days, tier.bonus_percent)

    return web.json_response({"position": _stake_json(position), "balance": user.balance})


@routes.post("/api/staking/{position_id}/claim")
async def post_staking_claim(request: web.Request) -> web.Response:
    session, user = request["session"], request["user"]
    position = await staking_repo.get_position(session, int(request.match_info["position_id"]))
    if position is None or position.user_id != user.id:
        return web.json_response({"error": "not_found"}, status=404)
    if not is_matured(position):
        return web.json_response({"error": "not_matured", "matures_at": position.matures_at.isoformat()}, status=400)

    payout = payout_amount(position)
    user.balance += payout
    position.status = StakeStatus.COMPLETED
    await session.commit()
    await session.refresh(user)

    return web.json_response({"payout": payout, "balance": user.balance})


# ------------------------------------------------------------------- розыгрыши


@routes.get("/api/giveaways")
async def get_giveaways(request: web.Request) -> web.Response:
    session, user = request["session"], request["user"]
    await resolve_all_expired(session)
    active = await giveaways_repo.list_active(session)

    payload = []
    for giveaway in active:
        entry = await giveaways_repo.get_entry(session, giveaway, user)
        entries = await giveaways_repo.count_entries(session, giveaway)
        payload.append(_giveaway_json(giveaway, entry is not None, entries))

    return web.json_response(payload)


@routes.post("/api/giveaways/{giveaway_id}/join")
async def post_giveaway_join(request: web.Request) -> web.Response:
    session, user = request["session"], request["user"]
    giveaway = await giveaways_repo.get(session, int(request.match_info["giveaway_id"]))
    if giveaway is None or giveaway.status != GiveawayStatus.ACTIVE:
        return web.json_response({"error": "not_active"}, status=400)

    existing = await giveaways_repo.get_entry(session, giveaway, user)
    if existing:
        return web.json_response({"error": "already_joined"}, status=400)

    await giveaways_repo.join(session, giveaway, user)
    return web.json_response({"joined": True})


# ------------------------------------------------------------------------ faq


_bot_username: str | None = None


@routes.get("/api/support")
async def get_support(request: web.Request) -> web.Response:
    """Ссылка на поддержку: отдельный бот, если подключён, иначе
    чат поддержки в основном боте (t.me/<бот>?start=support)."""
    support_bot = await settings_service.get_setting(request["session"], settings_service.SUPPORT_BOT_USERNAME)
    if support_bot:
        return web.json_response({"url": f"https://t.me/{support_bot}?start=support"})
    global _bot_username
    if _bot_username is None:
        _bot_username = (await request.app["bot"].get_me()).username
    return web.json_response({"url": f"https://t.me/{_bot_username}?start=support"})


@routes.get("/api/faq")
async def get_faq(_request: web.Request) -> web.Response:
    return web.json_response([{"question": q, "answer": a} for q, a in FAQ_ENTRIES])


# -------------------------------------------------------------- промокоды


PROMO_ERRORS = {
    "not_found": "Такого промокода нет",
    "exhausted": "Промокод закончился",
    "already_used": "Ты уже активировал этот промокод",
}


def _promo_json(promo) -> dict:
    return {
        "code": promo.code,
        "kind": promo.kind.value,
        "amount": promo.amount,
        "case_code": promo.case_code,
        "max_uses": promo.max_uses,
        "uses": promo.uses,
    }


@routes.post("/api/promo/redeem")
async def post_promo_redeem(request: web.Request) -> web.Response:
    session, user = request["session"], request["user"]
    code = str((await request.json()).get("code", "")).strip()
    if not code:
        return web.json_response({"error": "empty", "message": "Введи промокод"}, status=400)
    try:
        promo = await rewards_repo.redeem_promo(session, user, code)
    except rewards_repo.PromoError as err:
        if err.code != "not_found":
            return web.json_response({"error": err.code, "message": PROMO_ERRORS[err.code]}, status=400)
        # Не промокод — возможно, личный код партнёра.
        try:
            pc = await partner_service.apply_partner_code(session, user, code)
        except partner_service.PartnerError as perr:
            if perr.code == "not_found":
                return web.json_response({"error": "not_found", "message": PROMO_ERRORS["not_found"]}, status=400)
            return web.json_response({"error": perr.code, "message": PARTNER_ERRORS[perr.code]}, status=400)
        await session.refresh(user)
        return web.json_response({
            "partner": {"deposit_bonus_percent": pc.deposit_bonus_percent, "case_code": pc.case_code, "case_amount": pc.case_amount},
            "me": await _user_json(request),
        })
    await session.refresh(user)
    return web.json_response({"promo": _promo_json(promo), "me": await _user_json(request)})


PARTNER_ERRORS = {
    "own_code": "Это твой собственный партнёрский код",
    "already_partner_ref": "Партнёрский код уже активирован",
}


# ------------------------------------------------------------ админ-панель
# Доступ — только Telegram id из ADMIN_IDS; проверяется на каждом запросе.


def _require_admin(request: web.Request) -> web.Response | None:
    if not is_admin(request["user"].tg_id):
        return web.json_response({"error": "forbidden"}, status=403)
    return None


@routes.post("/api/admin/luck")
async def post_admin_luck(request: web.Request) -> web.Response:
    """Подкрутка шансов игрока: luck ×0…×20 (0 — ничего не заходит), null — снять."""
    if (denied := _require_admin(request)) is not None:
        return denied
    session = request["session"]
    body = await request.json()
    target, err = await _admin_target(request, str(body.get("user", "")))
    if err is not None:
        return err
    luck = body.get("luck")
    if luck in (None, "", 1, 1.0, "1"):
        target.luck = None
    else:
        value = _num(luck)
        if value is None or not 0 <= value <= 20:
            return web.json_response({"error": "bad_luck", "message": "Подкрутка: от ×0 до ×20"}, status=400)
        target.luck = value
    await session.commit()
    return web.json_response(await _admin_user_json(session, target))


@routes.get("/api/admin/deposits")
async def get_admin_deposits(request: web.Request) -> web.Response:
    """Открытые заявки на пополнение (на проверке и в очереди) — старые сверху."""
    if (denied := _require_admin(request)) is not None:
        return denied
    session = request["session"]
    rows = (await session.execute(
        select(DepositRequest).where(DepositRequest.status.in_(deposit_moderation.OPEN_STATUSES)).order_by(DepositRequest.id)
    )).scalars().all()
    result = []
    for r in rows:
        items_by_id = {int(i): await deposit_items_repo.get_item(session, int(i)) for i in r.items}
        data = _deposit_request_json(r, {k: v for k, v in items_by_id.items() if v}, await deposit_moderation.queue_position(session, r))
        owner = await session.get(User, r.user_id)
        data["player"] = f"@{owner.username}" if owner.username else (owner.first_name or str(owner.tg_id))
        data["player_tg_id"] = owner.tg_id
        result.append(data)
    return web.json_response(result)


@routes.post("/api/admin/deposits/{request_id}")
async def post_admin_deposit_decision(request: web.Request) -> web.Response:
    if (denied := _require_admin(request)) is not None:
        return denied
    body = await request.json()
    approve = body.get("action") == "approve"
    try:
        decision = await deposit_moderation.resolve_deposit(
            request["session"], request.app["bot"], int(request.match_info["request_id"]),
            approve=approve, admin_tg_id=request["user"].tg_id,
        )
    except deposit_moderation.DepositAlreadyResolved:
        return web.json_response({"error": "already_resolved", "message": "Заявка уже обработана"}, status=400)
    except deposit_moderation.NotYourTurn:
        return web.json_response({"error": "not_your_turn", "message": "Сначала заявка, которая первая в очереди"}, status=400)
    return web.json_response({"id": decision.request.id, "status": decision.request.status.value, "credited": decision.credited})


@routes.get("/api/admin/settings")
async def get_admin_settings(request: web.Request) -> web.Response:
    if (denied := _require_admin(request)) is not None:
        return denied
    session = request["session"]
    return web.json_response({
        "required_channel": await settings_service.required_channel(session),
        "free_case_cooldown_hours": await settings_service.free_case_cooldown_hours(session),
        "support_url": await settings_service.get_setting(session, settings_service.SUPPORT_URL),
        "support_bot": await settings_service.get_setting(session, settings_service.SUPPORT_BOT_USERNAME),
        "design": await settings_service.ui_design(session),
        "stars_rate": await stars_service.rate(session),
        "stars_code_bonus_percent": await stars_service.code_bonus(session),
    })


@routes.post("/api/admin/settings")
async def post_admin_settings(request: web.Request) -> web.Response:
    """Канал обязательной подписки (пусто — отключить) и кулдаун бесплатного кейса."""
    if (denied := _require_admin(request)) is not None:
        return denied
    session = request["session"]
    body = await request.json()
    if "required_channel" in body:
        try:
            channel = settings_service.normalize_channel(body.get("required_channel") or "")
        except ValueError:
            return web.json_response({"error": "bad_channel", "message": "Канал: @username или ссылка t.me/…"}, status=400)
        if channel:
            # Бот должен видеть участников канала, иначе проверка подписки
            # всегда будет «нет» — сразу говорим об этом админу.
            try:
                await request.app["bot"].get_chat_member(channel, request["user"].tg_id)
            except Exception:  # noqa: BLE001
                return web.json_response({
                    "error": "bot_not_in_channel",
                    "message": f"Добавь бота админом в {channel}, иначе подписку не проверить",
                }, status=400)
        await settings_service.set_setting(session, settings_service.REQUIRED_CHANNEL, channel)
    for key, field, lo, hi in ((stars_service.STARS_RATE, "stars_rate", 0.01, 100),
                               (stars_service.STARS_CODE_BONUS, "stars_code_bonus_percent", 0, 500)):
        if field in body:
            value = _num(body.get(field))
            if value is None or not lo <= value <= hi:
                return web.json_response({"error": "bad_" + field, "message": f"{field}: от {lo} до {hi}"}, status=400)
            await settings_service.set_setting(session, key, f"{value:g}")
    if "support_url" in body:
        try:
            support = settings_service.normalize_link(body.get("support_url") or "")
        except ValueError:
            return web.json_response({"error": "bad_link", "message": "Поддержка: @username или https-ссылка"}, status=400)
        await settings_service.set_setting(session, settings_service.SUPPORT_URL, support)
    if "design" in body:
        if body.get("design") not in settings_service.UI_DESIGNS:
            return web.json_response({"error": "bad_design", "message": "Дизайн: v2 или classic"}, status=400)
        await settings_service.set_setting(session, settings_service.UI_DESIGN, body["design"])
    if "support_bot_token" in body:
        token = str(body.get("support_bot_token") or "").strip()
        if token:
            try:
                username = await support_bot.check_token(token)
            except support_bot.BadToken:
                return web.json_response({"error": "bad_token", "message": "Токен не подошёл — скопируй его из @BotFather целиком"}, status=400)
            if token == config.bot_token:
                return web.json_response({"error": "bad_token", "message": "Это токен основного бота — нужен токен нового бота поддержки"}, status=400)
            await settings_service.set_setting(session, settings_service.SUPPORT_BOT_TOKEN, token)
            await settings_service.set_setting(session, settings_service.SUPPORT_BOT_USERNAME, username)
            await support_bot.start(token)
        else:  # пусто — отключить отдельного бота, поддержка снова в основном
            await settings_service.set_setting(session, settings_service.SUPPORT_BOT_TOKEN, None)
            await settings_service.set_setting(session, settings_service.SUPPORT_BOT_USERNAME, None)
            await support_bot.stop()
    if "free_case_cooldown_hours" in body:
        hours = _num(body.get("free_case_cooldown_hours"))
        if hours is None or not 0 < hours <= 24 * 7:
            return web.json_response({"error": "bad_cooldown", "message": "Кулдаун: от 0 до 168 часов"}, status=400)
        await settings_service.set_setting(session, settings_service.FREE_CASE_COOLDOWN_HOURS, f"{hours:g}")
    return await get_admin_settings(request)


async def _admin_target(request: web.Request, query: str):
    target = await find_user(request["session"], query or "")
    if target is None:
        return None, web.json_response({"error": "user_not_found", "message": "Пользователь не найден (он должен хотя бы раз открыть бота)"}, status=404)
    return target, None


async def _admin_user_json(session, target) -> dict:
    return {
        "tg_id": target.tg_id,
        "username": target.username,
        "first_name": target.first_name,
        "balance": target.balance,
        "partner_percent": target.partner_percent,
        "luck": target.luck,
        "is_admin": is_admin(target.tg_id),
        "is_owner": is_owner(target.tg_id),
        "referral_count": await count_referrals(session, target),
        "case_credits": await rewards_repo.case_credits(session, target),
    }


async def _reload_admins(session) -> list[int]:
    ids = list((await session.execute(select(AdminGrant.tg_id))).scalars().all())
    set_granted_admins(ids)
    return ids


@routes.get("/api/admin/admins")
async def get_admin_admins(request: web.Request) -> web.Response:
    """Выданные админки — видит и меняет только владелец (ADMIN_IDS)."""
    if not is_owner(request["user"].tg_id):
        return web.json_response({"error": "forbidden"}, status=403)
    session = request["session"]
    out = []
    for tg_id in await _reload_admins(session):
        u = await get_user_by_tg_id(session, tg_id)
        out.append({"tg_id": tg_id, "username": u.username if u else None, "first_name": u.first_name if u else None})
    return web.json_response(out)


@routes.post("/api/admin/admins")
async def post_admin_admins(request: web.Request) -> web.Response:
    """{user, action: grant|revoke} — выдать или снять админ-панель."""
    if not is_owner(request["user"].tg_id):
        return web.json_response({"error": "forbidden", "message": "Выдавать админку может только владелец"}, status=403)
    session = request["session"]
    body = await request.json()
    target, err = await _admin_target(request, str(body.get("user", "")))
    if err is not None:
        return err
    if is_owner(target.tg_id):
        return web.json_response({"error": "owner", "message": "Это владелец — его админку не снять"}, status=400)
    row = await session.get(AdminGrant, target.tg_id)
    if body.get("action") == "grant":
        if row is None:
            session.add(AdminGrant(tg_id=target.tg_id, granted_by=request["user"].tg_id))
    elif row is not None:
        await session.delete(row)
    await session.commit()
    await _reload_admins(session)
    return web.json_response(await _admin_user_json(session, target))


@routes.get("/api/admin/user")
async def get_admin_user(request: web.Request) -> web.Response:
    if (denied := _require_admin(request)) is not None:
        return denied
    target, err = await _admin_target(request, request.query.get("q", ""))
    if err is not None:
        return err
    return web.json_response(await _admin_user_json(request["session"], target))


@routes.post("/api/admin/grant")
async def post_admin_grant(request: web.Request) -> web.Response:
    if (denied := _require_admin(request)) is not None:
        return denied
    session = request["session"]
    body = await request.json()
    target, err = await _admin_target(request, str(body.get("user", "")))
    if err is not None:
        return err
    kind = body.get("kind")
    try:
        amount = int(body.get("amount", 0))
    except (TypeError, ValueError):
        amount = 0
    if amount <= 0 or amount > 10_000_000:
        return web.json_response({"error": "bad_amount", "message": "Неверное количество"}, status=400)

    if kind in ("balance", "tokens"):  # «tokens» — старые клиенты: демо-фишек больше нет
        await add_balance(session, target, amount)
    elif kind == "case":
        code = body.get("case_code")
        if code not in CASE_THEMES:
            return web.json_response({"error": "bad_case", "message": "Неизвестный кейс"}, status=400)
        await rewards_repo.add_case_credits(session, target, code, amount)
    else:
        return web.json_response({"error": "bad_kind"}, status=400)
    await session.refresh(target)
    return web.json_response(await _admin_user_json(session, target))


@routes.post("/api/admin/balance")
async def post_admin_balance(request: web.Request) -> web.Response:
    """Списать у игрока amount B или обнулить баланс (mode=zero)."""
    if (denied := _require_admin(request)) is not None:
        return denied
    session = request["session"]
    body = await request.json()
    target, err = await _admin_target(request, str(body.get("user", "")))
    if err is not None:
        return err
    if body.get("mode") == "zero":
        target.balance = 0
    else:
        amount = _num(body.get("amount"))
        if amount is None or amount <= 0:
            return web.json_response({"error": "bad_amount", "message": "Неверное количество"}, status=400)
        target.balance = max(0, target.balance - int(amount))
    await session.commit()
    return web.json_response(await _admin_user_json(session, target))


@routes.post("/api/admin/partner")
async def post_admin_partner(request: web.Request) -> web.Response:
    if (denied := _require_admin(request)) is not None:
        return denied
    session = request["session"]
    body = await request.json()
    target, err = await _admin_target(request, str(body.get("user", "")))
    if err is not None:
        return err
    percent = body.get("percent")
    if percent in (None, ""):
        target.partner_percent = None  # снять партнёрку
    else:
        try:
            value = float(percent)
        except (TypeError, ValueError):
            value = -1
        if not 0 < value <= 50:
            return web.json_response({"error": "bad_percent", "message": "Процент — от 0 до 50"}, status=400)
        target.partner_percent = value
    await session.commit()
    await session.refresh(target)
    return web.json_response(await _admin_user_json(session, target))


@routes.get("/api/admin/promos")
async def get_admin_promos(request: web.Request) -> web.Response:
    if (denied := _require_admin(request)) is not None:
        return denied
    promos = await rewards_repo.list_promos(request["session"])
    return web.json_response([_promo_json(p) for p in promos])


@routes.post("/api/admin/promos")
async def post_admin_promo(request: web.Request) -> web.Response:
    if (denied := _require_admin(request)) is not None:
        return denied
    session = request["session"]
    body = await request.json()
    try:
        kind = PromoKind(body.get("kind"))
        amount = int(body.get("amount", 0))
        max_uses = int(body.get("max_uses", 1))
    except (TypeError, ValueError):
        return web.json_response({"error": "bad_request", "message": "Проверь поля"}, status=400)
    if amount <= 0 or not 1 <= max_uses <= 100_000:
        return web.json_response({"error": "bad_request", "message": "Количество и лимит должны быть > 0"}, status=400)
    case_code = body.get("case_code") if kind == PromoKind.CASE else None
    if kind == PromoKind.CASE and case_code not in CASE_THEMES:
        return web.json_response({"error": "bad_case", "message": "Выбери кейс"}, status=400)
    custom = str(body.get("code") or "").strip().upper() or None
    if custom and (len(custom) > 32 or not custom.replace("_", "").replace("-", "").isalnum()):
        return web.json_response({"error": "bad_code", "message": "Код: буквы/цифры, до 32 символов"}, status=400)
    if custom and (await rewards_repo.get_promo(session, custom) or await partner_service.get_partner_code(session, custom)):
        return web.json_response({"error": "code_taken", "message": "Такой код уже есть"}, status=400)
    promo = await rewards_repo.create_promo(
        session, kind=kind, amount=amount, max_uses=max_uses, case_code=case_code,
        code=custom, created_by_tg_id=request["user"].tg_id,
    )
    return web.json_response(_promo_json(promo))


# -------------------------------------------------------- админ: партнёрки


def _partner_code_json(pc, partner) -> dict:
    return {
        "code": pc.code,
        "is_active": pc.is_active,
        "uses": pc.uses,
        "deposit_bonus_percent": pc.deposit_bonus_percent,
        "case_code": pc.case_code,
        "case_amount": pc.case_amount,
        "commission_percent": partner.partner_percent,
        "partner": {"tg_id": partner.tg_id, "username": partner.username, "first_name": partner.first_name},
    }


@routes.get("/api/admin/partners")
async def get_admin_partners(request: web.Request) -> web.Response:
    if (denied := _require_admin(request)) is not None:
        return denied
    rows = await partner_service.list_partner_codes(request["session"])
    return web.json_response([_partner_code_json(pc, u) for pc, u in rows])


def _num(value, default=None):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


@routes.post("/api/admin/partners")
async def post_admin_partner_grant(request: web.Request) -> web.Response:
    if (denied := _require_admin(request)) is not None:
        return denied
    session = request["session"]
    body = await request.json()
    target, err = await _admin_target(request, str(body.get("user", "")))
    if err is not None:
        return err
    commission = _num(body.get("commission_percent"))
    bonus = _num(body.get("deposit_bonus_percent"), 0)
    case_amount = int(_num(body.get("case_amount"), 1))
    case_code = body.get("case_code") or None
    if commission is None or not 0 < commission <= 50:
        return web.json_response({"error": "bad_percent", "message": "% партнёра — от 0 до 50"}, status=400)
    if not 0 <= bonus <= 100:
        return web.json_response({"error": "bad_bonus", "message": "Бонус к пополнению — от 0 до 100%"}, status=400)
    if case_code is not None and case_code not in CASE_THEMES:
        return web.json_response({"error": "bad_case", "message": "Неизвестный кейс"}, status=400)
    if not 0 <= case_amount <= 100:
        return web.json_response({"error": "bad_amount", "message": "Кейсов — от 0 до 100"}, status=400)
    code = str(body.get("code") or "").strip().upper() or None
    if code:
        if len(code) > 32 or not code.replace("_", "").replace("-", "").isalnum():
            return web.json_response({"error": "bad_code", "message": "Код: буквы/цифры, до 32 символов"}, status=400)
        taken = await partner_service.get_partner_code(session, code)
        if (taken and taken.user_id != target.id) or await rewards_repo.get_promo(session, code):
            return web.json_response({"error": "code_taken", "message": "Такой код уже занят"}, status=400)
    pc = await partner_service.grant_partnership(
        session, target, commission_percent=commission, deposit_bonus_percent=bonus,
        case_code=case_code, case_amount=case_amount, code=code,
    )
    return web.json_response(_partner_code_json(pc, target))


@routes.post("/api/admin/partners/revoke")
async def post_admin_partner_revoke(request: web.Request) -> web.Response:
    if (denied := _require_admin(request)) is not None:
        return denied
    target, err = await _admin_target(request, str((await request.json()).get("user", "")))
    if err is not None:
        return err
    await partner_service.revoke_partnership(request["session"], target)
    return web.json_response({"ok": True})
