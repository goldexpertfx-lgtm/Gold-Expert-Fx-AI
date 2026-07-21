from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import PAYMENT_METHODS


def payment_method_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for key, info in PAYMENT_METHODS.items():
        builder.button(text=info["label"], callback_data=f"pm:{key}")
    builder.adjust(2)
    return builder.as_markup()


def owner_quick_actions_keyboard(order_code: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Approve", callback_data=f"oa:approve:{order_code}")
    builder.button(text="❌ Reject", callback_data=f"oa:reject:{order_code}")
    builder.button(text="⏳ Wait", callback_data=f"oa:pending:{order_code}")
    builder.button(text="📷 Send Clear Screenshot", callback_data=f"oa:reshoot:{order_code}")
    builder.button(text="💬 Custom Reply", callback_data=f"oa:custom:{order_code}")
    builder.adjust(2, 2, 1)
    return builder.as_markup()
