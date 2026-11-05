"""Cooking mode: step-by-step guide with timers and questions."""
import sys
import time
from html import escape
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st  # noqa: E402

from app.components import ui  # noqa: E402
from core.ai.llm_client import LLMClient, LLMUnavailable  # noqa: E402
from core.safety.filter import SafetyProfile  # noqa: E402
from core.services.cooking import (answer_question, step_ingredients,  # noqa: E402
                                   step_timers)
from db.session import get_store  # noqa: E402

SOURCE_LABEL = {"tips": "💡 Quick kitchen tip", "ai": "✨ Local AI (can be wrong)",
                "none": ""}


class NoAI:
    def generate_json(self, *args, **kwargs):
        raise LLMUnavailable("AI turned off by the user")


st.set_page_config(page_title="Cooking mode · CraveCraft AI", page_icon="👩‍🍳",
                   layout="wide")
st.markdown(ui.CSS, unsafe_allow_html=True)
st.markdown("""<style>
.bigstep{display:flex;gap:18px;background:#fff;border-radius:22px;padding:26px 28px;
 box-shadow:0 8px 22px rgba(0,0,0,.10);border-left:8px solid #E8742A;margin:10px 0 14px;}
.bigstep .n{min-width:54px;height:54px;border-radius:50%;
 background:linear-gradient(135deg,#F6A04D,#E8742A);color:#fff;font-weight:800;
 font-size:1.5rem;display:flex;align-items:center;justify-content:center;}
.bigstep .tx{font-size:1.3rem;line-height:1.5;padding-top:6px;}
</style>""", unsafe_allow_html=True)

store = get_store()
recipe = st.session_state.get("cooking_recipe")
if recipe is None:
    st.title("👩‍🍳 Cooking mode")
    st.info("Choose a recipe on the home page first, then press **Start cooking**.")
    st.page_link("main.py", label="Go to the home page", icon="🏠")
    st.stop()

profile = st.session_state.get("profile") or SafetyProfile()

with st.sidebar:
    use_ai = st.checkbox("✨ Use the local AI for questions", value=True,
                         help="Needs Ollama running. Common kitchen problems are "
                              "answered without it.")


def reset() -> None:
    st.session_state.update(cook_step=0, timers={}, chat=[], cook_done=False)


def go(delta: int) -> None:
    st.session_state["cook_step"] += delta


def finish() -> None:
    st.session_state["cook_done"] = True
    st.session_state["just_finished"] = True


def start_timer(key: str, label: str, seconds: int) -> None:
    st.session_state["timers"][key] = {"label": label, "end": time.time() + seconds}


if st.session_state.get("cooking_id") != recipe.id:
    reset()
    st.session_state["cooking_id"] = recipe.id

emoji = ui.RECIPE_EMOJI.get(recipe.id, "🍛")
st.title(f"{emoji} {recipe.name}")

# ---------------- finished ----------------
if st.session_state["cook_done"]:
    if st.session_state.pop("just_finished", False):
        st.balloons()
    st.success(f"🎉 You made {recipe.name}! Enjoy your meal.")
    rating = st.select_slider("How did it turn out?", [1, 2, 3, 4, 5], value=4,
                              format_func=lambda r: "⭐" * r)
    c1, c2 = st.columns(2)
    if c1.button("❤️ Save with this rating", type="primary", use_container_width=True):
        store.save_favorite(recipe.id, recipe.name)
        store.set_rating(recipe.id, rating)
        st.success("Saved to your favorites.")
    if c2.button("🔁 Cook again", use_container_width=True):
        reset()
        st.rerun()
    st.stop()

# ---------------- step view ----------------
total = len(recipe.steps)
step = st.session_state["cook_step"]
st.progress((step + 1) / total, text=f"Step {step + 1} of {total}")

left, right = st.columns([1.5, 1], gap="large")

with left:
    st.markdown(f'<div class="bigstep"><div class="n">{step + 1}</div>'
                f'<div class="tx">{escape(recipe.steps[step])}</div></div>',
                unsafe_allow_html=True)

    n1, n2, _ = st.columns([1, 1, 1])
    n1.button("⬅ Previous", on_click=go, args=(-1,), disabled=step == 0,
              use_container_width=True)
    if step < total - 1:
        n2.button("Next ➡", on_click=go, args=(1,), type="primary",
                  use_container_width=True)
    else:
        n2.button("🎉 Finish cooking", on_click=finish, type="primary",
                  use_container_width=True)

    st.markdown("#### ⏱️ Timers")
    found = step_timers(recipe.steps[step])
    if found:
        for col, (label, secs) in zip(st.columns(len(found)), found):
            col.button(f"Start {label} timer", key=f"t_{step}_{secs}",
                       on_click=start_timer,
                       args=(f"{step}-{secs}", f"Step {step + 1}: {label}", secs),
                       use_container_width=True)
    with st.expander("Custom timer"):
        mins = st.number_input("Minutes", min_value=1, max_value=180, value=5,
                               key="custom_min")
        st.button("Start custom timer", key="custom_start", on_click=start_timer,
                  args=(f"custom-{time.time()}", f"Custom: {int(mins)} min",
                        int(mins) * 60))

    def timer_panel() -> None:
        timers = st.session_state["timers"]
        if not timers:
            st.caption("No timers running.")
            return
        now = time.time()
        for key, timer in list(timers.items()):
            remaining = int(timer["end"] - now)
            c1, c2 = st.columns([4, 1])
            if remaining > 0:
                c1.markdown(f"⏳ **{timer['label']}**: {remaining // 60:02d}:"
                            f"{remaining % 60:02d} left")
            else:
                c1.success(f"⏰ {timer['label']}: time's up!")
            if c2.button("✖", key=f"cancel_{key}", help="Remove this timer"):
                timers.pop(key, None)
                st.rerun(scope="fragment")

    # Refresh every second only while at least one timer exists.
    st.fragment(run_every=1 if st.session_state["timers"] else None)(timer_panel)()

with right:
    st.markdown("#### 🧂 Using in this step")
    used = step_ingredients(recipe, step)
    if used:
        st.markdown(ui.chips(used), unsafe_allow_html=True)
        st.caption("Matched by name, so it may miss an ingredient.")
    else:
        st.caption("No listed ingredient is named in this step.")

    if recipe.tips:
        with st.expander("💡 Tips for this dish"):
            st.markdown(ui.notes(recipe.tips), unsafe_allow_html=True)

    st.markdown("#### 💬 Ask about this step")
    with st.form("ask_form", clear_on_submit=True):
        question = st.text_input("Your question",
                                 placeholder="My gravy is too thick. What should I do?")
        asked = st.form_submit_button("Ask")
    if asked and question.strip():
        with st.spinner("Thinking..."):
            reply = answer_question(question, recipe, step, profile,
                                    llm=LLMClient() if use_ai else NoAI())
        st.session_state["chat"].insert(0, (question.strip(), reply))

    for q, reply in st.session_state["chat"][:4]:
        st.markdown(f"**You:** {q}")
        st.write(reply.text)
        if SOURCE_LABEL[reply.source]:
            st.caption(SOURCE_LABEL[reply.source])