"""Weekly meal planner and grocery list."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st  # noqa: E402

from app.components import ui  # noqa: E402
from core.knowledge.loader import load_seed_recipes  # noqa: E402
from core.recommender.ranker import Preferences  # noqa: E402
from core.safety.allergens import ALLERGEN_LABELS  # noqa: E402
from core.safety.diet_rules import DIETS  # noqa: E402
from core.safety.filter import (SafetyProfile, filter_ingredients,  # noqa: E402
                                safe_recipes)
from core.services.nutrition import estimate_nutrition  # noqa: E402
from core.services.planner import DAY_NAMES, grocery_list, plan_week  # noqa: E402
from db.session import get_store  # noqa: E402

DIET_CHOICES = [d for d in DIETS if d != "non_vegetarian"]


def parse_list(text: str) -> list[str]:
    return [p.strip() for p in text.replace("\n", ",").split(",") if p.strip()]


st.set_page_config(page_title="Meal planner · CraveCraft AI", page_icon="📅",
                   layout="wide")
st.markdown(ui.CSS, unsafe_allow_html=True)
store = get_store()

st.title("📅 Weekly meal planner")
st.caption("One main dish per day, plus one combined shopping list.")

c1, c2 = st.columns(2)
diet = c1.selectbox("Diet", DIET_CHOICES, format_func=lambda k: DIETS[k]["label"])
days = c2.slider("Number of days", 3, 7, 5)
allergens = st.multiselect("Allergies", list(ALLERGEN_LABELS),
                           format_func=lambda k: ALLERGEN_LABELS[k])
custom = st.text_input("Anything else you avoid?", placeholder="e.g. mushroom, brinjal")
saved_count = len(store.list_pantry())
use_saved = st.checkbox(f"Use my saved pantry ({saved_count} "
                        f"item{'s' if saved_count != 1 else ''})",
                        value=saved_count > 0, disabled=saved_count == 0)
extra = st.text_input("Other ingredients you have", placeholder="rice, onion, tomato")

if st.button("📅 Plan my week", type="primary"):
    try:
        profile = SafetyProfile(diet=diet, allergens=allergens,
                                custom_avoid=parse_list(custom))
    except ValueError as exc:
        st.error(f"Invalid food rules: {exc}")
        st.stop()
    items = parse_list(extra)
    if use_saved:
        items += [i.name for i in store.list_pantry()]
    allowed, _blocked = filter_ingredients(items, profile)
    prefs = Preferences(pantry=allowed,
                        use_first=[i.name for i in store.expiring_soon()])
    candidates = safe_recipes(load_seed_recipes(), profile)
    st.session_state["plan"] = plan_week(candidates, prefs, days)
    st.session_state["plan_wanted"] = days

plan = st.session_state.get("plan")
if plan is None:
    st.stop()
if not plan:
    st.error("No safe recipes found for those food rules.")
    st.stop()
if len(plan) < st.session_state["plan_wanted"]:
    st.info(f"Only {len(plan)} different safe dishes are available for your "
            "food rules, so the plan is shorter than requested.")

nutrition = [estimate_nutrition(m.recipe) for m in plan]
st.markdown("### 📅 Your week")
for day, match, n in zip(DAY_NAMES, plan, nutrition):
    r = match.recipe
    with st.container(border=True):
        a, b, c = st.columns([3, 2, 2])
        a.markdown(f"**{day}** · {ui.RECIPE_EMOJI.get(r.id, '🍛')} {r.name}")
        b.caption(f"{r.total_time_min} min · {r.difficulty.title()} · {r.region}")
        c.caption(f"~{n.kcal:.0f} kcal/serving · {len(match.missing)} to buy")
avg = sum(n.kcal for n in nutrition) / len(nutrition)
st.caption(f"Average about {avg:.0f} kcal per serving of the main dish "
           "(rough estimate, main dish only).")

items, staples = grocery_list(plan)
st.markdown("### 🛒 Shopping list")
if not items:
    st.success("Your pantry already covers every main ingredient.")
for item in items:
    st.checkbox(f"{item.label}  ·  _{', '.join(item.used_in)}_",
                key=f"buy_{item.name}_{item.unit}")
if staples:
    st.markdown("**Check your staples:** " + ", ".join(staples))
st.caption("Your saved pantry quantities are not tracked across days. If a dish "
           "uses an ingredient you have, it is treated as available.")

text = "\n".join([f"- {i.label}" for i in items] +
                 (["", "Staples to check: " + ", ".join(staples)] if staples else []))
st.download_button("⬇️ Download list (.txt)", text, file_name="shopping_list.txt")