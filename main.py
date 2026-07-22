"""
Gold Expert Fx — Manual Payment Verification Bot (single-file version)

Everything lives in this one file on purpose: config, database models,
keyboards, customer-side flow, and owner-side flow. This avoids the
cross-file import mismatches that come from partially updating a
multi-file repo.

REQUIRED ENVIRONMENT VARIABLES (set these on Render, under
Environment -> Environment Variables):
    BOT_TOKEN      - 8851943854:AAGfy9xw9srlQCE5g_yH0hMYqjPsI5NC-e4
    OWNER_ID       - 7415265825
    ADMIN_CHAT_ID  - 4477244119

Optional:
    DATABASE_URL   - defaults to a local sqlite file

requirements.txt needed alongside this file:
    aiogram==3.13.1
    sqlalchemy==2.0.35
    aiosqlite==0.20.0
"""

import asyncio
import logging
import os
import random
import string
from datetime import datetime

from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import CommandStart, CommandObject, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.base import StorageKey
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from sqlalchemy import (
    Column, Integer, String, BigInteger, DateTime, Text, Enum as SAEnum, ForeignKey, select
)
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
import enum

logging.basicConfig(level=logging.INFO)

# ============================================================================
# CONFIG
# ============================================================================
BOT_TOKEN = os.getenv("BOT_TOKEN", "PUT_YOUR_BOT_TOKEN_HERE")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "0"))
OWNER_ID = int(os.getenv("OWNER_ID", "0"))
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./gefx_orders.db")

# Edit these to your real prices / invite links.
PRODUCTS = {
    "vip_monthly":        {"label": "VIP Monthly Membership",   "price": "49 USDT",  "invite_link": "https://t.me/+your_monthly_invite"},
    "vip_quarterly":      {"label": "VIP Quarterly Membership", "price": "129 USDT", "invite_link": "https://t.me/+your_quarterly_invite"},
    "vip_half_year":      {"label": "VIP Half Year Membership", "price": "229 USDT", "invite_link": "https://t.me/+your_halfyear_invite"},
    "vip_yearly":         {"label": "VIP Yearly Membership",    "price": "399 USDT", "invite_link": "https://t.me/+your_yearly_invite"},
    "vip_lifetime":       {"label": "VIP Lifetime Membership",  "price": "699 USDT", "invite_link": "https://t.me/+your_lifetime_invite"},
    "copy_trading":       {"label": "Copy Trading",             "price": "Contact for pricing", "invite_link": "https://t.me/+your_copytrading_invite"},
    "account_management": {"label": "Account Management",       "price": "Contact for pricing", "invite_link": "https://t.me/+your_accountmgmt_invite"},
}

# Edit these to your real payment addresses / accounts.
PAYMENT_METHODS = {
    "binance_pay":   {"label": "Binance Pay",   "details": "Binance Pay ID: XXXXXXXX"},
    "usdt_trc20":    {"label": "USDT (TRC20)",  "details": "Address: T-xxxxxxxxxxxxxxxxxxxxxxxxxxxxx"},
    "usdt_bep20":    {"label": "USDT (BEP20)",  "details": "Address: 0xxxxxxxxxxxxxxxxxxxxxxxxxxxxx"},
    "btc":           {"label": "Bitcoin",       "details": "Address: bc1xxxxxxxxxxxxxxxxxxxxxxxxxx"},
    "eth":           {"label": "Ethereum",      "details": "Address: 0xxxxxxxxxxxxxxxxxxxxxxxxxxxxx"},
    "ltc":           {"label": "Litecoin",      "details": "Address: Lxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"},
    "perfect_money": {"label": "Perfect Money", "details": "Account: Uxxxxxxx"},
    "skrill":        {"label": "Skrill",        "details": "Email: payments@goldexpertfx.com"},
    "neteller":      {"label": "Neteller",      "details": "Email: payments@goldexpertfx.com"},
    "payoneer":      {"label": "Payoneer",      "details": "Email: payments@goldexpertfx.com"},
    "wise":          {"label": "Wise",          "details": "Email: payments@goldexpertfx.com"},
    "bank_transfer": {"label": "Bank Transfer",  "details": "Contact admin for bank details"},
}

SCREENSHOT_RECEIVED_MSG = (
    "✅ Payment screenshot received successfully.\n"
    "Our team will manually verify your payment. Please wait for our confirmation.\n"
    "Do not send multiple screenshots."
)
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

# ============================================================================
# DATABASE MODELS
# ============================================================================
Base = declarative_base()


class OrderStatus(str, enum.Enum):
    PENDING_PAYMENT = "pending_payment"
    AWAITING_SCREENSHOT = "awaiting_screenshot"
    SCREENSHOT_SENT = "screenshot_sent"
    APPROVED = "approved"
    REJECTED = "rejected"
    PENDING_REVIEW = "pending_review"


class MessageDirection(str, enum.Enum):
    CUSTOMER_TO_ADMIN = "customer_to_admin"
    ADMIN_TO_CUSTOMER = "admin_to_customer"


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_code = Column(String(20), unique=True, nullable=False, index=True)

    customer_telegram_id = Column(BigInteger, nullable=False, index=True)
    customer_username = Column(String(64), nullable=True)
    customer_full_name = Column(String(128), nullable=True)

    product = Column(String(64), nullable=False)
    price = Column(String(64), nullable=True)
    payment_method = Column(String(64), nullable=True)

    status = Column(SAEnum(OrderStatus), default=OrderStatus.PENDING_PAYMENT, nullable=False)

    screenshot_file_id = Column(String(255), nullable=True)
    admin_forward_chat_id = Column(BigInteger, nullable=True)
    admin_forward_message_id = Column(BigInteger, nullable=True)

    admin_reply_text = Column(Text, nullable=True)
    admin_reply_by = Column(BigInteger, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    verified_at = Column(DateTime, nullable=True)

    messages = relationship("ConversationMessage", back_populates="order", order_by="ConversationMessage.created_at")


class ConversationMessage(Base):
    __tablename__ = "conversation_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, index=True)

    direction = Column(SAEnum(MessageDirection), nullable=False)
    content = Column(Text, nullable=True)
    telegram_message_id = Column(BigInteger, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    order = relationship("Order", back_populates="messages")


engine = create_async_engine(DATABASE_URL, echo=False)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


# ============================================================================
# KEYBOARDS
# ============================================================================
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


# ============================================================================
# SHARED FSM STORAGE (so admin-side code can reset a customer's state)
# ============================================================================
storage = MemoryStorage()


class PaymentFlow(StatesGroup):
    choosing_payment_method = State()
    waiting_for_screenshot = State()


def generate_order_code() -> str:
    suffix = "".join(random.choices(string.digits, k=6))
    return f"GEFX-{suffix}"


# ============================================================================
# CUSTOMER-SIDE ROUTER
# ============================================================================
customer_router = Router()


@customer_router.message(CommandStart(deep_link=True))
async def start_with_product(message: Message, command: CommandObject, state: FSMContext):
    payload = (command.args or "").strip()
    product_info = PRODUCTS.get(payload)

    if not product_info:
        await message.answer(
            "Welcome to Gold Expert Fx.\n"
            "Please use a valid link (VIP, Copy Trading, Account Management) to start an order."
        )
        return

    order_code = generate_order_code()

    async with async_session() as session:
        order = Order(
            order_code=order_code,
            customer_telegram_id=message.from_user.id,
            customer_username=message.from_user.username,
            customer_full_name=message.from_user.full_name,
            product=payload,
            price=product_info["price"],
            status=OrderStatus.PENDING_PAYMENT,
        )
        session.add(order)
        await session.commit()

    await state.update_data(order_code=order_code)
    await state.set_state(PaymentFlow.choosing_payment_method)

    await message.answer(
        f"Order created: {order_code}\n"
        f"Plan: {product_info['label']}\n"
        f"Price: {product_info['price']}\n\n"
        f"Please choose your payment method:",
        reply_markup=payment_method_keyboard(),
    )


@customer_router.callback_query(PaymentFlow.choosing_payment_method, F.data.startswith("pm:"))
async def choose_payment_method(callback: CallbackQuery, state: FSMContext):
    method_key = callback.data.split(":", 1)[1]
    method_info = PAYMENT_METHODS.get(method_key)

    if not method_info:
        await callback.answer("Invalid option, please try again.", show_alert=True)
        return

    data = await state.get_data()
    order_code = data.get("order_code")

    async with async_session() as session:
        result = await session.execute(select(Order).where(Order.order_code == order_code))
        order = result.scalar_one_or_none()
        if order:
            order.payment_method = method_key
            order.status = OrderStatus.AWAITING_SCREENSHOT
            await session.commit()

    await state.set_state(PaymentFlow.waiting_for_screenshot)
    await callback.message.edit_text(
        f"Order: {order_code}\n"
        f"Payment method: {method_info['label']}\n\n"
        f"{method_info['details']}\n\n"
        f"Once you've paid, please send the payment screenshot here as a photo."
    )
    await callback.answer()


@customer_router.message(PaymentFlow.waiting_for_screenshot, F.photo)
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

        photo = message.photo[-1]
        product_info = PRODUCTS.get(order.product, {})
        method_info = PAYMENT_METHODS.get(order.payment_method, {})

        order.screenshot_file_id = photo.file_id
        order.status = OrderStatus.SCREENSHOT_SENT

        caption = (
            f"🧾 New payment screenshot\n\n"
            f"Order ID: {order.order_code}\n"
            f"Customer Name: {order.customer_full_name or 'N/A'}\n"
            f"Username: @{order.customer_username or 'N/A'}\n"
            f"Telegram ID: {order.customer_telegram_id}\n"
            f"Selected Plan: {product_info.get('label', order.product)}\n"
            f"Price: {order.price}\n"
            f"Payment Method: {method_info.get('label', order.payment_method)}\n"
            f"Date & Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}\n\n"
            f"Reply to THIS message to send a response to the customer, "
            f"or use the buttons below."
        )
        sent = await bot.send_photo(
            chat_id=ADMIN_CHAT_ID,
            photo=photo.file_id,
            caption=caption,
            reply_markup=owner_quick_actions_keyboard(order.order_code),
        )

        order.admin_forward_chat_id = sent.chat.id
        order.admin_forward_message_id = sent.message_id

        session.add(ConversationMessage(
            order_id=order.id,
            direction=MessageDirection.CUSTOMER_TO_ADMIN,
            content="[payment screenshot]",
            telegram_message_id=message.message_id,
        ))

        await session.commit()

    await message.answer(SCREENSHOT_RECEIVED_MSG)
    await state.clear()


@customer_router.message(PaymentFlow.waiting_for_screenshot)
async def waiting_but_not_photo(message: Message):
    await message.answer("Please send the payment screenshot as a photo (not text).")


@customer_router.message(PaymentFlow.choosing_payment_method)
async def waiting_for_method_choice(message: Message):
    await message.answer("Please tap one of the payment method buttons above to continue.")


@customer_router.message(F.chat.type == "private")
async def relay_followup_to_admin(message: Message, state: FSMContext, bot: Bot):
    current_state = await state.get_state()
    if current_state is not None:
        return

    async with async_session() as session:
        result = await session.execute(
            select(Order)
            .where(Order.customer_telegram_id == message.from_user.id)
            .where(Order.status.in_([OrderStatus.SCREENSHOT_SENT, OrderStatus.PENDING_REVIEW]))
            .order_by(Order.created_at.desc())
        )
        order = result.scalars().first()

        if not order or not order.admin_forward_message_id:
            return

        content = message.text or message.caption or "[non-text message]"

        await bot.forward_message(
            chat_id=order.admin_forward_chat_id,
            from_chat_id=message.chat.id,
            message_id=message.message_id,
        )
        await bot.send_message(
            chat_id=order.admin_forward_chat_id,
            text=f"☝️ Follow-up message for order {order.order_code} (reply to the original screenshot above to respond).",
            reply_to_message_id=order.admin_forward_message_id,
        )

        session.add(ConversationMessage(
            order_id=order.id,
            direction=MessageDirection.CUSTOMER_TO_ADMIN,
            content=content,
            telegram_message_id=message.message_id,
        ))
        await session.commit()


# ============================================================================
# ADMIN-SIDE ROUTER
# ============================================================================
admin_router = Router()


def _is_owner(user_id: int) -> bool:
    return user_id == OWNER_ID


async def _find_order_by_forward(session, chat_id: int, message_id: int):
    result = await session.execute(
        select(Order).where(
            Order.admin_forward_chat_id == chat_id,
            Order.admin_forward_message_id == message_id,
        )
    )
    return result.scalar_one_or_none()


async def _find_order_by_code(session, order_code: str):
    result = await session.execute(select(Order).where(Order.order_code == order_code))
    return result.scalar_one_or_none()


async def _reset_customer_to_screenshot_state(bot: Bot, order: Order):
    key = StorageKey(bot_id=bot.id, chat_id=order.customer_telegram_id, user_id=order.customer_telegram_id)
    fsm = FSMContext(storage=storage, key=key)
    await fsm.set_state(PaymentFlow.waiting_for_screenshot)
    await fsm.update_data(order_code=order.order_code)


async def resolve_order(order: Order, decision_text: str, bot: Bot, session, actor_id: int):
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


@admin_router.message(F.chat.id == ADMIN_CHAT_ID, F.reply_to_message)
async def admin_reply_relay(message: Message, bot: Bot):
    if not _is_owner(message.from_user.id):
        await message.reply("Only the owner can verify payments.")
        return

    async with async_session() as session:
        order = await _find_order_by_forward(session, message.chat.id, message.reply_to_message.message_id)
        if not order:
            return

        reply_text = message.text or message.caption or ""
        await resolve_order(order, reply_text, bot, session, message.from_user.id)

    await message.reply(f"✅ Sent to customer (order {order.order_code}).")


@admin_router.callback_query(F.data.startswith("oa:"))
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
         
