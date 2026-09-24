"""Интеграционные тесты Mini App API (webapp/api.py, webapp/server.py).

conftest.in_memory_db патчит bot.database.engine.async_session — но
webapp/server.py импортирует async_session отдельным именем
(`from bot.database.engine import async_session`), как и обработчики бота,
поэтому здесь дополнительно патчим и его на ту же тестовую БД.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import time
from urllib.parse import urlencode

import pytest
from aiohttp.test_utils import TestClient, TestServer

import webapp.server as webapp_server_module
from bot.config import config
from webapp.server import create_app


class FakeBot:
    """Бот-заглушка: канал @braincore_news существует, подписчики — в subscribers."""

    channels = {"@braincore_news"}

    def __init__(self):
        self.subscribers: set[int] = set()
        self.sent: list[tuple[int, str]] = []

    async def send_message(self, chat_id, text, **kwargs):
        self.sent.append((chat_id, text))

    async def get_me(self):
        class Me:
            username = "BrainCorre_bot"

        return Me()

    async def create_invoice_link(self, **kwargs):
        self.last_invoice = kwargs
        return f"https://t.me/$invoice_{kwargs['payload']}"

    async def get_chat_member(self, chat_id, user_id):
        if chat_id not in self.channels:
            raise RuntimeError("chat not found")

        class Member:
            status = "member" if user_id in self.subscribers else "left"

        return Member()


TEST_BALANCE = 1_000_000


def _init_data(tg_id: int, *, username: str = "tester", first_name: str = "Test") -> str:
    # config.bot_token — frozen dataclass, не подменяем: подписываем тем же
    # токеном, который реально видит middleware (в тестовом окружении обычно
    # пустая строка — HMAC с ней работает точно так же, как с любой другой).
    user = json.dumps({"id": tg_id, "username": username, "first_name": first_name})
    data = {"auth_date": str(int(time.time())), "user": user, "query_id": "AAABBBCCC"}
    check_string = "\n".join(f"{k}={v}" for k, v in sorted(data.items()))
    secret = hmac.new(b"WebAppData", config.bot_token.encode(), hashlib.sha256).digest()
    data["hash"] = hmac.new(secret, check_string.encode(), hashlib.sha256).hexdigest()
    return urlencode(data)


@pytest.fixture
async def client(in_memory_db, monkeypatch):
    monkeypatch.setattr(webapp_server_module, "async_session", in_memory_db)

    # conftest.in_memory_db only creates tables (Base.metadata.create_all) —
    # seed the same case/quest fixture data init_db() would normally add,
    # via the private seed helpers (they look up bot.database.engine's own
    # async_session at call time, which conftest already points at the test DB).
    # _seed_cases_reconcile also needs the app_meta table, already created above.
    from bot.database.engine import _seed_cases_reconcile, _seed_items_reconcile, _seed_quests_if_empty

    await _seed_items_reconcile()
    await _seed_cases_reconcile()
    await _seed_quests_if_empty()

    # Демо-фишек больше нет: основному тестовому игроку (auth_headers) заранее
    # кладём B на баланс, чтобы открывать кейсы и батлы.
    from bot.database.repo.users import get_or_create_user

    async with in_memory_db() as session:
        user = await get_or_create_user(session, 999111, "tester", "Test")
        user.balance = TEST_BALANCE
        await session.commit()

    app = create_app(FakeBot())
    server = TestServer(app)
    test_client = TestClient(server)
    await test_client.start_server()
    try:
        yield test_client
    finally:
        await test_client.close()


@pytest.fixture
def auth_headers():
    return {"Authorization": "tma " + _init_data(999111)}


async def test_me_requires_auth(client) -> None:
    r = await client.get("/api/me")
    assert r.status == 401


async def test_me_auto_creates_user(client, auth_headers) -> None:
    r = await client.get("/api/me", headers=auth_headers)
    assert r.status == 200
    body = await r.json()
    assert body["tg_id"] == 999111
    assert body["balance"] == TEST_BALANCE
    # новый игрок — без стартовых фишек: демо-режима нет
    r = await client.get("/api/me", headers={"Authorization": "tma " + _init_data(123123)})
    assert (await r.json())["balance"] == 0
    assert "game_tokens" not in await r.json()


async def test_cases_feed_and_open(client, auth_headers) -> None:
    r = await client.get("/api/cases?category=starter", headers=auth_headers)
    assert r.status == 200
    cases = (await r.json())["cases"]
    openable = next(c for c in cases if c["is_openable"] and c["price_tokens"])

    r = await client.post(f"/api/cases/{openable['id']}/open", headers=auth_headers, json={"qty": 1})
    assert r.status == 200
    body = await r.json()
    assert len(body["won"]) == 1

    r = await client.get("/api/inventory", headers=auth_headers)
    inventory = await r.json()
    assert len(inventory) == 1
    assert inventory[0]["name"] == body["won"][0]["name"]


async def test_inventory_sell(client, auth_headers) -> None:
    r = await client.get("/api/cases?category=starter", headers=auth_headers)
    case = next(c for c in (await r.json())["cases"] if c["is_openable"] and c["price_tokens"])
    r = await client.post(f"/api/cases/{case['id']}/open", headers=auth_headers, json={"qty": 1})
    won = (await r.json())["won"][0]

    r = await client.get("/api/me", headers=auth_headers)
    tokens_before = (await r.json())["balance"]

    r = await client.get("/api/inventory", headers=auth_headers)
    item = (await r.json())[0]

    r = await client.post(f"/api/inventory/{item['id']}/sell", headers=auth_headers)
    assert r.status == 200
    body = await r.json()
    assert body["sold_name"] == won["name"]
    assert body["payout"] == won["value"]
    assert body["balance"] == tokens_before + body["payout"]

    r = await client.get("/api/inventory", headers=auth_headers)
    assert await r.json() == []

    # повторная продажа того же (уже удалённого) предмета -> 404, не крэш
    r = await client.post(f"/api/inventory/{item['id']}/sell", headers=auth_headers)
    assert r.status == 404


async def test_case_open_reel_lands_on_server_decided_winner(client, auth_headers) -> None:
    """Провабли-фёрность: результат решает сервер ДО генерации ленты
    рулетки — лента только декорация вокруг уже готового исхода, клиент
    не может повлиять на won[]. Прогоняем несколько раз, т.к. и выбор
    результата, и наполнение ленты — рандом."""
    r = await client.get("/api/cases?category=starter", headers=auth_headers)
    case = next(c for c in (await r.json())["cases"] if c["is_openable"] and c["price_tokens"])

    for _ in range(8):
        r = await client.get(f"/api/me", headers=auth_headers)
        r = await client.post(f"/api/cases/{case['id']}/open", headers=auth_headers, json={"qty": 1})
        assert r.status == 200
        body = await r.json()
        assert len(body["reel"]) == 40
        assert body["reveal_index"] == 34
        landed = body["reel"][34]
        won = body["won"][0]
        assert landed["name"] == won["name"]
        assert landed["value"] == won["value"]
        assert landed["rarity"] == won["rarity"]


async def test_case_detail_hides_chances(client, auth_headers) -> None:
    r = await client.get("/api/cases?category=starter", headers=auth_headers)
    for case in (await r.json())["cases"]:
        r = await client.get(f"/api/cases/{case['id']}", headers=auth_headers)
        detail = await r.json()
        assert detail["items"]
        assert all("chance_percent" not in i for i in detail["items"])


async def test_case_open_rejects_insufficient_tokens(client, auth_headers) -> None:
    r = await client.get("/api/cases?category=starter", headers=auth_headers)
    cases = (await r.json())["cases"]
    openable = [c for c in cases if c["is_openable"] and c["price_tokens"]]
    assert openable, "seed data must contain at least one openable priced case"
    expensive = max(openable, key=lambda c: c["price_tokens"])

    # новый игрок с пустым балансом не может открыть платный кейс
    broke = {"Authorization": "tma " + _init_data(424242)}
    r = await client.post(f"/api/cases/{expensive['id']}/open", headers=broke, json={"qty": 1})
    assert r.status == 400
    body = await r.json()
    assert body["error"] == "not_enough_tokens" and body["balance"] == 0


async def test_upgrader_spin_consumes_contribution(client, auth_headers) -> None:
    r = await client.get("/api/cases?category=starter", headers=auth_headers)
    case = next(c for c in (await r.json())["cases"] if c["is_openable"] and c["price_tokens"])
    r = await client.post(f"/api/cases/{case['id']}/open", headers=auth_headers, json={"qty": 1})
    won = (await r.json())["won"][0]

    r = await client.get("/api/inventory", headers=auth_headers)
    contribution = (await r.json())[0]

    r = await client.get(
        f"/api/upgrader/targets?min_value={contribution['value']}&exclude_name={contribution['name']}",
        headers=auth_headers,
    )
    targets = await r.json()
    assert targets

    r = await client.post(
        "/api/upgrader/spin",
        headers=auth_headers,
        json={
            "contribution_item_id": contribution["id"],
            "target_name": targets[0]["name"],
            "target_value": targets[0]["value"],
        },
    )
    assert r.status == 200
    body = await r.json()
    assert "success" in body and "chance" in body

    # contribution всегда списывается; выигрыш добавляет новый предмет ровно
    # при success=True. Не сравниваем id напрямую: SQLite переиспользует
    # ROWID таблицы, опустевшей после удаления единственной строки.
    r = await client.get("/api/inventory", headers=auth_headers)
    remaining = await r.json()
    if body["success"]:
        assert len(remaining) == 1
        assert remaining[0]["name"] == targets[0]["name"]
        assert remaining[0]["value"] == targets[0]["value"]
    else:
        assert remaining == []


async def test_crash_start_state_cashout(client, auth_headers) -> None:
    r = await client.get("/api/cases?category=starter", headers=auth_headers)
    case = next(c for c in (await r.json())["cases"] if c["is_openable"] and c["price_tokens"])
    await client.post(f"/api/cases/{case['id']}/open", headers=auth_headers, json={"qty": 1})

    r = await client.get("/api/inventory", headers=auth_headers)
    item = (await r.json())[0]

    r = await client.post("/api/crash/start", headers=auth_headers, json={"item_id": item["id"]})
    assert r.status == 200

    r = await client.get("/api/crash/state", headers=auth_headers)
    state = await r.json()
    assert state["active"] or state["result"]["outcome"] == "crashed"
    assert state["stake"]["name"] == item["name"]

    if state["active"]:
        r = await client.post("/api/crash/cashout", headers=auth_headers)
        assert r.status == 200
        body = await r.json()
        assert body["result"]["outcome"] == "cashed"
        prize = body["result"]["prize"]
        assert prize["value"] >= item["value"]  # приз не хуже ставки
        inventory = await (await client.get("/api/inventory", headers=auth_headers)).json()
        assert inventory[0]["name"] == prize["name"]

    # итог раунда не теряется между опросами
    for _ in range(2):
        r = await client.get("/api/crash/state", headers=auth_headers)
        again = await r.json()
        assert again["active"] is False and again["result"]["outcome"] in ("crashed", "cashed")


async def test_dice_roll(client, auth_headers) -> None:
    r = await client.get("/api/cases?category=starter", headers=auth_headers)
    case = next(c for c in (await r.json())["cases"] if c["is_openable"] and c["price_tokens"])
    await client.post(f"/api/cases/{case['id']}/open", headers=auth_headers, json={"qty": 1})

    r = await client.get("/api/inventory", headers=auth_headers)
    item = (await r.json())[0]

    r = await client.get("/api/dice/rules", headers=auth_headers)
    color = (await r.json())["colors"][0]

    r = await client.post("/api/dice/roll", headers=auth_headers, json={"item_id": item["id"], "color": color})
    assert r.status == 200
    body = await r.json()
    assert len(body["dice"]) == 4


async def test_staking_flow(client, auth_headers, in_memory_db) -> None:
    from bot.database.repo.users import add_balance, get_user_by_tg_id

    async with in_memory_db() as session:
        user = await get_user_by_tg_id(session, 999111)
        if user is None:
            from bot.database.repo.users import get_or_create_user

            user = await get_or_create_user(session, 999111, "tester", "Test")
        await add_balance(session, user, 500)

    r = await client.get("/api/staking", headers=auth_headers)
    staking = await r.json()
    assert staking["balance"] == TEST_BALANCE + 500
    tier = staking["tiers"][0]

    r = await client.post("/api/staking/start", headers=auth_headers, json={"term_days": tier["term_days"], "amount": 200})
    assert r.status == 200

    r = await client.get("/api/staking", headers=auth_headers)
    staking2 = await r.json()
    assert staking2["active"] is not None
    assert staking2["active"]["matured"] is False


async def test_faq_and_giveaways_smoke(client, auth_headers) -> None:
    r = await client.get("/api/faq", headers=auth_headers)
    assert r.status == 200
    assert len(await r.json()) > 0

    r = await client.get("/api/giveaways", headers=auth_headers)
    assert r.status == 200
    assert isinstance(await r.json(), list)


async def test_static_pages_served(client) -> None:
    for path in ["/", "/webapp", "/static/js/app.js", "/static/css/app.css"]:
        r = await client.get(path)
        assert r.status == 200, path


async def test_cases_catalog_grouped_by_collections(client, auth_headers) -> None:
    r = await client.get("/api/cases", headers=auth_headers)
    assert r.status == 200
    collections = (await r.json())["collections"]
    assert [c["key"] for c in collections] == ["starter", "free", "apex"]
    for collection in collections:
        for case in collection["cases"]:
            assert case["theme"]["filling"] and case["theme"]["aura"]
            assert case["top_item_image_url"].endswith(".webp")
            assert case["heroes"] and case["heroes"][0]["name"] == case["top_item_name"]
            assert case["image_url"] == f"/static/assets/cases/{case['code']}.webp"


async def test_free_case_gives_coins_or_brainrot_then_cooldown(client, auth_headers) -> None:
    cases = (await (await client.get("/api/cases?category=free", headers=auth_headers)).json())["cases"]
    free = cases[0]
    assert free["price_tokens"] == 0
    before = (await (await client.get("/api/me", headers=auth_headers)).json())["balance"]
    r = await client.post(f"/api/cases/{free['id']}/open", headers=auth_headers, json={"qty": 1})
    body = await r.json()
    assert r.status == 200 and body["cost"] == 0 and body["free_wait_seconds"] > 0
    won = body["won"][0]
    assert body["balance"] == before + (won["value"] if won.get("coins") else 0)
    r = await client.post(f"/api/cases/{free['id']}/open", headers=auth_headers, json={"qty": 1})
    assert r.status == 400 and (await r.json())["error"] == "free_cooldown"


async def test_case_items_carry_market_snapshot(client, auth_headers) -> None:
    cases = (await (await client.get("/api/cases?category=apex", headers=auth_headers)).json())["cases"]
    top = next(c for c in cases if c["code"] == "strawberry")
    items = (await (await client.get(f"/api/cases/{top['id']}", headers=auth_headers)).json())["items"]
    assert items[0]["name"] == "Strawberry Elephant" and items[0]["market"]["tier"] == "T0"


async def test_unknown_category_is_400(client, auth_headers) -> None:
    r = await client.get("/api/cases?category=nope", headers=auth_headers)
    assert r.status == 400


async def test_multi_open_returns_reel_per_win_and_real_game_info(client, auth_headers) -> None:
    r = await client.get("/api/cases?category=starter", headers=auth_headers)
    case = next(c for c in (await r.json())["cases"] if c["code"] == "crystal")  # только Secret
    r = await client.post(f"/api/cases/{case['id']}/open", headers=auth_headers, json={"qty": 3})
    assert r.status == 200
    body = await r.json()
    assert len(body["won"]) == len(body["reels"]) == 3
    for won, reel in zip(body["won"], body["reels"]):
        assert reel[body["reveal_index"]]["name"] == won["name"]
        assert won["rarity"] in ("secret", "og")
        assert won["game"]["wiki_url"].startswith("https://stealabrainrot.fandom.com/wiki/")
        assert won["inventory_id"]


async def test_upgrader_rejects_unknown_target(client, auth_headers) -> None:
    r = await client.get("/api/cases?category=starter", headers=auth_headers)
    case = min((await r.json())["cases"], key=lambda c: c["price_tokens"])
    await client.post(f"/api/cases/{case['id']}/open", headers=auth_headers, json={"qty": 1})
    item = (await (await client.get("/api/inventory", headers=auth_headers)).json())[0]
    r = await client.post(
        "/api/upgrader/spin",
        headers=auth_headers,
        json={"contribution_item_id": item["id"], "target_name": "Fake Brainrot", "target_value": 1},
    )
    assert r.status == 400
    # вклад не списан
    assert len(await (await client.get("/api/inventory", headers=auth_headers)).json()) == 1


async def test_upgrader_targets_chance_between_75_and_1(client, auth_headers) -> None:
    r = await client.get("/api/upgrader/targets?min_value=300", headers=auth_headers)
    targets = await r.json()
    assert targets
    for t in targets:
        assert 400 <= t["value"] <= 30000
        assert 1 <= t["chance_percent"] <= 75



# ---------------------------------------------------------- админка/промокоды


@pytest.fixture
def admin_headers(monkeypatch):
    from bot import config as config_module
    import webapp.api as api_module

    monkeypatch.setattr(api_module, "is_admin", lambda tg_id: tg_id == 777000)
    return {"Authorization": "tma " + _init_data(777000, username="boss")}


async def test_admin_endpoints_forbidden_for_regular_user(client, auth_headers) -> None:
    for method, path in (("get", "/api/admin/promos"), ("post", "/api/admin/grant"), ("post", "/api/admin/partner")):
        r = await getattr(client, method)(path, headers=auth_headers, **({"json": {}} if method == "post" else {}))
        assert r.status == 403
    me = await (await client.get("/api/me", headers=auth_headers)).json()
    assert me["is_admin"] is False


async def test_admin_grant_tokens_and_partner(client, auth_headers, admin_headers) -> None:
    await client.get("/api/me", headers=auth_headers)  # создаём игрока 999111
    me_admin = await (await client.get("/api/me", headers=admin_headers)).json()
    assert me_admin["is_admin"] is True

    r = await client.post("/api/admin/grant", headers=admin_headers, json={"user": "999111", "kind": "tokens", "amount": 500})
    assert r.status == 200
    before = (await r.json())["balance"]
    me = await (await client.get("/api/me", headers=auth_headers)).json()
    assert me["balance"] == before

    r = await client.post("/api/admin/partner", headers=admin_headers, json={"user": "@tester", "percent": 12})
    assert r.status == 200 and (await r.json())["partner_percent"] == 12
    ref = await (await client.get("/api/referral", headers=auth_headers)).json()
    assert ref["tier"] == {"name": "Партнёр", "commission_percent": 12}


async def test_promo_case_credits_open_case_for_free(client, auth_headers, admin_headers) -> None:
    await client.get("/api/me", headers=auth_headers)
    r = await client.post("/api/admin/promos", headers=admin_headers,
                          json={"kind": "case", "amount": 2, "case_code": "fastfood", "max_uses": 1, "code": "free-nonna"})
    assert r.status == 200 and (await r.json())["code"] == "FREE-NONNA"

    r = await client.post("/api/promo/redeem", headers=auth_headers, json={"code": "free-nonna"})
    assert r.status == 200
    assert (await r.json())["me"]["case_credits"] == {"fastfood": 2}
    # повторно — нельзя
    r = await client.post("/api/promo/redeem", headers=auth_headers, json={"code": "FREE-NONNA"})
    assert r.status == 400 and (await r.json())["error"] in ("already_used", "exhausted")

    cases = (await (await client.get("/api/cases?category=starter", headers=auth_headers)).json())["cases"]
    nonna = next(c for c in cases if c["code"] == "fastfood")
    tokens_before = (await (await client.get("/api/me", headers=auth_headers)).json())["balance"]
    r = await client.post(f"/api/cases/{nonna['id']}/open", headers=auth_headers, json={"qty": 1, "use_credits": True})
    body = await r.json()
    assert body["free"] is True and body["cost"] == 0 and body["credits_left"] == 1
    assert body["balance"] == tokens_before


async def test_promo_tokens_and_unknown_code(client, auth_headers, admin_headers) -> None:
    await client.get("/api/me", headers=auth_headers)
    promo = await (await client.post("/api/admin/promos", headers=admin_headers,
                                     json={"kind": "tokens", "amount": 300, "max_uses": 5})).json()
    assert len(promo["code"]) == 8
    before = (await (await client.get("/api/me", headers=auth_headers)).json())["balance"]
    r = await client.post("/api/promo/redeem", headers=auth_headers, json={"code": promo["code"].lower()})
    assert (await r.json())["me"]["balance"] == before + 300
    r = await client.post("/api/promo/redeem", headers=auth_headers, json={"code": "NOPE1234"})
    assert r.status == 400 and (await r.json())["error"] == "not_found"



async def test_partner_code_gives_referral_case_bonus_and_commission(client, auth_headers, admin_headers) -> None:
    from bot.database.engine import async_session as real_session  # noqa: F401  (сессия теста — та же in-memory)
    from bot.database.repo.users import get_user_by_tg_id
    from bot.services.partner_service import deposit_bonus
    from bot.services.referral_service import credit_referral_commission
    import webapp.server as server_module

    await client.get("/api/me", headers=admin_headers)  # партнёр = 777000
    await client.get("/api/me", headers=auth_headers)  # игрок = 999111

    r = await client.post("/api/admin/partners", headers=admin_headers, json={
        "user": "777000", "code": "boss10", "commission_percent": 10,
        "deposit_bonus_percent": 20, "case_code": "referral", "case_amount": 2,
    })
    assert r.status == 200 and (await r.json())["code"] == "BOSS10"
    listing = await (await client.get("/api/admin/partners", headers=admin_headers)).json()
    assert listing[0]["commission_percent"] == 10

    # свой код активировать нельзя
    r = await client.post("/api/promo/redeem", headers=admin_headers, json={"code": "boss10"})
    assert r.status == 400 and (await r.json())["error"] == "own_code"

    r = await client.post("/api/promo/redeem", headers=auth_headers, json={"code": "Boss10"})
    assert r.status == 200
    me = (await r.json())["me"]
    assert me["case_credits"] == {"referral": 2}
    assert me["deposit_bonus_percent"] == 20
    r = await client.post("/api/promo/redeem", headers=auth_headers, json={"code": "boss10"})
    assert (await r.json())["error"] == "already_partner_ref"

    # реферальный кейс: купить нельзя, открыть бесплатно — можно
    case = await (await client.get("/api/cases/by-code/referral", headers=auth_headers)).json()
    r = await client.post(f"/api/cases/{case['id']}/open", headers=auth_headers, json={"qty": 1})
    assert r.status == 400 and (await r.json())["error"] == "referral_only"
    r = await client.post(f"/api/cases/{case['id']}/open", headers=auth_headers, json={"qty": 1, "use_credits": True})
    assert r.status == 200 and (await r.json())["free"] is True

    # бонус к пополнению и комиссия партнёру
    async with server_module.async_session() as session:
        player = await get_user_by_tg_id(session, 999111)
        partner = await get_user_by_tg_id(session, 777000)
        assert deposit_bonus(player, 1000) == 200
        before = partner.balance
        assert await credit_referral_commission(session, player, 1000) == 100
        await session.refresh(partner)
        assert partner.balance == before + 100

    # снятие партнёрки — код больше не активируется
    r = await client.post("/api/admin/partners/revoke", headers=admin_headers, json={"user": "777000"})
    assert r.status == 200


async def test_market_pulse(client, auth_headers) -> None:
    body = await (await client.get("/api/market", headers=auth_headers)).json()
    assert body["hot"][0]["name"] == "Strawberry Elephant"
    assert all(b["market"]["demand"] == "Very Low" for b in body["cold"])
    assert body["sources"]


async def test_free_case_requires_channel_subscription(client, auth_headers, admin_headers) -> None:
    # бот не в канале — админу сразу говорят об этом
    r = await client.post("/api/admin/settings", headers=admin_headers, json={"required_channel": "@unknown_chan"})
    assert r.status == 400 and (await r.json())["error"] == "bot_not_in_channel"
    r = await client.post("/api/admin/settings", headers=admin_headers,
                          json={"required_channel": "https://t.me/braincore_news", "free_case_cooldown_hours": 12})
    body = await r.json()
    assert (body["required_channel"], body["free_case_cooldown_hours"], body["support_url"]) == ("@braincore_news", 12, None)
    assert body["stars_rate"] == 1.75
    # обычному игроку настройки недоступны
    assert (await client.get("/api/admin/settings", headers=auth_headers)).status == 403

    catalog = await (await client.get("/api/cases", headers=auth_headers)).json()
    assert catalog["required_channel"] == "@braincore_news" and catalog["free_cooldown_hours"] == 12
    free = next(c for col in catalog["collections"] for c in col["cases"] if c["category"] == "free")

    r = await client.post(f"/api/cases/{free['id']}/open", headers=auth_headers, json={"qty": 1})
    body = await r.json()
    assert r.status == 400 and body["error"] == "subscribe_required"
    assert body["channel_url"] == "https://t.me/braincore_news"

    client.server.app["bot"].subscribers.add(999111)
    r = await client.post(f"/api/cases/{free['id']}/open", headers=auth_headers, json={"qty": 1})
    body = await r.json()
    assert r.status == 200 and 11 * 3600 < body["free_wait_seconds"] <= 12 * 3600

    # отписка канала отключает проверку
    r = await client.post("/api/admin/settings", headers=admin_headers, json={"required_channel": ""})
    assert (await r.json())["required_channel"] is None



async def test_deposit_catalog_lists_brainrots_gears_and_stars(client, auth_headers) -> None:
    body = await (await client.get("/api/deposit/catalog", headers=auth_headers)).json()
    assert len(body["brainrot"]) == 57
    garama = next(i for i in body["brainrot"] if i["name"] == "Garama and Madundung")
    assert (garama["price_b"], garama["min_qty"]) == (41, 2) and garama["image_url"].endswith(".webp")
    assert body["hirsy"] and body["stars"]["rate"] >= 1


async def test_deposit_request_goes_to_moderation_not_balance(client, auth_headers) -> None:
    catalog = await (await client.get("/api/deposit/catalog", headers=auth_headers)).json()
    kraken = next(i for i in catalog["brainrot"] if i["name"] == "Kraken")
    before = (await (await client.get("/api/me", headers=auth_headers)).json())["balance"]
    r = await client.post("/api/deposit/request", headers=auth_headers,
                          json={"category": "brainrot", "items": {kraken["id"]: 1}, "nickname": "dimon"})
    body = await r.json()
    assert r.status == 200 and body["request"]["status"] == "pending" and body["request"]["total_b"] == 3077
    # B не начисляется, пока модератор не подтвердит
    assert (await (await client.get("/api/me", headers=auth_headers)).json())["balance"] == before
    mine = await (await client.get("/api/deposit/requests", headers=auth_headers)).json()
    assert mine[0]["items"] == [{"name": "Kraken", "qty": 1}]

    garama = next(i for i in catalog["brainrot"] if i["name"] == "Garama and Madundung")
    r = await client.post("/api/deposit/request", headers=auth_headers,
                          json={"category": "brainrot", "items": {garama["id"]: 1}, "nickname": "dimon"})
    assert r.status == 400 and (await r.json())["error"] == "bad_cart"  # «от 2 шт»


async def test_deposit_stars_creates_invoice(client, auth_headers) -> None:
    r = await client.post("/api/deposit/stars", headers=auth_headers, json={"amount": 100})
    body = await r.json()
    assert r.status == 200 and body["invoice_url"].startswith("https://t.me/$invoice_stars_dep:999111:")
    assert client.server.app["bot"].last_invoice["currency"] == "XTR"
    r = await client.post("/api/deposit/stars", headers=auth_headers, json={"amount": 1})
    assert r.status == 200  # минимума нет — от 1 ⭐
    r = await client.post("/api/deposit/stars", headers=auth_headers, json={"amount": 0})
    assert r.status == 400


async def test_deposit_queue_one_by_one(client, auth_headers, admin_headers) -> None:
    """Строгая очередь: одна заявка на игрока; в работе — первая; зачислить
    можно только её; после решения в работу уходит следующая."""
    catalog = await (await client.get("/api/deposit/catalog", headers=auth_headers)).json()
    assert "buffs" not in catalog  # бафы убраны
    kraken = next(i for i in catalog["brainrot"] if i["name"] == "Kraken")
    griffin = next(i for i in catalog["brainrot"] if i["name"] == "Griffin")
    second = {"Authorization": "tma " + _init_data(555777, username="second")}

    r = await client.post("/api/deposit/request", headers=auth_headers,
                          json={"category": "brainrot", "items": {kraken["id"]: 1}, "nickname": "dimon"})
    first = await r.json()
    assert first["queue_position"] == 1 and first["request"]["status"] == "pending"
    r = await client.post("/api/deposit/request", headers=auth_headers,
                          json={"category": "brainrot", "items": {griffin["id"]: 1}, "nickname": "dimon"})
    assert r.status == 400 and (await r.json())["error"] == "already_open"
    r = await client.post("/api/deposit/request", headers=second,
                          json={"category": "brainrot", "items": {griffin["id"]: 1}, "nickname": "vasya"})
    waiting = await r.json()
    assert waiting["queue_position"] == 2 and waiting["request"]["status"] == "queued"

    assert (await client.get("/api/admin/deposits", headers=auth_headers)).status == 403
    queue = await (await client.get("/api/admin/deposits", headers=admin_headers)).json()
    assert [(q["id"], q["queue_position"]) for q in queue] == [(first["request"]["id"], 1), (waiting["request"]["id"], 2)]

    # второго не зачислить, пока не решён первый
    r = await client.post(f"/api/admin/deposits/{waiting['request']['id']}", headers=admin_headers, json={"action": "approve"})
    assert r.status == 400 and (await r.json())["error"] == "not_your_turn"

    before = (await (await client.get("/api/me", headers=auth_headers)).json())["balance"]
    r = await client.post(f"/api/admin/deposits/{first['request']['id']}", headers=admin_headers, json={"action": "approve"})
    assert (await r.json())["credited"] == 3077
    assert (await (await client.get("/api/me", headers=auth_headers)).json())["balance"] == before + 3077
    # следующий в работе, игрок получил сообщение
    mine = await (await client.get("/api/deposit/requests", headers=second)).json()
    assert mine[0]["status"] == "pending" and mine[0]["queue_position"] == 1
    sent = client.server.app["bot"].sent
    assert any(chat == 999111 and "Начислено 3077 B" in t for chat, t in sent)
    assert any(chat == 555777 and "Твоя очередь настала" in t for chat, t in sent)
    assert any(chat == 555777 and "2-й в очереди" in t for chat, t in sent)
    assert any(chat == 999111 and "1-й в очереди" in t for chat, t in sent)

    r = await client.post(f"/api/admin/deposits/{waiting['request']['id']}", headers=admin_headers, json={"action": "reject"})
    assert (await r.json())["status"] == "rejected"
    r = await client.post(f"/api/admin/deposits/{first['request']['id']}", headers=admin_headers, json={"action": "approve"})
    assert r.status == 400  # уже решена
    assert await (await client.get("/api/admin/deposits", headers=admin_headers)).json() == []


async def test_stars_rate_and_code_bonus(client, auth_headers, admin_headers) -> None:
    r = await client.post("/api/deposit/stars/quote", headers=auth_headers, json={"amount": 100})
    assert (await r.json())["credited"] == 175  # 1 ⭐ = 1.75 B
    r = await client.post("/api/deposit/stars/quote", headers=auth_headers, json={"amount": 100, "code": "NOPE"})
    assert r.status == 400 and (await r.json())["error"] == "bad_code"
    # любой код даёт бонус +10%: промокод…
    await client.post("/api/admin/promos", headers=admin_headers, json={"kind": "balance", "amount": 1, "code": "stars10"})
    r = await client.post("/api/deposit/stars/quote", headers=auth_headers, json={"amount": 100, "code": "stars10"})
    assert (await r.json())["credited"] == 192
    # …и реферальный код другого игрока (свой — нет)
    other = await (await client.get("/api/me", headers={"Authorization": "tma " + _init_data(313131)})).json()
    r = await client.post("/api/deposit/stars/quote", headers=auth_headers, json={"amount": 100, "code": other["referral_code"]})
    assert (await r.json())["bonus_percent"] == 10
    me = await (await client.get("/api/me", headers=auth_headers)).json()
    r = await client.post("/api/deposit/stars/quote", headers=auth_headers, json={"amount": 100, "code": me["referral_code"]})
    assert r.status == 400
    r = await client.post("/api/deposit/stars", headers=auth_headers, json={"amount": 100, "code": "stars10"})
    assert (await r.json())["credited"] == 192
    assert "192 B" in client.server.app["bot"].last_invoice["description"]


async def test_withdraw_exchange_flow(client, auth_headers, admin_headers, in_memory_db) -> None:
    from bot.database.models import User
    from bot.database.repo import inventory as inventory_repo
    from sqlalchemy import select

    async with in_memory_db() as session:
        user = (await session.execute(select(User).where(User.tg_id == 999111))).scalar_one()
        await inventory_repo.add_items(session, user, "test", [("Dragon Cannelloni", 973)])
    inv = await (await client.get("/api/inventory", headers=auth_headers)).json()
    dragon = next(i for i in inv if i["name"] == "Dragon Cannelloni")

    # стока нет — вариантов нет
    assert (await (await client.get(f"/api/withdraw/options/{dragon['id']}", headers=auth_headers)).json())["options"] == []
    assert (await client.post("/api/admin/stock", headers=auth_headers, json={"name": "Garama and Madundung", "delta": 1})).status == 403
    r = await client.post("/api/admin/stock", headers=admin_headers, json={"name": "Garama and Madundung", "delta": 30})
    assert (await r.json())["count"] == 30
    stock = await (await client.get("/api/withdraw/stock", headers=auth_headers)).json()
    assert stock[0]["name"] == "Garama and Madundung" and stock[0]["count"] == 30

    opts = (await (await client.get(f"/api/withdraw/options/{dragon['id']}", headers=auth_headers)).json())["options"]
    opt = opts[0]
    assert opt["items"][0]["qty"] == 23 and opt["topup_b"] == 30
    r = await client.post("/api/withdraw", headers=auth_headers, json={"item_id": dragon["id"], "option_key": opt["key"], "nickname": "dimon"})
    req = await r.json()
    assert r.status == 200 and req["status"] == "pending"
    # брейнрот ушёл из инвентаря, сток зарезервирован
    assert all(i["id"] != dragon["id"] for i in await (await client.get("/api/inventory", headers=auth_headers)).json())
    assert (await (await client.get("/api/withdraw/stock", headers=auth_headers)).json())[0]["count"] == 7

    before = (await (await client.get("/api/me", headers=auth_headers)).json())["balance"]
    queue = await (await client.get("/api/admin/withdrawals", headers=admin_headers)).json()
    assert queue[0]["id"] == req["id"]
    r = await client.post(f"/api/admin/withdrawals/{req['id']}", headers=admin_headers, json={"action": "done"})
    assert (await r.json())["status"] == "done"
    assert (await (await client.get("/api/me", headers=auth_headers)).json())["balance"] == before + 30
    assert any("Вывод" in t and "выдан" in t for _, t in client.server.app["bot"].sent)


async def test_withdraw_cancel_returns_item_and_stock(client, auth_headers, admin_headers, in_memory_db) -> None:
    from bot.database.models import User
    from bot.database.repo import inventory as inventory_repo
    from sqlalchemy import select

    async with in_memory_db() as session:
        user = (await session.execute(select(User).where(User.tg_id == 999111))).scalar_one()
        await inventory_repo.add_items(session, user, "test", [("Kraken", 3077)])
    await client.post("/api/admin/stock", headers=admin_headers, json={"name": "Kraken", "delta": 1})
    kraken = next(i for i in await (await client.get("/api/inventory", headers=auth_headers)).json() if i["name"] == "Kraken")
    opts = (await (await client.get(f"/api/withdraw/options/{kraken['id']}", headers=auth_headers)).json())["options"]
    assert opts[0]["direct"] and opts[0]["topup_b"] == 0
    req = await (await client.post("/api/withdraw", headers=auth_headers,
                                   json={"item_id": kraken["id"], "option_key": opts[0]["key"], "nickname": "dimon"})).json()
    r = await client.post(f"/api/admin/withdrawals/{req['id']}", headers=admin_headers, json={"action": "cancel"})
    assert (await r.json())["status"] == "cancelled"
    assert any(i["name"] == "Kraken" for i in await (await client.get("/api/inventory", headers=auth_headers)).json())
    assert (await (await client.get("/api/withdraw/stock", headers=auth_headers)).json())[0]["count"] == 1


async def test_approved_brainrot_deposit_fills_stock(client, auth_headers, admin_headers) -> None:
    catalog = await (await client.get("/api/deposit/catalog", headers=auth_headers)).json()
    garama = next(i for i in catalog["brainrot"] if i["name"] == "Garama and Madundung")
    r = await client.post("/api/deposit/request", headers=auth_headers,
                          json={"category": "brainrot", "items": {garama["id"]: 4}, "nickname": "dimon"})
    req = await r.json()
    assert r.status == 200, req
    await client.post(f"/api/admin/deposits/{req['request']['id']}", headers=admin_headers, json={"action": "approve"})
    stock = await (await client.get("/api/withdraw/stock", headers=auth_headers)).json()
    assert {"name": "Garama and Madundung", "count": 4}.items() <= stock[0].items()


async def test_upgrader_stake_up_to_five(client, auth_headers, in_memory_db) -> None:
    from bot.database.models import User
    from bot.database.repo import inventory as inventory_repo
    from sqlalchemy import select

    async with in_memory_db() as session:
        user = (await session.execute(select(User).where(User.tg_id == 999111))).scalar_one()
        await inventory_repo.add_items(session, user, "test", [("Garama and Madundung", 41)] * 6)
    ids = [i["id"] for i in await (await client.get("/api/inventory", headers=auth_headers)).json()]
    r = await client.post("/api/upgrader/spin", headers=auth_headers, json={"contribution_item_ids": ids[:6], "target_name": "Kraken"})
    assert r.status == 400 and (await r.json())["error"] == "too_many_items"
    targets = await (await client.get("/api/upgrader/targets?min_value=205", headers=auth_headers)).json()
    target = targets[0]["name"]
    r = await client.post("/api/upgrader/spin", headers=auth_headers, json={"contribution_item_ids": ids[:5], "target_name": target})
    body = await r.json()
    assert r.status == 200 and body["stake_value"] == 205 and len(body["contributions"]) == 5
    left = await (await client.get("/api/inventory", headers=auth_headers)).json()
    assert len([i for i in left if i["id"] in ids[:5]]) == 0


async def test_admin_luck_set_and_cancel(client, auth_headers, admin_headers) -> None:
    await client.get("/api/me", headers=auth_headers)
    assert (await client.post("/api/admin/luck", headers=auth_headers, json={"user": "999111", "luck": 5})).status == 403
    r = await client.post("/api/admin/luck", headers=admin_headers, json={"user": "999111", "luck": 5})
    assert (await r.json())["luck"] == 5
    r = await client.post("/api/admin/luck", headers=admin_headers, json={"user": "999111", "luck": 100})
    assert r.status == 400
    r = await client.post("/api/admin/luck", headers=admin_headers, json={"user": "999111", "luck": None})
    assert (await r.json())["luck"] is None


async def test_admin_take_and_zero_balance(client, auth_headers, admin_headers) -> None:
    await client.get("/api/me", headers=auth_headers)
    await client.post("/api/admin/grant", headers=admin_headers, json={"user": "999111", "kind": "balance", "amount": 500})
    assert (await client.post("/api/admin/balance", headers=auth_headers, json={"user": "999111", "mode": "zero"})).status == 403
    r = await client.post("/api/admin/balance", headers=admin_headers, json={"user": "999111", "amount": 200})
    left = (await r.json())["balance"]
    r = await client.post("/api/admin/balance", headers=admin_headers, json={"user": "999111", "amount": -5})
    assert r.status == 400
    r = await client.post("/api/admin/balance", headers=admin_headers, json={"user": "999111", "mode": "zero"})
    assert left >= 300 and (await r.json())["balance"] == 0


async def test_stars_no_upper_limit(client, auth_headers) -> None:
    r = await client.post("/api/deposit/stars/quote", headers=auth_headers, json={"amount": 5_000_000})
    assert r.status == 200 and (await r.json())["credited"] == 8_750_000


async def test_deposit_request_with_code_bonus(client, auth_headers, admin_headers) -> None:
    catalog = await (await client.get("/api/deposit/catalog", headers=auth_headers)).json()
    kraken = next(i for i in catalog["brainrot"] if i["name"] == "Kraken")
    assert (await client.get("/api/deposit/code?code=NOPE", headers=auth_headers)).status == 400
    await client.post("/api/admin/promos", headers=admin_headers, json={"kind": "balance", "amount": 1, "code": "dep10"})
    assert (await (await client.get("/api/deposit/code?code=dep10", headers=auth_headers)).json())["bonus_percent"] == 10

    r = await client.post("/api/deposit/request", headers=auth_headers,
                          json={"category": "brainrot", "items": {kraken["id"]: 1}, "nickname": "dimon", "code": "NOPE"})
    assert r.status == 400 and (await r.json())["error"] == "bad_code"
    r = await client.post("/api/deposit/request", headers=auth_headers,
                          json={"category": "brainrot", "items": {kraken["id"]: 1}, "nickname": "dimon", "code": "dep10"})
    req = (await r.json())["request"]
    assert req["promo_code"] == "DEP10" and req["bonus_b"] == 307

    before = (await (await client.get("/api/me", headers=auth_headers)).json())["balance"]
    r = await client.post(f"/api/admin/deposits/{req['id']}", headers=admin_headers, json={"action": "approve"})
    assert (await r.json())["credited"] == 3077 + 307
    assert (await (await client.get("/api/me", headers=auth_headers)).json())["balance"] == before + 3384


async def test_withdraw_queue_cancel_and_exchange(client, auth_headers, admin_headers, in_memory_db) -> None:
    from bot.database.models import User
    from bot.database.repo import inventory as inventory_repo
    from sqlalchemy import select

    second = {"Authorization": "tma " + _init_data(565656, username="two")}
    await client.get("/api/me", headers=second)
    async with in_memory_db() as session:
        for tg in (999111, 565656):
            u = (await session.execute(select(User).where(User.tg_id == tg))).scalar_one()
            await inventory_repo.add_items(session, u, "test", [("Kraken", 3077)])
    await client.post("/api/admin/stock", headers=admin_headers, json={"name": "Kraken", "delta": 2})
    await client.post("/api/admin/stock", headers=admin_headers, json={"name": "Garama and Madundung", "delta": 50})

    k1 = next(i for i in await (await client.get("/api/inventory", headers=auth_headers)).json() if i["name"] == "Kraken")
    # обмен вместо прямого вывода, даже если Kraken в стоке
    ex = (await (await client.get(f"/api/withdraw/options/{k1['id']}?exchange=1", headers=auth_headers)).json())["options"]
    assert ex and all(b["name"] != "Kraken" for o in ex for b in o["items"])
    direct = (await (await client.get(f"/api/withdraw/options/{k1['id']}", headers=auth_headers)).json())["options"][0]
    first = await (await client.post("/api/withdraw", headers=auth_headers,
                                     json={"item_id": k1["id"], "option_key": direct["key"], "nickname": "dimon"})).json()
    assert first["queue_position"] == 1

    k2 = next(i for i in await (await client.get("/api/inventory", headers=second)).json() if i["name"] == "Kraken")
    opt2 = (await (await client.get(f"/api/withdraw/options/{k2['id']}", headers=second)).json())["options"][0]
    wait = await (await client.post("/api/withdraw", headers=second,
                                    json={"item_id": k2["id"], "option_key": opt2["key"], "nickname": "two_sab"})).json()
    assert wait["queue_position"] == 2 and wait["status"] == "queued"

    # второго нельзя выдать раньше первого; первый отменяет сам — второй в работе
    r = await client.post(f"/api/admin/withdrawals/{wait['id']}", headers=admin_headers, json={"action": "done"})
    assert (await r.json())["error"] == "not_your_turn"
    assert (await client.post(f"/api/withdraw/{first['id']}/cancel", headers=second)).status == 400  # чужую нельзя
    r = await client.post(f"/api/withdraw/{first['id']}/cancel", headers=auth_headers)
    assert (await r.json())["status"] == "cancelled"
    assert any(i["name"] == "Kraken" for i in await (await client.get("/api/inventory", headers=auth_headers)).json())
    mine = await (await client.get("/api/withdraw/requests", headers=second)).json()
    assert mine[0]["status"] == "pending" and mine[0]["queue_position"] == 1
    sent = client.server.app["bot"].sent
    assert any(chat == 565656 and "Твоя очередь настала" in t for chat, t in sent)


async def test_player_cancels_deposit_request(client, auth_headers) -> None:
    catalog = await (await client.get("/api/deposit/catalog", headers=auth_headers)).json()
    kraken = next(i for i in catalog["brainrot"] if i["name"] == "Kraken")
    req = (await (await client.post("/api/deposit/request", headers=auth_headers,
                                    json={"category": "brainrot", "items": {kraken["id"]: 1}, "nickname": "dimon"})).json())["request"]
    r = await client.post(f"/api/deposit/requests/{req['id']}/cancel", headers=auth_headers)
    assert (await r.json())["status"] == "cancelled"
    assert (await client.post(f"/api/deposit/requests/{req['id']}/cancel", headers=auth_headers)).status == 400
