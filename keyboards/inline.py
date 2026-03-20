from __future__ import annotations

from typing import Optional

from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def create_main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(text="Создать розыгрыш", callback_data="create_giveaway")],
        ]
    )


def giveaway_keyboard(giveaway_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(text="Участвовать", callback_data=f"join:{giveaway_id}")],
        ]
    )

