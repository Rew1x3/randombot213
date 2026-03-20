from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, filters, CallbackQueryHandler, CommandHandler

from config import settings
from database.repositories import GiveawayRepository
from database.session import SessionLocal
from keyboards.inline import giveaway_keyboard
from utils.prizes import parse_prizes
from utils.time import parse_end_time_utc, to_human_datetime_utc

logger = logging.getLogger(__name__)

STATE_TITLE = 0
STATE_PRIZES = 1
STATE_WINNERS_COUNT = 2
STATE_CHANNEL_ID = 3  # подписка (где must be subscribed)
STATE_PUBLISH_CHANNEL_ID = 4  # куда публикуем сообщение о розыгрыше
STATE_CONDITIONS = 5
STATE_END_TIME = 6

USERDATA = {
    "title": "gc_title",
    "prizes": "gc_prizes",
    "winners_count": "gc_winners_count",
    "channel_id": "gc_channel_id",
    "publish_channel_id": "gc_publish_channel_id",
    "conditions": "gc_conditions",
    "end_time": "gc_end_time",
}


async def create_entry_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.effective_user is None:
        return ConversationHandler.END
    if update.effective_user.id not in set(settings.admin_ids):
        if update.effective_message is not None:
            await update.effective_message.reply_text("Недостаточно прав. Розыгрыши может создавать только администратор.")
        return ConversationHandler.END

    if update.callback_query is not None:
        await update.callback_query.answer()
    if update.effective_message is not None:
        await update.effective_message.reply_text("Отлично! Введите название/описание розыгрыша:")
    # Сбрасываем предыдущие данные диалога
    context.user_data.pop(USERDATA["title"], None)
    context.user_data.pop(USERDATA["prizes"], None)
    context.user_data.pop(USERDATA["winners_count"], None)
    context.user_data.pop(USERDATA["channel_id"], None)
    context.user_data.pop(USERDATA["publish_channel_id"], None)
    context.user_data.pop(USERDATA["conditions"], None)
    context.user_data.pop(USERDATA["end_time"], None)
    return STATE_TITLE


async def title_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.effective_message is None:
        return ConversationHandler.END
    context.user_data[USERDATA["title"]] = update.effective_message.text.strip()
    await update.effective_message.reply_text(
        "Введите список призов. Можно через запятую или перенос строки.\nНапример:\n"
        "1) iPhone, 2) Подарок, 3) Скидка"
    )
    return STATE_PRIZES


async def prizes_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.effective_message is None:
        return ConversationHandler.END
    prizes_text = update.effective_message.text.strip()
    prizes = parse_prizes(prizes_text)
    if not prizes:
        await update.effective_message.reply_text("Список призов пуст. Введите хотя бы один приз.")
        return STATE_PRIZES
    context.user_data[USERDATA["prizes"]] = prizes_text
    await update.effective_message.reply_text("Сколько победителей выбрать? (целое число)")
    return STATE_WINNERS_COUNT


async def winners_count_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.effective_message is None:
        return ConversationHandler.END
    text = update.effective_message.text.strip()
    try:
        winners_count = int(text)
    except ValueError:
        await update.effective_message.reply_text("Нужно целое число. Попробуйте снова.")
        return STATE_WINNERS_COUNT
    if winners_count <= 0:
        await update.effective_message.reply_text("Число победителей должно быть > 0.")
        return STATE_WINNERS_COUNT
    context.user_data[USERDATA["winners_count"]] = winners_count
    if settings.subscription_channel_id == 0:
        await update.effective_message.reply_text(
            "ВНИМАНИЕ: SUBSCRIPTION_CHANNEL_ID в `.env` не задана. "
            "Введите ID канала/чата для проверки подписки вручную на следующем шаге."
        )
    await update.effective_message.reply_text(
        "Укажите ID канала/чата для проверки подписки (куда пользователь должен быть подписан).\n"
        f"Можно ввести пустое сообщение, чтобы использовать значение из .env: `{settings.subscription_channel_id}`"
    )
    return STATE_CHANNEL_ID


async def channel_id_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.effective_message is None:
        return ConversationHandler.END
    text = (update.effective_message.text or "").strip()
    if text == "":
        channel_id = settings.subscription_channel_id
    else:
        try:
            channel_id = int(text)
        except ValueError:
            await update.effective_message.reply_text("Некорректный ID. Введите число (например -100123...)")
            return STATE_CHANNEL_ID

    context.user_data[USERDATA["channel_id"]] = channel_id

    await update.effective_message.reply_text(
        "Укажите ID канала/чата, куда нужно опубликовать сообщение о розыгрыше.\n"
        "Можно ввести пустое сообщение, чтобы использовать тот же ID, что и для проверки подписки."
    )
    return STATE_PUBLISH_CHANNEL_ID


async def publish_channel_id_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.effective_message is None:
        return ConversationHandler.END

    text = (update.effective_message.text or "").strip()
    subscription_channel_id: int = context.user_data[USERDATA["channel_id"]]

    if text == "":
        publish_channel_id = subscription_channel_id
    else:
        try:
            publish_channel_id = int(text)
        except ValueError:
            await update.effective_message.reply_text("Некорректный ID. Введите число (например -100123...)")
            return STATE_PUBLISH_CHANNEL_ID

    context.user_data[USERDATA["publish_channel_id"]] = publish_channel_id
    await update.effective_message.reply_text("Условия участия (опционально). Можно пропустить — просто отправьте пустое сообщение.")
    return STATE_CONDITIONS


async def conditions_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.effective_message is None:
        return ConversationHandler.END
    text = (update.effective_message.text or "").strip()
    context.user_data[USERDATA["conditions"]] = text if text else None
    await update.effective_message.reply_text(
        "Когда завершить розыгрыш? Введите дату/время (UTC) в формате:\n"
        "`YYYY-MM-DD HH:MM`\nНапример: 2026-03-25 18:30"
    )
    return STATE_END_TIME


async def end_time_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.effective_message is None:
        return ConversationHandler.END
    text = update.effective_message.text.strip()
    try:
        end_time = parse_end_time_utc(text)
    except ValueError as e:
        await update.effective_message.reply_text(str(e))
        return STATE_END_TIME

    now = datetime.now(timezone.utc)
    if end_time <= now:
        await update.effective_message.reply_text("Время окончания должно быть в будущем. Попробуйте снова.")
        return STATE_END_TIME

    context.user_data[USERDATA["end_time"]] = end_time

    title: str = context.user_data[USERDATA["title"]]
    prizes_text: str = context.user_data[USERDATA["prizes"]]
    winners_count: int = context.user_data[USERDATA["winners_count"]]
    subscription_channel_id: int = context.user_data[USERDATA["channel_id"]]
    publish_chat_id: int = context.user_data[USERDATA["publish_channel_id"]]
    conditions_text: Optional[str] = context.user_data[USERDATA["conditions"]]
    created_by = update.effective_user.id if update.effective_user else None

    async with SessionLocal() as session:
        repo = GiveawayRepository(session)
        giveaway = await repo.create_giveaway(
            title=title,
            prizes_text=prizes_text,
            winners_count=winners_count,
            subscription_channel_id=subscription_channel_id,
            conditions_text=conditions_text,
            end_time=end_time,
            publish_chat_id=publish_chat_id,
            created_by=created_by,
        )

    # Глубокая ссылка для участия (/start join_<id>)
    bot_username = context.application.bot_data.get("bot_username")
    if bot_username:
        join_link = f"https://t.me/{bot_username}?start=join_{giveaway.id}"
    else:
        join_link = f"/start join_{giveaway.id}"

    text = (
        f"🎲 <b>Розыгрыш #{giveaway.id}</b>\n\n"
        f"<b>{title}</b>\n\n"
        f"Победителей: <b>{winners_count}</b>\n"
        f"Окончание: <b>{to_human_datetime_utc(end_time)}</b>\n"
        f"Условия: {conditions_text or '—'}\n\n"
        f"Призы:\n{prizes_text}\n\n"
        f"Чтобы участвовать:\n"
        f"1) Нажмите кнопку «Участвовать» (если сообщение видно)\n"
        f"2) Или перейдите по ссылке:\n{join_link}"
    )

    # Публикуем сообщение о розыгрыше в канале/чате
    try:
        await context.bot.send_message(
            chat_id=publish_chat_id,
            text=text,
            reply_markup=giveaway_keyboard(giveaway.id),
            parse_mode="HTML",
            disable_web_page_preview=True,
        )
    except Exception as e:
        await update.effective_message.reply_text(
            "Розыгрыш создан, но бот не смог опубликовать сообщение в указанном канале/чате. "
            f"Проверьте, что у бота есть права на публикацию. Ошибка: {e}"
        )
        return ConversationHandler.END

    # И подтверждаем администратору в личке
    if update.effective_chat is not None and update.effective_chat.id != publish_chat_id:
        await update.effective_message.reply_text(
            f"Розыгрыш создан и опубликован в канале/чате `{publish_chat_id}`.\nID розыгрыша: {giveaway.id}",
            parse_mode="Markdown",
        )
    else:
        await update.effective_message.reply_text(
            f"Розыгрыш создан. Сообщение опубликовано. ID розыгрыша: {giveaway.id}"
        )
    return ConversationHandler.END


async def cancel_dialog(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.effective_message is not None:
        await update.effective_message.reply_text("Создание розыгрыша отменено.")
    return ConversationHandler.END


def build_giveaway_creator_conversation() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(create_entry_callback, pattern=r"^create_giveaway$"),
        ],
        states={
            STATE_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, title_step)],
            STATE_PRIZES: [MessageHandler(filters.TEXT & ~filters.COMMAND, prizes_step)],
            STATE_WINNERS_COUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, winners_count_step)],
            STATE_CHANNEL_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, channel_id_step)],
            STATE_PUBLISH_CHANNEL_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, publish_channel_id_step)],
            STATE_CONDITIONS: [MessageHandler(filters.TEXT & ~filters.COMMAND, conditions_step)],
            STATE_END_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, end_time_step)],
        },
        fallbacks=[CommandHandler("cancel", cancel_dialog)],
        per_user=True,
        per_chat=True,
        allow_reentry=True,
    )

