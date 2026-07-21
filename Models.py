"""
SQLAlchemy models for the manual payment-verification flow.
"""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, BigInteger, DateTime, Text, Enum as SAEnum
)
from sqlalchemy.orm import declarative_base
import enum

Base = declarative_base()


class OrderStatus(str, enum.Enum):
    PENDING_PAYMENT = "pending_payment"          # order created, waiting for screenshot
    SCREENSHOT_SENT = "screenshot_sent"          # customer uploaded screenshot, waiting on admin
    APPROVED = "approved"                        # admin approved (typed a reply that included approval)
    REJECTED = "rejected"                        # admin rejected
    REPLIED = "replied"                          # admin replied but neither approved/rejected explicitly


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_code = Column(String(20), unique=True, nullable=False)   # e.g. GEFX-000123

    customer_telegram_id = Column(BigInteger, nullable=False, index=True)
    customer_username = Column(String(64), nullable=True)

    product = Column(String(64), nullable=False)     # vip_monthly / copy_trading / etc.
    amount = Column(String(32), nullable=False)       # store as string to avoid float issues, e.g. "49.00 USDT"

    status = Column(SAEnum(OrderStatus), default=OrderStatus.PENDING_PAYMENT, nullable=False)

    screenshot_file_id = Column(String(255), nullable=True)     # telegram file_id of the screenshot
    admin_forward_chat_id = Column(BigInteger, nullable=True)   # chat where screenshot was forwarded to admin
    admin_forward_message_id = Column(BigInteger, nullable=True)  # message id of that forwarded post (the one admin replies to)

    admin_reply_text = Column(Text, nullable=True)
    admin_reply_by = Column(BigInteger, nullable=True)   # admin's telegram id who replied

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
  
