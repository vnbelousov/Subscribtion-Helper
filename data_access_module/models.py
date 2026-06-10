from datetime import datetime, date
from decimal import Decimal

from sqlalchemy import BigInteger, Boolean, Date, DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from data_access_module.database import Base

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    username: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    subscriptions: Mapped[list["Subscription"]] = relationship(
        back_populates="user"
    )

class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    icon: Mapped[str] = mapped_column(String(10), nullable=False)

    subscriptions: Mapped[list["Subscription"]] = relationship(
        back_populates="category"
    )

class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(primary_key=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
    )

    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id"),
        nullable=False,
    )

    service_name: Mapped[str] = mapped_column(String(150), nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="RUB")

    billing_period: Mapped[str] = mapped_column(String(30), nullable=False)

    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    next_payment_date: Mapped[date] = mapped_column(Date, nullable=False)

    status: Mapped[str] = mapped_column(String(30), default="active")

    management_url: Mapped[str | None] = mapped_column(String(300), nullable=True)

    reminders_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    reminder_days_before: Mapped[int] = mapped_column(default=1)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship(
        back_populates="subscriptions"
    )

    category: Mapped["Category"] = relationship(
        back_populates="subscriptions"
    )

    payments: Mapped[list["Payment"]] = relationship(
        back_populates="subscription"
    )

    reminders: Mapped[list["Reminder"]] = relationship(
        back_populates="subscription"
    )

class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True)

    subscription_id: Mapped[int] = mapped_column(
        ForeignKey("subscriptions.id"),
        nullable=False,
    )

    payment_date: Mapped[date] = mapped_column(Date, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="RUB")

    subscription: Mapped["Subscription"] = relationship(
        back_populates="payments"
    )

class Reminder(Base):
    __tablename__ = "reminders"

    id: Mapped[int] = mapped_column(primary_key=True)

    subscription_id: Mapped[int] = mapped_column(
        ForeignKey("subscriptions.id"),
        nullable=False,
    )

    send_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="planned")

    subscription: Mapped["Subscription"] = relationship(
        back_populates="reminders"
    )