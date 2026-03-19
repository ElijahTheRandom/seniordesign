"""
views/load_previous_runs.py
----------------------------------
Renders the PS Analytics load previous runs page for statistical methods.

WHY THIS FILE EXISTS:
    The help page provides users with a list of stored runs that they have saved
    in the PS Analytics application. This allows users to easily access and reopen
    their previous runs without having to start from scratch each time.
    

PUBLIC INTERFACE:
    render_load_previous_runs()
"""
import streamlit as st

st.markdown("""
<style>
.card-buttons .stButton>button {
    margin-top: 0;  /* remove spacing above buttons */
}
.card-wrapper {
    background: linear-gradient(145deg, #2e2f34, #272a30);
    border: 1px solid rgba(228, 120, 29, 0.15);
    border-radius: 12px;
    padding: 1rem;
    margin-bottom: 0.75rem;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
/* Style the card */
.analysis-card-container {
    background: linear-gradient(145deg, #2e2f34, #272a30);
    border: 1px solid rgba(228, 120, 29, 0.15);
    border-radius: 12px;
    padding: 1rem;
    margin-bottom: 1rem;
}

/* Reduce spacing above buttons so they appear inside the card */
.analysis-card-container .stButton>button {
    margin-top: 0 !important;
}

/* Optional: columns inside the card */
.analysis-card-container .css-1lcbmhc {  /* adjust if needed for your Streamlit version */
    gap: 0.5rem;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>

/* FULL-WIDTH CARD (matches analysis page) */
.analysis-card {
    background: linear-gradient(145deg, #2e2f34, #272a30);
    border: 1px solid rgba(228, 120, 29, 0.15);
    border-radius: 12px;

    padding: 0.75rem 1.25rem;   /* MUCH thinner */
    margin-bottom: 0.75rem;

    display: flex;
    flex-direction: column;
    justify-content: center;

    box-shadow:
        0 2px 4px rgba(0, 0, 0, 0.08),
        0 6px 12px rgba(0, 0, 0, 0.12);

    transition: all 0.2s ease;
}

.analysis-card:hover {
    border-color: rgba(228, 120, 29, 0.35);
    transform: translateY(-2px);
}

/* TOP SHINE */
.analysis-card::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 1px;
    background: linear-gradient(90deg,
        transparent,
        rgba(228, 120, 29, 0.3),
        transparent);
}

/* HOVER */
.analysis-card:hover {
    border-color: rgba(228, 120, 29, 0.35);
    box-shadow:
        0 8px 12px rgba(0, 0, 0, 0.15),
        0 16px 24px rgba(0, 0, 0, 0.2),
        0 24px 48px rgba(0, 0, 0, 0.15),
        0 0 0 1px rgba(228, 120, 29, 0.2);
    transform: translateY(-4px) scale(1.01);
}

</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
div[data-testid="stAppViewContainer"] .block-container {
    padding-left: 0.5rem !important;
    padding-right: 1rem !important;
}
</style>
""", unsafe_allow_html=True)

def render_load_previous_runs() -> None:

    st.markdown("<div style='margin-top: 1rem;'></div>", unsafe_allow_html=True)

    st.markdown(
        "<hr style='margin: 0; border: none; height: 1px; "
        "background: linear-gradient(90deg, transparent 0%, "
        "rgba(228, 120, 29, 0.5) 50%, transparent 100%);' />",
        unsafe_allow_html=True
    )

    st.header("Saved Runs", anchor=False)
    st.markdown("<div style='margin-bottom: 3.5rem;'></div>", unsafe_allow_html=True)

    runs = st.session_state.get("saved_runs", [])

    if not runs:
        st.info("No saved runs yet.\nRun an analysis and click 'Save Run' to see it here.")
        return

    # 🔥 GRID (THIS is what you're missing)
    for run in runs:
        st.markdown('<div class="run-card-wrapper">', unsafe_allow_html=True)
        with st.container():
            _render_run_card(run)
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown("<div style='height: 1.5rem;'></div>", unsafe_allow_html=True)

def _render_run_card(run: dict) -> None:
    run_id = run["id"]

    # 🔥 marker (invisible)
    st.markdown('<div class="run-card-marker"></div>', unsafe_allow_html=True)

    # --- TITLE ---
    st.markdown(f"""
        <div style='font-size:25px; font-weight:600; color:#fb923c; margin-bottom: 0.75rem;'>
            Saved Run - {run['name']}
        </div>
    """, unsafe_allow_html=True)

    # --- BUTTONS ---
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("Rename", key=f"load_rename_{run_id}", use_container_width=True):
            st.session_state.renaming_run_id = run_id

    with col2:
        if st.button("Replay", key=f"load_replay_{run_id}", use_container_width=True):
            st.session_state.active_run_id = run_id
            st.session_state.current_view = "home"
            st.rerun()

    with col3:
        if st.button("Delete", key=f"load_delete_{run_id}", use_container_width=True):
            st.session_state.analysis_runs = [
                r for r in st.session_state.analysis_runs if r["id"] != run_id
            ]
            st.rerun()

    if st.session_state.get("renaming_run_id") == run_id:
        st.markdown("<div style='margin-top: 0.75rem;'></div>", unsafe_allow_html=True)
        _render_rename_form_load(run)

def _render_rename_form_load(run: dict) -> None:
    new_name = st.text_input(
        "Rename run",
        value=run["name"],
        key=f"load_rename_input_{run['id']}",
        label_visibility="collapsed"
    )

    save_col, cancel_col = st.columns([1, 1])

    with save_col:
        if st.button(
            "Save",
            key=f"load_save_{run['id']}",
            use_container_width=True
        ):
            run["name"] = new_name.strip() or run["name"]
            st.session_state.renaming_run_id = None
            st.rerun()

    with cancel_col:
        if st.button(
            "Cancel",
            key=f"load_cancel_{run['id']}",
            use_container_width=True
        ):
            st.session_state.renaming_run_id = None
            st.rerun()