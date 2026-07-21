"""
Customer-side flow.

/start <product>
    -> order created with product + price auto-filled from config.PRODUCTS
    -> customer picks a payment method (inline buttons)
    -> customer is shown payment details, asked to send a screenshot

photo received
    -> saved, forwarded to admin with full order context + quick-action buttons
    -> customer gets the fixed confirmation message

any message sent AFTER the screenshot but before an owner decision
    -> forwarded to admin too (linked to the same order), so nothing customer
       says gets lost while they're waiting
"""
import random
import string
from datetime import datetime

from aiogram import Router, F, Bot
from aiogram.filters import CommandStart, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery
from sqlalchemy import select

from config import ADMIN_CHAT_ID, PRODUCTS, PAYMENT_METHODS
from db import async_session
from models import Order, OrderStatus, ConversationMessage, MessageDirection
from keyboards import payment_method_keyboard, owner_quick_actions_keyboard

router = Router()

SCREENSHOT_RECEIVED_MSG = (
    "✅ Payment screenshot received successfully.\n"
    "Our team will manually verify your payment. Please wait for our confirmation.\n"
    "Do not send multiple screenshots."
)


class PaymentFlow(StatesGroup):
    choosing_payment_method = State()
    waiting_for_screenshot = State()


def generate_order_code() -> str:
    suffix = "".join(random.choices(string.digits, k=6))
    return f"GEFX-{suffix}"


# ---------------------------------------------------------------------------
# Step 1: /start <product> — auto-detect product + price, ask payment method
# ---------------------------------------------------------------------------
@router.message(CommandStart(deep_link=True))
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


# ---------------------------------------------------------------------------
# Step 2: customer picks a payment method
# ---------------------------------------------------------------------------
@router.callback_query(PaymentFlow.choosing_payment_method, F.data.startswith("pm:"))
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


# ---------------------------------------------------------------------------
# Step 3: customer sends the screenshot -> forward to admin
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


@router.message(PaymentFlow.waiting_for_screenshot)
async def waiting_but_not_photo(message: Message):
    await message.answer("Please send the payment screenshot as a photo (not text).")


@router.message(PaymentFlow.choosing_payment_method)
async def waiting_for_method_choice(message: Message):
    await message.answer("Please tap one of the payment method buttons above to continue.")


# ---------------------------------------------------------------------------
# Step 4: any further customer message while awaiting a decision -> forward too
# ---------------------------------------------------------------------------
@router.message(F.chat.type == "private")
async def relay_followup_to_admin(message: Message, state: FSMContext, bot: Bot):
    # Only handles messages that fall outside the FSM states above — i.e. a
    # customer messaging again after their screenshot was already sent, while
    # still waiting on the owner. If they're mid-flow, the handlers above
    # already caught it, so reaching here means: no active state.
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
            return  # nothing to link this message to

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
