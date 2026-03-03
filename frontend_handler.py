"""
frontend_handler.py
-------------------
Routes result messages from BackendHandler to Streamlit UI components.

RESPONSIBILITIES:
    - Receive and store result messages from the backend
    - Route statistical (numeric/text) results to stat card displays
    - Route graphical results to image/chart containers
    - Manage run history in st.session_state
    - Handle partial failures gracefully (per-method error display)
    - Support sidebar run selection

NOT RESPONSIBLE FOR:
    - Performing any statistical computation
    - Knowing which specific methods exist (fully dynamic dispatch)
    - Data loading or CSV parsing

PUBLIC INTERFACE:
    FrontendHandler
        .handle_result_message(message)  → stores + renders
        .render_results(run_id)          → renders a stored run by ID
        .store_run(message)              → persists to session_state
        .render_error(method_name, err)  → renders a single error card
        .render_sidebar()               → run selector + metadata

SESSION STATE KEYS MANAGED:
    st.session_state["ps_runs"]          : dict[run_id, RunRecord]
    st.session_state["ps_active_run_id"] : str | None
"""

from __future__ import annotations

import io
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import streamlit as st

# ---------------------------------------------------------------------------
# Internal data model
# ---------------------------------------------------------------------------

@dataclass
class RunRecord:
    """
    Lightweight snapshot of one completed (or partially completed) analysis.

    Attributes:
        run_id:      Unique identifier for this run.
        name:        Human-readable label shown in the sidebar.
        created_at:  ISO timestamp of when this record was stored.
        stat_results: List of successful numeric/text result dicts.
        chart_results: List of successful graphical result dicts.
        errors:      List of error result dicts for failed methods.
        raw_message: The original Message object (kept for re-rendering).
    """
    run_id: str
    name: str
    created_at: str
    stat_results: list[dict[str, Any]] = field(default_factory=list)
    chart_results: list[dict[str, Any]] = field(default_factory=list)
    errors: list[dict[str, Any]] = field(default_factory=list)
    raw_message: Any = None  # Message object; typed as Any to avoid import coupling


# ---------------------------------------------------------------------------
# Result type classifiers
# ---------------------------------------------------------------------------

def _is_chart_result(result: dict[str, Any]) -> bool:
    """
    Return True if this result contains graphical output (image buffer or path).

    A result is considered a chart result when it carries one of:
        - "image"  : bytes / BytesIO (in-memory image buffer)
        - "path"   : str             (file path to a saved image/chart)
        - "figure" : matplotlib/plotly figure object
    """
    return any(k in result for k in ("image", "path", "figure"))


def _is_stat_result(result: dict[str, Any]) -> bool:
    """
    Return True if this result carries a numeric or text value for display.
    """
    return "value" in result and not _is_chart_result(result)


# ---------------------------------------------------------------------------
# FrontendHandler
# ---------------------------------------------------------------------------

class FrontendHandler:
    """
    Routes BackendHandler result messages to Streamlit UI components.

    Design principles
    -----------------
    * Fully dynamic: no hardcoded method names anywhere.
    * Modular: each rendering concern is an isolated private method.
    * Tolerant: partial failures never prevent successful results from showing.
    * Stateless per render: all persistent state lives in st.session_state.
    """

    # Session-state keys
    _RUNS_KEY: str = "ps_runs"
    _ACTIVE_KEY: str = "ps_active_run_id"

    # ---------------------------------------------------------------------------
    # Session-state bootstrap
    # ---------------------------------------------------------------------------

    @classmethod
    def _ensure_session_state(cls) -> None:
        """Initialise session-state keys on first call."""
        if cls._RUNS_KEY not in st.session_state:
            st.session_state[cls._RUNS_KEY] = {}
        if cls._ACTIVE_KEY not in st.session_state:
            st.session_state[cls._ACTIVE_KEY] = None

    # ---------------------------------------------------------------------------
    # Public interface
    # ---------------------------------------------------------------------------

    def handle_result_message(self, message: Any) -> None:
        """
        Entry point called by the main page after BackendHandler returns.

        Stores the run and immediately renders it.

        Args:
            message: A Message object whose `.results` list has been populated
                     by BackendHandler.handle_request().
        """
        self._ensure_session_state()
        run_id = self.store_run(message)
        self.render_results(run_id)

    def store_run(self, message: Any) -> str:
        """
        Partition message results into stat/chart/error buckets and persist.

        Args:
            message: Populated Message object from BackendHandler.

        Returns:
            The run_id string assigned to this run.
        """
        self._ensure_session_state()

        run_id = str(uuid.uuid4())
        dataset_id = getattr(message, "dataset_id", None) or "unknown"
        name = f"Run — {dataset_id} @ {datetime.now().strftime('%H:%M:%S')}"

        stat_results: list[dict] = []
        chart_results: list[dict] = []
        errors: list[dict] = []

        for result in (message.results or []):
            if not isinstance(result, dict):
                continue

            if not result.get("ok", True):
                errors.append(result)
            elif _is_chart_result(result):
                chart_results.append(result)
            else:
                stat_results.append(result)

        record = RunRecord(
            run_id=run_id,
            name=name,
            created_at=datetime.now().isoformat(),
            stat_results=stat_results,
            chart_results=chart_results,
            errors=errors,
            raw_message=message,
        )

        st.session_state[self._RUNS_KEY][run_id] = record
        st.session_state[self._ACTIVE_KEY] = run_id
        return run_id

    def render_results(self, run_id: str) -> None:
        """
        Render the full results page for the given run_id.

        Renders in order: stat cards → charts → errors → action buttons.
        If run_id is not found in session state, shows a warning.

        Args:
            run_id: The ID of the run to render.
        """
        self._ensure_session_state()
        runs: dict[str, RunRecord] = st.session_state[self._RUNS_KEY]

        if run_id not in runs:
            st.warning(f"Run `{run_id}` not found in session state.")
            return

        record = runs[run_id]

        st.markdown(
            "<hr style='margin: 0; border: none; height: 1px; "
            "background: linear-gradient(90deg, transparent 0%, "
            "rgba(228, 120, 29, 0.5) 50%, transparent 100%);' />",
            unsafe_allow_html=True,
        )
        st.header(f"Analysis Results — {record.name}", anchor=False)
        st.markdown("---")

        self._render_stat_section(record)
        self._render_chart_section(record)
        self._render_error_section(record)
        self._render_action_buttons(record)

    def render_error(self, method_name: str, error: str) -> None:
        """
        Render a single inline error card for a failed method.

        Args:
            method_name: The statistical method that failed.
            error:       Human-readable error string from the backend.
        """
        st.markdown(
            f"""
            <div style="
                border: 1px solid #c0392b;
                border-radius: 8px;
                padding: 1rem 1.2rem;
                background: rgba(192, 57, 43, 0.08);
                margin-bottom: 0.8rem;
            ">
                <div style="font-weight: 600; color: #c0392b; margin-bottom: 0.25rem;">
                    ⚠ {method_name} failed
                </div>
                <div style="font-size: 0.85rem; color: #888;">{error}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    def render_sidebar(self) -> str | None:
        """
        Render a run-selector in the Streamlit sidebar.

        Returns:
            The run_id currently selected by the user, or None if no runs exist.
        """
        self._ensure_session_state()
        runs: dict[str, RunRecord] = st.session_state[self._RUNS_KEY]

        with st.sidebar:
            st.subheader("Previous Runs")

            if not runs:
                st.caption("No runs yet.")
                return None

            run_options = {
                record.name: run_id
                for run_id, record in reversed(list(runs.items()))
            }

            selected_name = st.radio(
                "Select a run to view:",
                options=list(run_options.keys()),
                index=0,
                label_visibility="collapsed",
            )

            chosen_id = run_options[selected_name]
            st.session_state[self._ACTIVE_KEY] = chosen_id
            return chosen_id

    # ---------------------------------------------------------------------------
    # Private section renderers
    # ---------------------------------------------------------------------------

    def _render_stat_section(self, record: RunRecord) -> None:
        """Render all numeric/text stat cards for this run."""
        if not record.stat_results:
            return

        st.subheader("Statistical Results", anchor=False)
        st.markdown("<div style='margin-bottom: 1.5rem;'></div>", unsafe_allow_html=True)

        for i in range(0, len(record.stat_results), 3):
            cols = st.columns([1, 1, 1], gap="large")
            for j in range(3):
                idx = i + j
                if idx < len(record.stat_results):
                    with cols[j]:
                        self._render_stat_card(record.stat_results[idx])
            st.markdown("<div style='margin-bottom: 1.5rem;'></div>", unsafe_allow_html=True)

        st.markdown("---")

    def _render_stat_card(self, result: dict[str, Any]) -> None:
        """
        Render a single stat result card.

        Reads the following keys from the result dict (all optional except id):
            id            : method name used as title fallback
            value         : primary display value
            params_used   : shown as subtext if present
            loss_of_precision : appends a warning icon if True
        """
        method_id: str = result.get("id", "Unknown")
        value: Any = result.get("value", "—")
        params: dict = result.get("params_used") or {}
        precision_loss: bool = result.get("loss_of_precision", False)

        title = method_id.replace("_", " ").title()
        if precision_loss:
            title += " ⚠"

        value_str = f"{value:.4g}" if isinstance(value, float) else str(value)

        subtext_parts = [f"{k}={v}" for k, v in params.items()]
        subtext_html = (
            f'<div style="font-size:0.75rem;color:#888;margin-top:0.3rem;">'
            f'{", ".join(subtext_parts)}</div>'
            if subtext_parts else ""
        )

        st.markdown(
            f"""
            <div style="
                border: 1px solid rgba(228,120,29,0.3);
                border-radius: 10px;
                padding: 1.2rem;
                background: rgba(228,120,29,0.05);
                text-align: center;
                min-height: 100px;
            ">
                <div style="font-weight:600;font-size:0.95rem;color:#e4781d;
                            margin-bottom:0.4rem;">{title}</div>
                <div style="font-size:1.6rem;font-weight:700;">{value_str}</div>
                {subtext_html}
            </div>
            """,
            unsafe_allow_html=True,
        )

    def _render_chart_section(self, record: RunRecord) -> None:
        """Render all graphical results (images, paths, figures)."""
        if not record.chart_results:
            return

        st.subheader("Visualizations", anchor=False)
        st.markdown("<div style='margin-bottom: 1rem;'></div>", unsafe_allow_html=True)

        for result in record.chart_results:
            self._render_single_chart(result)

        st.markdown("---")

    def _render_single_chart(self, result: dict[str, Any]) -> None:
        """
        Route a single chart result to the correct Streamlit renderer.

        Priority order: figure → image buffer → file path.
        """
        method_id = result.get("id", "Chart")
        caption = method_id.replace("_", " ").title()

        if "figure" in result:
            # Matplotlib or Plotly figure object
            fig = result["figure"]
            # Try Plotly first, fall back to Matplotlib
            try:
                st.plotly_chart(fig, use_container_width=True)
            except Exception:
                try:
                    st.pyplot(fig)
                except Exception as exc:
                    st.warning(f"Could not render figure for {caption}: {exc}")

        elif "image" in result:
            img = result["image"]
            if isinstance(img, bytes):
                img = io.BytesIO(img)
            st.image(img, caption=caption, use_container_width=True)

        elif "path" in result:
            path: str = result["path"]
            try:
                st.image(path, caption=caption, use_container_width=True)
            except Exception as exc:
                st.warning(f"Could not load image at `{path}` for {caption}: {exc}")

        else:
            st.info(f"{caption}: no renderable output.")

    def _render_error_section(self, record: RunRecord) -> None:
        """Render all method-level errors as a collapsible block."""
        if not record.errors:
            return

        with st.expander(f"⚠ {len(record.errors)} method(s) failed", expanded=False):
            for err in record.errors:
                self.render_error(
                    method_name=err.get("id", "Unknown"),
                    error=err.get("error", "An unknown error occurred."),
                )

    def _render_action_buttons(self, record: RunRecord) -> None:
        """Render Export and Delete action buttons for this run."""
        btn_export, btn_delete = st.columns([1, 1])

        with btn_export:
            export_text = self._build_export_text(record)
            st.download_button(
                label="⬇ Export Results",
                data=export_text,
                file_name=f"{record.name}.txt",
                mime="text/plain",
                use_container_width=True,
            )

        with btn_delete:
            if st.button("🗑 Delete This Run", use_container_width=True,
                         key=f"delete_{record.run_id}"):
                del st.session_state[self._RUNS_KEY][record.run_id]
                runs_remaining = st.session_state[self._RUNS_KEY]
                st.session_state[self._ACTIVE_KEY] = (
                    next(reversed(runs_remaining)) if runs_remaining else None
                )
                st.rerun()

    # ---------------------------------------------------------------------------
    # Export helper
    # ---------------------------------------------------------------------------

    def _build_export_text(self, record: RunRecord) -> str:
        """
        Build a plain-text summary of the run for download.

        Args:
            record: The RunRecord to export.

        Returns:
            Multi-line string suitable for a .txt file.
        """
        lines = [f"Analysis Results — {record.name}", f"Run ID: {record.run_id}",
                 f"Created: {record.created_at}", ""]

        if record.stat_results:
            lines.append("=== Statistical Results ===")
            for r in record.stat_results:
                method = r.get("id", "unknown")
                value = r.get("value", "N/A")
                params = r.get("params_used") or {}
                param_str = f"  (params: {params})" if params else ""
                lines.append(f"  {method}: {value}{param_str}")
            lines.append("")

        if record.chart_results:
            lines.append("=== Visualizations ===")
            for r in record.chart_results:
                method = r.get("id", "unknown")
                path = r.get("path", "<in-memory>")
                lines.append(f"  {method}: {path}")
            lines.append("")

        if record.errors:
            lines.append("=== Errors ===")
            for r in record.errors:
                method = r.get("id", "unknown")
                error = r.get("error", "unknown error")
                lines.append(f"  {method}: {error}")
            lines.append("")

        return "\n".join(lines)