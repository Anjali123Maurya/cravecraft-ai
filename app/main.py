"""CraveCraft AI: styled Streamlit page.

Run from the project root:
    streamlit run app/main.py
"""
import sys
from pathlib import Path

# Make `core`, `app` and `db` importable when Streamlit runs this file.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st  # noqa: E402

from app.components import ui  # noqa: E402
from core.ai.adapter import adapt_recipe  # noqa: E402
from core.ai.llm_client import LLMClient, LLMUnavailable  # noqa: E402
from core.config import get_settings  # noqa: E402
from core.knowledge.loader import load_seed_recipes  # noqa: E402
from core.recommender.ranker import Preferences, rank_recipes  # noqa: E402
from core.safety.allergens import ALLERGEN_LABELS  # noqa: E402
from core.safety.diet_rules import DIETS  # noqa: E402
from core.safety.filter import (SafetyProfile, filter_ingredients,  # noqa: E402
                                safe_recipes)
from db.session import get_store  # noqa: E402
from core.services.nutrition import estimate_nutrition  # noqa: E402

CRAVINGS = {
    "🌶️ Spicy": "spicy", "🍋 Tangy": "tangy", "🧈 Creamy": "creamy",
    "🍛 Savory": "savory", "🔥 Smoky": "smoky", "🥜 Crunchy": "crunchy",
    "🤗 Comforting": "comforting", "🥗 Fresh & light": "fresh",
}
TIME_OPTIONS = {"Any": None, "20 min": 20, "30 min": 30, "45 min": 45,
                "1 hour": 60, "90 min": 90}
# Vegetarian-family diets only: the recipe set has no meat dishes yet.
DIET_CHOICES = [d for d in DIETS if d != "non_vegetarian"]


class NoAI:
    """Stand-in used when the AI checkbox is off."""

    def generate_json(self, *args, **kwargs):
        raise LLMUnavailable("AI turned off by the user")


def parse_list(text: str) -> list[str]:
    parts = text.replace("\n", ",").split(",")
    return [p.strip() for p in parts if p.strip()]


st.set_page_config(page_title="CraveCraft AI", page_icon="🍛", layout="wide")
st.markdown(ui.CSS, unsafe_allow_html=True)
settings = get_settings()

# ---------------- Sidebar: food rules ----------------
with st.sidebar:
    st.markdown("### 🥗 Your food rules")
    default_diet = (settings.default_diet if settings.default_diet in DIET_CHOICES
                    else "vegetarian")
    diet = st.selectbox("Diet", DIET_CHOICES, index=DIET_CHOICES.index(default_diet),
                        format_func=lambda k: DIETS[k]["label"])
    allergens = st.multiselect("Allergies", list(ALLERGEN_LABELS),
                               format_func=lambda k: ALLERGEN_LABELS[k])
    custom = st.text_input("Anything else you avoid?", placeholder="e.g. mushroom, brinjal")
    st.caption("Extra items are matched by name only. Always check packaged "
               "food labels yourself.")
    st.divider()
    use_ai = st.checkbox("✨ Use the local AI to tailor the text", value=True,
                         help="Needs Ollama running. Turn off to see the plain recipe.")

# ---------------- Header and inputs ----------------
st.markdown(ui.hero(), unsafe_allow_html=True)

st.markdown("#### 🥕 What's in your kitchen?")
pantry_text = st.text_area("Ingredients", height=90, label_visibility="collapsed",
                           placeholder="potatoes, onion, tomato, paneer, capsicum ...")

saved_count = len(get_store().list_pantry())
include_saved = st.checkbox(
    f"➕ Also use my saved pantry ({saved_count} item{'s' if saved_count != 1 else ''})",
    value=saved_count > 0, disabled=saved_count == 0)

st.markdown("#### 😋 What are you craving?")
picked = st.pills("Cravings", list(CRAVINGS), selection_mode="multi",
                  label_visibility="collapsed")

time_label = st.selectbox("⏱️ Time available", list(TIME_OPTIONS))

if st.button("🍳  Find my recipe", type="primary"):
    items = parse_list(pantry_text)
    if include_saved:
        items += [i.name for i in get_store().list_pantry()]
    if not items:
        st.warning("Please type at least one ingredient.")
    else:
        try:
            profile = SafetyProfile(diet=diet, allergens=allergens,
                                    custom_avoid=parse_list(custom))
        except ValueError as exc:
            st.error(f"Invalid food rules: {exc}")
            st.stop()
        allowed, blocked = filter_ingredients(items, profile)
        store = get_store()
        prefs = Preferences(pantry=allowed,
                            cravings=[CRAVINGS[c] for c in (picked or [])],
                            max_total_minutes=TIME_OPTIONS[time_label],
                            recent_ids=store.recent_recipe_ids(),
                            use_first=[i.name for i in store.expiring_soon()])
        candidates = safe_recipes(load_seed_recipes(), profile)
        ranked = rank_recipes(candidates, prefs, top_n=3, min_coverage=0.25)
        if len(ranked) < 3:  # relax the rule so the user sees more choices
            ranked = rank_recipes(candidates, prefs, top_n=3, min_coverage=0.1)
        st.session_state.update(profile=profile, prefs=prefs, ranked=ranked,
                                blocked=blocked, adapted={}, searched=True,
                                chosen_id=ranked[0].recipe.id if ranked else None)

# ---------------- Results ----------------
if not st.session_state.get("searched"):
    st.markdown(ui.how_it_works(), unsafe_allow_html=True)
    st.stop()

ranked = st.session_state["ranked"]
profile = st.session_state["profile"]
prefs = st.session_state["prefs"]

for name, violations in st.session_state["blocked"]:
    rules = ", ".join(sorted({v.rule.split(":")[1] for v in violations}))
    st.info(f"Left out **{name}** because it conflicts with your rules ({rules}).")

if not ranked:
    st.error("No safe recipe matches those ingredients yet. Try adding more "
             "ingredients, or relax your filters.")
    st.stop()

st.markdown("### 🍽️ Best matches for you")
cols = st.columns(len(ranked))
for col, m in zip(cols, ranked):
    with col:
        selected = st.session_state["chosen_id"] == m.recipe.id
        st.markdown(ui.dish_card(m, selected), unsafe_allow_html=True)
        label = "✔ Selected" if selected else "View this recipe"
        if st.button(label, key=f"pick_{m.recipe.id}", use_container_width=True,
                     disabled=selected):
            st.session_state["chosen_id"] = m.recipe.id

chosen_id = st.session_state["chosen_id"]
match = next(m for m in ranked if m.recipe.id == chosen_id)

adapted_cache = st.session_state["adapted"]
if chosen_id not in adapted_cache:
    with st.spinner("Adapting the recipe to you (the first run can take a few "
                    "seconds while the model loads)..."):
        llm = LLMClient() if use_ai else NoAI()
        adapted_cache[chosen_id] = adapt_recipe(match, prefs, profile, llm=llm)
    get_store().add_history(chosen_id, match.recipe.name)
result = adapted_cache[chosen_id]
recipe = result.recipe

st.markdown(ui.banner(recipe, result.used_llm), unsafe_allow_html=True)

store = get_store()
fav_col, cook_col, _ = st.columns([1, 1, 2])
with fav_col:
    if store.is_favorite(recipe.id):
        st.success("❤️ Saved")
    elif st.button("🤍 Save to favorites", key=f"fav_{recipe.id}",
                   use_container_width=True):
        store.save_favorite(recipe.id, recipe.name)
        st.rerun()
with cook_col:
    if st.button("👩‍🍳 Start cooking", key=f"cook_{recipe.id}", type="primary",
                 use_container_width=True):
        st.session_state["cooking_recipe"] = recipe
        st.session_state.pop("cooking_id", None)
        st.switch_page("pages/3_Cooking.py")

if use_ai:
    for warning in result.warnings:
        st.warning(warning)
st.markdown(ui.stats(recipe), unsafe_allow_html=True)

left, right = st.columns([1, 1.25], gap="large")
with left:
    st.markdown("### 🧂 Ingredients")
    have = [i for i in recipe.ingredients if i.in_pantry]
    need = [i for i in recipe.ingredients if not i.in_pantry]
    st.markdown(ui.chips(have), unsafe_allow_html=True)
    if need:
        st.markdown(ui.buy_box(need), unsafe_allow_html=True)
with right:
    st.markdown("### 👩‍🍳 Steps")
    st.markdown(ui.steps(recipe.steps), unsafe_allow_html=True)

st.markdown("### 🥗 Nutrition (estimate per serving)")
st.markdown(ui.nutrition_box(estimate_nutrition(recipe)), unsafe_allow_html=True)
with st.expander("What was counted?"):
    n = estimate_nutrition(recipe)
    st.write(f"Matched {len(n.matched)} ingredients ({n.coverage:.0%}).")
    if n.unmatched:
        st.write("Not found: " + ", ".join(n.unmatched))
        
if recipe.tips:
    st.markdown("### 💡 Tips")
    st.markdown(ui.notes(recipe.tips), unsafe_allow_html=True)
if recipe.substitutions:
    st.markdown("### 🔄 Substitutions")
    st.markdown(ui.notes(recipe.substitutions, sub=True), unsafe_allow_html=True)