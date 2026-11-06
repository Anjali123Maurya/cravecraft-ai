"""Favorites and history page."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st  # noqa: E402

from app.components import ui  # noqa: E402
from core.knowledge.loader import load_seed_recipes  # noqa: E402
from app.components.store import get_store

st.set_page_config(page_title="Favorites · CraveCraft AI", page_icon="❤️", layout="wide")
st.markdown(ui.CSS, unsafe_allow_html=True)
store = get_store()
recipes = {r.id: r for r in load_seed_recipes()}


def rate(recipe_id: str, key: str) -> None:
    store.set_rating(recipe_id, st.session_state[key])


st.title("❤️ Favorites & History")
tab_fav, tab_hist = st.tabs(["Favorites", "Recently viewed"])

with tab_fav:
    favorites = store.list_favorites()
    if not favorites:
        st.info("No favorites yet. Open a recipe on the home page and tap "
                "'Save to favorites'.")
    for fav in favorites:
        recipe = recipes.get(fav.recipe_id)
        with st.container(border=True):
            c1, c2, c3 = st.columns([3, 2, 1])
            c1.markdown(f"### {ui.RECIPE_EMOJI.get(fav.recipe_id, '🍛')} {fav.recipe_name}")
            key = f"rate_{fav.recipe_id}"
            c2.selectbox("Your rating", [0, 1, 2, 3, 4, 5], index=fav.rating or 0,
                         format_func=lambda r: "Not rated" if r == 0 else "⭐" * r,
                         key=key, on_change=rate, args=(fav.recipe_id, key))
            if c3.button("Remove", key=f"unfav_{fav.recipe_id}"):
                store.remove_favorite(fav.recipe_id)
                st.rerun()
            if recipe:
                with st.expander("Show recipe"):
                    st.write(recipe.description)
                    st.markdown(ui.steps(recipe.steps), unsafe_allow_html=True)

with tab_hist:
    history = store.list_history(limit=30)
    if not history:
        st.info("Nothing viewed yet.")
    for entry in history:
        st.write(f"{ui.RECIPE_EMOJI.get(entry.recipe_id, '🍛')} **{entry.recipe_name}** "
                 f"· {entry.created_at.strftime('%d %b, %H:%M')}")
    if history and st.button("Clear history"):
        store.clear_history()
        st.rerun()