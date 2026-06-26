import streamlit as st
import websocket
import json
import requests

API_BASE = "https://dangling-unsettled-book.ngrok-free.app"
WS_URL = "wss://dangling-unsettled-book.ngrok-free.app/api/chat/ws/chat"

st.set_page_config(page_title="RAG Chatbot", layout="centered", page_icon="📚")

st.markdown("""
<style>
    /* hide default streamlit header/footer */
    #MainMenu, footer { visibility: hidden; }

    /* auth card */
    .auth-card {
        background: #1e1e2e;
        border: 1px solid #313244;
        border-radius: 12px;
        padding: 2rem 2.5rem;
        max-width: 420px;
        margin: 4rem auto 0;
    }
    .auth-title {
        font-size: 1.5rem;
        font-weight: 700;
        color: #cdd6f4;
        margin-bottom: 0.25rem;
    }
    .auth-sub {
        font-size: 0.85rem;
        color: #6c7086;
        margin-bottom: 1.5rem;
    }
    .error-msg {
        background: #2a1a1a;
        border-left: 3px solid #f38ba8;
        padding: 0.5rem 0.75rem;
        border-radius: 4px;
        color: #f38ba8;
        font-size: 0.85rem;
        margin-top: 0.5rem;
    }
    .success-msg {
        background: #1a2a1a;
        border-left: 3px solid #a6e3a1;
        padding: 0.5rem 0.75rem;
        border-radius: 4px;
        color: #a6e3a1;
        font-size: 0.85rem;
        margin-top: 0.5rem;
    }

    /* top bar */
    .topbar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 0.5rem 0 1rem;
        border-bottom: 1px solid #313244;
        margin-bottom: 1rem;
    }
    .topbar-title {
        font-size: 1.1rem;
        font-weight: 600;
        color: #cdd6f4;
    }
    .topbar-user {
        font-size: 0.8rem;
        color: #6c7086;
    }

    /* source chip */
    .source-chip {
        display: inline-block;
        background: #181825;
        border: 1px solid #313244;
        border-radius: 6px;
        padding: 0.2rem 0.5rem;
        font-size: 0.75rem;
        color: #89b4fa;
        margin: 2px;
    }
</style>
""", unsafe_allow_html=True)

for key, val in {
    "token": None,
    "username": None,
    "messages": [],
    "auth_tab": "login",
    "show_history": False,
}.items():
    if key not in st.session_state:
        st.session_state[key] = val


def do_register(username, password):
    try:
        r = requests.post(f"{API_BASE}/auth/register",
                          json={"username": username, "password": password},
                          headers = {"ngrok-skip-browser-warning": "true"})
        return r.status_code == 201, r.json()
    except Exception as e:
        return False, {"detail": str(e)}


def do_login(username, password):
    try:
        r = requests.post(f"{API_BASE}/auth/login",
                          data={"username": username, "password": password},
                          headers = {"ngrok-skip-browser-warning": "true"})
        if r.status_code == 200:
            data = r.json()
            return True, data["access_token"]
        return False, r.json().get("detail", "Login failed")
    except Exception as e:
        return False, str(e)


def do_fetch_history(token):
    try:
        r = requests.get(f"{API_BASE}/history/",
                         headers={"Authorization": f"Bearer {token}","ngrok-skip-browser-warning": "true"})
        if r.status_code == 200:
            return r.json().get("history", [])
    except:
        pass
    return []


def do_clear_history(token):
    try:
        requests.delete(f"{API_BASE}/history/",
                        headers={"Authorization": f"Bearer {token}","ngrok-skip-browser-warning": "true"})
    except:
        pass

if not st.session_state.token:
    st.markdown('<div class="auth-card">', unsafe_allow_html=True)
    st.markdown('<div class="auth-title">📚 RAG Chatbot</div>', unsafe_allow_html=True)
    st.markdown('<div class="auth-sub">Ask questions from your AI/ML books</div>', unsafe_allow_html=True)

    tab_login, tab_register = st.tabs(["Login", "Register"])

    with tab_login:
        username = st.text_input("Username", key="login_user", placeholder="your username")
        password = st.text_input("Password", type="password", key="login_pass", placeholder="••••••••")
        if st.button("Login", use_container_width=True, type="primary"):
            if username and password:
                ok, result = do_login(username, password)
                if ok:
                    st.session_state.token = result
                    st.session_state.username = username
                    st.session_state.messages = []
                    st.rerun()
                else:
                    st.markdown(f'<div class="error-msg">{result}</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="error-msg">Please fill in both fields.</div>', unsafe_allow_html=True)

    with tab_register:
        new_user = st.text_input("Username", key="reg_user", placeholder="choose a username")
        new_pass = st.text_input("Password", type="password", key="reg_pass", placeholder="••••••••")
        if st.button("Create account", use_container_width=True, type="primary"):
            if new_user and new_pass:
                ok, result = do_register(new_user, new_pass)
                if ok:
                    st.markdown('<div class="success-msg">Account created! Switch to Login.</div>',
                                unsafe_allow_html=True)
                else:
                    st.markdown(f'<div class="error-msg">{result.get("detail", "Error")}</div>',
                                unsafe_allow_html=True)
            else:
                st.markdown('<div class="error-msg">Please fill in both fields.</div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)
    st.stop()


col_title, col_hist, col_logout = st.columns([4, 1.2, 1])
with col_title:
    st.markdown(f"**📚 RAG Chatbot** &nbsp;·&nbsp; <span style='color:#6c7086;font-size:0.8rem'>{st.session_state.username}</span>",
                unsafe_allow_html=True)
with col_hist:
    if st.button("📋 History", use_container_width=True):
        st.session_state.show_history = not st.session_state.show_history
with col_logout:
    if st.button("Logout", use_container_width=True):
        for k in ["token", "username", "messages", "show_history"]:
            st.session_state[k] = None if k == "token" else ([] if k == "messages" else False)
        st.rerun()

st.divider()

if st.session_state.show_history:
    with st.expander("📋 Your past conversations", expanded=True):
        history = do_fetch_history(st.session_state.token)
        if not history:
            st.caption("No history yet.")
        else:
            col_h, col_clr = st.columns([5, 1])
            with col_clr:
                if st.button("🗑 Clear", key="clear_hist"):
                    do_clear_history(st.session_state.token)
                    st.rerun()
            for item in history:
                ts = item.get("timestamp", "")[:16].replace("T", " ")
                st.markdown(f"**Q:** {item['query']}")
                st.markdown(f"**A:** {item['answer'][:300]}{'...' if len(item['answer']) > 300 else ''}")
                st.caption(ts)
                st.divider()

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("sources"):
            with st.expander("Sources"):
                for s in msg["sources"]:
                    st.markdown(f"**{s['source']}** — Page {s['page']} (score: {s['score']})")
                    st.caption(s["preview"])

query = st.chat_input("Ask something from the books...")

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
            ws.connect(f"{WS_URL}?token={st.session_state.token}")
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