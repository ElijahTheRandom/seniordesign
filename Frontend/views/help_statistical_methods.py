"""
views/help_statistical_methods.py
----------------------------------
Renders the PS Analytics help page for statistical methods.

WHY THIS FILE EXISTS:
    The help page provides users with information about the different
    statistical methods available in the PS Analytics application.

PUBLIC INTERFACE:
    render_help_statistical_methods()
"""

import streamlit as st

st.markdown("""
<style>
div[data-testid="stAppViewContainer"] .block-container {
    padding-left: 0.5rem !important;
    padding-right: 1rem !important;
}
</style>
""", unsafe_allow_html=True)

def render_help_statistical_methods() -> None:
    """
    Render the help page for statistical methods.
    
    Displays information about the various statistical methods
    available in the PS Analytics application.
    """
    st.markdown("<div style='margin-top: 1rem;'></div>", unsafe_allow_html=True)
    st.markdown(
        "<hr style='margin: 0; border: none; height: 1px; "
        "background: linear-gradient(90deg, transparent 0%, "
        "rgba(228, 120, 29, 0.5) 50%, transparent 100%);' />",
        unsafe_allow_html=True
    )
    
    # Create a container with padding/indentation
    content_col, _ = st.columns([3, 2], gap="medium")
    
    with content_col:
        st.header("Statistical Methods", anchor=False)
        # Additional content will be added here in the future
