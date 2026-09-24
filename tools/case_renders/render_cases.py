"""Пересобирает 3D-модели кейсов: webapp/static/assets/cases/<code>.webp.

    cd tools/case_renders && npm install
    CHROMIUM_PATH=/path/to/chrome python render_cases.py [code ...]

Берёт каталог из bot.data.seed_cases (тема кейса + два самых дорогих
брейнрота — «герои», которые сидят внутри модели), рендерит через
drive.js / render.html и сохраняет webp. Запускать после изменения
состава или темы кейса.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))

from PIL import Image  # noqa: E402

from bot.data.brainrot_roster import slugify  # noqa: E402
from bot.data.coins import COIN_RARITY  # noqa: E402
from bot.data.seed_cases import CASE_THEMES, SEED_CASES  # noqa: E402

OUT = ROOT / "webapp" / "static" / "assets" / "cases"


def specs(only: set[str]) -> list[dict]:
    result = []
    for case in SEED_CASES:
        if only and case.code not in only:
            continue
        theme = CASE_THEMES[case.code]
        heroes = [i.name for i in case.items if i.rarity != COIN_RARITY][:2]
        result.append({
            "code": case.code,
            "heroes": [f"/brainrots/{slugify(n)}.webp" for n in heroes],
            "theme": {"filling": theme.filling, "aura": theme.aura, "shell": list(theme.shell), "accent": theme.accent},
        })
    return result


def main() -> None:
    only = set(sys.argv[1:])
    with tempfile.TemporaryDirectory() as tmp:
        spec_file = Path(tmp) / "specs.json"
        spec_file.write_text(json.dumps(specs(only)))
        subprocess.run(["node", str(HERE / "drive.js"), str(spec_file), tmp], check=True)
        OUT.mkdir(parents=True, exist_ok=True)
        for png in Path(tmp).glob("*.png"):
            Image.open(png).convert("RGB").save(OUT / f"{png.stem}.webp", "WEBP", quality=86, method=6)
            print("saved", OUT / f"{png.stem}.webp")


if __name__ == "__main__":
    main()
