"""
statistics.py  —  PS Analytics debug/timing page.

Direct-URL only: http://<host>:<port>/statistics

Not linked from anywhere in the UI. Streamlit's auto-generated pages nav is
hidden globally via theme.css so adding this file doesn't expose it in the
sidebar. The page reads timing data recorded by backend_handler.handle_request
and persisted to results_cache/<run>/results_*.json.
"""

import glob
import json
import os
import shutil
import sys
from datetime import datetime

import streamlit as st
from PIL import Image
from pathlib import Path

# ---------------------------------------------------------------------------
# Path setup — lets sibling Frontend packages import cleanly
# ---------------------------------------------------------------------------

_PAGES_DIR    = os.path.dirname(__file__)
_FRONTEND_DIR = os.path.abspath(os.path.join(_PAGES_DIR, ".."))
_PROJECT_ROOT = os.path.abspath(os.path.join(_FRONTEND_DIR, ".."))

for p in (_FRONTEND_DIR, _PROJECT_ROOT):
    if p not in sys.path:
        sys.path.insert(0, p)

from styles.theme import inject_styles  # noqa: E402

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

_ICON_PATH = Path(_FRONTEND_DIR) / "pages" / "assets" / "PStheMainMan.png"

st.set_page_config(
    page_title="PS Analytics — Stats",
    layout="wide",
    page_icon=Image.open(_ICON_PATH) if _ICON_PATH.is_file() else None,
    initial_sidebar_state="collapsed",
)

inject_styles()

RESULTS_CACHE = os.path.join(_PROJECT_ROOT, "results_cache")


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def _scan_runs() -> list[dict]:
    """
    Walk results_cache/*/results_*.json and return a list of run summaries.
    Most recent first. Runs without timings (older, pre-instrumentation) are
    included with timings == None so the health panel can count them.
    """
    if not os.path.isdir(RESULTS_CACHE):
        return []

    runs = []
    for folder in sorted(os.listdir(RESULTS_CACHE)):
        folder_path = os.path.join(RESULTS_CACHE, folder)
        if not os.path.isdir(folder_path):
            continue
        json_files = sorted(glob.glob(os.path.join(folder_path, "results_*.json")))
        if not json_files:
            continue
        json_path = json_files[-1]  # most recent save for this run
        try:
            with open(json_path, "r") as f:
                payload = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue

        timings = payload.get("timings") or None

        # Method ids — prefer the structured list, fall back to results list
        method_ids = []
        for m in payload.get("methods") or []:
            if isinstance(m, dict) and m.get("id"):
                method_ids.append(m["id"])
            elif isinstance(m, str):
                method_ids.append(m)

        chart_types = []
        for g in payload.get("graphics") or []:
            if isinstance(g, dict) and g.get("type"):
                chart_types.append(g["type"])

        try:
            mtime = os.path.getmtime(json_path)
        except OSError:
            mtime = 0

        runs.append({
            "folder_name": folder,
            "folder_path": folder_path,
            "json_path": json_path,
            "mtime": mtime,
            "dataset_id": payload.get("dataset_id"),
            "dataset_version": payload.get("dataset_version"),
            "method_ids": method_ids,
            "chart_types": chart_types,
            "timings": timings,
        })

    runs.sort(key=lambda r: r["mtime"], reverse=True)
    return runs


def _fmt_ms(ms) -> str:
    if ms is None:
        return "—"
    try:
        ms = float(ms)
    except (TypeError, ValueError):
        return "—"
    if ms >= 1000:
        return f"{ms / 1000:.2f} s"
    return f"{ms:.1f} ms"


def _fmt_ts(iso_ts) -> str:
    if not iso_ts:
        return "—"
    try:
        return datetime.fromisoformat(iso_ts).strftime("%Y-%m-%d %H:%M:%S")
    except (TypeError, ValueError):
        return str(iso_ts)


# ---------------------------------------------------------------------------
# Render
# ---------------------------------------------------------------------------

st.markdown(
    """
    <style>
    .debug-banner {
        border: 1px solid rgba(228, 120, 29, 0.35);
        background: rgba(228, 120, 29, 0.08);
        padding: 0.6rem 1rem;
        border-radius: 6px;
        margin-bottom: 1rem;
        color: rgba(255,255,255,0.85);
        font-family: 'Roboto Mono', monospace;
        font-size: 0.85rem;
    }
    .ps-stats-section {
        margin-top: 1.5rem;
        margin-bottom: 0.5rem;
    }
    </style>
    <div class="debug-banner">
        <strong>Debug page</strong> — timing breakdown for every run in
        <code>results_cache/</code>. Not linked from the app UI.
    </div>
    """,
    unsafe_allow_html=True,
)

st.title("Run timings")

runs = _scan_runs()

if not runs:
    st.info("No runs found in `results_cache/`. Run an analysis to populate this page.")
    st.stop()

# --- Health panel ---------------------------------------------------------

instrumented = [r for r in runs if r["timings"]]
legacy = [r for r in runs if not r["timings"]]

hc1, hc2, hc3 = st.columns(3)
hc1.metric("Total runs", len(runs))
hc2.metric("Instrumented", len(instrumented))
hc3.metric("Pre-instrumentation (no timings)", len(legacy))

# --- Summary table --------------------------------------------------------

st.markdown("<div class='ps-stats-section'></div>", unsafe_allow_html=True)
st.subheader("Summary")

summary_rows = []
for r in runs:
    t = r["timings"] or {}
    summary_rows.append({
        "Run folder": r["folder_name"],
        "Dataset": f"{r['dataset_id']} v{r['dataset_version']}",
        "Started": _fmt_ts(t.get("started_at")),
        "Total": _fmt_ms(t.get("total_ms")),
        "Dispatch": _fmt_ms(t.get("dispatch_ms")),
        "Compute": _fmt_ms(t.get("compute_ms")),
        "Charts": _fmt_ms(t.get("charts_ms")),
        "Persist": _fmt_ms(t.get("persistence_ms")),
        "# methods": len(r["method_ids"]),
        "# charts": len(r["chart_types"]),
    })

st.dataframe(summary_rows, use_container_width=True, hide_index=True)

# --- Per-run breakdown ----------------------------------------------------

st.markdown("<div class='ps-stats-section'></div>", unsafe_allow_html=True)
st.subheader("Per-run breakdown")

if not instrumented:
    st.caption("No instrumented runs yet. Completed runs after the timing "
               "instrumentation landed will show up here.")
else:
    for r in instrumented:
        t = r["timings"]
        label = f"{r['folder_name']} — total {_fmt_ms(t.get('total_ms'))}"
        with st.expander(label, expanded=False):
            del_key = f"stats_delete_{r['folder_name']}"
            if st.button(
                "Delete run",
                key=del_key,
                help="Permanently remove this run's cached folder.",
            ):
                try:
                    shutil.rmtree(r["folder_path"])
                    st.rerun()
                except OSError as exc:
                    st.error(f"Failed to delete {r['folder_path']}: {exc}")

            c1, c2 = st.columns(2)

            with c1:
                st.markdown("**Per-method compute time**")
                per_method = t.get("per_method_ms") or {}
                if per_method:
                    st.bar_chart(per_method, horizontal=True)
                    st.dataframe(
                        [{"method": k, "ms": v} for k, v in per_method.items()],
                        use_container_width=True,
                        hide_index=True,
                    )
                else:
                    st.caption("No methods ran.")

            with c2:
                st.markdown("**Per-chart generation time**")
                per_chart = t.get("per_chart_ms") or {}
                if per_chart:
                    st.bar_chart(per_chart, horizontal=True)
                    st.dataframe(
                        [{"chart": k, "ms": v} for k, v in per_chart.items()],
                        use_container_width=True,
                        hide_index=True,
                    )
                else:
                    st.caption("No charts were requested.")

            st.markdown("**Phase totals**")
            st.dataframe(
                [
                    {"phase": "dispatch",    "ms": t.get("dispatch_ms")},
                    {"phase": "compute",     "ms": t.get("compute_ms")},
                    {"phase": "charts",      "ms": t.get("charts_ms")},
                    {"phase": "persistence", "ms": t.get("persistence_ms")},
                    {"phase": "total",       "ms": t.get("total_ms")},
                ],
                use_container_width=True,
                hide_index=True,
            )

            st.caption(
                f"started_at: {_fmt_ts(t.get('started_at'))}  ·  "
                f"finished_at: {_fmt_ts(t.get('finished_at'))}  ·  "
                f"folder: {r['folder_path']}"
            )

# --- Legacy runs (no timings) ---------------------------------------------

if legacy:
    st.markdown("<div class='ps-stats-section'></div>", unsafe_allow_html=True)
    st.subheader("Pre-instrumentation runs")
    st.caption(
        "These runs were saved before timing instrumentation landed. "
        "They have no compute/chart breakdown — delete them if you don't need them."
    )
    for r in legacy:
        c_label, c_btn = st.columns([4, 1])
        with c_label:
            st.markdown(
                f"**{r['folder_name']}** — {r['dataset_id']} v{r['dataset_version']}"
                f"  ·  {len(r['method_ids'])} method(s), {len(r['chart_types'])} chart(s)"
            )
        with c_btn:
            if st.button(
                "Delete",
                key=f"stats_delete_legacy_{r['folder_name']}",
                use_container_width=True,
            ):
                try:
                    shutil.rmtree(r["folder_path"])
                    st.rerun()
                except OSError as exc:
                    st.error(f"Failed to delete {r['folder_path']}: {exc}")
