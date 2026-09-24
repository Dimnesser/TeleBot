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
    async def get_me(self):
        class Me:
            username = "BrainCorre_bot"

        return Me()


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
    from bot.database.engine import _seed_cases_reconcile, _seed_quests_if_empty

    await _seed_cases_reconcile()
    await _seed_quests_if_empty()

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
    assert body["game_tokens"] == config.demo_starting_tokens


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
    tokens_before = (await r.json())["game_tokens"]

    r = await client.get("/api/inventory", headers=auth_headers)
    item = (await r.json())[0]

    r = await client.post(f"/api/inventory/{item['id']}/sell", headers=auth_headers)
    assert r.status == 200
    body = await r.json()
    assert body["sold_name"] == won["name"]
    assert body["payout"] == round(won["value"] * 0.9)
    assert body["game_tokens"] == tokens_before + body["payout"]

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
        if (await r.json())["game_tokens"] < case["price_tokens"]:
            await client.post("/api/demo-topup", headers=auth_headers)
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


async def test_case_detail_drop_chances_sum_to_100(client, auth_headers) -> None:
    r = await client.get("/api/cases?category=starter", headers=auth_headers)
    for case in (await r.json())["cases"]:
        if not case["is_openable"]:
            continue
        r = await client.get(f"/api/cases/{case['id']}", headers=auth_headers)
        detail = await r.json()
        total = sum(i["chance_percent"] for i in detail["items"])
        assert 99.0 <= total <= 101.0, f"{case['name']}: chances sum to {total}"


async def test_case_open_rejects_insufficient_tokens(client, auth_headers) -> None:
    r = await client.get("/api/cases?category=starter", headers=auth_headers)
    cases = (await r.json())["cases"]
    openable = [c for c in cases if c["is_openable"] and c["price_tokens"]]
    assert openable, "seed data must contain at least one openable priced case"
    expensive = max(openable, key=lambda c: c["price_tokens"])

    # спамим открытия, пока не кончатся токены
    for _ in range(50):
        r = await client.post(f"/api/cases/{expensive['id']}/open", headers=auth_headers, json={"qty": 1})
        if r.status != 200:
            break

    assert r.status == 400
    body = await r.json()
    assert body["error"] == "not_enough_tokens"


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
    assert state["active"] or state["crashed"]

    if state["active"]:
        r = await client.post("/api/crash/cashout", headers=auth_headers)
        assert r.status == 200

    r = await client.get("/api/crash/state", headers=auth_headers)
    assert (await r.json())["active"] is False


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
    assert staking["balance"] == 500
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
    assert [c["key"] for c in collections] == ["starter", "signature", "apex"]
    for collection in collections:
        for case in collection["cases"]:
            assert case["theme"]["shape"]
            assert case["top_item_image_url"].endswith(".webp")


async def test_unknown_category_is_400(client, auth_headers) -> None:
    r = await client.get("/api/cases?category=nope", headers=auth_headers)
    assert r.status == 400


async def test_multi_open_returns_reel_per_win_and_real_game_info(client, auth_headers) -> None:
    r = await client.get("/api/cases?category=starter", headers=auth_headers)
    case = min((await r.json())["cases"], key=lambda c: c["price_tokens"])
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
