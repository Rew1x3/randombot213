from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from database.repositories import GiveawayRepository
from database.session import SessionLocal
from utils.time import to_human_datetime_utc


async def active_giveaways_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user is None:
        return

    async with SessionLocal() as session:
        repo = GiveawayRepository(session)
        giveaways = await repo.get_active_giveaways(limit=50)

    if not giveaways:
        await update.effective_message.reply_text("Нет активных розыгрышей.")
        return

    bot_username = context.application.bot_data.get("bot_username")
    lines: list[str] = ["Активные розыгрыши:"]

    for g in giveaways:
        if bot_username:
            join_link = f"https://t.me/{bot_username}?start=join_{g.id}"
        else:
            join_link = f"/start join_{g.id}"

        lines.append(f"\n#{g.id} — {g.title}")
        lines.append(f"Окончание: {to_human_datetime_utc(g.end_time)}")
        lines.append(f"Победителей: {g.winners_count}")
        lines.append(f"Участвовать: {join_link}")

    await update.effective_message.reply_text("\n".join(lines), disable_web_page_preview=True)

