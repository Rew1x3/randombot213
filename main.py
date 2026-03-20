import asyncio
import logging

from telegram import BotCommand
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, filters

from config import settings
from database.session import init_db
from handlers.admin import end_giveaway_admin, select_winner_admin
from handlers.errors import error_handler
from handlers.participation import join_callback, join_command
from handlers.start import start_command
from handlers.giveaway_creator import build_giveaway_creator_conversation
from handlers.active import active_giveaways_command
from utils.giveaway_resolver import auto_resolve_due_giveaways_job
from utils.logging import setup_logging


async def post_init(application: Application) -> None:
    # На некоторых хостингах могут остаться старые webhook'ы.
    # Нам нужен polling, поэтому сбрасываем webhook при старте.
    try:
        await application.bot.delete_webhook(drop_pending_updates=True)
    except Exception:
        # Если вебхук не настроен/недоступен — не считаем это критичным.
        pass

    # Бэкапим username для формирования deep-link
    try:
        me = await application.bot.get_me()
        application.bot_data["bot_username"] = me.username
    except Exception:
        application.bot_data["bot_username"] = None

    # Устанавливаем список команд, которые видны в UI.
    # ВАЖНО: скрытая команда /select_winner умышленно не добавляется.
    try:
        await application.bot.set_my_commands(
            [
                BotCommand("start", "Привет и создание/участие"),
                BotCommand("join", "Участие: /join <ID_розыгрыша>"),
                BotCommand("active_giveaways", "Список активных розыгрышей"),
            ]
        )
    except Exception:
        logging.getLogger(__name__).warning("Не удалось установить команды бота (set_my_commands).", exc_info=True)


def main() -> None:
    logger = setup_logging(settings.log_level)

    # Инициализация БД
    asyncio.run(init_db())

    application = (
        Application.builder()
        .token(settings.bot_token)
        .post_init(post_init)
        .build()
    )

    # Обработчики команд/коллбеков
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("join", join_command))
    application.add_handler(CommandHandler("active_giveaways", active_giveaways_command, filters=filters.ChatType.PRIVATE))

    # Deep-link для создания розыгрыша
    application.add_handler(CallbackQueryHandler(join_callback, pattern=r"^join:\d+$"))

    # Конструктор диалога создания розыгрыша
    application.add_handler(build_giveaway_creator_conversation())

    # Админские команды (работают в приватном чате)
    application.add_handler(CommandHandler("end_giveaway", end_giveaway_admin, filters=filters.ChatType.PRIVATE))
    application.add_handler(CommandHandler("select_winner", select_winner_admin, filters=filters.ChatType.PRIVATE))

    # Логирование ошибок
    application.add_error_handler(error_handler)

    # Автоматическое завершение розыгрышей по времени
    application.job_queue.run_repeating(auto_resolve_due_giveaways_job, interval=60, first=10)

    logger.info("Bot is starting (polling).")
    application.run_polling()


if __name__ == "__main__":
    main()

