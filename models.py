"""
SQLAlchemy models for the manual payment-verification flow.
"""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, BigInteger, DateTime, Text, Enum as SAEnum, ForeignKey
)
from sqlalchemy.orm import declarative_base, relationship
import enum

Base = declarative_base()


class OrderStatus(str, enum.Enum):
    PENDING_PAYMENT = "pending_payment"      # order created, waiting for payment method choice
    AWAITING_SCREENSHOT = "awaiting_screenshot"  # payment method chosen, waiting for screenshot
    SCREENSHOT_SENT = "screenshot_sent"      # screenshot uploaded, waiting on owner
    APPROVED = "approved"
    REJECTED = "rejected"
    PENDING_REVIEW = "pending_review"        # owner said "pending" / still checking


class MessageDirection(str, enum.Enum):
    CUSTOMER_TO_ADMIN = "customer_to_admin"
    ADMIN_TO_CUSTOMER = "admin_to_customer"


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_code = Column(String(20), unique=True, nullable=False, index=True)  # e.g. GEFX-000123

    customer_telegram_id = Column(BigInteger, nullable=False, index=True)
    customer_username = Column(String(64), nullable=True)
    customer_full_name = Column(String(128), nullable=True)

    product = Column(String(64), nullable=False)      # key from config.PRODUCTS
    price = Column(String(64), nullable=True)          # snapshotted at order-creation time
    payment_method = Column(String(64), nullable=True)  # key from config.PAYMENT_METHODS

    status = Column(SAEnum(OrderStatus), default=OrderStatus.PENDING_PAYMENT, nullable=False)

    screenshot_file_id = Column(String(255), nullable=True)
    admin_forward_chat_id = Column(BigInteger, nullable=True)
    admin_forward_message_id = Column(BigInteger, nullable=True)  # the anchor message owner replies to

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
