"""
styles/theme.py
---------------
Loads and injects the PS Analytics CSS theme into the Streamlit app.

WHY THIS FILE EXISTS:
    Previously, all styling was applied via ~19 separate st.markdown()
    calls scattered through mainpage.py. This file replaces all of them
    with a single function call: inject_styles().

    The actual CSS lives in theme.css (same directory), which your IDE
    can lint, format, and autocomplete properly — unlike CSS buried inside
    Python triple-quoted strings.

USAGE:
    from styles.theme import inject_styles

    # Call once after st.set_page_config(), before rendering any UI:
    inject_styles()

HOW IT WORKS:
    1. Reads theme.css from disk at the path relative to this file.
    2. Wraps the content in a <style> tag.
    3. Calls st.markdown(..., unsafe_allow_html=True) once.

    All 19 previous st.markdown("<style>...") calls are now this
    single function call.
"""

import os
import streamlit as st


# Resolve the CSS file path relative to this module's location.
# This means inject_styles() works correctly regardless of which
# directory the app is launched from.
_CSS_PATH = os.path.join(os.path.dirname(__file__), "theme.css")


def inject_styles() -> None:
    """
    Read theme.css and inject it into the Streamlit page.

    Call this once at the top of mainpage.py, after st.set_page_config()
    and before any rendering code.

    Raises:
        FileNotFoundError: If theme.css cannot be found at the expected
            path. This indicates the styles/ directory is missing or the
            file was renamed/deleted.
    """
    if not os.path.exists(_CSS_PATH):
        raise FileNotFoundError(
            f"Theme CSS not found at: {_CSS_PATH}\n"
            f"Expected location: styles/theme.css"
        )

    with open(_CSS_PATH, "r", encoding="utf-8") as f:
        css = f.read()

    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
