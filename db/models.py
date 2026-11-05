"""Database tables (SQLAlchemy 2.0 style)."""
from datetime import date, datetime

from sqlalchemy import String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class PantryItem(Base):
    __tablename__ = "pantry_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    quantity: Mapped[float | None] = mapped_column(default=None)
    unit: Mapped[str] = mapped_column(String(20), default="")
    purchase_date: Mapped[date | None] = mapped_column(default=None)
    expiry_date: Mapped[date | None] = mapped_column(default=None)
    notes: Mapped[str] = mapped_column(String(200), default="")


class Favorite(Base):
    __tablename__ = "favorites"

    id: Mapped[int] = mapped_column(primary_key=True)
    recipe_id: Mapped[str] = mapped_column(String(80), unique=True)
    recipe_name: Mapped[str] = mapped_column(String(120))
    rating: Mapped[int | None] = mapped_column(default=None)  # 1..5
    saved_at: Mapped[datetime] = mapped_column(default=datetime.now)


class HistoryEntry(Base):
    __tablename__ = "history"

    id: Mapped[int] = mapped_column(primary_key=True)
    recipe_id: Mapped[str] = mapped_column(String(80))
    recipe_name: Mapped[str] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)