from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes, filters

from config import settings


def _is_admin(user_id: int | None) -> bool:
    if user_id is None:
        return False
    return user_id in set(settings.admin_ids)


async def end_giveaway_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user is None:
        return
    if not _is_admin(update.effective_user.id):
        await update.effective_message.reply_text("Недостаточно прав.")
        return

    if not context.args:
        await update.effective_message.reply_text("Использование: /end_giveaway <ID_розыгрыша>")
        return

    try:
        giveaway_id = int(context.args[0])
    except ValueError:
        await update.effective_message.reply_text("Некорректный ID розыгрыша.")
        return

    from utils.giveaway_resolver import resolve_and_publish

    await resolve_and_publish(context.application, giveaway_id)


async def select_winner_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Скрытая админ-команда:
      /select_winner <ID_розыгрыша> <telegram_id_победителя_1>
    """
    if update.effective_user is None:
        return
    if not _is_admin(update.effective_user.id):
        await update.effective_message.reply_text("Недостаточно прав.")
        return

    if len(context.args) < 2:
        await update.effective_message.reply_text("Использование: /select_winner <ID_розыгрыша> <telegram_id_победителя_1>")
        return

    try:
        giveaway_id = int(context.args[0])
        first_telegram_id = int(context.args[1])
    except ValueError:
        await update.effective_message.reply_text("Некорректные параметры. Проверьте ID.")
        return

    from utils.giveaway_resolver import resolve_and_publish

    await resolve_and_publish(context.application, giveaway_id, special_first_telegram_id=first_telegram_id)

