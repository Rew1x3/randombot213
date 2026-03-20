from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Giveaway(Base):
    __tablename__ = "giveaways"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    prizes_text: Mapped[str] = mapped_column(Text, nullable=False)
    winners_count: Mapped[int] = mapped_column(Integer, nullable=False)

    # Канал, подписка на который обязательна для участия
    subscription_channel_id: Mapped[int] = mapped_column(BigInteger, nullable=False)

    conditions_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active", index=True)
    publish_chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    participants: Mapped[list["Participant"]] = relationship(
        back_populates="giveaway",
        cascade="all, delete-orphan",
    )
    winners: Mapped[list["Winner"]] = relationship(
        back_populates="giveaway",
        cascade="all, delete-orphan",
        order_by="Winner.position",
    )


class Participant(Base):
    __tablename__ = "participants"
    __table_args__ = (UniqueConstraint("giveaway_id", "telegram_id", name="uq_participant_giveaway_user"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    giveaway_id: Mapped[int] = mapped_column(Integer, ForeignKey("giveaways.id", ondelete="CASCADE"), index=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, index=True)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    giveaway: Mapped["Giveaway"] = relationship(back_populates="participants")


class Winner(Base):
    __tablename__ = "winners"
    __table_args__ = (
        UniqueConstraint("giveaway_id", "position", name="uq_winner_position"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    giveaway_id: Mapped[int] = mapped_column(Integer, ForeignKey("giveaways.id", ondelete="CASCADE"), index=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, index=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False)  # 1..N
    prize_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    selected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    giveaway: Mapped["Giveaway"] = relationship(back_populates="winners")

