"""
Telegram Moderation Bot (Full Version)
=======================================

requirements.txt:
    aiogram==3.13.1
    aiosqlite==0.20.0
    aiofiles==24.1.0

Environment variables (set on Render, NEVER hardcode these):
    BOT_TOKEN            -> bot token from @BotFather
    OWNER_ID             -> your numeric Telegram user id
    COMMUNITY_CHAT_ID     -> numeric chat id of "Gold Expert Fx Community" (e.g. -100xxxxxxxxxx)
    PRIVATE_CHANNEL_ID    -> numeric chat id of "Gold Expert Fx Private Channel" (e.g. -100xxxxxxxxxx)

Only NEW join requests (received after this bot is running) are managed. Requests
that were already pending before the bot started are left untouched.

Behaviour implemented:
    1. Owner posts ANY link (even third-party) in the community -> never deleted.
    2. The 3 whitelisted links below, when posted DIRECTLY (not forwarded) by
       anyone in the community -> never deleted.
    3. Any other link posted by a normal member -> deleted.
    4. Any message FORWARDED from an admin OR forwarded from a private channel
       and containing a link -> deleted, even if the link is whitelisted.
    5. Join requests to the Private Channel:
         - If the requesting user is currently a member of the Community ->
           request is left pending. Once that user LEAVES the Community, a
           7 hour timer starts; after 7 hours the request is auto-approved.
         - If the requesting user is NOT a member of the Community (direct
           join request) -> approved immediately.
"""

import asyncio
import logging
import os
import re
import sqlite3
import time
from contextlib import closing

from aiogram import Bot, Dispatcher, F, Router
from aiogram.enums import ChatMemberStatus, ParseMode
from aiogram.types import ChatJoinRequest, ChatMemberUpdated, Message
from aiogram.client.default import DefaultBotProperties

# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #

BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("Set BOT_TOKEN before running.")

OWNER_ID = int(os.environ.get("OWNER_ID", "0"))
COMMUNITY_CHAT_ID = int(os.environ.get("COMMUNITY_CHAT_ID", "0"))
PRIVATE_CHANNEL_ID = int(os.environ.get("PRIVATE_CHANNEL_ID", "0"))

# Links allowed to stay if posted DIRECTLY (not forwarded) in the community.
WHITELISTED_LINKS = {
    "https://www.brokeraccountguide.com/",
    "https://t.me/GoldExpertFxCommunity",
    "https://telegram.me/+Ri2SC_TdIFY5NTI1",
}

APPROVAL_DELAY_SECONDS = 7 * 60 * 60  # 7 hours
DB_PATH = "bot_data.db"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

URL_REGEX = re.compile(
    r"(https?://\S+|t(?:elegram)?\.me/\S+|www\.\S+)", re.IGNORECASE
)

router = Router()

# --------------------------------------------------------------------------- #
# Storage (sqlite) for pending join requests
# --------------------------------------------------------------------------- #

def db_init() -> None:
    with closing(sqlite3.connect(DB_PATH)) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS pending_join_requests (
                user_id INTEGER PRIMARY KEY,
                status TEXT NOT NULL,           -- 'waiting_leave' or 'waiting_period'
                left_at REAL                    -- unix timestamp when user left community
            )
            """
        )
        conn.commit()


def db_set_waiting_leave(user_id: int) -> None:
    with closing(sqlite3.connect(DB_PATH)) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO pending_join_requests (user_id, status, left_at) "
            "VALUES (?, 'waiting_leave', NULL)",
            (user_id,),
        )
        conn.commit()


def db_mark_left(user_id: int) -> None:
    with closing(sqlite3.connect(DB_PATH)) as conn:
        cur = conn.execute(
            "SELECT status FROM pending_join_requests WHERE user_id = ?", (user_id,)
        )
        row = cur.fetchone()
        if row and row[0] == "waiting_leave":
            conn.execute(
                "UPDATE pending_join_requests SET status = 'waiting_period', left_at = ? "
                "WHERE user_id = ?",
                (time.time(), user_id),
            )
            conn.commit()


def db_get_due_approvals(cutoff_ts: float) -> list[int]:
    with closing(sqlite3.connect(DB_PATH)) as conn:
        cur = conn.execute(
            "SELECT user_id FROM pending_join_requests "
            "WHERE status = 'waiting_period' AND left_at IS NOT NULL AND left_at <= ?",
            (cutoff_ts,),
        )
        return [r[0] for r in cur.fetchall()]


def db_remove(user_id: int) -> None:
    with closing(sqlite3.connect(DB_PATH)) as conn:
        conn.execute("DELETE FROM pending_join_requests WHERE user_id = ?", (user_id,))
        conn.commit()


def db_has_pending(user_id: int) -> bool:
    with closing(sqlite3.connect(DB_PATH)) as conn:
        cur = conn.execute(
            "SELECT 1 FROM pending_join_requests WHERE user_id = ?", (user_id,)
        )
        return cur.fetchone() is not None


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def extract_links(text: str) -> list[str]:
    if not text:
        return []
    return URL_REGEX.findall(text)


def is_forwarded(message: Message) -> bool:
    return getattr(message, "forward_origin", None) is not None


async def is_forward_source_admin_or_private_channel(bot: Bot, message: Message) -> bool:
    """
    True if the message was forwarded from:
      - a chat admin of the community, OR
      - any private channel
    """
    origin = getattr(message, "forward_origin", None)
    if origin is None:
        return False

    origin_type = getattr(origin, "type", None)

    if origin_type == "channel":
        return True

    sender_user = getattr(origin, "sender_user", None)
    if sender_user is not None and COMMUNITY_CHAT_ID:
        try:
            member = await bot.get_chat_member(COMMUNITY_CHAT_ID, sender_user.id)
            if member.status in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR):
                return True
        except Exception as e:
            logger.warning("Could not check forward sender admin status: %s", e)

    return False


async def is_member_of_community(bot: Bot, user_id: int) -> bool:
    if not COMMUNITY_CHAT_ID:
        return False
    try:
        member = await bot.get_chat_member(COMMUNITY_CHAT_ID, user_id)
        return member.status in (
            ChatMemberStatus.MEMBER,
            ChatMemberStatus.ADMINISTRATOR,
            ChatMemberStatus.CREATOR,
            ChatMemberStatus.RESTRICTED,
        )
    except Exception as e:
        logger.warning("Could not check community membership for %s: %s", user_id, e)
        return False


# --------------------------------------------------------------------------- #
# Handlers: link moderation
# --------------------------------------------------------------------------- #

@router.message(F.chat.id == COMMUNITY_CHAT_ID)
async def moderate_links(message: Message, bot: Bot) -> None:
    text = message.text or message.caption or ""
    links = extract_links(text)
    if not links:
        return

    sender_id = message.from_user.id if message.from_user else None

    # 1. Owner's links are always safe.
    if sender_id == OWNER_ID:
        return

    forwarded = is_forwarded(message)

    if forwarded:
        # 4. Forwarded from admin or private channel -> delete regardless of whitelist.
        if await is_forward_source_admin_or_private_channel(bot, message):
            await _delete_message(bot, message)
            return

    # 2/3. Direct post: whitelist check.
    if all(link in WHITELISTED_LINKS for link in links) and not forwarded:
        return  # allowed, don't delete

    await _delete_message(bot, message)


async def _delete_message(bot: Bot, message: Message) -> None:
    try:
        await bot.delete_message(message.chat.id, message.message_id)
    except Exception as e:
        logger.warning("Failed to delete message %s: %s", message.message_id, e)


# --------------------------------------------------------------------------- #
# Core join-request decision logic (shared by live handler + startup scan)
# --------------------------------------------------------------------------- #

async def process_join_request(bot: Bot, user_id: int) -> None:
    if await is_member_of_community(bot, user_id):
        db_set_waiting_leave(user_id)
        logger.info("User %s is a community member; join request left pending.", user_id)
    else:
        try:
            await bot.approve_chat_join_request(PRIVATE_CHANNEL_ID, user_id)
            logger.info("Approved direct join request for user %s.", user_id)
        except Exception as e:
            logger.warning("Failed to approve join request for %s: %s", user_id, e)


# --------------------------------------------------------------------------- #
# Handlers: join requests to the private channel (NEW requests, live)
# --------------------------------------------------------------------------- #

@router.chat_join_request(F.chat.id == PRIVATE_CHANNEL_ID)
async def handle_join_request(request: ChatJoinRequest, bot: Bot) -> None:
    await process_join_request(bot, request.from_user.id)


@router.chat_member(F.chat.id == COMMUNITY_CHAT_ID)
async def handle_community_membership_change(event: ChatMemberUpdated) -> None:
    old_status = event.old_chat_member.status
    new_status = event.new_chat_member.status
    user_id = event.new_chat_member.user.id

    left_statuses = (ChatMemberStatus.LEFT, ChatMemberStatus.KICKED)
    was_in = old_status not in left_statuses
    now_out = new_status in left_statuses

    if was_in and now_out and db_has_pending(user_id):
        db_mark_left(user_id)
        logger.info("User %s left the community; 7h approval timer started.", user_id)


# --------------------------------------------------------------------------- #
# Background task: approve pending requests once 7h have passed since leaving
# --------------------------------------------------------------------------- #

async def approval_worker(bot: Bot) -> None:
    while True:
        cutoff = time.time() - APPROVAL_DELAY_SECONDS
        for user_id in db_get_due_approvals(cutoff):
            try:
                await bot.approve_chat_join_request(PRIVATE_CHANNEL_ID, user_id)
                logger.info("Auto-approved delayed join request for user %s.", user_id)
            except Exception as e:
                logger.warning("Failed to auto-approve %s: %s", user_id, e)
            finally:
                db_remove(user_id)
        await asyncio.sleep(300)  # check every 5 minutes


# --------------------------------------------------------------------------- #
# Entrypoint
# --------------------------------------------------------------------------- #

async def main() -> None:
    db_init()

    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.include_router(router)

    asyncio.create_task(approval_worker(bot))

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(
        bot,
        allowed_updates=[
            "message",
            "chat_join_request",
            "chat_member",
        ],
    )


if __name__ == "__main__":
    asyncio.run(main())
    
