"""Mini AI Pokédex Chatbot — Streamlit UI (run: streamlit run app.py)"""
import plotly.graph_objects as go
import streamlit as st

from src.data_loader import STAT_LABEL, STATS, load_data
from src.router_light import parse
from src.tools import Answer, execute, get_row

st.set_page_config(page_title="Mini AI Pokédex", page_icon="🔴", layout="centered")


@st.cache_data
def get_df():
    return load_data()


df = get_df()

EXAMPLES = [
    "Show info and weaknesses of Bulbasaur",
    "Top 5 fire-type Pokémon by Speed",
    "Which Pokémon are weak to water 4x?",
    "Compare Pikachu and Raichu",
    "Legendary Gen 3 Pokémon with the highest Sp. Attack, top 3",
]

# ---------------- Sidebar ----------------
with st.sidebar:
    st.header("⚙️ Settings")
    mode = st.radio("Mode", ["Option 1: Lightweight (rules + fuzzy)", "Option 2: Ollama (local LLM)"])
    use_llm = mode.startswith("Option 2")
    model = st.text_input("Ollama model name", "qwen2.5:7b", disabled=not use_llm)
    st.caption("all data comes from pokemon.csv")
    st.subheader("Example questions")
    for i, ex in enumerate(EXAMPLES):
        if st.button(ex, key=f"ex{i}"):
            st.session_state["pending"] = ex
    if st.button("🗑️ Clear chat"):
        st.session_state["messages"] = []


def radar_chart(names: list[str]) -> go.Figure:
    fig = go.Figure()
    labels = [STAT_LABEL[s] for s in STATS]
    for n in names:
        r = get_row(df, n)
        vals = [int(r[s]) for s in STATS]
        fig.add_trace(go.Scatterpolar(r=vals + vals[:1], theta=labels + labels[:1], fill="toself", name=n))
    fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 255])),
                      showlegend=len(names) > 1, height=380, margin=dict(l=40, r=40, t=30, b=30))
    return fig


def show(msg: dict, key: str):
    st.markdown(msg["text"])
    if msg.get("table") is not None:
        st.dataframe(msg["table"], hide_index=True)
    if msg.get("radar"):
        st.plotly_chart(radar_chart(msg["radar"]), key=f"radar_{key}")


def answer(question: str) -> Answer:
    note = ""
    if use_llm:
        try:
            from src.router_llm import narrate, parse_with_llm
            q = parse_with_llm(df, question, model)
            ans = execute(df, q)
            if q["intent"] != "help":
                ans.text = narrate(question, ans, model)
            return ans
        except Exception as e:  # Ollama not running / model not pulled -> fall back to Option 1
            note = f"> ⚠️ Could not reach Ollama ({e}) — answered with Lightweight mode instead.\n\n"
    ans = execute(df, parse(df, question))
    ans.text = note + ans.text
    return ans


# ---------------- Chat ----------------
st.title("🔴 Mini AI Pokédex")
st.caption("Ask in English or Thai: single-Pokémon info · rankings · weakness analysis")

if "messages" not in st.session_state:
    st.session_state["messages"] = [{"role": "assistant", "text": "Hi! I'm your Pokédex. Ask me about Gen 1–7 Pokémon.\n\n"
                                     "Click an example question in the sidebar, or type your own below."}]

for i, m in enumerate(st.session_state["messages"]):
    with st.chat_message(m["role"]):
        show(m, str(i))

prompt = st.chat_input("Ask anything about Pokémon...") or st.session_state.pop("pending", None)
if prompt:
    st.session_state["messages"].append({"role": "user", "text": prompt})
    with st.spinner("Searching the Pokédex..."):
        ans = answer(prompt)
    st.session_state["messages"].append(
        {"role": "assistant", "text": ans.text, "table": ans.table, "radar": ans.radar})
    st.rerun()
