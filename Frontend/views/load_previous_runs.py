"""
views/load_previous_runs.py
----------------------------------
Renders the PS Analytics load previous runs page.

WHY THIS FILE EXISTS:
    The load previous runs page provides users with a list of stored runs
    that they have saved in the PS Analytics application. This allows users
    to easily access and reopen their previous runs without having to start
    from scratch each time.

PUBLIC INTERFACE:
    render_load_previous_runs()
"""
import sys
import os
import json
import glob

_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
if _PROJECT_ROOT not in sys.path:
    sys.path.append(_PROJECT_ROOT)

import streamlit as st
import pandas as pd
from datetime import datetime

from class_templates.message_structure import Message
from frontend_handler import handle_result

SAVED_RUNS_FILE = os.path.join(_PROJECT_ROOT, "results_cache", "saved_runs.json")


def render_load_previous_runs() -> None:
    """
    Render the load previous runs page.

    Reads saved_runs.json and displays each saved run as a card with
    a Load button. Clicking Load reconstructs the run from the cached
    results and navigates to the results tab.
    """
    st.markdown("<div style='margin-top: 1rem;'></div>", unsafe_allow_html=True)
    st.markdown(
        "<hr style='margin: 0; border: none; height: 1px; "
        "background: linear-gradient(90deg, transparent 0%, "
        "rgba(228, 120, 29, 0.5) 50%, transparent 100%);' />",
        unsafe_allow_html=True
    )

    st.header("Load Previous Runs", anchor=False)

    saved_runs = _read_saved_runs()

    if not saved_runs:
        st.info("No saved runs found. Run an analysis and click **Save Run** to save it here.")
        return

    st.markdown("<div style='margin-bottom: 1rem;'></div>", unsafe_allow_html=True)

    for entry in reversed(saved_runs):
        _render_saved_run_card(entry, saved_runs)


def _render_saved_run_card(entry: dict, saved_runs: list) -> None:
    """Render a single saved run as a styled card with Load and Delete buttons."""
    run_id = entry.get("id", "unknown")
    name = entry.get("name", "Unnamed Run")
    saved_at = entry.get("saved_at", "")
    dataset_id = entry.get("dataset_id", "Unknown dataset")
    methods = entry.get("methods", [])
    visualizations = entry.get("visualizations", [])
    cache_folder = entry.get("cache_folder", "")

    # Format the saved timestamp
    try:
        dt = datetime.fromisoformat(saved_at)
        display_time = dt.strftime("%b %d, %Y at %I:%M %p")
    except (ValueError, TypeError):
        display_time = saved_at or "Unknown time"

    # Method/viz summary
    method_names = []
    for m in methods:
        if isinstance(m, dict):
            method_names.append(m.get("id", str(m)))
        else:
            method_names.append(str(m))

    summary_parts = []
    if method_names:
        summary_parts.append(f"{len(method_names)} method(s)")
    if visualizations:
        summary_parts.append(f"{len(visualizations)} chart(s)")
    summary = " · ".join(summary_parts) if summary_parts else "No methods or charts"

    folder_exists = os.path.isdir(cache_folder) if cache_folder else False

    st.markdown(f"""
    <div class="analysis-card" style="padding: 1.25rem 1.5rem; margin-bottom: 0.5rem;">
        <div class="analysis-title" style="font-size: 1.1rem; margin-bottom: 0.3rem;">{name}</div>
        <div class="analysis-subtext" style="font-size: 0.85rem; margin-bottom: 0.15rem;">
            Dataset: {dataset_id} · {summary}
        </div>
        <div class="analysis-subtext" style="font-size: 0.8rem; opacity: 0.6;">
            Saved {display_time}
        </div>
    </div>
    """, unsafe_allow_html=True)

    col_load, col_delete = st.columns([3, 1])

    with col_load:
        if not folder_exists:
            st.button(
                "Cache missing",
                key=f"load_disabled_{run_id}",
                disabled=True,
                use_container_width=True,
            )
        elif st.button("Load Run", key=f"load_run_{run_id}", use_container_width=True):
            _load_run_from_cache(entry)

    with col_delete:
        if st.button("🗑️", key=f"delete_saved_{run_id}", help="Remove from saved runs"):
            updated = [s for s in saved_runs if s["id"] != run_id]
            _write_saved_runs(updated)
            st.rerun()

    st.markdown("<div style='margin-bottom: 1rem;'></div>", unsafe_allow_html=True)


def _load_run_from_cache(entry: dict) -> None:
    """
    Reconstruct a run dict from the cache folder and add it to session state.

    Steps:
        1. Find the results JSON in the cache folder.
        2. Parse it into a Message object.
        3. Load the table CSV (if saved).
        4. Build the run dict and add to analysis_runs.
        5. Navigate to the run.
    """
    cache_folder = entry["cache_folder"]

    # Already loaded? Just navigate to it.
    existing = next(
        (r for r in st.session_state.analysis_runs if r["id"] == entry["id"]),
        None,
    )
    if existing:
        st.session_state.active_run_id = entry["id"]
        st.session_state.current_view = "home"
        st.rerun()
        return

    # 1. Find the results JSON
    json_files = glob.glob(os.path.join(cache_folder, "results_*.json"))
    if not json_files:
        st.error("No results JSON found in the cache folder.")
        return

    json_path = sorted(json_files)[-1]  # most recent

    try:
        with open(json_path, "r") as f:
            data_dict = json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        st.error(f"Failed to read cached results: {exc}")
        return

    # 2. Reconstruct the Message object
    result_message = Message(
        dataset_id=data_dict.get("dataset_id"),
        dataset_version=data_dict.get("dataset_version"),
        metadata=data_dict.get("metadata", []),
        selection=data_dict.get("selection", {}),
        methods=data_dict.get("methods", []),
        graphics=data_dict.get("graphics", []),
        results=data_dict.get("results", []),
        run_folder=cache_folder,
    )

    # 3. Load the table CSV (saved by the Save Run action)
    table_path = os.path.join(cache_folder, "table.csv")
    if os.path.isfile(table_path):
        table_df = pd.read_csv(table_path)
    else:
        table_df = pd.DataFrame()

    # 4. Extract method and visualization names for the run dict
    methods_list = entry.get("methods", [])
    viz_list = entry.get("visualizations", [])

    # 5. Build the run dict
    run = {
        "id":             entry["id"],
        "name":           entry.get("name", "Loaded Run"),
        "methods":        methods_list,
        "visualizations": viz_list,
        "result_message": result_message,
        "table":          table_df,
        "data":           table_df,
    }

    # Generate stat/error cards from results
    handle_result(run)

    # 6. Add to session and navigate
    st.session_state.analysis_runs.append(run)
    st.session_state.active_run_id = run["id"]
    st.session_state.current_view = "home"
    st.rerun()


# ---------------------------------------------------------------------------
# saved_runs.json helpers
# ---------------------------------------------------------------------------

def _read_saved_runs() -> list:
    """Read and return the list from saved_runs.json, or [] if missing."""
    if not os.path.isfile(SAVED_RUNS_FILE):
        return []
    try:
        with open(SAVED_RUNS_FILE, "r") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def _write_saved_runs(saved_runs: list) -> None:
    """Write the saved_runs list to saved_runs.json."""
    with open(SAVED_RUNS_FILE, "w") as f:
        json.dump(saved_runs, f, indent=2)