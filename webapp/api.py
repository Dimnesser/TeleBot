"""REST API Mini App'а — тонкий HTTP-слой поверх тех же bot.database.repo и
bot.services, что использует long-polling бот. Игровая логика НЕ дублируется:
каждый хендлер здесь — прямой аналог соответствующего callback-хендлера в
bot/handlers/*.py, просто с JSON вместо edit_text/inline-кнопок.
"""
from __future__ import annotations

from aiohttp import web

from bot.config import config
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
)
from bot.database.repo import cases as cases_repo
from bot.database.repo import giveaways as giveaways_repo
from bot.database.repo import inventory as inventory_repo
from bot.database.repo import quests as quests_repo
from bot.database.repo import staking as staking_repo
from bot.database.repo.known_items import list_known_items
from bot.database.repo.users import add_game_tokens, count_referrals
from bot.services import quest_service
from bot.services.battle_service import run_battle
from bot.services.cases_service import draw_items, total_cost
from bot.services.dice_service import COLORS, MATCH_PAYOUT_TABLE, resolve_roll
from bot.services.giveaway_service import resolve_all_expired
from bot.services.staking_service import MIN_STAKE_AMOUNT, STAKE_TIERS, is_matured, payout_amount, tier_by_term
from bot.services.upgrader_service import chance_percent, roll_success
from bot.utils.texts import FAQ_ENTRIES
from webapp.crash_runtime import cashout as crash_cashout
from webapp.crash_runtime import history_label as crash_history_label
from webapp.crash_runtime import poll_state as crash_poll_state
from webapp.crash_runtime import start_round as crash_start_round

routes = web.RouteTableDef()


# ---------------------------------------------------------------- сериализация


def _case_json(case: Case) -> dict:
    return {
        "id": case.id,
        "category": case.category.value,
        "name": case.name,
        "price_tokens": case.price_tokens,
        "item_count_label": case.item_count_label,
        "note": case.note,
        "is_openable": case.is_openable,
    }


def _case_item_json(item: CaseItem) -> dict:
    return {"name": item.name, "value": item.value}


def _inventory_item_json(item: InventoryItem) -> dict:
    return {
        "id": item.id,
        "case_id": item.case_id,
        "case_name": item.case_name,
        "item_name": item.item_name,
        "value": item.value,
        "obtained_at": item.obtained_at.isoformat(),
    }


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
        "tg_id": user.tg_id,
        "username": user.username,
        "first_name": user.first_name,
        "balance": user.balance,
        "game_tokens": user.game_tokens,
        "referral_code": user.referral_code,
        "referral_count": referral_count,
        "referral_earned_total": user.referral_earned_total,
    }


# --------------------------------------------------------------------- профиль


@routes.get("/api/me")
async def get_me(request: web.Request) -> web.Response:
    return web.json_response(await _user_json(request))


@routes.post("/api/demo-topup")
async def post_demo_topup(request: web.Request) -> web.Response:
    session, user = request["session"], request["user"]
    user = await add_game_tokens(session, user, config.demo_topup_tokens)
    return web.json_response({"game_tokens": user.game_tokens, "amount": config.demo_topup_tokens})


@routes.get("/api/inventory")
async def get_inventory(request: web.Request) -> web.Response:
    session, user = request["session"], request["user"]
    limit = int(request.query.get("limit", "20"))
    items = await inventory_repo.list_all(session, user)
    return web.json_response([_inventory_item_json(i) for i in items[:limit]])


# ----------------------------------------------------------------------- кейсы


@routes.get("/api/cases")
async def get_cases(request: web.Request) -> web.Response:
    session = request["session"]
    category = CaseCategory(request.query.get("category", CaseCategory.CASES.value))
    cases = await cases_repo.list_cases(session, category)
    return web.json_response({"category": category.value, "cases": [_case_json(c) for c in cases]})


@routes.get("/api/cases/{case_id}")
async def get_case_detail(request: web.Request) -> web.Response:
    session = request["session"]
    case = await cases_repo.get_case(session, int(request.match_info["case_id"]))
    if case is None:
        return web.json_response({"error": "not_found"}, status=404)
    items = await cases_repo.list_case_items(session, case.id)
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
    if user.game_tokens < cost:
        return web.json_response({"error": "not_enough_tokens", "cost": cost, "balance": user.game_tokens}, status=400)

    items = await cases_repo.list_case_items(session, case.id)
    won = draw_items(items, qty)

    user.game_tokens -= cost
    await session.commit()
    await session.refresh(user)

    await inventory_repo.add_items(session, user, case.name, [(i.name, i.value) for i in won], case_id=case.id)
    await quest_service.record_progress(session, user, f"open_case:{case.code}")

    return web.json_response(
        {"won": [_case_item_json(i) for i in won], "cost": cost, "game_tokens": user.game_tokens}
    )


# -------------------------------------------------------------------- апгрейдер


@routes.get("/api/upgrader/targets")
async def get_upgrader_targets(request: web.Request) -> web.Response:
    session = request["session"]
    min_value = int(request.query.get("min_value", "0"))
    exclude_name = request.query.get("exclude_name")
    items = await list_known_items(session)
    eligible = [i for i in items if i.value > min_value and i.name != exclude_name]
    return web.json_response([{"name": i.name, "value": i.value} for i in eligible])


@routes.post("/api/upgrader/spin")
async def post_upgrader_spin(request: web.Request) -> web.Response:
    session, user = request["session"], request["user"]
    body = await request.json()
    item_id = body.get("contribution_item_id")
    target_name = body.get("target_name")
    target_value = body.get("target_value")
    if not item_id or not target_name or not target_value:
        return web.json_response({"error": "missing_fields"}, status=400)

    item = await inventory_repo.get_by_id(session, int(item_id))
    if item is None or item.user_id != user.id:
        return web.json_response({"error": "item_gone"}, status=404)

    chance = chance_percent(item.value, int(target_value))
    success = roll_success(chance)

    contribution_label = {"name": item.item_name, "value": item.value}
    await inventory_repo.delete(session, item)
    won_item = None
    if success:
        won_item = {"name": target_name, "value": int(target_value)}
        await inventory_repo.add_items(session, user, "Апгрейдер", [(target_name, int(target_value))])
    await quest_service.record_progress(session, user, "upgrader_spin")

    return web.json_response(
        {"success": success, "chance": chance, "contribution": contribution_label, "won_item": won_item}
    )


# ------------------------------------------------------------------------ краш


@routes.get("/api/crash/state")
async def get_crash_state(request: web.Request) -> web.Response:
    user = request["user"]
    state = crash_poll_state(user.tg_id)
    if state is None:
        return web.json_response({"active": False, "history": crash_history_label()})

    round_, mult, crashed = state
    return web.json_response(
        {
            "active": not crashed,
            "crashed": crashed,
            "multiplier": mult,
            "stake": {"name": round_.item_name, "value": round_.item_value},
            "history": crash_history_label(),
        }
    )


@routes.post("/api/crash/start")
async def post_crash_start(request: web.Request) -> web.Response:
    session, user = request["session"], request["user"]
    body = await request.json()
    item_id = body.get("item_id")
    if not item_id:
        return web.json_response({"error": "missing_item"}, status=400)

    if crash_poll_state(user.tg_id) is not None:
        return web.json_response({"error": "already_running"}, status=400)

    item = await inventory_repo.get_by_id(session, int(item_id))
    if item is None or item.user_id != user.id:
        return web.json_response({"error": "item_gone"}, status=404)

    item_name, item_value = item.item_name, item.value
    await inventory_repo.delete(session, item)
    crash_start_round(user.tg_id, item_name, item_value)

    return web.json_response({"active": True, "multiplier": 1.0, "stake": {"name": item_name, "value": item_value}})


@routes.post("/api/crash/cashout")
async def post_crash_cashout(request: web.Request) -> web.Response:
    session, user = request["session"], request["user"]
    result = crash_cashout(user.tg_id)
    if result is None:
        return web.json_response({"error": "no_active_round_or_crashed"}, status=400)

    round_, mult = result
    winnings = round(round_.item_value * mult)
    await inventory_repo.add_items(session, user, "Краш", [(round_.item_name, winnings)])

    return web.json_response({"multiplier": mult, "won_item": {"name": round_.item_name, "value": winnings}})


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
        won_item = {"name": item_name, "value": winnings}
        await inventory_repo.add_items(session, user, "Дайсы", [(item_name, winnings)])

    return web.json_response(
        {
            "dice": result.dice,
            "match_count": result.match_count,
            "bonus": result.bonus,
            "win": result.is_win,
            "multiplier": result.multiplier,
            "stake": {"name": item_name, "value": item_value},
            "won_item": won_item,
        }
    )


# ---------------------------------------------------------------------- батл


@routes.get("/api/battle/cases")
async def get_battle_cases(request: web.Request) -> web.Response:
    session = request["session"]
    openable = []
    for category in CaseCategory:
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
    if user.game_tokens < cost:
        return web.json_response({"error": "not_enough_tokens", "cost": cost, "balance": user.game_tokens}, status=400)

    user.game_tokens -= cost
    await session.commit()
    await session.refresh(user)

    items = await cases_repo.list_case_items(session, case.id)
    result = run_battle(items)

    if result.winner == "player":
        await inventory_repo.add_items(
            session,
            user,
            f"Батл: {case.name}",
            [(result.player_item.name, result.player_item.value), (result.bot_item.name, result.bot_item.value)],
            case_id=case.id,
        )
    elif result.winner == "tie":
        await add_game_tokens(session, user, cost)

    return web.json_response(
        {
            "winner": result.winner,
            "player_item": _case_item_json(result.player_item),
            "bot_item": _case_item_json(result.bot_item),
            "game_tokens": user.game_tokens,
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
    user = await add_game_tokens(session, user, quest.reward_tokens)

    return web.json_response({"reward": quest.reward_tokens, "game_tokens": user.game_tokens})


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
            "tier": {"name": tier.name, "commission_percent": tier.commission_percent},
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


@routes.get("/api/faq")
async def get_faq(_request: web.Request) -> web.Response:
    return web.json_response([{"question": q, "answer": a} for q, a in FAQ_ENTRIES])
