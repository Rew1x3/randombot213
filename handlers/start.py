from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from config import settings
from keyboards.inline import create_main_keyboard


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user is None or update.effective_chat is None:
        return

    is_admin = update.effective_user.id in set(settings.admin_ids)

    # Поддерживаем deep-link участия: /start join_<giveaway_id>
    if context.args:
        token = context.args[0]
        if token.startswith("join_"):
            try:
                giveaway_id = int(token.split("_", 1)[1])
            except ValueError:
                await update.effective_message.reply_text("Некорректный ID розыгрыша.")
                return

            from handlers.participation import join_by_giveaway_id

            await join_by_giveaway_id(update, context, giveaway_id)
            return

    text = (
        "Привет! Я бот для розыгрышей.\n\n"
        "Чтобы участвовать, нажмите кнопку «Участвовать» в сообщении с розыгрышем "
        "или используйте ссылку вида: /start join_<ID>."
    )
    if is_admin:
        text += "\nЧтобы создать розыгрыш, нажмите «Создать розыгрыш»."
        await update.effective_message.reply_text(text, reply_markup=create_main_keyboard())
    else:
        await update.effective_message.reply_text(text)

