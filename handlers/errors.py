import logging
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.exception("Unhandled exception: %s", context.error)

    if isinstance(update, Update) and update.effective_message is not None:
        try:
            await update.effective_message.reply_text("Произошла ошибка. Попробуйте позже.")
        except Exception:
            pass

