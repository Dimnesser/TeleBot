"""Рыночный срез Steal a Brainrot для брейнротов ростера.

Данные не придуманы — это снимок двух публичных трейдерских источников
(на дату MARKET_SNAPSHOT_DATE), только для персонажей из ростера:
  * TIER — тир-лист трейдеров tradekitsune.com/stealabrainrot/brainrots-tierlist
    (T0 — топ, T7 — самый низ);
  * DEMAND — спрос из game.guide/steal-a-brainrot-value-list
    (Very High / High / Medium / Low / Very Low).
Кого нет в источнике — того нет и здесь (фронтенд тогда просто не рисует
значок). Цены в кейсах по-прежнему берутся из brainrot_roster, а не отсюда:
ценности трейдеров расходятся между сайтами на 20–40%.
"""
from __future__ import annotations

MARKET_SNAPSHOT_DATE = "24.09.2026"
MARKET_SOURCES = (
    "https://tradekitsune.com/stealabrainrot/brainrots-tierlist",
    "https://game.guide/steal-a-brainrot-value-list",
)

TIER: dict[str, str] = {
    "Strawberry Elephant": "T0",
    "Signore Carapace": "T1",
    "Meowl": "T0",
    "Skibidi Toilet": "T0",
    "Elefanto Frigo": "T1",
    "Love Love Bear": "T0",
    "Griffin": "T0",
    "Antonio": "T2",
    "Dragon Gingerini": "T0",
    "Fishino Clownino": "T2",
    "La Supreme Combinasion": "T0",
    "Ginger Gerat": "T2",
    "Tirilikalika Tirilikalako": "T2",
    "Hydra Dragon Cannelloni": "T0",
    "Dragon Cannelloni": "T0",
    "La Casa Boo": "T1",
    "Rosey and Teddy": "T0",
    "Ketupat Bros": "T1",
    "Dug dug dug": "T3",
    "Los Sekolahs": "T1",
    "Fortunu and Cashuru": "T1",
    "Los Amigos": "T1",
    "Reinito Sleighito": "T1",
    "Cerberus": "T0",
    "Spooky and Pumpky": "T1",
    "Sammyni Fattini": "T2",
    "Cooki and Milki": "T0",
    "Fragrama and Chocrama": "T1",
    "La Food Combinasion": "T1",
    "Celestial Pegasus": "T0",
    "Capitano Moby": "T0",
    "Popcuru and Fizzuru": "T0",
    "Burguro And Fryuro": "T0",
    "Garama and Madundung": "T2",
    "67": "T4",
    "La Grande Combinasion": "T4",
}

DEMAND: dict[str, str] = {
    "Strawberry Elephant": "Very High",
    "Signore Carapace": "Medium",
    "Meowl": "Very Low",
    "Skibidi Toilet": "Very Low",
    "Elefanto Frigo": "Very High",
    "Love Love Bear": "Very Low",
    "Griffin": "Very Low",
    "Antonio": "High",
    "Dragon Gingerini": "High",
    "Kalika Bros": "Very High",
    "Fishino Clownino": "High",
    "Digi Narwhal": "Very Low",
    "Ginger Gerat": "Very Low",
    "Hydra Bunny": "High",
    "Tirilikalika Tirilikalako": "Low",
    "Hydra Dragon Cannelloni": "Very Low",
    "Dragon Cannelloni": "Very High",
    "La Casa Boo": "Very Low",
    "Rosey and Teddy": "Very Low",
    "Ketupat Bros": "Very Low",
    "Foxini Lanternini": "Very Low",
    "Los Sekolahs": "High",
    "Los Amigos": "High",
    "Reinito Sleighito": "High",
    "Cerberus": "Very Low",
    "Spooky and Pumpky": "High",
    "Sammyni Fattini": "High",
    "Cooki and Milki": "Very Low",
    "Fragrama and Chocrama": "High",
    "La Food Combinasion": "High",
    "Celestial Pegasus": "High",
    "Capitano Moby": "High",
    "Popcuru and Fizzuru": "Very Low",
    "Burguro And Fryuro": "Very Low",
    "Garama and Madundung": "High",
}

HOT_DEMAND = ("Very High", "High")
COLD_DEMAND = ("Very Low",)


def market_info(name: str) -> dict | None:
    tier, demand = TIER.get(name), DEMAND.get(name)
    if tier is None and demand is None:
        return None
    return {"tier": tier, "demand": demand}


def names_with_demand(levels: tuple[str, ...]) -> list[str]:
    return [n for n, d in DEMAND.items() if d in levels]


def names_in_tiers(*tiers: str) -> list[str]:
    return [n for n, t in TIER.items() if t in tiers]
