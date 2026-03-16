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

def render_load_previous_runs() -> None:
    """
    Render the load previous runs page for statistical methods.
    
    Displays a list of stored runs that the user has saved in the PS Analytics application.
    This allows users to easily access and reopen their previous runs without having to
    start from scratch each time.
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
        st.header("Load Previous Runs", anchor=False)
        # Additional content will be added here in the future