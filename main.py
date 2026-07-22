"""
Telegram Moderation Bot (Final Full Version)
=============================================

ONLY two features are active in this bot:
    1. Link moderation in the community.
    2. Join-request handling for the private channel (including a one-time
       startup scan of requests that were already pending before this bot
       started running).

requirements.txt:
    aiogram==3.13.1
    aiosqlite==0.20.0
    aiofiles==24.1.0

Environment variables (set these on Render -> Environment. NEVER hardcode them):
    BOT_TOKEN            -> bot token from @BotFather
    OWNER_ID             -> your numeric Telegram user id
    COMMUNITY_CHAT_ID     -> numeric chat id of "Gold Expert Fx Community" (e.g. -100xxxxxxxxxx)
    PRIVATE_CHANNEL_ID    -> numeric chat id of "Gold Expert Fx Private Channel" (e.g. -100xxxxxxxxxx)

Only NEW join requests (received while this bot is running) are managed.
Requests that were already pending before the bot started are left alone.

--------------------------------------------------------------------------
FEATURE 1: LINK MODERATION (community)
--------------------------------------------------------------------------
    - Owner posts ANY link (even third-party) -> never deleted.
    - The 3 whitelisted links below, when posted DIRECTLY (not forwarded) by
      anyone -> never deleted.
    - Any other link posted by a normal member -> deleted.
    - Any message FORWARDED from an admin OR forwarded from a private channel
      and containing a link -> deleted, even if the link is one of the
      whitelisted ones.
    - Works both for normal group messages AND for direct channel posts
      (Telegram delivers channel posts as a separate update type).

--------------------------------------------------------------------------
FEATURE 2: JOIN REQUESTS (private channel)
--------------------------------------------------------------------------
    - If the requesting user is currently a member of the Community -> the
      request is left pending (neither approved nor declined) for as long as
      that user stays in the Community -- even if that is years. The moment
      that user LEAVES the Community (whenever that happens), a 7 hour timer
      starts; after 7 hours the request is auto-approved (never declined).
    - If the requesting user is NOT a member of the Community (a direct join
      request) -> approved immediately.
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
    if getattr(message, "forward_origin", None) is not None:
        return True
    # Legacy / alternate fields some Bot API versions & auto-forwarded
    # channel posts populate instead of forward_origin.
    if getattr(message, "forward_from_chat", None) is not None:
        return True
    if getattr(message, "forward_from", None) is not None:
        return True
    if getattr(message, "is_automatic_forward", False):
        return True
    return False


async def is_forward_source_admin_or_private_channel(bot: Bot, message: Message) -> bool:
    """
    True if the message was forwarded from:
      - a chat admin of the community, OR
      - any private channel (including Telegram's automatic forward from a
        linked channel into its discussion group)
    """
    origin = getattr(message, "forward_origin", None)
    legacy_chat = getattr(message, "forward_from_chat", None)
    legacy_user = getattr(message, "forward_from", None)

    origin_type = getattr(origin, "type", None) if origin else None

    # New-style origin says it came from a channel.
    if origin_type == "channel":
        return True

    # Legacy / auto-forward field: forwarded from any channel.
    if legacy_chat is not None and getattr(legacy_chat, "type", None) == "channel":
        return True

    # Telegram's automatic forward from a linked channel into its discussion group.
    if getattr(message, "is_automatic_forward", False):
        return True

    # Forwarded from a user -> check if that user is an admin of the community.
    sender_user = getattr(origin, "sender_user", None) if origin else None
    sender_user = sender_user or legacy_user
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
# FEATURE 1: link moderation (covers both normal messages and channel posts)
# --------------------------------------------------------------------------- #

@router.message(F.chat.id == COMMUNITY_CHAT_ID)
async def moderate_links_message(message: Message, bot: Bot) -> None:
    await moderate_links(message, bot)


@router.channel_post(F.chat.id == COMMUNITY_CHAT_ID)
async def moderate_links_channel_post(message: Message, bot: Bot) -> None:
    # Handles posts made directly in the channel (e.g. by admins), which
    # Telegram delivers as channel_post updates instead of plain message updates.
    await moderate_links(message, bot)


async def moderate_links(message: Message, bot: Bot) -> None:
    text = message.text or message.caption or ""
    links = extract_links(text)
    if not links:
        return

    sender_id = message.from_user.id if message.from_user else None
    forwarded = is_forwarded(message)
    logger.info(
        "Link detected in chat %s (msg %s): links=%s sender=%s forwarded=%s",
        message.chat.id, message.message_id, links, sender_id, forwarded,
    )

    # Owner's links are always safe.
    if sender_id == OWNER_ID:
        logger.info("-> kept: sender is OWNER_ID")
        return

    if forwarded:
        # Forwarded from admin or private channel -> delete regardless of whitelist.
        if await is_forward_source_admin_or_private_channel(bot, message):
            logger.info("-> deleting: forwarded from admin or private channel")
            await _delete_message(bot, message)
            return

    # Direct post: whitelist check.
    if all(link in WHITELISTED_LINKS for link in links) and not forwarded:
        logger.info("-> kept: whitelisted link, not forwarded")
        return  # allowed, don't delete

    # Anything else with a link gets removed.
    logger.info("-> deleting: not owner, not whitelisted-direct")
    await _delete_message(bot, message)


async def _delete_message(bot: Bot, message: Message) -> None:
    try:
        await bot.delete_message(message.chat.id, message.message_id)
        logger.info("Deleted message %s in chat %s", message.message_id, message.chat.id)
    except Exception as e:
        logger.warning("Failed to delete message %s: %s", message.message_id, e)


# --------------------------------------------------------------------------- #
# FEATURE 2: join requests to the private channel
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


async def approval_worker(bot: Bot) -> None:
    """Background loop: approve pending requests once 7h have passed since leaving."""
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
            "channel_post",
            "chat_join_request",
            "chat_member",
        ],
    )


if __name__ == "__main__":
    asyncio.run(main())
    
