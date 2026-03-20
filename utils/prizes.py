from __future__ import annotations

import re
from typing import List


def parse_prizes(prizes_text: str) -> List[str]:
    """
    Разбивает ввод администратора на список призов.
    Поддержка разделителей: запятые и переносы строк.
    """
    raw = prizes_text.strip()
    if not raw:
        return []
    # Разделяем по запятым/переводам строк
    parts = re.split(r"[,\n\r]+", raw)
    prizes = [p.strip() for p in parts if p.strip()]
    # Убираем дубликаты при сохранении порядка
    seen = set()
    out: List[str] = []
    for p in prizes:
        if p not in seen:
            seen.add(p)
            out.append(p)
    return out

