"""Брейнроты для кейсов: только реальные персонажи Steal a Brainrot и только
те, что пользователь прислал на скриншотах (раздел «Депозит брейнротом»).

Никого не выдумываем:
  * список имён и ценность `value` (в B, она же ценность в 🎫 демо-режима) —
    буквально со скриншотов пользователя;
  * тир (Secret / OG), цена покупки `cost` и доход `income` в игре — из
    инфобокса статьи Steal a Brainrot Wiki (stealabrainrot.fandom.com),
    снято через MediaWiki API `WIKI_SNAPSHOT_DATE`;
  * изображение — официальный внутриигровой рендер из той же статьи,
    webapp/static/assets/brainrots/<slug>.webp.

На скриншоте было «Signora Carapace» — на вики персонаж называется
Signore Carapace, используется написание вики.

В кейсах — только Secret и OG (как на референсе пользователя: даже самые
дешёвые кейсы там из Secret). Brainrot God не используется.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from enum import Enum

WIKI_SNAPSHOT_DATE = "24.09.2026"
WIKI_BASE_URL = "https://stealabrainrot.fandom.com/wiki/"


class Rarity(str, Enum):
    """Тиры ровно как в игре. В кейсах используются только SECRET и OG,
    остальные нужны, чтобы старые записи инвентаря продолжали читаться."""

    COMMON = "common"
    RARE = "rare"
    EPIC = "epic"
    LEGENDARY = "legendary"
    MYTHIC = "mythic"
    BRAINROT_GOD = "brainrot_god"
    SECRET = "secret"
    OG = "og"


RARITY_ORDER: list[Rarity] = list(Rarity)

# Названия тиров — как в самой игре, не переводятся.
RARITY_LABEL: dict[Rarity, str] = {
    Rarity.COMMON: "Common",
    Rarity.RARE: "Rare",
    Rarity.EPIC: "Epic",
    Rarity.LEGENDARY: "Legendary",
    Rarity.MYTHIC: "Mythic",
    Rarity.BRAINROT_GOD: "Brainrot God",
    Rarity.SECRET: "Secret",
    Rarity.OG: "OG",
}
RARITY_LABEL_RU = RARITY_LABEL  # старое имя, на него ссылается бот

# Основной + акцентный цвет тира; дублируется в webapp/static/css/app.css (--r-*).
RARITY_COLOR: dict[Rarity, tuple[str, str]] = {
    Rarity.COMMON: ("#a3adc2", "#5d667a"),
    Rarity.RARE: ("#3fa7ff", "#1c5fae"),
    Rarity.EPIC: ("#a66bff", "#5b2bb5"),
    Rarity.LEGENDARY: ("#ffb534", "#c46a12"),
    Rarity.MYTHIC: ("#ff4d6d", "#a3123a"),
    Rarity.BRAINROT_GOD: ("#33f0d0", "#1a6cff"),
    Rarity.SECRET: ("#f2f2f7", "#8a8aa0"),
    Rarity.OG: ("#ffd84d", "#ff4fd8"),
}


def slugify(name: str) -> str:
    """Имя -> имя файла ассета: "Dug dug dug" -> "dug-dug-dug"."""
    ascii_name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", ascii_name.lower()).strip("-")


@dataclass(frozen=True)
class RosterBrainrot:
    name: str
    rarity: Rarity
    value: int  # ценность со скриншота пользователя (B = 🎫)
    cost: str  # цена покупки в игре, как на вики ("250B")
    income: str  # доход в секунду в игре, как на вики ("250M")

    @property
    def slug(self) -> str:
        return slugify(self.name)

    @property
    def wiki_url(self) -> str:
        return WIKI_BASE_URL + self.name.replace(" ", "_")


S, OG = Rarity.SECRET, Rarity.OG

ROSTER: list[RosterBrainrot] = [
    RosterBrainrot("Garama and Madundung", S, 41, "10B", "50M"),
    RosterBrainrot("Cash or Card", S, 43, "40B", "100M"),
    RosterBrainrot("Burguro And Fryuro", S, 73, "75B", "150M"),
    RosterBrainrot("Pizza and Ranch", S, 80, "55B", "130M"),
    RosterBrainrot("Popcuru and Fizzuru", S, 87, "135B", "170M"),
    RosterBrainrot("Capitano Moby", S, 91, "125B", "160M"),
    RosterBrainrot("Celestial Pegasus", S, 93, "150B", "175M"),
    RosterBrainrot("La Food Combinasion", S, 103, "30B", "90M"),
    RosterBrainrot("Fragrama and Chocrama", S, 121, "40B", "100M"),
    RosterBrainrot("Cooki and Milki", S, 130, "100B", "155M"),
    RosterBrainrot("Sammyni Fattini", S, 140, "20B", "70M"),
    RosterBrainrot("Spooky and Pumpky", S, 145, "25B", "80M"),
    RosterBrainrot("Cerberus", S, 155, "150B", "175M"),
    RosterBrainrot("Globa Steppa", S, 164, "3B", "27.5M"),
    RosterBrainrot("Reinito Sleighito", S, 176, "60B", "140M"),
    RosterBrainrot("Los Amigos", S, 220, "55B", "130M"),
    RosterBrainrot("Fortunu and Cashuru", S, 230, "55B", "130M"),
    RosterBrainrot("Quackini Snackini", S, 258, "15.5B", "65M"),
    RosterBrainrot("La Breakfast Combinasion", S, 293, "130B", "165M"),
    RosterBrainrot("Duggy Bros", S, 323, "30B", "90M"),
    RosterBrainrot("Los Sekolahs", S, 325, "45B", "110M"),
    RosterBrainrot("Los Secret Combinasionas", S, 419, "75B", "150M"),
    RosterBrainrot("Dug dug dug", S, 425, "5B", "35M"),
    RosterBrainrot("Foxini Lanternini", S, 445, "47.5B", "115M"),
    RosterBrainrot("Rico Dinero", S, 460, "7.5B", "42.5M"),
    RosterBrainrot("Venuspino", S, 487, "150B", "175M"),
    RosterBrainrot("Ketupat Bros", S, 488, "65B", "145M"),
    RosterBrainrot("Rosey and Teddy", S, 525, "130B", "165M"),
    RosterBrainrot("Bumbatron", S, 603, "140B", "172.5M"),
    RosterBrainrot("La Casa Boo", S, 621, "40B", "100M"),
    RosterBrainrot("Bunny and Eggy", S, 862, "135B", "170M"),
    RosterBrainrot("Dragon Cannelloni", S, 973, "250B", "250M"),
    RosterBrainrot("Pancake and Syrup", S, 1109, "50B", "125M"),
    RosterBrainrot("Jelly Moby", S, 1153, "150B", "175M"),
    RosterBrainrot("Hydra Dragon Cannelloni", S, 1220, "300B", "300M"),
    RosterBrainrot("Sammyni Cakini", S, 1244, "12.5B", "85M"),
    RosterBrainrot("Moby Bros", S, 1604, "225B", "225M"),
    RosterBrainrot("Tirilikalika Tirilikalako", S, 1660, "7.5B", "42.5M"),
    RosterBrainrot("Hydra Bunny", S, 1722, "175B", "185M"),
    RosterBrainrot("Ginger Gerat", S, 1965, "22.5B", "75M"),
    RosterBrainrot("Digi Narwhal", S, 2139, "200B", "200M"),
    RosterBrainrot("La Supreme Combinasion", S, 2704, "200B", "200M"),
    RosterBrainrot("Fishino Clownino", S, 2803, "48.5B", "120M"),
    RosterBrainrot("Kraken", S, 3077, "200B", "200M"),
    RosterBrainrot("Kalika Bros", S, 3470, "47.5B", "115M"),
    RosterBrainrot("Dragon Aquanini", S, 3701, "375B", "375M"),
    RosterBrainrot("Dragon Gingerini", S, 4915, "350B", "350M"),
    RosterBrainrot("Antonio", S, 5549, "50B", "125M"),
    RosterBrainrot("Griffin", S, 6307, "400B", "400M"),
    RosterBrainrot("Love Love Bear", S, 6737, "225B", "225M"),
    RosterBrainrot("Arcadragon", S, 10860, "215B", "215M"),
    RosterBrainrot("Elefanto Frigo", S, 11809, "175B", "185M"),
    RosterBrainrot("Skibidi Toilet", OG, 13154, "450B", "450M"),
    RosterBrainrot("John Pork", OG, 14530, "500B", "500M"),
    RosterBrainrot("Meowl", OG, 16839, "650B", "600M"),
    RosterBrainrot("Signore Carapace", S, 33024, "275B", "275M"),
    RosterBrainrot("Strawberry Elephant", OG, 42509, "750B", "750M"),
]

# Дешёвые Secret — как в дешёвых кейсах на референсе пользователя: имена и
# ценность `value` в B — буквально с его скриншота раздела «Что может
# выпасть» (там же видно, что даже самые дешёвые кейсы состоят из Secret).
# Тир, цена и доход в игре — из вики, как и у остальных.
CHEAP_SECRETS: list[RosterBrainrot] = [
    RosterBrainrot("67", S, 5, "1.25B", "7.5M"),
    RosterBrainrot("La Grande Combinasion", S, 9, "1B", "10M"),
    RosterBrainrot("Money Money Puggy", S, 14, "2.6B", "21M"),
    RosterBrainrot("Nuclearo Dinossauro", S, 15, "2.5B", "15M"),
    RosterBrainrot("Tang Tang Keletang", S, 25, "4.5B", "33.5M"),
    RosterBrainrot("Orcaledon", S, 28, "7B", "40M"),
    RosterBrainrot("Lavadorito Spinito", S, 31, "8B", "45M"),
    RosterBrainrot("Ventoliero Pavonero", S, 41, "15.5B", "65M"),
    RosterBrainrot("Ketchuru and Musturu", S, 51, "7.5B", "42.5M"),
    RosterBrainrot("Noodle Noodle Poodle", S, 54, "3B", "27.5M"),
]
ROSTER = ROSTER + CHEAP_SECRETS

ROSTER_BY_NAME: dict[str, RosterBrainrot] = {b.name: b for b in ROSTER}


def rarity_for(name: str, value: int) -> Rarity:
    """Реальный тир персонажа. Для имён вне ростера (старые записи
    инвентаря) тир не угадываем — считаем Secret, минимальный тир кейсов."""
    entry = ROSTER_BY_NAME.get(name)
    return entry.rarity if entry else Rarity.SECRET

