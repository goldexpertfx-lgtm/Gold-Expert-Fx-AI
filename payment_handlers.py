"""
Manual payment verification flow.

Flow:
1. Customer runs /start <product>  -> bot creates an Order, asks for a screenshot.
2. Customer sends a photo          -> bot saves it, forwards it to ADMIN_CHAT_ID
                                       with the order code in the caption, and marks
                                       the order as SCREENSHOT_SENT.
3. Admin (owner) REPLIES to that forwarded photo message, typing anything
   ("approved, VIP added" / "rejected, wrong amount" / whatever).
4. Bot detects the reply, matches it back to the order via the forwarded
   message_id, and sends the admin's exact text to the customer. No AI,
   no auto-approval logic — the admin's own words are what get sent.

This is intentionally manual: the bot is a messenger between customer and
admin, not a decision-maker.
"""
import random
import string

from aiogram import Router, F, Bot
from aiogram.filters import CommandStart, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message
from sqlalchemy import select

from config import ADMIN_CHAT_ID
from db import async_session
from models import Order, OrderStatus

router = Router()


class PaymentFlow(StatesGroup):
    waiting_for_screenshot = State()


def generate_order_code() -> str:
    suffix = "".join(random.choices(string.digits, k=6))
    return f"GEFX-{suffix}"


PRODUCT_LABELS = {
    "vip_monthly": "VIP Monthly Membership",
    "vip_quarterly": "VIP Quarterly Membership",
    "vip_yearly": "VIP Yearly Membership",
    "vip_lifetime": "VIP Lifetime Membership",
    "copy_trading": "Copy Trading",
    "account_management": "Account Management",
}


# ---------------------------------------------------------------------------
# Step 1: /start <product> — create the order, ask for screenshot
# ---------------------------------------------------------------------------
@router.message(CommandStart(deep_link=True))
async def start_with_product(message: Message, command: CommandObject, state: FSMContext):
    payload = (command.args or "").strip()
    product = payload if payload in PRODUCT_LABELS else None

    if not product:
        await message.answer(
            "Welcome to Gold Expert Fx.\n"
            "Please use a valid link (e.g. VIP, Copy Trading, Account Management) "
            "to start an order."
        )
        return

    order_code = generate_order_code()

    async with async_session() as session:
        order = Order(
            order_code=order_code,
            customer_telegram_id=message.from_user.id,
            customer_username=message.from_user.username,
            product=product,
            amount="TBD",  # set this once you wire in your real pricing table
            status=OrderStatus.PENDING_PAYMENT,
        )
        session.add(order)
        await session.commit()

    await state.update_data(order_code=order_code)
    await state.set_state(PaymentFlow.waiting_for_screenshot)

    await message.answer(
        f"Order created: {order_code}\n"
        f"Product: {PRODUCT_LABELS[product]}\n\n"
        f"Please make your payment and then send the payment screenshot here "
        f"as a photo. It will be reviewed by an admin, and you'll get a reply "
        f"directly here once it's checked."
    )


# ---------------------------------------------------------------------------
# Step 2: customer sends the screenshot -> forward to admin
# ---------------------------------------------------------------------------
@router.message(PaymentFlow.waiting_for_screenshot, F.photo)
async def receive_screenshot(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    order_code = data.get("order_code")

    async with async_session() as session:
        result = await session.execute(select(Order).where(Order.order_code == order_code))
        order = result.scalar_one_or_none()

        if not order:
            await message.answer("Could not find your order. Please start again with /start.")
            await state.clear()
            return

        photo = message.photo[-1]  # highest resolution
        order.screenshot_file_id = photo.file_id
        order.status = OrderStatus.SCREENSHOT_SENT

        # Forward the screenshot to the admin with order context in the caption.
        caption = (
            f"🧾 New payment screenshot\n"
            f"Order: {order.order_code}\n"
            f"Product: {PRODUCT_LABELS.get(order.product, order.product)}\n"
            f"Customer: @{order.customer_username or 'N/A'} (id: {order.customer_telegram_id})\n\n"
            f"Reply to THIS message to send a response directly to the customer."
        )
        sent = await bot.send_photo(
            chat_id=ADMIN_CHAT_ID,
            photo=photo.file_id,
            caption=caption,
        )

        order.admin_forward_chat_id = sent.chat.id
        order.admin_forward_message_id = sent.message_id

        await session.commit()

    await message.answer(
        f"Screenshot received for order {order_code}. "
        f"An admin will review it and reply to you here shortly."
    )
    await state.clear()


@router.message(PaymentFlow.waiting_for_screenshot)
async def waiting_but_not_photo(message: Message):
    await message.answer("Please send the payment screenshot as a photo (not text).")


# ---------------------------------------------------------------------------
# Step 3: admin replies to the forwarded screenshot -> relay to customer
# ---------------------------------------------------------------------------
@router.message(F.chat.id == ADMIN_CHAT_ID, F.reply_to_message)
async def admin_reply_relay(message: Message, bot: Bot):
    replied = message.reply_to_message

    async with async_session() as session:
        result = await session.execute(
            select(Order).where(
                Order.admin_forward_chat_id == message.chat.id,
                Order.admin_forward_message_id == replied.message_id,
            )
        )
        order = result.scalar_one_or_none()

        if not order:
            return  # admin replied to some unrelated message, ignore

        reply_text = message.text or message.caption or ""

        order.admin_reply_text = reply_text
        order.admin_reply_by = message.from_user.id

        lowered = reply_text.lower()
        if "approve" in lowered:
            order.status = OrderStatus.APPROVED
        elif "reject" in lowered or "decline" in lowered:
            order.status = OrderStatus.REJECTED
        else:
            order.status = OrderStatus.REPLIED

        await session.commit()

        # Send the admin's own words to the customer, unmodified.
        await bot.send_message(
            chat_id=order.customer_telegram_id,
            text=f"Update on your order {order.order_code}:\n\n{reply_text}",
        )

    await message.reply(f"✅ Sent to customer (order {order.order_code}).")
  
