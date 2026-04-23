"""
views/results.py
----------------
Renders the analysis results page for a completed PS Analytics run.

WHY THIS FILE EXISTS:
    The results display was previously inline in mainpage.py (lines
    1842–1982), with stat card generation, visualization rendering,
    export logic, and delete handling all in one block.

    Extracting it here gives the results page its own clear structure:
    header → stat cards → visualizations → data table → action buttons.

PUBLIC INTERFACE:
    render_results(run, base_dir)

PRIVATE HELPERS:
    _render_stat_cards(run)
    _render_visualizations(run)
    _render_data_table(run)
    _render_action_buttons(run)
    _build_export_text(run)

STAT DISPATCH TABLE (module-level):
    STAT_COMPUTERS maps method name strings → compute functions.
    To add a new statistic, write one _compute_*() function and add
    one entry to STAT_COMPUTERS. The rendering loop never changes.

    Each compute function receives run["table"] (a DataFrame) and
    returns a list of card tuples:
        ("stat", title_html, value_str)           — 3-tuple
        ("stat", title_html, value_str, subtext)  — 4-tuple

SESSION STATE READ:
    active_run_id, analysis_runs

SESSION STATE WRITTEN:
    active_run_id, analysis_runs (on delete)
"""
import sys
import os
import json
import base64
from pathlib import Path
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from PIL import Image

from utils.helpers import df_to_ascii_table
from frontend_handler import handle_result
from logic.run_manager import VIZ_NAMES, build_success_save_message


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

from datetime import datetime
from io import BytesIO

_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
if _PROJECT_ROOT not in sys.path:
    sys.path.append(_PROJECT_ROOT)

SAVED_RUNS_FILE = os.path.join(_PROJECT_ROOT, "results_cache", "saved_runs.json")

_HUZZAH_PATH = Path(__file__).parent.parent / "pages" / "assets" / "huzzahAhSquirrel.png"
with open(_HUZZAH_PATH, "rb") as _f:
    _HUZZAH_B64 = base64.b64encode(_f.read()).decode()

if "show_success_save_dialog" not in st.session_state:
    st.session_state.show_success_save_dialog = False

if "modal_message" not in st.session_state:
    st.session_state.modal_message = ""

def _show_success_save_toast() -> None:
    """Inject a self-dismissing toast notification matching the homepage style."""
    import re, json as _json
    message = st.session_state.get("modal_message", "")
    b64 = _HUZZAH_B64

    html_msg = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', message)
    html_msg = html_msg.replace("\n", "<br>")
    msg_json = _json.dumps(html_msg)

    components.html(
        f"""
        <script>
        (function() {{
            const doc = window.parent.document;

            if (!doc.getElementById('ps-toast-styles')) {{
                const s = doc.createElement('style');
                s.id = 'ps-toast-styles';
                s.textContent =
                    '@keyframes ps-in{{from{{opacity:0;transform:translateY(-14px)}}' +
                    'to{{opacity:1;transform:translateY(0)}}}}' +
                    '@keyframes ps-out{{from{{opacity:1;transform:translateY(0)}}' +
                    'to{{opacity:0;transform:translateY(-14px)}}}}' ;
                doc.head.appendChild(s);
            }}

            const prev = doc.getElementById('ps-success-toast');
            if (prev) prev.remove();

            const toast = doc.createElement('div');
            toast.id = 'ps-success-toast';
            toast.style.cssText = [
                'position:fixed', 'top:1.25rem', 'right:1.25rem', 'z-index:9999',
                'background:#1e2530', 'border:1px solid rgba(228,120,29,0.45)',
                'border-radius:12px', 'padding:0.9rem 1.1rem',
                'display:flex', 'align-items:center', 'gap:0.9rem',
                'box-shadow:0 8px 32px rgba(0,0,0,0.55)', 'max-width:340px',
                'pointer-events:none',
                'animation:ps-in 0.3s ease, ps-out 0.45s ease 4.55s forwards'
            ].join(';');

            const img = doc.createElement('img');
            img.src = 'data:image/png;base64,{b64}';
            img.style.cssText = 'width:52px;height:52px;object-fit:contain;border-radius:6px;flex-shrink:0';

            const txt = doc.createElement('div');
            txt.innerHTML = {msg_json};
            txt.style.cssText = 'color:#ffffff;font-size:0.875rem;line-height:1.45;font-family:sans-serif';

            toast.appendChild(img);
            toast.appendChild(txt);
            doc.body.appendChild(toast);

            setTimeout(() => {{ if (toast.parentNode) toast.remove(); }}, 5000);
        }})();
        </script>
        """,
        height=0,
    )

# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def render_results(run: dict, base_dir: str) -> None:
    """
    Render the full results page for a single analysis run.

    Args:
        run:      The run dict: { id, name, table, data, columns, rows,
                                  methods, visualizations }
        base_dir: Absolute path to the frontend directory.
    """

    # Only compute cards if not already cached on the run
    if "cards" not in run:
        run = handle_result(run)

    st.markdown("<div style='margin-top: 1rem;'></div>", unsafe_allow_html=True)
    st.markdown(
        "<hr style='margin: 0; border: none; height: 1px; "
        "background: linear-gradient(90deg, transparent 0%, "
        "rgba(228, 120, 29, 0.5) 50%, transparent 100%);' />",
        unsafe_allow_html=True
    )

    if st.session_state.get("show_success_save_dialog"):
        st.session_state.show_success_save_dialog = False
        _show_success_save_toast()

    if st.session_state.get("show_export_dialog"):
        _export_run_dialog(run)
        st.session_state.show_export_dialog = False

    if "show_export_dialog" not in st.session_state:
        st.session_state.show_export_dialog = False

    st.header(f"Analysis Results — {run['name']}", anchor=False)
    _render_stat_cards(run)
    _render_precision_notice(run)
    _render_multi_column_notice(run)
    _render_precision_warnings(run)
    _render_visualizations(run)
    _render_data_table(run)
    _render_action_buttons(run)


# ---------------------------------------------------------------------------
# Section renderers
# ---------------------------------------------------------------------------

# ============================================================================
# ⭐ STATISTICAL RESULTS DISPLAY
# Variables:
#   - run["methods"] (list of selected method names)
#   - STAT_COMPUTERS[method_name] (dispatch table mapping to compute functions)
#   - run["table"] (DataFrame passed to compute functions)
# Rendered via stat cards using _render_stat_card(title, value, subtext)
# ============================================================================

def _render_stat_cards(run: dict, show_divider: bool = True) -> None:
    """
    Compute and render all stat cards for the methods in this run.

    Uses the STAT_COMPUTERS dispatch table to look up the compute
    function for each selected method. Unknown methods are silently
    skipped (future-proofing: old run dicts won't crash the page if a
    method name changes).

    Cards are laid out in a Pinterest-style grid of 3 columns with
    breathing room between rows.
    """
    cards = run.get("cards", [])

    if not cards:
        return

    st.subheader("Statistical Analysis", anchor=False)
    st.markdown("<div style='margin-bottom: 2rem;'></div>", unsafe_allow_html=True)

    # Greedy-pack into rows of 3 slots: cards with long values (LSR equation,
    # Percentile lists) span 2 slots so they don't get smushed.
    for row in _pack_stat_cards(cards, row_slots=3):
        weights = [w for w, _ in row]
        used = sum(weights)
        # Pad the last row to 3 slots so solo/narrow rows don't stretch.
        if used < 3:
            weights = weights + [3 - used]
        cols = st.columns(weights, gap="large")
        for idx, (_, card) in enumerate(row):
            with cols[idx]:
                if card[0] == "error":
                    _render_error_card(card[1], card[2])
                else:
                    _render_stat_card(*card[1:])  # unpack title, value, [subtext]

        st.markdown("<div style='margin-bottom: 2rem;'></div>", unsafe_allow_html=True)

    if show_divider:
        st.markdown("---")


def _card_slot_width(card: tuple) -> int:
    """
    Decide how many layout slots (out of 3) a card should span.

    Rationale: cards like Least Squares Regression ("y = 1.23x + 4.56  R² = ...")
    and Percentile ("25th: 10.50, 50th: 20.00, 75th: 30.50") carry a lot more
    text than a single scalar. At 1/3 page width with the 2.5rem stat font,
    they either wrap ugly or overflow. 2/3 width lets them breathe.
    """
    if card[0] == "error":
        return 1
    value_str = card[2] if len(card) >= 3 else ""
    subtext = card[3] if len(card) >= 4 else ""
    longest = max(len(value_str), len(subtext))
    multi_part = value_str.count(",") >= 2  # percentile-style lists
    equation = "=" in value_str  # LSR y = ... R² = ... or any structured result
    if longest > 35 or multi_part or equation:
        return 2
    return 1


def _pack_stat_cards(cards: list, row_slots: int = 3) -> list:
    """Greedy row-pack cards using per-card slot widths."""
    rows: list = []
    current: list = []
    used = 0
    for card in cards:
        w = min(_card_slot_width(card), row_slots)
        if used + w > row_slots:
            rows.append(current)
            current = []
            used = 0
        current.append((w, card))
        used += w
    if current:
        rows.append(current)
    return rows


def _render_stat_card(title: str, value: str, subtext: str = None) -> None:
    """
    Render a single stat card using the .analysis-card CSS class.

    Args:
        title:   Card header HTML (may contain <b> tags).
        value:   The primary numeric value to display.
        subtext: Optional secondary label below the value.
    """
    subtext_html = (
        f'<div class="analysis-subtext">{subtext}</div>'
        if subtext else ""
    )
    st.markdown(f"""
    <div class="analysis-card">
        <div class="analysis-title">{title}</div>
        <div class="analysis-value">{value}</div>
        {subtext_html}
    </div>
    """, unsafe_allow_html=True)


def _render_error_card(title: str, error_msg: str) -> None:
    """
    Render an error card for a method that could not compute.
    Uses smaller text and a red accent to distinguish from success cards.
    """
    st.markdown(f"""
    <div class="analysis-card-error">
        <div class="analysis-title">{title}</div>
        <div class="analysis-error-msg">{error_msg}</div>
    </div>
    """, unsafe_allow_html=True)


def _render_precision_notice(run: dict) -> None:
    """
    Render a small footnote under the stat cards disclosing that values are
    rounded for display (Req 5.6). Kept visually distinct from the overflow /
    cancellation notices below — this is "your display is abbreviated",
    those are "your values may be wrong".
    """
    has_stat_card = any(c[0] == "stat" for c in run.get("cards", []))
    if not has_stat_card:
        return
    st.caption(
        "Displayed values are rounded to 6 significant figures. "
        "CSV and TSV exports contain the full computed precision."
    )


def _render_multi_column_notice(run: dict) -> None:
    """
    Render an info box when univariate methods ran against >1 selected column.

    These methods (mean, median, mode, variance, standard deviation, percentile,
    coefficient of variation) flatten their input, so selecting multiple columns
    produces one combined result — not per-column results. The user rarely
    expects that, so we spell it out explicitly.

    The detection list is built in frontend_handler.handle_result as
    run["multi_column_univariate_names"].
    """
    names = run.get("multi_column_univariate_names") or []
    if not names:
        return

    selected = run.get("columns") or []
    col_count = len(selected)
    unique_names = sorted(set(names))
    if len(unique_names) == 1:
        subject = unique_names[0]
        verb = "expects"
    else:
        subject = ", ".join(unique_names[:-1]) + f", and {unique_names[-1]}"
        verb = "expect"

    st.info(
        f"**Column selection notice**\n\n"
        f"{subject} {verb} a single column of data. With {col_count} columns "
        f"selected, all values were combined into one dataset before computing, "
        f"so the result reflects every selected column together — not each column "
        f"individually. To get per-column results, run the analysis separately on "
        f"each column."
    )
    st.markdown("<div style='margin-bottom: 1rem;'></div>", unsafe_allow_html=True)


def _render_precision_warnings(run: dict) -> None:
    """
    If any method flagged a loss-of-precision risk, render an info box
    listing each affected method and its explanation.
    """
    warnings = run.get("precision_warnings") or []
    if not warnings:
        return

    lines = []
    for w in warnings:
        lines.append(f"**{w['name']}**: {w['note']}")

    st.info(
        "**Precision/Overflow Notices**\n\n"
        + "\n".join(lines),
    )
    st.markdown("<div style='margin-bottom: 1rem;'></div>", unsafe_allow_html=True)



def _render_visualizations(run: dict, show_divider: bool = True) -> None:
    """
    Render the visualizations section using chart images saved by the backend.

    Reads result_message.graphics, which is populated by BackendHandler after
    chart PNGs are generated into the results_cache run folder.

    Args:
        run: The run dict containing "result_message" (a Message object).
    """
    graphics = getattr(run.get("result_message"), "graphics", None)
    if not graphics:
        return

    st.subheader("Visualizations", anchor=False)
    st.markdown("<div style='margin-bottom: 1rem;'></div>", unsafe_allow_html=True)

    # --- Step 1: Rounded corners ---
    st.markdown(
        """
        <style>
        img {
            border-radius: 15px !important;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    # --- Step 2: Grid layout ---
    cols = st.columns(3)  # adjust number of columns as needed

    for idx, chart in enumerate(graphics):

        if chart.get("ok") and chart.get("path"):
            image = Image.open(chart["path"])
            col = cols[idx % len(cols)]
            with col:
                # Display smaller thumbnail-style image
                st.image(image)

        else:
            chart_type = chart.get('type', 'Chart')
            friendly = VIZ_NAMES.get(chart_type, chart_type.replace('_', ' ').title())
            st.error(f"**{friendly}:** {chart.get('error', 'Failed to generate')}.")


def _render_data_table(run: dict, show_divider: bool = True) -> None:
    """
    Render the selected data table with a row/column summary caption.

    Args:
        run: The run dict containing "data" (the sliced DataFrame).
    """
    st.subheader("Selected Data", anchor=False)
    st.markdown("<div style='margin-bottom: 1rem;'></div>", unsafe_allow_html=True)

    st.dataframe(run["data"], use_container_width=True)
    st.caption(
        f"Rows: {len(run['data'])}, Columns: {len(run['data'].columns)}"
    )
    
    if show_divider:
        st.markdown("---")

@st.dialog("Export Run")
def _export_run_dialog(run: dict):

    st.write("Choose an export format:")

    # TXT report
    st.download_button(
        "Export TXT Report",
        data=_build_export_text(run),
        file_name=f"{run['name']} Full Report.txt",
        mime="text/plain",
        use_container_width=True,
    )

    # CSV export — results section followed by selected data (Req 3.8, 3.9)
    st.download_button(
        "Export CSV Report",
        data=_build_combined_export(run, sep=","),
        file_name=f"{run['name']} Full Report.csv",
        mime="text/csv",
        use_container_width=True,
    )

    # TSV export — results section followed by selected data (Req 3.8, 3.9)
    st.download_button(
        "Export TSV Report",
        data=_build_combined_export(run, sep="\t"),
        file_name=f"{run['name']} Full Report.tsv",
        mime="text/tab-separated-values",
        use_container_width=True,
    )

def _render_charts_zip_download_button(run: dict) -> None:
    """
    Render a native Streamlit Export Charts button that builds the ZIP
    client-side when clicked.

    Python cannot read the user's current theme (it lives in browser
    localStorage), so on click we inject a zero-height JS block that
    loads each chart PNG onto a canvas, inverts it when the UI is in
    light mode, and packs them into a ZIP with JSZip for download.

    Using a real st.button keeps the visual styling in sync with the
    other action buttons via theme.css — the iframe only carries the JS.
    """
    graphics = getattr(run.get("result_message"), "graphics", None) or []

    charts_payload = []
    for idx, chart in enumerate(graphics):
        if not (chart.get("ok") and chart.get("path")):
            continue
        try:
            with open(chart["path"], "rb") as f:
                chart_b64 = base64.b64encode(f.read()).decode()
        except OSError:
            continue
        chart_type = chart.get("type", f"chart_{idx}")
        charts_payload.append({
            "name": f"{chart_type}_{idx}.jpeg",
            "type": chart_type,
            "data": chart_b64,
        })

    if not charts_payload:
        st.button("Export Charts", disabled=True, use_container_width=True)
        return

    run_id = run.get("id", "")
    if st.button("Export Charts", use_container_width=True, key=f"export_charts_{run_id}"):
        zip_name = f"{run.get('name', 'run')} Charts.zip"
        payload_json = json.dumps(charts_payload)
        components.html(
            f"""
            <script src="https://cdnjs.cloudflare.com/ajax/libs/jszip/3.10.1/jszip.min.js"></script>
            <script>
            (async function() {{
                const charts = {payload_json};
                const zipName = {json.dumps(zip_name)};
                const isLightMode = (window.parent.localStorage.getItem("ps_analytics_theme") || "dark") === "light";

                async function loadImage(src) {{
                    return new Promise((resolve, reject) => {{
                        const img = new Image();
                        img.onload = () => resolve(img);
                        img.onerror = reject;
                        img.src = src;
                    }});
                }}

                const zip = new JSZip();
                for (const chart of charts) {{
                    const img = await loadImage("data:image/png;base64," + chart.data);
                    const canvas = document.createElement("canvas");
                    canvas.width = img.width;
                    canvas.height = img.height;
                    const ctx = canvas.getContext("2d");
                    if (isLightMode) {{
                        ctx.filter = "invert(1)";
                    }}
                    ctx.drawImage(img, 0, 0);
                    const blob = await new Promise(r => canvas.toBlob(r, "image/jpeg"));
                    zip.file(chart.name, blob);
                }}
                const zipBlob = await zip.generateAsync({{ type: "blob" }});
                const url = URL.createObjectURL(zipBlob);
                const link = document.createElement("a");
                link.href = url;
                link.download = zipName;
                document.body.appendChild(link);
                link.click();
                link.remove();
                URL.revokeObjectURL(url);
            }})();
            </script>
            """,
            height=0,
        )


def _render_action_buttons(run: dict) -> None:
    """
    Render the Save / Export / Export Charts / Delete action buttons at the bottom.

    Save:          Persists the run to saved_runs.json and writes table CSV to cache.
    Export Run:    Downloads a plain-text .txt report of the run's results.
    Export Charts: Downloads all chart images as a ZIP archive.
    Delete:        Removes the run from session state and navigates home.

    Args:
        run: The run dict to act on.
    """
    btn1, btn2, btn3, btn4 = st.columns(4)

    with btn1:
        if st.button("Save Run", use_container_width=True):
            _save_run(run)

    with btn2:
        if st.button("Export Run", use_container_width=True):
            st.session_state.show_export_dialog = True
            st.rerun()

    with btn3:
        _render_charts_zip_download_button(run)

    with btn4:
        if st.button("Delete Run", use_container_width=True):
            st.session_state.analysis_runs = [
                r for r in st.session_state.analysis_runs
                if r["id"] != run["id"]
            ]
            st.session_state.active_run_id = None
            st.rerun()


# ---------------------------------------------------------------------------
# Save run logic
# ---------------------------------------------------------------------------

def _save_run(run: dict) -> None:
    """
    Persist a run so it can be reloaded from the Load Previous Runs page.

    Steps:
        1. Locate the run's cache folder (from result_message.run_folder).
        2. Save the selected DataFrame as table.csv in that folder.
        3. Add / update an entry in saved_runs.json at the project root.
    """
    result_message = run.get("result_message")
    cache_folder = getattr(result_message, "run_folder", None) if result_message else None

    if not cache_folder or not os.path.isdir(cache_folder):
        st.error("Cannot save: no cache folder found for this run.")
        return

    # 1. Save the table as CSV so it can be reconstructed on load
    table_path = os.path.join(cache_folder, "table.csv")
    if isinstance(run.get("data"), pd.DataFrame):
        run["data"].to_csv(table_path, index=False)

    # 2. Read existing saved_runs.json (or start fresh)
    saved_runs = _read_saved_runs()

    # 3. Build the entry for this run
    entry = {
        "id": run["id"],
        "name": run["name"],
        "saved_at": datetime.now().isoformat(),
        "cache_folder": cache_folder,
        "dataset_id": getattr(result_message, "dataset_id", None),
        "methods": run.get("methods", []),
        "visualizations": run.get("visualizations", []),
    }

    # Replace if the same run id already exists, else append
    saved_runs = [s for s in saved_runs if s["id"] != run["id"]]
    saved_runs.append(entry)

    _write_saved_runs(saved_runs)

    st.session_state.modal_message = build_success_save_message(run)
    st.session_state.show_success_save_dialog = True
    st.rerun()

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
    """Atomically write the saved_runs list to saved_runs.json.

    Uses a temp-file + os.replace() so a crash mid-write cannot truncate
    or corrupt the history index that prior saved runs depend on.
    """
    tmp_path = SAVED_RUNS_FILE + ".tmp"
    try:
        os.makedirs(os.path.dirname(SAVED_RUNS_FILE), exist_ok=True)
        with open(tmp_path, "w") as f:
            json.dump(saved_runs, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, SAVED_RUNS_FILE)
    except OSError as exc:
        # Best-effort cleanup of the partial temp file; leave the existing
        # saved_runs.json untouched so previously saved runs still load.
        try:
            if os.path.isfile(tmp_path):
                os.remove(tmp_path)
        except OSError:
            pass
        st.error(f"Failed to save run history: {exc}")


# ---------------------------------------------------------------------------
# Export builder
# ---------------------------------------------------------------------------

def _explode_result_value(value, params_used):
    """
    Return a list of (field_label, cell_value) pairs for a single result's
    value. Scalars become one row; lists/dicts/DataFrames expand so the
    CSV/TSV is actually tabular instead of serializing structured values
    into an opaque string.
    """
    if isinstance(value, bool):
        return [("value", value)]
    if isinstance(value, (int, float)):
        return [("value", value)]
    if isinstance(value, list):
        if (
            params_used is not None
            and isinstance(params_used, (list, tuple))
            and len(params_used) == len(value)
            and all(isinstance(v, (int, float)) for v in value)
        ):
            pairs = []
            for p, v in zip(params_used, value):
                p_int = int(p) if float(p).is_integer() else p
                label = f"{p_int}th percentile" if isinstance(p_int, int) else f"{p_int} percentile"
                pairs.append((label, v))
            return pairs
        return [(f"value[{i}]", v) for i, v in enumerate(value)]
    if isinstance(value, dict):
        return [(str(k), v) for k, v in value.items()]
    try:
        if isinstance(value, pd.DataFrame):
            pairs = []
            for i, row in value.iterrows():
                for col in value.columns:
                    pairs.append((f"row{i}/{col}", row[col]))
            return pairs
    except Exception:
        pass
    return [("value", str(value) if value is not None else "")]


def _build_results_dataframe(run: dict, run_name: str | None = None) -> pd.DataFrame:
    """
    Build a long-format DataFrame of the run's computed results (Req 3.8).

    One row per (statistic, field) pair. Multi-valued outputs (percentile
    lists, LSR slope/intercept/equation, binomial tables) are exploded
    into multiple rows so downstream tools can consume them directly.
    Row/column selection is repeated on every row (Req 3.9).
    """
    from frontend_handler import _ID_TO_DISPLAY  # local import avoids cycle at module load

    sel_cols = ", ".join(str(c) for c in (run.get("columns") or []))
    sel_rows_list = run.get("rows") or []
    sel_rows = "All" if not sel_rows_list else ", ".join(str(r) for r in sel_rows_list)

    msg = run.get("result_message")
    results = list(getattr(msg, "results", []) or [])

    rows = []
    for res in results:
        stat_id = res.get("id", "")
        display = _ID_TO_DISPLAY.get(stat_id, stat_id)
        status = "ok" if res.get("ok") else "error"
        error_msg = res.get("error") or ""
        params = res.get("params_used")
        params_str = "" if params in (None, "", [], {}) else str(params)

        if res.get("ok"):
            exploded = _explode_result_value(res.get("value"), params)
        else:
            exploded = [("value", "")]

        for field, cell_value in exploded:
            row = {
                "Statistic": display,
                "Field": field,
                "Value": cell_value,
                "Status": status,
                "Error": error_msg,
                "Params": params_str,
                "Selection Columns": sel_cols,
                "Selection Rows": sel_rows,
            }
            if run_name is not None:
                row = {"Run": run_name, **row}
            rows.append(row)

    if not rows:
        cols = ["Statistic", "Field", "Value", "Status", "Error",
                "Params", "Selection Columns", "Selection Rows"]
        if run_name is not None:
            cols = ["Run"] + cols
        return pd.DataFrame(columns=cols)

    return pd.DataFrame(rows)


def _build_combined_export(run: dict, sep: str = ",") -> str:
    """
    Build a single CSV/TSV string with the run's results on top followed
    by the selected input data — mirrors the TXT report layout so the
    computed results (Req 3.8) and the exact selection they came from
    (Req 3.9) are in one downloadable file.
    """
    import csv
    import io

    buf = io.StringIO()
    w = csv.writer(buf, delimiter=sep, lineterminator="\n")

    # ---- Header ----
    w.writerow([f"Analysis Results - {run.get('name', '')}"])

    sel_cols = run.get("columns") or []
    sel_rows = run.get("rows") or []
    if sel_cols:
        w.writerow([f"Selected Columns: {', '.join(str(c) for c in sel_cols)}"])
    if sel_rows:
        w.writerow([f"Selected Rows: {', '.join(str(r) for r in sel_rows)}"])
    else:
        w.writerow(["Selected Rows: All"])

    measurement_levels = run.get("measurement_levels") or {}
    if not measurement_levels:
        msg = run.get("result_message")
        meta = getattr(msg, "metadata", None) if msg is not None else None
        if isinstance(meta, dict):
            measurement_levels = meta.get("measurement_levels") or {}
    if measurement_levels:
        w.writerow(["Column Measurement Levels:"])
        for col in (sel_cols or list(measurement_levels.keys())):
            level = measurement_levels.get(col)
            if level:
                w.writerow([f"  {col}: {level}"])

    w.writerow([])

    # ---- Results section ----
    w.writerow(["=== Results ==="])
    results_df = _build_results_dataframe(run)
    buf.flush()
    if not results_df.empty:
        buf.write(results_df.to_csv(index=False, sep=sep, lineterminator="\n"))
    else:
        w.writerow(["(no computed results)"])

    w.writerow([])

    # ---- Selected Data section ----
    w.writerow(["=== Selected Data ==="])
    data = run.get("data")
    buf.flush()
    if data is not None and not data.empty:
        buf.write(data.to_csv(index=False, sep=sep, lineterminator="\n"))
    else:
        w.writerow(["(no data)"])

    return buf.getvalue()


def _build_export_text(run: dict) -> str:
    """
    Build the plain-text export string for a run's .txt download.

    Sections included:
        - Run name header
        - Methods applied (if any)
        - Visualizations applied (if any)
        - Selected data as an ASCII table

    Args:
        run: The run dict to export.

    Returns:
        A multi-line string ready to be written to a .txt file.
    """
    lines = [f"Analysis Results — {run['name']}", ""]
    # --- Req 3.9: Include the exact row/column selection ---
    sel_cols = run.get("columns", [])
    sel_rows = run.get("rows", [])
    if sel_cols:
        lines.append(f"Selected Columns: {', '.join(str(c) for c in sel_cols)}")
    if sel_rows:
        lines.append(f"Selected Rows: {', '.join(str(r) for r in sel_rows)}")
    else:
        lines.append("Selected Rows: All")
    # --- Req 4.1: Include the measurement level tagged on each selected column.
    # Fresh runs populate run["measurement_levels"]; replayed runs only have it
    # on result_message.metadata. Check both.
    measurement_levels = run.get("measurement_levels") or {}
    if not measurement_levels:
        msg = run.get("result_message")
        meta = getattr(msg, "metadata", None) if msg is not None else None
        if isinstance(meta, dict):
            measurement_levels = meta.get("measurement_levels") or {}
    if measurement_levels:
        lines.append("Column Measurement Levels:")
        for col in sel_cols or list(measurement_levels.keys()):
            level = measurement_levels.get(col)
            if level:
                lines.append(f"  - {col}: {level}")
    lines.append("")

    if run.get("cards"):
        stat_cards = [c for c in run["cards"] if c[0] == "stat"]
        error_cards = [c for c in run["cards"] if c[0] == "error"]

        if stat_cards:
            lines.append("Methods Applied:")
            for card in stat_cards:
                title  = card[1].replace("<b>", "").replace("</b>", "")
                value  = card[2]
                if len(card) == 4:
                    subtext = card[3]
                    lines.append(f"- {title}: {value} ({subtext})")
                else:
                    lines.append(f"- {title}: {value}")
            lines.append("")

        if error_cards:
            lines.append("Errors:")
            for card in error_cards:
                title = card[1].replace("<b>", "").replace("</b>", "")
                lines.append(f"- {title}: {card[2]}")
            lines.append("")

    if run.get("visualizations"):
        lines.append("Visualizations Applied:")
        for v in run["visualizations"]:
            lines.append(f"- {v}")
        lines.append("")

    precision_warnings = run.get("precision_warnings") or []
    if precision_warnings:
        lines.append("Precision / Overflow Notices:")
        for w in precision_warnings:
            lines.append(f"  [{w['name']}] {w['note']}")
        lines.append("")

    lines.append("Selected Data:")
    lines.append(df_to_ascii_table(run["data"]))

    return "\n".join(lines)

