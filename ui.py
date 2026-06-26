import streamlit as st
import websocket
import json

WS_URL = "ws://localhost:8000/api/chat/ws/chat"

st.set_page_config(page_title="RAG Chatbot", layout="centered")
st.title("RAG Chatbot")
st.caption("Ask questions from your AI/ML books")

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("sources"):
            with st.expander("Sources"):
                for s in msg["sources"]:
                    st.markdown(f"**{s['source']}** — Page {s['page']} (score: {s['score']})")
                    st.caption(s["preview"])

query = st.chat_input("Ask something...")

if query:
    st.session_state.messages.append({"role": "user", "content": query})
    with st.chat_message("user"):
        st.markdown(query)

    with st.chat_message("assistant"):
        placeholder = st.empty()
        full_response = ""
        sources = []

        try:
            ws = websocket.WebSocket()
            ws.connect(WS_URL)
            ws.send(json.dumps({"query": query, "topk": 5}))

            while True:
                raw = ws.recv()

                if raw.startswith("__DONE__:"):
                    payload = json.loads(raw[len("__DONE__:"):])
                    sources = payload.get("sources", [])
                    if payload.get("error"):
                        st.error(f"Error: {payload['error']}")
                    break

                full_response += raw
                placeholder.markdown(full_response + "▌")

            ws.close()

        except Exception as e:
            st.error(f"Connection error: {e}")

        placeholder.markdown(full_response)

        if sources:
            with st.expander("Sources"):
                for s in sources:
                    st.markdown(f"**{s['source']}** — Page {s['page']} (score: {s['score']})")
                    st.caption(s["preview"])

        if full_response:
            st.session_state.messages.append({
                "role": "assistant",
                "content": full_response,
                "sources": sources
            })