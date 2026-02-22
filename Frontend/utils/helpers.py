"""
utils/helpers.py
----------------
Pure utility functions for PS Analytics.

WHY THIS FILE EXISTS:
    These functions were previously defined at the top of mainpage.py,
    interspersed with session state initialization and UI code. They are
    "pure" in the functional programming sense: given the same inputs,
    they always return the same output and have no side effects.

    Because they have zero dependency on Streamlit, they can be:
        - Tested with a simple `pytest` call, no browser needed
        - Imported by any module without pulling in the whole app
        - Understood in isolation without reading mainpage.py

THE RULE FOR THIS FILE:
    No `import streamlit`. No `st.*` calls. No session state access.
    If a function needs to render something, it belongs in views/, not here.
"""

import base64
import os

import pandas as pd


# ---------------------------------------------------------------------------
# File Utilities
# ---------------------------------------------------------------------------

def image_to_base64(path: str) -> str:
    """
    Read an image file from disk and return its base64-encoded string.

    Used to embed images directly in HTML/CSS without a separate HTTP
    request — necessary inside st.markdown() blocks.

    Args:
        path: Absolute or relative path to the image file.

    Returns:
        A base64-encoded UTF-8 string of the file's raw bytes.
    """
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()


# ---------------------------------------------------------------------------
# DataFrame Utilities
# ---------------------------------------------------------------------------

def strip_index(df: pd.DataFrame) -> pd.DataFrame:
    """
    Return a copy of df with its index reset to the default RangeIndex.

    Useful before passing DataFrames to AG Grid, which builds its own
    row numbering and can behave unexpectedly with non-default indices.

    Args:
        df: Any DataFrame.

    Returns:
        A new DataFrame with the same data but a fresh integer index.
    """
    return pd.DataFrame(df.values, columns=df.columns)


def df_to_ascii_table(df: pd.DataFrame) -> str:
    """
    Render a DataFrame as a plain-text ASCII table.

    Used when exporting analysis results to a .txt file so the output
    is human-readable without requiring Excel or a data viewer.

    Example output:
        +-------+-------+
        | col_a | col_b |
        +=======+=======+
        | 1     | 2     |
        +-------+-------+
        | 3     | 4     |
        +-------+-------+

    Args:
        df: The DataFrame to render.

    Returns:
        A multi-line string containing the ASCII table.
    """
    df_str = df.astype(str)

    # Determine the minimum column width needed to fit both header and data
    col_widths = {
        col: max(df_str[col].map(len).max(), len(col))
        for col in df_str.columns
    }

    def _border(fill: str) -> str:
        """Build a horizontal border row using the given fill character."""
        row = "+"
        for col in df_str.columns:
            row += fill * (col_widths[col] + 2) + "+"
        return row + "\n"

    def _data_row(row: pd.Series) -> str:
        """Build a single data row."""
        line = "|"
        for col in df_str.columns:
            line += " " + str(row[col]).ljust(col_widths[col]) + " |"
        return line + "\n"

    # Header
    header = "|"
    for col in df_str.columns:
        header += " " + col.ljust(col_widths[col]) + " |"
    header += "\n"

    # Assemble: top border + header + double-line separator + data rows
    table = _border("-") + header + _border("=")
    for _, row in df_str.iterrows():
        table += _data_row(row) + _border("-")

    return table


# ---------------------------------------------------------------------------
# Grid Selection Utilities
# ---------------------------------------------------------------------------

def normalize_grid_selection(
    selection: list | None,
    df: pd.DataFrame
) -> dict | None:
    """
    Normalize the raw selection payload from AG Grid Range into a clean
    dict of column names and 1-based row indices.

    AG Grid returns selection as a list of range objects, each with:
        { "startRow": int, "endRow": int, "columns": [str, ...] }

    This function:
        1. Validates and coerces the raw data
        2. Deduplicates rows and columns across multiple ranges
        3. Preserves the original column order from the DataFrame
        4. Returns 1-based row indices to match the UI's row selector

    Args:
        selection: Raw list of range dicts from aggrid_range(), or None.
        df:        The DataFrame currently displayed in the grid.

    Returns:
        { "columns": [str, ...], "rows": [int, ...] }  on success
        None if selection is empty, None, or contains no valid ranges.
    """
    if not selection:
        return None

    selected_cols: set[str] = set()
    selected_rows: set[int] = set()
    col_order = list(df.columns)

    for rng in selection:
        start_row = rng.get("startRow")
        end_row = rng.get("endRow")
        cols = rng.get("columns") or []

        if start_row is None or end_row is None or not cols:
            continue

        try:
            start = int(start_row)
            end = int(end_row)
        except (TypeError, ValueError):
            continue

        for col in cols:
            if col in df.columns:
                selected_cols.add(col)

        # Convert 0-based AG Grid indices to 1-based UI row numbers
        for row_idx in range(start, end + 1):
            selected_rows.add(row_idx + 1)

    if not selected_cols and not selected_rows:
        return None

    return {
        "columns": sorted(selected_cols, key=lambda c: col_order.index(c)),
        "rows": sorted(selected_rows),
    }


def apply_grid_selection_to_filters(
    selection: list | None,
    df: pd.DataFrame
) -> None:
    """
    Sync the AG Grid range selection into Streamlit session state.

    Writes to:
        st.session_state["selected_columns"]  – list of column names
        st.session_state["selected_rows"]     – list of 1-based row ints
        st.session_state["last_grid_selection"] – dedup signature tuple

    This function is intentionally the ONE place where grid selection
    is translated into session state. The Analysis Configuration panel
    reads from session state, not from the grid directly — keeping those
    two widgets decoupled.

    Early-exits without writing if the selection hasn't changed since the
    last call (prevents unnecessary reruns).

    Args:
        selection: Raw list of range dicts from aggrid_range(), or None.
        df:        The DataFrame currently displayed in the grid.
    """
    # Import here to avoid a circular dependency if this module is ever
    # tested standalone. `st` is the only Streamlit symbol we need and
    # only for session state — no rendering happens here.
    import streamlit as st

    normalized = normalize_grid_selection(selection, df)
    if not normalized:
        return

    signature = (tuple(normalized["columns"]), tuple(normalized["rows"]))
    if st.session_state.get("last_grid_selection") == signature:
        # Nothing changed — skip the write to avoid triggering a rerun
        return

    st.session_state["selected_columns"] = normalized["columns"]
    st.session_state["selected_rows"] = normalized["rows"]
    st.session_state["last_grid_selection"] = signature


# ---------------------------------------------------------------------------
# Streamlit Utilities
# ---------------------------------------------------------------------------

def render_modal_content(img_path: str, message: str) -> None:
    """
    Render an image centred above a message body inside a modal container.

    Used by both the error modal (warningSquirrel) and success modal
    (huzzahAhSquirrel) in mainpage.py.

    Args:
        img_path: Absolute path to the image asset to display.
        message:  Multi-line string. Blank lines become vertical spacers.
    """
    from PIL import Image
    # Import here to avoid a circular dependency if this module is ever
    # tested standalone. `st` is the only Streamlit symbol we need and
    # only for session state — no rendering happens here.
    import streamlit as st

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if os.path.exists(img_path):
            st.image(Image.open(img_path))
        else:
            st.error(f"Image not found: {img_path}")

    st.markdown("---")
    for line in message.split("\n"):
        st.markdown(line if line.strip() else "")
