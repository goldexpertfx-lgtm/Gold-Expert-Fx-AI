"""
Owner-side flow — everything here only acts on input from OWNER_ID.
Anyone else in ADMIN_CHAT_ID can see the forwarded screenshots and replies,
but their replies/button-taps are ignored (with a small notice).
"""
from datetime import datetime

from aiogram import Router, F, Bot
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from aiogram.types import Message, CallbackQuery
from sqlalchemy import select

from config import ADMIN_CHAT_ID, OWNER_ID, PRODUCTS
from db import async_session
from models import Order, OrderStatus, ConversationMessage, MessageDirection
from storage import storage
from customer_handlers import PaymentFlow

router = Router()

APPROVED_TEMPLATE = (
    "✅ Your payment has been verified and approved!\n\n"
    "Welcome to Gold Expert Fx. Here is your access link:\n{invite_link}\n\n"
    "If the link doesn't work, message us here and we'll resend it."
)
REJECTED_TEMPLATE = (
    "❌ We were unable to verify your payment.\n"
    "Please check the amount/screenshot and reply here, or contact support for help."
)
PENDING_TEMPLATE = "⏳ Please wait, verification is in progress."
RESHOOT_TEMPLATE = (
    "📷 The screenshot isn't clear enough to verify. "
    "Please send a new, clear screenshot showing the full transaction details."
)


def _is_owner(user_id: int) -> bool:
    return user_id == OWNER_ID


async def _find_order_by_forward(session, chat_id: int, message_id: int) -> Order | None:
    result = await session.execute(
        select(Order).where(
            Order.admin_forward_chat_id == chat_id,
            Order.admin_forward_message_id == message_id,
        )
    )
    return result.scalar_one_or_none()


async def _find_order_by_code(session, order_code: str) -> Order | None:
    result = await session.execute(select(Order).where(Order.order_code == order_code))
    return result.scalar_one_or_none()


async def _reset_customer_to_screenshot_state(bot: Bot, order: Order):
    """After a 'send clear screenshot' request, put the customer's FSM back
    into waiting_for_screenshot so their next photo is processed as a fresh
    screenshot upload (new admin forward + confirmation), not a generic
    follow-up message."""
    key = StorageKey(bot_id=bot.id, chat_id=order.customer_telegram_id, user_id=order.customer_telegram_id)
    fsm = FSMContext(storage=storage, key=key)
    await fsm.set_state(PaymentFlow.waiting_for_screenshot)
    await fsm.update_data(order_code=order.order_code)


async def resolve_order(order: Order, decision_text: str, bot: Bot, session, actor_id: int):
    """
    Apply a decision to an order and relay the right message to the customer.
    `decision_text` is whatever the owner typed, or a keyword from a button.
    """
    lowered = decision_text.strip().lower()

    if lowered in ("approve", "approved"):
        product_info = PRODUCTS.get(order.product, {})
        text_to_customer = APPROVED_TEMPLATE.format(invite_link=product_info.get("invite_link", "contact admin"))
        order.status = OrderStatus.APPROVED
        order.verified_at = datetime.utcnow()
    elif lowered in ("reject", "rejected", "decline", "declined"):
        text_to_customer = REJECTED_TEMPLATE
        order.status = OrderStatus.REJECTED
    elif lowered in ("pending", "wait"):
        text_to_customer = PENDING_TEMPLATE
        order.status = OrderStatus.PENDING_REVIEW
    elif lowered == "reshoot":
        text_to_customer = RESHOOT_TEMPLATE
        order.status = OrderStatus.AWAITING_SCREENSHOT
        await _reset_customer_to_screenshot_state(bot, order)
    else:
        # Any custom text the owner typed goes to the customer exactly as written.
        text_to_customer = decision_text
        order.status = OrderStatus.PENDING_REVIEW

    order.admin_reply_text = decision_text
    order.admin_reply_by = actor_id

    session.add(ConversationMessage(
        order_id=order.id,
        direction=MessageDirection.ADMIN_TO_CUSTOMER,
        content=text_to_customer,
    ))
    await session.commit()

    await bot.send_message(
        chat_id=order.customer_telegram_id,
        text=f"Update on your order {order.order_code}:\n\n{text_to_customer}",
    )


# ---------------------------------------------------------------------------
# Owner replies with text to the forwarded screenshot
# ---------------------------------------------------------------------------
@router.message(F.chat.id == ADMIN_CHAT_ID, F.reply_to_message)
async def admin_reply_relay(message: Message, bot: Bot):
    if not _is_owner(message.from_user.id):
        await message.reply("Only the owner can verify payments.")
        return

    async with async_session() as session:
        order = await _find_order_by_forward(session, message.chat.id, message.reply_to_message.message_id)
        if not order:
            return  # reply to something unrelated, ignore

        reply_text = message.text or message.caption or ""
        await resolve_order(order, reply_text, bot, session, message.from_user.id)

    await message.reply(f"✅ Sent to customer (order {order.order_code}).")


# ---------------------------------------------------------------------------
# Owner uses the quick-action buttons
# ---------------------------------------------------------------------------
@router.callback_query(F.data.startswith("oa:"))
async def owner_quick_action(callback: CallbackQuery, bot: Bot):
    if not _is_owner(callback.from_user.id):
        await callback.answer("Only the owner can verify payments.", show_alert=True)
        return

    _, action, order_code = callback.data.split(":", 2)

    if action == "custom":
        await callback.answer("Just reply to this message with your text — it'll be sent as-is.", show_alert=True)
        return

    async with async_session() as session:
        order = await _find_order_by_code(session, order_code)
        if not order:
            await callback.answer("Order not found.", show_alert=True)
            return

        action_map = {"approve": "approved", "reject": "rejected", "pending": "pending", "reshoot": "reshoot"}
        await resolve_order(order, action_map[action], bot, session, callback.from_user.id)

    await callback.answer(f"Done — {action} sent to customer.")
    await callback.message.reply(f"✅ Marked {action} for order {order_code}.")


# ---------------------------------------------------------------------------
# Owner lookup commands
# ---------------------------------------------------------------------------
@router.message(Command("orders"))
async def list_orders(message: Message):
    if not _is_owner(message.from_user.id):
        return

    async with async_session() as session:
        result = await session.execute(select(Order).order_by(Order.created_at.desc()).limit(10))
        orders = result.scalars().all()

    if not orders:
        await message.answer("No orders yet.")
        return

    lines = [
        f"{o.order_code} | {o.product} | {o.status.value} | @{o.customer_username or 'N/A'}"
        for o in orders
    ]
    await message.answer("Recent orders:\n" + "\n".join(lines))


@router.message(Command("search"))
async def search_order(message: Message, command: CommandObject):
    if not _is_owner(message.from_user.id):
        return

    order_code = (command.args or "").strip()
    if not order_code:
        await message.answer("Usage: /search GEFX-123456")
        return

    async with async_session() as session:
        order = await _find_order_by_code(session, order_code)
        if not order:
            await message.answer("No such order.")
            return

        history_lines = [
            f"[{m.direction.value}] {m.content}" for m in order.messages
        ]

    await message.answer(
        f"Order: {order.order_code}\n"
        f"Customer: {order.customer_full_name} (@{order.customer_username}, id {order.customer_telegram_id})\n"
        f"Product: {order.product}\n"
        f"Price: {order.price}\n"
        f"Payment method: {order.payment_method}\n"
        f"Status: {order.status.value}\n\n"
        f"Conversation:\n" + ("\n".join(history_lines) if history_lines else "(no messages logged)")
    )


@router.message(Command("user"))
async def search_user(message: Message, command: CommandObject):
    if not _is_owner(message.from_user.id):
        return

    raw_id = (command.args or "").strip()
    if not raw_id.isdigit():
        await message.answer("Usage: /user 123456789")
        return

    async with async_session() as session:
        result = await session.execute(
            select(Order).where(Order.customer_telegram_id == int(raw_id)).order_by(Order.created_at.desc())
        )
        orders = result.scalars().all()

    if not orders:
        await message.answer("No orders found for this user.")
        return

    lines = [f"{o.order_code} | {o.product} | {o.status.value}" for o in orders]
    await message.answer(f"Orders for {raw_id}:\n" + "\n".join(lines))
