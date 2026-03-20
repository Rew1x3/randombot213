from __future__ import annotations

from typing import Optional

from telegram import Bot
from telegram.constants import ChatMemberStatus
from telegram.error import BadRequest, Forbidden


async def is_user_subscribed(
    bot: Bot,
    channel_id: int,
    user_id: int,
) -> bool:
    """
    Проверка подписки через getChatMember.
    Возвращает True, если пользователь состоит в канале (member/administrator/creator).
    """
    try:
        member = await bot.get_chat_member(chat_id=channel_id, user_id=user_id)
    except (Forbidden, BadRequest):
        return False

    status = member.status
    # Обычно для "подписан" подходят не-left статусы.
    return status not in (ChatMemberStatus.LEFT, ChatMemberStatus.KICKED, ChatMemberStatus.BANNED)


def escape_html(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


async def safe_user_mention(bot: Bot, user_id: int) -> str:
    """
    Формирует HTML-упоминание вида <a href="tg://user?id=...">Имя</a>.
    Если нет данных пользователя, использует user_id.
    """
    name = str(user_id)
    try:
        # getChat может не вернуть профиль, но часто работает
        chat = await bot.get_chat(user_id)
        if getattr(chat, "first_name", None):
            name = chat.first_name
        if getattr(chat, "last_name", None):
            name = f"{chat.first_name} {chat.last_name}"
        if getattr(chat, "username", None):
            name = f"@{chat.username}"
    except Exception:
        pass

    return f'<a href="tg://user?id={user_id}">{escape_html(name)}</a>'

