"""Styling and small HTML builders for the CraveCraft UI.

Everything that comes from recipes or the AI goes through html.escape()
before it is placed into HTML.
"""
from html import escape

RECIPE_EMOJI = {
    "dal-tadka": "🍲", "aloo-matar": "🥔", "aloo-gobi": "🥦",
    "palak-paneer": "🥬", "chana-masala": "🥘", "rajma": "🫘",
    "bhindi-masala": "🌿", "jeera-rice": "🍚", "sambar": "🍜",
    "lemon-rice": "🍋", "poha": "🍛", "upma": "🥣", "gujarati-kadhi": "🥛",
    "baingan-bharta": "🍆", "paneer-bhurji": "🧀", "moong-dal-khichdi": "🫕",
        "dosa": "🥞", "podi-idli": "⚪", "pav-bhaji": "🍞", "veg-pulao": "🍚",
    "dhokla": "🟨", "matar-paneer": "🧈", "kadai-paneer": "🌶️",
    "aloo-paratha": "🫓", "veg-biryani": "🍛", "masoor-dal": "🥣",
    "methi-thepla": "🍃", "veg-korma": "🥥", "bisi-bele-bath": "🍲",
    "mixed-veg-sabzi": "🥕", "curd-rice": "🍙", "sabudana-khichdi": "🥜",
}

REGION_GRADIENT = {
    "North Indian": ("#F6A04D", "#E8742A"),
    "Punjabi": ("#F2B134", "#D9822B"),
    "South Indian": ("#7DB46C", "#3E7C47"),
    "Maharashtrian": ("#F08A5D", "#C8553D"),
    "Gujarati": ("#F7C948", "#E09F1F"),
}
DEFAULT_GRADIENT = ("#F6A04D", "#E8742A")

CSS = """
<style>
#MainMenu, footer {visibility: hidden;}
.block-container {padding-top: 2rem; max-width: 1150px;}
h1, h2, h3 {color: #7A1F2B !important;}
section[data-testid="stSidebar"] {border-right: 1px solid #F3D3B0;}

.hero {
  background: linear-gradient(120deg, #7A1F2B 0%, #C8553D 55%, #E8742A 100%);
  border-radius: 24px; padding: 28px 34px; color: #fff;
  box-shadow: 0 10px 28px rgba(122,31,43,.25); margin-bottom: 22px;
}
.hero .emoji-row {font-size: 1.9rem; letter-spacing: 8px; margin-bottom: 4px;}
.hero .brand {font-size: 2.5rem; font-weight: 800; margin: 0; color: #fff;}
.hero .brand span {color: #FFD37A;}
.hero .tag {font-size: 1.05rem; opacity: .95; margin-top: 4px;}

.how {display: flex; gap: 14px; flex-wrap: wrap; margin: 10px 0 6px;}
.how .tile {flex: 1; min-width: 210px; background: #fff; border-radius: 18px;
  padding: 18px; box-shadow: 0 4px 14px rgba(0,0,0,.06); text-align: center;}
.how .big {font-size: 2.2rem;}
.how .t {font-weight: 700; color: #7A1F2B; margin-top: 4px;}
.how .d {color: #6b5547; font-size: .92rem;}

.dish-card {background: #fff; border-radius: 20px; overflow: hidden;
  box-shadow: 0 6px 18px rgba(0,0,0,.08); border: 3px solid transparent;
  margin-bottom: 8px;}
.dish-card.selected {border-color: #E8742A;}
.dish-art {height: 100px; display: flex; align-items: center;
  justify-content: center; font-size: 3.2rem;}
.dish-body {padding: 12px 16px 14px;}
.dish-name {font-weight: 700; font-size: 1.05rem; color: #7A1F2B;}
.dish-meta {color: #6b5547; font-size: .85rem; margin: 2px 0 8px;}
.bar {background: #F3E3D0; height: 8px; border-radius: 99px; overflow: hidden;}
.bar > div {height: 100%; background: linear-gradient(90deg, #3E7C47, #7DB46C);}
.bar-label {font-size: .78rem; color: #3E7C47; margin-top: 4px; font-weight: 600;}

.banner {border-radius: 24px; padding: 26px 30px; color: #fff;
  display: flex; gap: 22px; align-items: center; margin: 8px 0 14px;
  box-shadow: 0 8px 22px rgba(0,0,0,.15);}
.banner .art {font-size: 4.6rem; line-height: 1;}
.banner .name {font-size: 2rem; font-weight: 800; margin: 0;}
.banner .desc {font-size: 1.02rem; margin-top: 6px; opacity: .96;}
.banner .src {margin-top: 10px; font-size: .8rem; opacity: .9;}

.stats {display: flex; gap: 12px; flex-wrap: wrap; margin: 6px 0 16px;}
.stat {flex: 1; min-width: 130px; background: #fff; border-radius: 16px;
  padding: 12px 14px; box-shadow: 0 3px 10px rgba(0,0,0,.06); text-align: center;}
.stat .v {font-size: 1.25rem; font-weight: 800; color: #7A1F2B;}
.stat .l {font-size: .78rem; color: #8a7466; text-transform: uppercase;
  letter-spacing: .05em;}

.chip {display: inline-block; padding: 5px 13px; border-radius: 999px;
  background: #FFE3C2; color: #5a3a1e; margin: 3px 4px 3px 0; font-size: .92rem;}
.buy-box {background: #FDEBE7; border: 2px dashed #E39A8E; border-radius: 16px;
  padding: 12px 16px; margin-top: 12px;}
.buy-box .h {font-weight: 700; color: #9B2C1F; margin-bottom: 4px;}
.chip.buy {background: #fff; color: #9B2C1F; border: 1px solid #E39A8E;}

.step {display: flex; gap: 14px; background: #fff; border-radius: 16px;
  padding: 13px 16px; margin-bottom: 10px; box-shadow: 0 3px 10px rgba(0,0,0,.06);}
.step .n {min-width: 34px; height: 34px; border-radius: 50%;
  background: linear-gradient(135deg, #F6A04D, #E8742A); color: #fff;
  font-weight: 800; display: flex; align-items: center; justify-content: center;}
.step .tx {padding-top: 4px; line-height: 1.45;}

.note {background: #fff; border-left: 5px solid #3E7C47; border-radius: 10px;
  padding: 9px 14px; margin-bottom: 8px; box-shadow: 0 2px 8px rgba(0,0,0,.05);}
.note.sub {border-left-color: #E8742A;}

div.stButton > button {border-radius: 999px; font-weight: 700; padding: .5rem 1.4rem;}
div.stButton > button[kind="primary"] {
  background: linear-gradient(90deg, #E8742A, #C8553D); border: none; color: #fff;}
</style>
"""


def _grad(region: str) -> str:
    a, b = REGION_GRADIENT.get(region, DEFAULT_GRADIENT)
    return f"linear-gradient(135deg, {a}, {b})"


def hero() -> str:
    return """
    <div class="hero">
      <div class="emoji-row">🍅 🌶️ 🥔 🧅 🍋 🫘</div>
      <p class="brand">Crave<span>Craft</span> AI</p>
      <div class="tag">Turn what's in your kitchen into a recipe you'll actually crave.</div>
    </div>"""


def how_it_works() -> str:
    tiles = [("🥕", "1. Tell me your ingredients", "Type what you have. I'll ignore anything your diet or allergies rule out."),
             ("😋", "2. Pick your craving", "Spicy, tangy, creamy... and how much time you have."),
             ("👩‍🍳", "3. Cook with confidence", "A tested recipe, tailored to you, with a clear shopping list.")]
    inner = "".join(f'<div class="tile"><div class="big">{e}</div>'
                    f'<div class="t">{t}</div><div class="d">{d}</div></div>'
                    for e, t, d in tiles)
    return f'<div class="how">{inner}</div>'


def dish_card(match, selected: bool) -> str:
    r = match.recipe
    emoji = RECIPE_EMOJI.get(r.id, "🍛")
    pct = int(match.coverage * 100)
    need = f"need {len(match.missing)} more" if match.missing else "nothing to buy"
    return f"""
    <div class="dish-card {'selected' if selected else ''}">
      <div class="dish-art" style="background:{_grad(r.region)}">{emoji}</div>
      <div class="dish-body">
        <div class="dish-name">{escape(r.name)}</div>
        <div class="dish-meta">{escape(r.region)} · {r.total_time_min} min · {escape(r.difficulty.title())}</div>
        <div class="bar"><div style="width:{pct}%"></div></div>
        <div class="bar-label">You have {pct}% · {need}</div>
      </div>
    </div>"""


def banner(recipe, used_llm: bool) -> str:
    emoji = RECIPE_EMOJI.get(recipe.id, "🍛")
    src = ("✨ Text tailored by the local AI" if used_llm else "📖 Recipe shown as written")
    return f"""
    <div class="banner" style="background:{_grad(recipe.region)}">
      <div class="art">{emoji}</div>
      <div>
        <p class="name">{escape(recipe.name)}</p>
        <div class="desc">{escape(recipe.description)}</div>
        <div class="src">{src} · ingredients and steps always come from a tested recipe</div>
      </div>
    </div>"""


def stats(recipe) -> str:
    items = [("⏱️", f"{recipe.total_time_min} min", "Total time"),
             ("👨‍🍳", recipe.difficulty.title(), "Difficulty"),
             ("🍽️", str(recipe.servings), "Serves"),
             ("🌶️", ", ".join(recipe.flavor_profile[:2]).title(), "Flavor")]
    inner = "".join(f'<div class="stat"><div class="v">{escape(e)} {escape(v)}</div>'
                    f'<div class="l">{l}</div></div>' for e, v, l in items)
    return f'<div class="stats">{inner}</div>'


def fmt_ingredient(ing) -> str:
    qty = f"{ing.quantity:g} " if ing.quantity else ""
    unit = f"{ing.unit} " if ing.unit else ""
    return escape(f"{qty}{unit}{ing.name}")


def chips(ingredients, buy: bool = False) -> str:
    cls = "chip buy" if buy else "chip"
    return "".join(f'<span class="{cls}">{fmt_ingredient(i)}</span>' for i in ingredients)


def buy_box(ingredients) -> str:
    return (f'<div class="buy-box"><div class="h">🛒 You need to buy</div>'
            f'{chips(ingredients, buy=True)}</div>')


def steps(step_list) -> str:
    return "".join(f'<div class="step"><div class="n">{i}</div>'
                   f'<div class="tx">{escape(s)}</div></div>'
                   for i, s in enumerate(step_list, 1))


def notes(lines, sub: bool = False) -> str:
    cls = "note sub" if sub else "note"
    return "".join(f'<div class="{cls}">{escape(line)}</div>' for line in lines)