from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import ContextTypes

from config import settings
from database.repositories import GiveawayRepository
from database.session import SessionLocal
from utils.telegram_utils import is_user_subscribed

logger = logging.getLogger(__name__)


async def join_by_giveaway_id(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    giveaway_id: int,
) -> None:
    if update.effective_user is None:
        return

    user_id = update.effective_user.id
    bot = context.bot

    async def _notify_user(text: str) -> None:
        # В callback из канала reply/редактирование часто приводит к отправке сообщений в канал.
        # Поэтому всегда пробуем отправлять личное сообщение пользователю.
        try:
            await bot.send_message(chat_id=user_id, text=text)
        except Exception:
            # fallback для случая, когда личные сообщения недоступны
            if update.effective_message is not None:
                await update.effective_message.reply_text(text)

    async with SessionLocal() as session:
        repo = GiveawayRepository(session)
        giveaway = await repo.get_giveaway(giveaway_id)

        if giveaway is None:
            await _notify_user("Розыгрыш с таким ID не найден.")
            return

        if giveaway.status != "active":
            await _notify_user("Этот розыгрыш уже завершён.")
            return

        if giveaway.subscription_channel_id == 0:
            await _notify_user(
                "Похоже, администратор не настроил канал для проверки подписки для этого розыгрыша. "
                "Попробуйте позже."
            )
            return

        subscribed = await is_user_subscribed(bot, giveaway.subscription_channel_id, user_id)
        if not subscribed:
            await _notify_user(
                "Для участия нужно быть подписанным на канал. "
                "Пожалуйста, подпишитесь и попробуйте снова."
            )
            return

        added = await repo.add_participant(giveaway_id, user_id)
        if not added:
            await _notify_user("Вы уже участвуете в этом розыгрыше.")
            return

    await _notify_user("Вы добавлены в список участников. Удачи!")


async def join_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.effective_message.reply_text("Использование: /join <ID_розыгрыша>")
        return

    try:
        giveaway_id = int(context.args[0])
    except ValueError:
        await update.effective_message.reply_text("Некорректный ID розыгрыша.")
        return

    await join_by_giveaway_id(update, context, giveaway_id)


async def join_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.callback_query is None:
        return

    query = update.callback_query
    await query.answer()

    data = query.data or ""
    # expected join:<id>
    try:
        giveaway_id = int(data.split(":", 1)[1])
    except Exception:
        await query.edit_message_text("Некорректный параметр розыгрыша.")
        return

    # Для callback удобнее отвечать в личку, а не редактировать сообщение.
    from_copy_update = update
    await join_by_giveaway_id(from_copy_update, context, giveaway_id)

