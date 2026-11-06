"""My Pantry page: saved ingredients with expiry tracking."""
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st  # noqa: E402

from app.components import ui  # noqa: E402

from db.repositories import expiry_status  # noqa: E402
from app.components.store import get_store

UNITS = ["", "piece", "g", "kg", "ml", "l", "cup", "tbsp", "tsp", "packet"]
BADGE = {"expired": "🔴 Expired", "soon": "🟠 Use soon",
         "ok": "🟢 Fresh", "none": "⚪ No date"}

st.set_page_config(page_title="My Pantry · CraveCraft AI", page_icon="🧺", layout="wide")
st.markdown(ui.CSS, unsafe_allow_html=True)
store = get_store()

st.title("🧺 My Pantry")
st.caption("Saved ingredients can be added to any recipe search from the home page.")

urgent = store.expiring_soon()
if urgent:
    today = date.today()
    st.warning("**Use these first:** " + ", ".join(
        f"{i.name} ({'expired' if expiry_status(i, today) == 'expired' else 'expires ' + i.expiry_date.strftime('%d %b')})"
        for i in urgent))

with st.form("add_item", clear_on_submit=True):
    c1, c2, c3 = st.columns([3, 1, 1])
    name = c1.text_input("Ingredient")
    qty = c2.number_input("Quantity", min_value=0.0, value=0.0, step=1.0)
    unit = c3.selectbox("Unit", UNITS)
    c4, c5, c6 = st.columns(3)
    bought = c4.date_input("Purchase date", value=date.today())
    has_expiry = c5.checkbox("It has an expiry date")
    expiry = c6.date_input("Expiry date", value=date.today() + timedelta(days=7))
    notes = st.text_input("Storage notes (optional)", placeholder="e.g. keep in fridge")
    submitted = st.form_submit_button("➕ Add to pantry", type="primary")

if submitted:
    try:
        store.add_pantry_item(name, qty or None, unit, bought,
                              expiry if has_expiry else None, notes)
        st.success(f"Added {name.strip()}.")
    except ValueError as exc:
        st.error(str(exc))

st.markdown("### Saved ingredients")
today = date.today()
items = store.list_pantry()
if not items:
    st.info("Your pantry is empty. Add your first ingredient above.")
for item in items:
    c1, c2, c3, c4 = st.columns([3, 2, 2, 1])
    c1.markdown(f"**{item.name}**" + (f"  \n{item.notes}" if item.notes else ""))
    c2.write(f"{item.quantity:g} {item.unit}".strip() if item.quantity else "-")
    status = expiry_status(item, today)
    when = f" · {item.expiry_date.strftime('%d %b %Y')}" if item.expiry_date else ""
    c3.write(BADGE[status] + when)
    if c4.button("🗑️", key=f"rm_{item.id}", help="Remove"):
        store.remove_pantry_item(item.id)
        st.rerun()