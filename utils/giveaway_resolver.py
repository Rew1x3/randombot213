from __future__ import annotations

import logging
import random
from datetime import datetime, timezone
from typing import List, Sequence, Tuple

from telegram.ext import ContextTypes

from database.repositories import GiveawayRepository
from database.session import SessionLocal
from utils.prizes import parse_prizes
from utils.telegram_utils import safe_user_mention

logger = logging.getLogger(__name__)


async def resolve_and_publish(
    application,
    giveaway_id: int,
    *,
    special_first_telegram_id: int | None = None,
) -> None:
    """
    Завершает розыгрыш (если он ещё активен) и публикует результаты в заданном чате.
    special_first_telegram_id:
      - если задан, этот пользователь становится победителем на 1-е место,
        а остальные места выбираются случайно из оставшихся участников.
    """
    bot = application.bot

    # 1) Вычисляем победителей и фиксируем в БД (в отдельной сессии)
    giveaway = None
    winners_ids: List[int] = []
    assigned_prizes: List[str | None] = []
    actual_count: int = 0
    participants_count_initial: int = 0

    async with SessionLocal() as session:
        repo = GiveawayRepository(session)
        giveaway = await repo.get_giveaway(giveaway_id)
        if giveaway is None:
            return

        if giveaway.status != "active":
            return

        participants = await repo.list_participant_ids(giveaway_id)
        participants_count_initial = len(participants)

        if not participants:
            await repo.end_giveaway_and_store_winners(giveaway, winners=[])
        else:
            actual_count = min(int(giveaway.winners_count), len(participants))

            if special_first_telegram_id is not None:
                if special_first_telegram_id not in participants:
                    # Команду не выполняем и розыгрыш не завершаем.
                    await bot.send_message(
                        chat_id=giveaway.publish_chat_id,
                        text=f"Не удалось назначить первого победителя: пользователь {special_first_telegram_id} не участвует в розыгрыше #{giveaway.id}.",
                    )
                    return

                remaining = [pid for pid in participants if pid != special_first_telegram_id]

                if actual_count == 1:
                    winners_ids = [special_first_telegram_id]
                else:
                    k = actual_count - 1
                    if k > len(remaining):
                        await bot.send_message(
                            chat_id=giveaway.publish_chat_id,
                            text=f"Недостаточно участников для выборки {actual_count} победителей в розыгрыше #{giveaway.id}.",
                        )
                        return
                    selected = random.sample(remaining, k=k)
                    winners_ids = [special_first_telegram_id] + selected
            else:
                winners_ids = random.sample(participants, k=actual_count)

            prizes = parse_prizes(giveaway.prizes_text)

            def prize_for_position(pos: int) -> str | None:
                if not prizes:
                    return None
                if len(prizes) == 1:
                    return prizes[0]
                idx = pos - 1
                if idx < len(prizes):
                    return prizes[idx]
                return prizes[-1]

            for idx, pid in enumerate(winners_ids, start=1):
                assigned_prizes.append(prize_for_position(idx))

            winners: Sequence[Tuple[int, str | None]] = list(zip(winners_ids, assigned_prizes))
            await repo.end_giveaway_and_store_winners(giveaway, winners=winners)

    # 2) Публикуем результат (после фиксации в БД)
    if giveaway is None:
        return

    if participants_count_initial == 0:
        text = f"Розыгрыш #{giveaway.id} завершён. Участников нет, победители не выбраны."
        await bot.send_message(chat_id=giveaway.publish_chat_id, text=text)
        return

    # Формируем сообщение с упоминаниями
    prizes = parse_prizes(giveaway.prizes_text)

    def prize_for_position(pos: int) -> str | None:
        if not prizes:
            return None
        if len(prizes) == 1:
            return prizes[0]
        idx = pos - 1
        if idx < len(prizes):
            return prizes[idx]
        return prizes[-1]

    lines = [f"🎉 <b>Результаты розыгрыша #{giveaway.id}</b>", "", f"<b>{giveaway.title}</b>", ""]
    lines.append(f"Победителей выбрано: <b>{actual_count}</b>")
    lines.append("")
    lines.append("Победители:")

    for pos, telegram_id in enumerate(winners_ids, start=1):
        mention = await safe_user_mention(bot, telegram_id)
        prize_text = prize_for_position(pos)
        if prize_text:
            lines.append(f"{pos}) {mention} — {prize_text}")
        else:
            lines.append(f"{pos}) {mention}")

    if giveaway.conditions_text:
        lines.append("")
        lines.append(f"Условия: {giveaway.conditions_text}")

    text = "\n".join(lines)
    await bot.send_message(chat_id=giveaway.publish_chat_id, text=text, parse_mode="HTML", disable_web_page_preview=True)


async def auto_resolve_due_giveaways_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    application = context.application
    now = datetime.now(timezone.utc)
    async with SessionLocal() as session:
        repo = GiveawayRepository(session)
        due_ids = await repo.get_due_giveaways(now)

    for giveaway_id in due_ids:
        try:
            await resolve_and_publish(application, giveaway_id)
        except Exception:
            logger.exception("Failed to resolve giveaway_id=%s", giveaway_id)

