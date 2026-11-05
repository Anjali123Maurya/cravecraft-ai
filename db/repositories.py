"""All database reads and writes live here, so the UI never touches SQL."""
from datetime import date, timedelta

from sqlalchemy import select

from db.models import Favorite, HistoryEntry, PantryItem


def expiry_status(item: PantryItem, today: date | None = None) -> str:
    """'none' | 'expired' | 'soon' (0-3 days) | 'ok'."""
    today = today or date.today()
    if item.expiry_date is None:
        return "none"
    days = (item.expiry_date - today).days
    if days < 0:
        return "expired"
    return "soon" if days <= 3 else "ok"


class Store:
    def __init__(self, session_factory):
        self._sf = session_factory

    # ---------- pantry ----------
    def add_pantry_item(self, name: str, quantity: float | None = None,
                        unit: str = "", purchase_date: date | None = None,
                        expiry_date: date | None = None,
                        notes: str = "") -> PantryItem:
        name = name.strip()
        if not name:
            raise ValueError("Ingredient name is required.")
        if quantity is not None and quantity < 0:
            raise ValueError("Quantity cannot be negative.")
        if purchase_date and expiry_date and expiry_date < purchase_date:
            raise ValueError("The expiry date is before the purchase date.")
        item = PantryItem(name=name, quantity=quantity, unit=unit.strip(),
                          purchase_date=purchase_date, expiry_date=expiry_date,
                          notes=notes.strip())
        with self._sf() as session:
            session.add(item)
            session.commit()
        return item

    def list_pantry(self) -> list[PantryItem]:
        with self._sf() as session:
            return list(session.scalars(
                select(PantryItem).order_by(PantryItem.name)))

    def remove_pantry_item(self, item_id: int) -> bool:
        with self._sf() as session:
            item = session.get(PantryItem, item_id)
            if item is None:
                return False
            session.delete(item)
            session.commit()
            return True

    def expiring_soon(self, today: date | None = None,
                      days: int = 3) -> list[PantryItem]:
        """Expired items and items expiring within `days`, soonest first."""
        limit = (today or date.today()) + timedelta(days=days)
        with self._sf() as session:
            return list(session.scalars(
                select(PantryItem)
                .where(PantryItem.expiry_date.is_not(None),
                       PantryItem.expiry_date <= limit)
                .order_by(PantryItem.expiry_date)))

    # ---------- favorites ----------
    def save_favorite(self, recipe_id: str, recipe_name: str) -> None:
        with self._sf() as session:
            exists = session.scalar(
                select(Favorite).where(Favorite.recipe_id == recipe_id))
            if exists is None:
                session.add(Favorite(recipe_id=recipe_id, recipe_name=recipe_name))
                session.commit()

    def remove_favorite(self, recipe_id: str) -> bool:
        with self._sf() as session:
            fav = session.scalar(
                select(Favorite).where(Favorite.recipe_id == recipe_id))
            if fav is None:
                return False
            session.delete(fav)
            session.commit()
            return True

    def is_favorite(self, recipe_id: str) -> bool:
        with self._sf() as session:
            return session.scalar(
                select(Favorite.id).where(Favorite.recipe_id == recipe_id)
            ) is not None

    def set_rating(self, recipe_id: str, rating: int) -> bool:
        """rating 1-5, or 0 to clear. Returns False if not a favorite."""
        if not 0 <= rating <= 5:
            raise ValueError("Rating must be between 0 and 5.")
        with self._sf() as session:
            fav = session.scalar(
                select(Favorite).where(Favorite.recipe_id == recipe_id))
            if fav is None:
                return False
            fav.rating = rating or None
            session.commit()
            return True

    def list_favorites(self) -> list[Favorite]:
        with self._sf() as session:
            return list(session.scalars(
                select(Favorite).order_by(Favorite.saved_at.desc(), Favorite.id.desc())))

    # ---------- history ----------
    def add_history(self, recipe_id: str, recipe_name: str) -> None:
        with self._sf() as session:
            session.add(HistoryEntry(recipe_id=recipe_id, recipe_name=recipe_name))
            session.commit()

    def list_history(self, limit: int = 50) -> list[HistoryEntry]:
        with self._sf() as session:
            return list(session.scalars(
                select(HistoryEntry).order_by(HistoryEntry.id.desc()).limit(limit)))

    def recent_recipe_ids(self, limit: int = 5) -> list[str]:
        """Distinct recipe ids, newest first."""
        seen: list[str] = []
        for entry in self.list_history(limit=100):
            if entry.recipe_id not in seen:
                seen.append(entry.recipe_id)
            if len(seen) >= limit:
                break
        return seen

    def clear_history(self) -> None:
        with self._sf() as session:
            session.query(HistoryEntry).delete()
            session.commit()