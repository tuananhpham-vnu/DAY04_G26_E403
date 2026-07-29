from __future__ import annotations

import json
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import streamlit as st

# ── project imports ────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from env_loader import load_lab_env
from providers import make_provider
from tools import load_tool_declarations, to_openai_tools
from versioning import build_artifact_version, artifact_version_dict
from chat import run_model_tool_loop, safe_slug, now_iso, write_transcript

ARTIFACTS_DIR = ROOT / "artifacts"
RUNS_DIR = ROOT / "runs"
TRANSCRIPTS_DIR = ROOT / "transcripts"
load_lab_env(ROOT)

try:
    from streamlit.runtime.scriptrunner import get_script_run_ctx
except ImportError:
    try:
        from streamlit.scriptrunner import get_script_run_ctx
    except ImportError:
        get_script_run_ctx = lambda: None

MAX_CONCURRENT_USERS = 8

if "_GLOBAL_ACTIVE_SESSIONS" not in globals():
    _GLOBAL_ACTIVE_SESSIONS: dict[str, float] = {}
    _GLOBAL_SESSIONS_LOCK = threading.Lock()

def check_and_register_session(max_users: int = 8) -> int:
    ctx = get_script_run_ctx()
    session_id = ctx.session_id if ctx else str(id(st.session_state))
    now = time.time()
    
    with _GLOBAL_SESSIONS_LOCK:
        # Clean up sessions inactive for more than 5 minutes (300 seconds)
        stale_sids = [sid for sid, last_seen in _GLOBAL_ACTIVE_SESSIONS.items() if now - last_seen > 300]
        for sid in stale_sids:
            del _GLOBAL_ACTIVE_SESSIONS[sid]
            
        if session_id not in _GLOBAL_ACTIVE_SESSIONS:
            if len(_GLOBAL_ACTIVE_SESSIONS) >= max_users:
                st.error(f"⛔ **Hệ thống đã đạt giới hạn tối đa {max_users} người dùng truy cập cùng lúc.**")
                st.info(f"👥 Đang có {len(_GLOBAL_ACTIVE_SESSIONS)}/{max_users} phiên làm việc. Vui lòng quay lại sau ít phút.")
                st.stop()
        
        _GLOBAL_ACTIVE_SESSIONS[session_id] = now
        return len(_GLOBAL_ACTIVE_SESSIONS)

# ═══════════════════════════════════════════════════════════════════════
#  PAGE CONFIG
# ═══════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="Research Agent · G26",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="expanded",
)

current_active_users = check_and_register_session(MAX_CONCURRENT_USERS)



# ═══════════════════════════════════════════════════════════════════════
#  GLOBAL CSS
# ═══════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
/* ── Google Font ─────────────────────────────────── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500;600&display=swap');

/* ── Root ────────────────────────────────────────── */
html, body, [data-testid="stAppViewContainer"],
[data-testid="stApp"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
    color: #f1f5f9 !important;
}

/* Remove default padding */
.block-container { padding-top: 1.5rem !important; }

/* ── Force ALL text light ────────────────────────── */
p, span, div, label, h1, h2, h3, h4, h5, h6,
.stMarkdown, .stText, .stCaption,
[data-testid="stMarkdownContainer"],
[data-testid="stCaptionContainer"] {
    color: #e2e8f0 !important;
}

/* Sidebar everything light */
section[data-testid="stSidebar"] {
    background: linear-gradient(195deg, #0c1222 0%, #101828 50%, #0a0f1d 100%) !important;
    border-right: 1px solid rgba(99,102,241,0.12) !important;
}
section[data-testid="stSidebar"] > div:first-child {
    padding-top: 1.2rem;
}
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] span,
section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] div {
    color: #cbd5e1 !important;
}
section[data-testid="stSidebar"] .stSelectbox label,
section[data-testid="stSidebar"] .stTextInput label,
section[data-testid="stSidebar"] .stSlider label,
section[data-testid="stSidebar"] .stNumberInput label {
    color: #94a3b8 !important;
    font-weight: 600 !important;
    font-size: .85rem !important;
}

/* ── Input fields ────────────────────────────────── */
input, textarea, select,
[data-baseweb="input"] input,
[data-baseweb="select"] div {
    color: #f1f5f9 !important;
}

/* ── Chat input ──────────────────────────────────── */
[data-testid="stChatInput"] textarea {
    font-family: 'Inter', sans-serif !important;
    font-size: 0.92rem !important;
    color: #f1f5f9 !important;
}

/* ── Chat messages ───────────────────────────────── */
[data-testid="stChatMessage"] p,
[data-testid="stChatMessage"] span,
[data-testid="stChatMessage"] div {
    color: #e2e8f0 !important;
}

/* ── Tabs ────────────────────────────────────────── */
button[data-baseweb="tab"] {
    font-family: 'Inter', sans-serif !important;
    font-weight: 600 !important;
    font-size: 0.88rem !important;
    color: #94a3b8 !important;
}
button[data-baseweb="tab"][aria-selected="true"] {
    color: #818cf8 !important;
}

/* ── Expander ────────────────────────────────────── */
details summary [data-testid="stExpanderToggleIcon"],
details summary [data-testid="stExpanderToggleIcon"] *,
details summary .material-symbols-rounded,
details summary .material-icons,
details summary svg {
    display: none !important;
    font-size: 0 !important;
    width: 0 !important;
    height: 0 !important;
    visibility: hidden !important;
    opacity: 0 !important;
}

details summary [data-testid="stMarkdownContainer"] p,
details summary [data-testid="stMarkdownContainer"] span {
    font-family: 'Inter', sans-serif !important;
    font-weight: 500 !important;
    color: #cbd5e1 !important;
}

/* ── Selectbox / dropdown ────────────────────────── */
[data-baseweb="select"] span,
[data-baseweb="select"] div {
    color: #e2e8f0 !important;
}

/* ── Slider value ────────────────────────────────── */
[data-testid="stThumbValue"],
[data-testid="stTickBarMin"],
[data-testid="stTickBarMax"] {
    color: #94a3b8 !important;
}

/* ── Info/Warning/Error boxes ────────────────────── */
[data-testid="stAlert"] p {
    color: #e2e8f0 !important;
}

/* ── Footer ──────────────────────────────────────── */
.stBottom, footer { color: #64748b !important; }

</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════════════════════════

def _load_json_dir(directory: Path, pattern: str = "*.json") -> list[dict]:
    out = []
    if directory.exists():
        for f in sorted(directory.glob(pattern), reverse=True):
            try:
                d = json.loads(f.read_text(encoding="utf-8"))
                d["_filename"] = f.name
                out.append(d)
            except Exception:
                pass
    return out


def _badge(text: str, color: str) -> str:
    bg = {"green": "rgba(34,197,94,.12)", "red": "rgba(239,68,68,.12)",
          "amber": "rgba(234,179,8,.12)", "blue": "rgba(99,102,241,.12)",
          "teal": "rgba(20,184,166,.12)"}
    fg = {"green": "#4ade80", "red": "#f87171", "amber": "#facc15",
          "blue": "#818cf8", "teal": "#2dd4bf"}
    bd = {"green": "rgba(34,197,94,.25)", "red": "rgba(239,68,68,.25)",
          "amber": "rgba(234,179,8,.25)", "blue": "rgba(99,102,241,.25)",
          "teal": "rgba(20,184,166,.25)"}
    return (
        f'<span style="display:inline-block;padding:2px 10px;border-radius:6px;'
        f'font-size:.76rem;font-weight:600;letter-spacing:.02em;'
        f'background:{bg[color]};color:{fg[color]};border:1px solid {bd[color]}">'
        f'{text}</span>'
    )


def _metric_html(value: str, label: str, icon: str = "") -> str:
    return f"""
    <div style="background:rgba(255,255,255,.03);border:1px solid rgba(255,255,255,.07);
                border-radius:12px;padding:1.1rem .8rem;text-align:center;">
        <div style="font-size:.85rem;margin-bottom:.25rem">{icon}</div>
        <div style="font-size:1.55rem;font-weight:800;
                    background:linear-gradient(135deg,#818cf8,#38bdf8);
                    -webkit-background-clip:text;-webkit-text-fill-color:transparent">
            {value}
        </div>
        <div style="font-size:.72rem;color:#64748b;text-transform:uppercase;
                    letter-spacing:.06em;margin-top:.25rem;font-weight:500">
            {label}
        </div>
    </div>"""


# ═══════════════════════════════════════════════════════════════════════
#  SIDEBAR
# ═══════════════════════════════════════════════════════════════════════
with st.sidebar:
    # Logo / title
    st.markdown(f"""
    <div style="text-align:center;padding:.6rem 0 1.2rem">
        <div style="font-size:2.2rem;margin-bottom:.15rem">🧪</div>
        <div style="font-size:1.1rem;font-weight:800;
                    background:linear-gradient(135deg,#c7d2fe,#818cf8);
                    -webkit-background-clip:text;-webkit-text-fill-color:transparent">
            Research Agent
        </div>
        <div style="font-size:.72rem;color:#64748b;font-weight:500;margin-top:.1rem;margin-bottom:.5rem">
            Group 26 · E403
        </div>
        <div>
            {_badge(f"👥 Active: {current_active_users}/{MAX_CONCURRENT_USERS}", "teal")}
        </div>
    </div>""", unsafe_allow_html=True)

    st.text_input("🔌 Provider", value="gemini", disabled=True)
    provider_name = "gemini"
    version_label = st.text_input("🏷️ Version", value="v3")
    model_override = st.text_input("🤖 Model (optional)", value="", placeholder="default")
    max_tool_rounds = st.slider("🔄 Max Tool Rounds", 1, 10, 4)
    history_window = st.slider("📚 History Window", 0, 20, 5)

    st.markdown("---")

    # Artifact version card
    try:
        av = build_artifact_version(version_label, ARTIFACTS_DIR / "system_prompt.md", ARTIFACTS_DIR / "tools.yaml")
        st.markdown(f"""
        <div style="background:rgba(99,102,241,.06);border:1px solid rgba(99,102,241,.15);
                    border-radius:10px;padding:.85rem 1rem;margin-top:.3rem">
            <div style="font-size:.68rem;color:#64748b;text-transform:uppercase;
                        letter-spacing:.06em;font-weight:600;margin-bottom:.45rem">
                📋 Artifact Version
            </div>
            <div style="font-family:'JetBrains Mono',monospace;font-size:.78rem;
                        color:#a5b4fc;font-weight:600;word-break:break-all">
                {av.artifact_version}
            </div>
            <div style="font-family:'JetBrains Mono',monospace;font-size:.66rem;
                        color:#475569;margin-top:.35rem;line-height:1.5">
                prompt &nbsp;{av.prompt_hash[:16]}…<br>
                tools &nbsp;&nbsp;{av.tools_hash[:16]}…
            </div>
        </div>""", unsafe_allow_html=True)
    except Exception:
        st.caption("⚠️ Cannot read artifact files.")

    st.markdown("<br>", unsafe_allow_html=True)

    if st.button("🔄 Refresh / Clear Chat", use_container_width=True, type="secondary"):
        for k in ("messages", "tool_traces", "transcript", "turn_index"):
            st.session_state.pop(k, None)
        st.rerun()


# ═══════════════════════════════════════════════════════════════════════
#  SESSION STATE
# ═══════════════════════════════════════════════════════════════════════
for key, default in [("messages", []), ("tool_traces", []), ("transcript", None), ("turn_index", 0)]:
    if key not in st.session_state:
        st.session_state[key] = default


# ═══════════════════════════════════════════════════════════════════════
#  HERO
# ═══════════════════════════════════════════════════════════════════════
st.markdown("""
<div style="background:linear-gradient(135deg,#1e1b4b 0%,#312e81 35%,#1e3a5f 70%,#0f172a 100%);
            border-radius:16px;padding:1.8rem 2.2rem;margin-bottom:1.2rem;
            border:1px solid rgba(99,102,241,.18);position:relative;overflow:hidden">
    <div style="position:absolute;top:-60%;right:-15%;width:350px;height:350px;
                background:radial-gradient(circle,rgba(99,102,241,.12) 0%,transparent 70%);
                border-radius:50%"></div>
    <div style="position:absolute;bottom:-40%;left:10%;width:250px;height:250px;
                background:radial-gradient(circle,rgba(56,189,248,.08) 0%,transparent 70%);
                border-radius:50%"></div>
    <div style="font-size:1.65rem;font-weight:900;position:relative;z-index:1;
                background:linear-gradient(135deg,#e0e7ff 0%,#a5b4fc 50%,#818cf8 100%);
                -webkit-background-clip:text;-webkit-text-fill-color:transparent">
        🧪 Research Agent
    </div>
    <div style="color:#94a3b8;font-size:.88rem;font-weight:400;position:relative;
                z-index:1;margin-top:.3rem;line-height:1.5">
        AI research assistant · Live tool execution · Full trace visibility · Evidence-driven optimization
    </div>
</div>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════
#  TABS
# ═══════════════════════════════════════════════════════════════════════
tab_chat, tab_runs, tab_transcripts = st.tabs(["💬 Live Chat", "📊 Run Logs", "📝 Transcripts"])


# ─── TAB: LIVE CHAT ───────────────────────────────────────────────────
with tab_chat:
    col_chat, col_trace = st.columns([5, 3], gap="large")

    # ── Chat column ──
    with col_chat:
        chat_hdr_col1, chat_hdr_col2 = st.columns([3, 1])
        with chat_hdr_col2:
            if st.button("🔄 Refresh Chat", key="btn_refresh_chat", use_container_width=True, type="secondary"):
                for k in ("messages", "tool_traces", "transcript", "turn_index"):
                    st.session_state.pop(k, None)
                st.rerun()

        # Render history using native chat elements
        for msg in st.session_state.messages:
            avatar = "👤" if msg["role"] == "user" else "🤖"
            with st.chat_message(msg["role"], avatar=avatar):
                st.markdown(msg["content"])

        # Input
        user_input = st.chat_input("Ask the research agent anything …")

        # Footer below chat input
        st.markdown("""
        <div style="text-align:center;padding:1rem 0 .3rem;color:#334155;font-size:.72rem;
                    border-top:1px solid rgba(255,255,255,.04);margin-top:1.5rem">
            Research Agent · Day 04 Lab v2 · <strong>Group 26 · E403</strong> &nbsp;|&nbsp; Built with Streamlit
        </div>
        """, unsafe_allow_html=True)

        if user_input:
            st.session_state.messages.append({"role": "user", "content": user_input})
            st.session_state.turn_index += 1

            with st.chat_message("user", avatar="👤"):
                st.markdown(user_input)

            with st.chat_message("assistant", avatar="🤖"):
                with st.spinner("🔄 Thinking & calling tools …"):
                    try:
                        system_prompt = (ARTIFACTS_DIR / "system_prompt.md").read_text(encoding="utf-8")
                        tool_declarations = load_tool_declarations(ARTIFACTS_DIR / "tools.yaml")
                        openai_tools = to_openai_tools(tool_declarations)
                        provider = make_provider(provider_name)
                        sel_model = model_override or None

                        hist = st.session_state.messages[:]
                        if history_window > 0:
                            hist = hist[-history_window * 2:]

                        messages = [{"role": "system", "content": system_prompt}, *hist]

                        result = run_model_tool_loop(
                            provider=provider,
                            messages=messages,
                            tools=openai_tools,
                            model=sel_model,
                            max_tool_rounds=max_tool_rounds,
                        )

                        assistant_text = result.get("assistant_text", "")
                        st.markdown(assistant_text)
                        st.session_state.messages.append({"role": "assistant", "content": assistant_text})

                        # store trace
                        st.session_state.tool_traces.append({
                            "turn": st.session_state.turn_index,
                            "user": user_input,
                            "status": result.get("status", ""),
                            "rounds": result.get("rounds", []),
                            "tool_events": result.get("tool_events", []),
                            "assistant_text": assistant_text,
                            "ts": now_iso(),
                        })

                        # save transcript
                        av = build_artifact_version(version_label, ARTIFACTS_DIR / "system_prompt.md", ARTIFACTS_DIR / "tools.yaml")
                        if st.session_state.transcript is None:
                            ts = datetime.now().strftime("%Y%m%dT%H%M%S%f")
                            tid = f"{safe_slug(version_label)}_{safe_slug(provider_name)}_{ts}"
                            st.session_state.transcript = {
                                "transcript_id": tid,
                                **artifact_version_dict(av),
                                "provider": provider_name,
                                "model": sel_model,
                                "system_prompt": str(ARTIFACTS_DIR / "system_prompt.md"),
                                "tools": str(ARTIFACTS_DIR / "tools.yaml"),
                                "history_window": history_window,
                                "max_tool_rounds": max_tool_rounds,
                                "created_at": now_iso(),
                                "updated_at": now_iso(),
                                "turns": [],
                            }

                        st.session_state.transcript["turns"].append({
                            "turn_index": st.session_state.turn_index,
                            "started_at": now_iso(), **result, "ended_at": now_iso(),
                            "user": user_input,
                        })
                        tp = TRANSCRIPTS_DIR / f"{st.session_state.transcript['transcript_id']}.transcript.json"
                        write_transcript(tp, st.session_state.transcript)

                    except Exception as exc:
                        err = f"**{type(exc).__name__}:** {exc}"
                        st.error(err)
                        st.session_state.messages.append({"role": "assistant", "content": f"⚠️ {err}"})

                st.rerun()

    # ── Trace column ──
    with col_trace:
        st.markdown("""
        <div style="font-size:1rem;font-weight:700;margin-bottom:.7rem;
                    color:#e2e8f0;display:flex;align-items:center;gap:.4rem">
            <span style="font-size:1.1rem">🔍</span> Tool Trace
        </div>""", unsafe_allow_html=True)

        if not st.session_state.tool_traces:
            st.markdown("""
            <div style="background:rgba(255,255,255,.02);border:1px solid rgba(255,255,255,.06);
                        border-radius:12px;padding:2.5rem 1rem;text-align:center">
                <div style="font-size:2.2rem;margin-bottom:.5rem;opacity:.5">🛠️</div>
                <div style="color:#475569;font-size:.85rem;line-height:1.5">
                    Tool traces appear here<br>when you chat with the agent
                </div>
            </div>""", unsafe_allow_html=True)
        else:
            for trace in reversed(st.session_state.tool_traces):
                turn_n = trace["turn"]
                status = trace["status"]
                status_badge = {
                    "answered": _badge("✅ Answered", "green"),
                    "waiting_for_user": _badge("⏳ Waiting", "amber"),
                    "max_tool_rounds": _badge("⚠️ Max Rounds", "red"),
                }.get(status, _badge(status, "blue"))

                user_preview = trace["user"][:80] + ("…" if len(trace["user"]) > 80 else "")

                st.markdown(f"""
                <div style="background:rgba(255,255,255,.025);border:1px solid rgba(255,255,255,.06);
                            border-radius:10px;padding:.9rem 1rem;margin-bottom:.6rem">
                    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:.35rem">
                        <span style="font-weight:700;font-size:.88rem;color:#e2e8f0">Turn {turn_n}</span>
                        {status_badge}
                    </div>
                    <div style="font-size:.8rem;color:#64748b;line-height:1.4">{user_preview}</div>
                </div>""", unsafe_allow_html=True)

                for rnd in trace.get("rounds", []):
                    rn = rnd.get("round", "?")
                    for ev in rnd.get("tool_results", []):
                        tname = ev.get("tool", "?")
                        targs = ev.get("args", {})
                        tres = ev.get("result", {})
                        is_err = isinstance(tres, dict) and "error" in tres
                        args_str = json.dumps(targs, ensure_ascii=False, default=str)
                        if len(args_str) > 100:
                            args_str = args_str[:100] + " …"

                        expander_title = f"{tname} · Round {rn}"
                        with st.expander(expander_title, expanded=False):
                            st.markdown(f"**Args:** `{args_str}`")
                            st.markdown("**Result:**")
                            st.json(tres)


# ─── TAB: RUN LOGS ────────────────────────────────────────────────────
with tab_runs:
    runs = _load_json_dir(RUNS_DIR)
    if not runs:
        st.info("📂 No run files found in `runs/`. Run `python run_eval.py` to generate eval logs.")
    else:
        sel_name = st.selectbox("Select Run", [r["_filename"] for r in runs], key="run_sel")
        run = next(r for r in runs if r["_filename"] == sel_name)

        summary = run.get("summary", {})

        # Metrics row
        c1, c2, c3, c4 = st.columns(4)
        def _fmt_pct(v):
            return f"{v:.0%}" if isinstance(v, (int, float)) else str(v)

        with c1:
            st.markdown(_metric_html(_fmt_pct(summary.get("case_accuracy", "–")), "Case Accuracy", "🎯"), unsafe_allow_html=True)
        with c2:
            st.markdown(_metric_html(_fmt_pct(summary.get("tool_routing_accuracy", "–")), "Tool Routing", "🔀"), unsafe_allow_html=True)
        with c3:
            st.markdown(_metric_html(_fmt_pct(summary.get("argument_accuracy", "–")), "Arg Accuracy", "📝"), unsafe_allow_html=True)
        with c4:
            m = summary.get("measured_cases", "?")
            t = summary.get("total_cases", "?")
            e = summary.get("provider_error_cases", 0)
            st.markdown(_metric_html(f"{m}/{t}", f"Measured (err:{e})", "📊"), unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # Run meta
        av_v = run.get("artifact_version", "N/A")
        st.markdown(f"""
        <div style="background:rgba(255,255,255,.02);border:1px solid rgba(255,255,255,.06);
                    border-radius:10px;padding:.9rem 1.1rem;display:flex;gap:2rem;flex-wrap:wrap">
            <div>
                <div style="font-size:.68rem;color:#475569;text-transform:uppercase;letter-spacing:.05em;font-weight:600">
                    Artifact Version</div>
                <div style="font-family:'JetBrains Mono',monospace;font-size:.82rem;color:#a5b4fc;font-weight:600;margin-top:.2rem">
                    {av_v}</div>
            </div>
            <div>
                <div style="font-size:.68rem;color:#475569;text-transform:uppercase;letter-spacing:.05em;font-weight:600">
                    Suite</div>
                <div style="font-size:.88rem;color:#e2e8f0;font-weight:600;margin-top:.2rem">
                    {run.get('suite','N/A')}</div>
            </div>
            <div>
                <div style="font-size:.68rem;color:#475569;text-transform:uppercase;letter-spacing:.05em;font-weight:600">
                    Provider</div>
                <div style="font-size:.88rem;color:#e2e8f0;font-weight:600;margin-top:.2rem">
                    {run.get('provider','N/A')}</div>
            </div>
        </div>""", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # Case results
        results = run.get("results", [])
        if results:
            st.subheader("📋 Case Results")
            for case in results:
                cid = case.get("case_id", case.get("id", "?"))
                cr = case.get("result", {})
                passed = cr.get("pass", False)
                failures = cr.get("failures", [])
                icon = "✅" if passed else "❌"

                with st.expander(f"{icon}  {cid}", expanded=not passed):
                    if failures:
                        for fail in failures:
                            st.warning(fail)
                    mm = cr.get("observed_mismatch", "")
                    if mm:
                        st.error(f"**Mismatch:** {mm}")
                    ac = case.get("actual_tool_calls", cr.get("actual_tool_calls", []))
                    if ac:
                        st.markdown("**Actual Tool Calls:**")
                        st.json(ac)
                    tr_data = case.get("tool_results", cr.get("tool_results", []))
                    if tr_data:
                        st.markdown("**Tool Results:**")
                        st.json(tr_data)

        with st.expander("🔍 Full Run JSON"):
            st.json(run)


# ─── TAB: TRANSCRIPTS ─────────────────────────────────────────────────
with tab_transcripts:
    trs = _load_json_dir(TRANSCRIPTS_DIR, "*.transcript.json")
    if not trs:
        st.info("📝 No transcripts found. Chat with the agent to create one.")
    else:
        sel_t = st.selectbox("Select Transcript", [t["_filename"] for t in trs], key="tr_sel")
        tr = next(t for t in trs if t["_filename"] == sel_t)

        # meta bar
        t_av = tr.get("artifact_version", "N/A")
        st.markdown(f"""
        <div style="background:rgba(255,255,255,.02);border:1px solid rgba(255,255,255,.06);
                    border-radius:10px;padding:.8rem 1rem;display:flex;gap:1.8rem;flex-wrap:wrap;
                    margin-bottom:1rem">
            <div>
                <span style="font-size:.68rem;color:#475569;text-transform:uppercase;font-weight:600">Version</span><br>
                <span style="font-family:'JetBrains Mono',monospace;font-size:.8rem;color:#a5b4fc;font-weight:600">{t_av}</span>
            </div>
            <div>
                <span style="font-size:.68rem;color:#475569;text-transform:uppercase;font-weight:600">Provider</span><br>
                <span style="font-size:.85rem;color:#e2e8f0;font-weight:600">{tr.get('provider','?')}</span>
            </div>
            <div>
                <span style="font-size:.68rem;color:#475569;text-transform:uppercase;font-weight:600">Model</span><br>
                <span style="font-size:.85rem;color:#e2e8f0;font-weight:600">{tr.get('model','default') or 'default'}</span>
            </div>
            <div>
                <span style="font-size:.68rem;color:#475569;text-transform:uppercase;font-weight:600">Turns</span><br>
                <span style="font-size:.85rem;color:#e2e8f0;font-weight:700">{len(tr.get('turns',[]))}</span>
            </div>
        </div>""", unsafe_allow_html=True)

        for turn in tr.get("turns", []):
            ti = turn.get("turn_index", "?")
            ut = turn.get("user", "")
            at_ = turn.get("assistant_text", "")

            with st.chat_message("user", avatar="👤"):
                st.caption(f"Turn {ti}")
                st.markdown(ut)

            # tool events
            for rnd in turn.get("rounds", []):
                rn = rnd.get("round", "?")
                for ev in rnd.get("tool_results", []):
                    tname = ev.get("tool", "?")
                    tres = ev.get("result", {})
                    with st.expander(f"Tool: **{tname}** (R{rn})"):
                        st.markdown(f"**Args:** `{json.dumps(ev.get('args',{}), ensure_ascii=False, default=str)}`")
                        st.json(tres)

            if at_:
                with st.chat_message("assistant", avatar="🤖"):
                    st.markdown(at_)

            st.divider()

        with st.expander("🔍 Full Transcript JSON"):
            st.json(tr)


