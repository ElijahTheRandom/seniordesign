import streamlit as st
import pandas as pd
import uuid
import base64
import html
import os
import io
import pprint
import sys

print("Loading mainpage.py...")

# Set up base directory for assets
BASE_DIR = os.path.dirname(__file__)
FRONTEND_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))
if FRONTEND_DIR not in sys.path:
    sys.path.insert(0, FRONTEND_DIR)

from PIL import Image
from streamlit_modal import Modal
from streamlit_aggrid_range import aggrid_range

# Function to convert image to base64
def image_to_base64(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()
    
def strip_index(df):
    return pd.DataFrame(df.values, columns=df.columns)

def df_to_ascii_table(df):
    # Convert everything to strings
    df_str = df.astype(str)

    # Get column widths
    col_widths = {
        col: max(df_str[col].map(len).max(), len(col))
        for col in df_str.columns
    }

    # Build top border
    top = "+"
    for col in df_str.columns:
        top += "-" * (col_widths[col] + 2) + "+"
    top += "\n"

    # Build header row
    header = "|"
    for col in df_str.columns:
        header += " " + col.ljust(col_widths[col]) + " |"
    header += "\n"

    # Build separator under header
    mid = "+"
    for col in df_str.columns:
        mid += "=" * (col_widths[col] + 2) + "+"
    mid += "\n"

    # Build data rows
    rows = ""
    for _, row in df_str.iterrows():
        rows += "|"
        for col in df_str.columns:
            rows += " " + str(row[col]).ljust(col_widths[col]) + " |"
        rows += "\n"
        
        # Add row separator
        rows += "+"
        for col in df_str.columns:
            rows += "-" * (col_widths[col] + 2) + "+"
        rows += "\n"

    return top + header + mid + rows


def normalize_grid_selection(selection, df):
    if not selection:
        return None

    selected_cols = set()
    selected_rows = set()
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

        for row_idx in range(start, end + 1):
            selected_rows.add(row_idx + 1)

    if not selected_cols and not selected_rows:
        return None

    return {
        "columns": sorted(selected_cols, key=lambda c: col_order.index(c)),
        "rows": sorted(selected_rows),
    }


def apply_grid_selection_to_filters(selection, df):
    normalized = normalize_grid_selection(selection, df)
    if not normalized:
        return

    signature = (tuple(normalized["columns"]), tuple(normalized["rows"]))
    if st.session_state.get("last_grid_selection") == signature:
        return

    st.session_state["selected_columns"] = normalized["columns"]
    st.session_state["selected_rows"] = normalized["rows"]
    st.session_state["last_grid_selection"] = signature


def render_modal_content(img_path, message):
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        if os.path.exists(img_path):
            img = Image.open(img_path)
            st.image(img)
        else:
            st.error(f"Image not found: {img_path}")

    st.markdown("---")

    for line in message.split("\n"):
        st.markdown(line if line.strip() else "")

# Card rendering functions
def stat_card(title, value, subtext=None):
    st.markdown(f"""
    <div class="analysis-card">
        <div class="analysis-title">{title}</div>
        <div class="analysis-value">{value}</div>
        {f'<div class="analysis-subtext">{subtext}</div>' if subtext else ''}
    </div>
    """, unsafe_allow_html=True)

def visual_card(title, render_fn):
    st.markdown(f"""
    <div class="analysis-card">
        <div class="analysis-title">{title}</div>
    """, unsafe_allow_html=True)
    
    render_fn()  # chart / plot function
    
    st.markdown("</div>", unsafe_allow_html=True)

# Session state
if "analysis_runs" not in st.session_state:
    st.session_state.analysis_runs = []

if "modal_message" not in st.session_state:
    st.session_state.modal_message = ""

if "has_file" not in st.session_state:
    st.session_state.has_file = False

if "checkbox_key_onecol" not in st.session_state:
    st.session_state.checkbox_key_onecol = 0   # Mean, Median, etc.

if "checkbox_key_twocol" not in st.session_state:
    st.session_state.checkbox_key_twocol = 0   # Pearson, Spearman, Regression

if "show_invalid_modal" not in st.session_state:
    st.session_state.show_invalid_modal = False

if "show_success_modal" not in st.session_state:
    st.session_state.show_success_modal = False
    
if "active_run_id" not in st.session_state:
    st.session_state.active_run_id = None

if "saved_table" not in st.session_state:
    st.session_state.saved_table = None

if "saved_uploaded_file" not in st.session_state:
    st.session_state.saved_uploaded_file = None

if "selected_columns" not in st.session_state:
    st.session_state.selected_columns = []

if "selected_rows" not in st.session_state:
    st.session_state.selected_rows = []

if "last_grid_selection" not in st.session_state:
    st.session_state.last_grid_selection = None


# Page config
st.set_page_config(
    page_title="PS Analytics",
    page_icon=os.path.join(BASE_DIR, "assets", "PStheMainMan.png"),
    layout="wide",
    initial_sidebar_state="expanded"
)

with st.sidebar:
    st.markdown("<hr class='sidebar-top-divider'>", unsafe_allow_html=True)
    st.header("Navigation")

    # --- Home button ---
    is_home_active = st.session_state.active_run_id is None
    if st.button(
        "Home",
        key="nav_home",
        use_container_width=True,
        type="primary" if is_home_active else "secondary"
    ):
        st.session_state.active_run_id = None
        st.rerun()

    st.markdown("---")

    # --- Analysis Runs ---
    st.header("Analysis Runs")

    for i, run in enumerate(st.session_state.analysis_runs):
        is_active = run["id"] == st.session_state.active_run_id

        cols = st.columns([6, 1])

        # Clickable run name (acts like a tab)
        with cols[0]:
            if st.button(
                run["name"],
                key=f"nav_run_{run['id']}",
                use_container_width=True,
                type="primary" if is_active else "secondary"
            ):
                st.session_state.active_run_id = run["id"]
                st.rerun()

        # Rename icon
        with cols[1]:
            if st.button(
                "✏️",
                key=f"rename_btn_{run['id']}",
                help="Rename Run"
            ):
                st.session_state["renaming_run_id"] = run["id"]

        # Inline rename input
        if st.session_state.get("renaming_run_id") == run["id"]:
            new_name = st.text_input(
                "Rename run",
                value=run["name"],
                key=f"rename_input_{run['id']}",
                label_visibility="collapsed"
            )

            rename_cols = st.columns(2)
            with rename_cols[0]:
                if st.button("Save", key=f"save_rename_{run['id']}"):
                    run["name"] = new_name.strip() or run["name"]
                    st.session_state["renaming_run_id"] = None
                    st.rerun()

            with rename_cols[1]:
                if st.button("Cancel", key=f"cancel_rename_{run['id']}"):
                    st.session_state["renaming_run_id"] = None
                    st.rerun()



# Create modal instances
error_modal = Modal(
    "Invalid Analysis",
    key="error_modal",
)

success_modal = Modal(
    "Success!",
    key="success_modal",
)

# Styling
st.markdown("""
<style>
/* Kill the link icon that sits inside the modal title */
div[data-testid="stModal"] h3 > a {
    display: none !important;
}

/* Ensure modal backdrop covers entire page including sidebar */
div[data-testid="stModal"] {
    position: fixed !important;
    top: 0 !important;
    left: 0 !important;
    right: 0 !important;
    bottom: 0 !important;
    z-index: 999999 !important;
    background-color: rgba(0, 0, 0, 0.5) !important;
}

/* Make sure sidebar is below modal */
section[data-testid="stSidebar"] {
    z-index: 1 !important;
}
</style>
""", unsafe_allow_html=True)

# Sidebar button alignment and active run emphasis
st.markdown("""
<style>

/* Target ONLY sidebar buttons - Base styling */
section[data-testid="stSidebar"] div[data-testid="stButton"] button {
    background-color: transparent !important;
    color: rgba(255, 255, 255, 0.8) !important;
    border: none !important;
    border-left: 3px solid transparent !important;
    border-radius: 6px !important;
    padding: 10px 12px !important;
    box-shadow: none !important;
    font-weight: 400 !important;
    text-align: left !important;
    transition: all 0.15s ease !important;
}

/* Secondary (inactive) buttons hover */
section[data-testid="stSidebar"] div[data-testid="stButton"] button[kind="secondary"]:hover {
    background-color: rgba(255, 255, 255, 0.05) !important;
    color: #ffffff !important;
    box-shadow: none !important;
}

/* Primary (active) buttons - Modern accent bar style */
section[data-testid="stSidebar"] div[data-testid="stButton"] button[kind="primary"] {
    background-color: rgba(228, 120, 29, 0.12) !important;
    border-left: 3px solid #e4781d !important;
    color: #ffffff !important;
    font-weight: 500 !important;
    box-shadow: none !important;
}

/* Focus — no big orange ring */
section[data-testid="stSidebar"] div[data-testid="stButton"] button:focus-visible {
    outline: none !important;
    box-shadow: none !important;
}

/* Rename icon button — extra subtle */
section[data-testid="stSidebar"] button:has(span:contains("✏️")) {
    padding: 4px !important;
    opacity: 0.75;
}

section[data-testid="stSidebar"] button:has(span:contains("✏️")):hover {
    opacity: 1;
    background-color: rgba(255, 255, 255, 0.08) !important;
}
</style>
""", unsafe_allow_html=True)

# Modern Glossy Black Background
st.markdown("""
<style>
/* Main app background - sophisticated black with depth */
.stApp,
[data-testid="stAppViewContainer"],
section[data-testid="stMain"] {
    background: radial-gradient(ellipse at top, #1a1a1a 0%, #0f0f0f 50%, #000000 100%) !important;
    position: static !important;
}
            
/* Make all Streamlit alert/info boxes orange themed */
div[data-testid="stAlert"] {
    background: linear-gradient(135deg, rgba(228, 120, 29, 0.18), rgba(228, 120, 29, 0.10)) !important;
    border: 1.5px solid rgba(228, 120, 29, 0.55) !important;
    border-radius: 10px !important;
    padding: 1rem 1.25rem !important;
    box-shadow:
        0 4px 12px rgba(0, 0, 0, 0.35),
        0 0 18px rgba(228, 120, 29, 0.25),
        inset 0 1px 2px rgba(255, 255, 255, 0.05) !important;
}
            
div[data-testid="stAlert"] { 
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15), 
    0 0 12px rgba(228, 120, 29, 0.25) !important; 
}

/* Make the text inside alerts white */
div[data-testid="stAlert"] p {
    color: rgba(255, 255, 255, 0.92) !important;
    font-weight: 500 !important;
}

/* Make the icon match the orange theme */
div[data-testid="stAlert"] svg {
    fill: #e4781d !important;
}
            
/* Remove the grey inner container inside alerts */
div[data-testid="stAlert"] > div {
    background: transparent !important;
    padding: 0 !important;
    margin: 0 !important;
    border: none !important;
}

/* Pull the custom sidebar <hr> upward to match main-page lines */
.sidebar-top-divider {
    margin-top: 0rem !important;   /* was -0.8rem */
    margin-bottom: 1.2rem !important;
}

/* Add subtle texture overlay for depth */
.stApp::before {
    content: '' !important;
    position: fixed !important;
    top: 0 !important;
    left: 0 !important;
    right: 0 !important;
    bottom: 0 !important;
    background-image: 
        radial-gradient(circle at 20% 30%, rgba(228, 120, 29, 0.02) 0%, transparent 50%),
        radial-gradient(circle at 80% 70%, rgba(228, 120, 29, 0.015) 0%, transparent 50%),
        url("data:image/svg+xml,%3Csvg viewBox='0 0 400 400' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)' opacity='0.025'/%3E%3C/svg%3E") !important;
    pointer-events: none !important;
    z-index: 0 !important;
    mix-blend-mode: overlay !important;
}

/* Ensure content stays above background */
.stApp > div,
[data-testid="stAppViewContainer"] > div {
    position: relative !important;
    z-index: 1 !important;
}

/* Add subtle shine effect on top */
.stApp::after {
    content: '' !important;
    position: fixed !important;
    top: 0 !important;
    left: 0 !important;
    right: 0 !important;
    height: 300px !important;
    background: linear-gradient(180deg, rgba(255, 255, 255, 0.01) 0%, transparent 100%) !important;
    pointer-events: none !important;
    z-index: 0 !important;
}
</style>
""", unsafe_allow_html=True)

# Modern enhancements - Glass morphism, cards, scrollbar, animations
st.markdown("""
<style>
/* Glass Morphism Sidebar - Enhanced Black */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, rgba(20, 20, 20, 0.95) 0%, rgba(10, 10, 10, 0.98) 100%) !important;
    backdrop-filter: blur(20px) saturate(180%) !important;
    border-right: 1px solid rgba(228, 120, 29, 0.15) !important;
    box-shadow: 4px 0 24px rgba(0, 0, 0, 0.5),
                inset -1px 0 0 rgba(255, 255, 255, 0.05) !important;
}

/* Custom Modern Scrollbar */
::-webkit-scrollbar {
    width: 8px;
    height: 8px;
}

::-webkit-scrollbar-track {
    background: rgba(255, 255, 255, 0.05);
    border-radius: 10px;
}

::-webkit-scrollbar-thumb {
    background: rgba(228, 120, 29, 0.5);
    border-radius: 10px;
}

::-webkit-scrollbar-thumb:hover {
    background: rgba(228, 120, 29, 0.7);
}


/* Modern Typography - Enhanced */
h1, h2, h3, h4 {
    font-weight: 600 !important;
    letter-spacing: -0.025em !important;
    background: linear-gradient(135deg, #ffffff 0%, rgba(255, 255, 255, 0.85) 100%) !important;
    -webkit-background-clip: text !important;
    -webkit-text-fill-color: transparent !important;
    background-clip: text !important;
    text-shadow: 0 2px 8px rgba(0, 0, 0, 0.3) !important;
    position: relative !important;
}

h1 {
    font-size: 2.2rem !important;
    font-weight: 700 !important;
    margin-bottom: 1.8rem !important;
    letter-spacing: -0.03em !important;
}

h2 {
    font-size: 1.6rem !important;
    margin-bottom: 1.5rem !important;
    font-weight: 600 !important;
}

h3 {
    font-size: 1.25rem !important;
    margin-bottom: 1.2rem !important;
    font-weight: 600 !important;
}

/* Body text and labels */
p, label, div[data-testid="stMarkdownContainer"] {
    line-height: 1.65 !important;
    color: rgba(255, 255, 255, 0.9) !important;
    font-weight: 400 !important;
    letter-spacing: 0.01em !important;
}

/* Labels specifically */
label {
    font-weight: 500 !important;
    color: rgba(255, 255, 255, 0.95) !important;
    font-size: 0.95rem !important;
    text-transform: none !important;
}

/* Captions with subtle style */
div[data-testid="stCaptionContainer"] {
    color: rgba(255, 255, 255, 0.6) !important;
    font-size: 0.875rem !important;
    font-style: italic !important;
    letter-spacing: 0.02em !important;
}

/* List items */
li {
    color: rgba(255, 255, 255, 0.85) !important;
    line-height: 1.7 !important;
    margin: 0.4rem 0 !important;
}

/* Add subtle glow to emphasized text */
strong, b {
    font-weight: 600 !important;
    color: rgba(255, 255, 255, 0.98) !important;
    text-shadow: 0 0 10px rgba(228, 120, 29, 0.2) !important;
}

/* Subtle text shimmer animation for headers */
@keyframes textShimmer {
    0% {
        background-position: -100% center;
    }
    100% {
        background-position: 200% center;
    }
}

h1, h2, h3 {
    background-size: 200% auto !important;
}

/* Add animated gradient underline to section headers */
h2::after, h3::after {
    content: '' !important;
    display: block !important;
    width: 60px !important;
    height: 3px !important;
    background: linear-gradient(90deg, #e4781d 0%, rgba(228, 120, 29, 0.5) 70%, transparent 100%) !important;
    margin-top: 12px !important;
    border-radius: 2px !important;
    animation: slideIn 0.6s ease-out !important;
}

@keyframes slideIn {
    from {
        width: 0;
        opacity: 0;
    }
    to {
        width: 60px;
        opacity: 1;
    }
}

/* Add subtle hover effect to headers */
h1:hover, h2:hover, h3:hover {
    animation: textShimmer 3s ease-in-out infinite !important;
}

/* Improve readability with text rendering */
* {
    -webkit-font-smoothing: antialiased !important;
    -moz-osx-font-smoothing: grayscale !important;
    text-rendering: optimizeLegibility !important;
}

/* Enhance button text */
button {
    font-weight: 500 !important;
    letter-spacing: 0.015em !important;
}

/* Section Dividers with Gradient */
hr {
    border: none !important;
    height: 1px !important;
    background: linear-gradient(90deg, 
        transparent 0%, 
        rgba(228, 120, 29, 0.5) 50%, 
        transparent 100%) !important;
    margin: 2rem 0 !important;
}

/* Pill-Style Tags for Selected Items - ENHANCED */
div[data-testid="stMultiSelect"] span[data-baseweb="tag"] {
    background: linear-gradient(135deg, rgba(228, 120, 29, 0.2), rgba(228, 120, 29, 0.15)) !important;
    border: 1.5px solid rgba(228, 120, 29, 0.5) !important;
    border-radius: 20px !important;
    padding: 4px 10px 4px 12px !important;
    margin: 2px 4px !important;
    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
    font-weight: 500 !important;
    font-size: 13px !important;
    line-height: 1.4 !important;
    display: inline-flex !important;
    align-items: center !important;
    gap: 6px !important;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2),
                0 0 8px rgba(228, 120, 29, 0.1) !important;
}

div[data-testid="stMultiSelect"] span[data-baseweb="tag"]:hover {
    background: linear-gradient(135deg, rgba(228, 120, 29, 0.3), rgba(228, 120, 29, 0.25)) !important;
    border-color: rgba(228, 120, 29, 0.7) !important;
    transform: scale(1.05) translateY(-1px) !important;
    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.3),
                0 0 16px rgba(228, 120, 29, 0.2) !important;
}

/* Ambient Glow Effect for Sidebar Active Elements Only */
section[data-testid="stSidebar"] button[kind="primary"]:not(:disabled) {
    box-shadow: 0 0 20px rgba(228, 120, 29, 0.15) !important;
    animation: pulse-glow 3s ease-in-out infinite !important;
}

@keyframes pulse-glow {
    0%, 100% {
        box-shadow: 0 0 20px rgba(228, 120, 29, 0.15) !important;
    }
    50% {
        box-shadow: 0 0 30px rgba(228, 120, 29, 0.25) !important;
    }
}

/* Smooth Micro-Animations for All Interactive Elements */
button, input, select, textarea, div[data-testid="stCheckbox"], 
div[data-testid="stMultiSelect"], div[data-testid="stSelectbox"] {
    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
}

button:active {
    transform: scale(0.98) !important;
}

/* Hover effects for all buttons */
button:hover:not(:disabled) {
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15) !important;
}

/* Input field animations */
div[data-testid="stMultiSelect"] div[role="combobox"]:focus-within {
    animation: input-focus 0.3s ease !important;
}

@keyframes input-focus {
    0% {
        transform: scale(1);
    }
    50% {
        transform: scale(1.01);
    }
    100% {
        transform: scale(1);
    }
}

/* Checkbox animation */
div[data-testid="stCheckbox"] input:checked + div:first-child {
    animation: checkbox-check 0.3s ease !important;
}

@keyframes checkbox-check {
    0% {
        transform: scale(0.8);
    }
    50% {
        transform: scale(1.1);
    }
    100% {
        transform: scale(1);
    }
}


/* Fade in animation - only for specific elements */
@keyframes fadeIn {
    from {
        opacity: 0;
        transform: translateY(20px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

@keyframes fadeInModal {
    from {
        opacity: 0;
        transform: scale(0.9) translateY(-20px);
    }
    to {
        opacity: 1;
        transform: scale(1) translateY(0);
    }
}

/* Apply fade in to file uploader */
div[data-testid="stFileUploader"] {
    animation: fadeIn 0.4s ease-out !important;
}

/* Apply fade in to modals - target the backdrop and content */
div[data-testid="stModal"] {
    animation: fadeInModal 0.5s cubic-bezier(0.34, 1.56, 0.64, 1) !important;
}

div[data-testid="stModal"] * {
    animation: fadeInModal 0.5s cubic-bezier(0.34, 1.56, 0.64, 1) !important;
}

/* Apply fade in to entire main content block when switching between homepage and runs */
.main .block-container {
    animation: fadeIn 0.6s ease-out !important;
}

/* Ensure all top-level children in main also animate */
.main .block-container > div {
    animation: fadeIn 0.6s ease-out !important;
}

/* Sidebar navigation hover animation */
section[data-testid="stSidebar"] div[data-testid="stButton"] button:hover {
    animation: button-hover 0.3s ease !important;
}

@keyframes button-hover {
    0% {
        transform: translateX(0);
    }
    50% {
        transform: translateX(3px);
    }
    100% {
        transform: translateX(0);
    }
}

/* Card-Style Containers with Depth - Modern Glossy Black */
div[data-testid="column"] {
    background: linear-gradient(145deg, rgba(25, 25, 25, 0.6), rgba(15, 15, 15, 0.4)) !important;
    border-radius: 16px !important;
    padding: 1rem !important;
    border: 1px solid rgba(255, 255, 255, 0.08) !important;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5),
                inset 0 1px 0 rgba(255, 255, 255, 0.05),
                0 0 0 1px rgba(255, 255, 255, 0.02) inset !important;
    backdrop-filter: blur(10px) !important;
    transition: all 0.3s ease !important;
}

div[data-testid="column"]:hover {
    border-color: rgba(228, 120, 29, 0.2) !important;
    box-shadow: 0 12px 48px rgba(0, 0, 0, 0.4),
                inset 0 1px 0 rgba(255, 255, 255, 0.08),
                0 0 20px rgba(228, 120, 29, 0.08) !important;
    transform: translateY(-2px) !important;
}

/* Status Badge Styling for Subheaders - Modern Glossy */
.stSubheader {
    display: inline-block !important;
    padding: 8px 16px !important;
    background: linear-gradient(135deg, rgba(228, 120, 29, 0.15), rgba(228, 120, 29, 0.08)) !important;
    border-left: 3px solid #e4781d !important;
    border-radius: 8px !important;
    margin-bottom: 1rem !important;
    box-shadow: 0 4px 12px rgba(228, 120, 29, 0.15),
                inset 0 1px 0 rgba(255, 255, 255, 0.05) !important;
    backdrop-filter: blur(8px) !important;
}
</style>
""", unsafe_allow_html=True)

# Sidebar toggle button styling and header adjustments
st.markdown("""
<style>
/* ===============================
   SIDEBAR TOGGLE – BOTH STATES
   =============================== */

/* ----- Hover when sidebar is OPEN ----- */
button[kind="secondary"][data-testid="collapsedControl"] {
    transition: background-color 0.15s ease-in-out !important;
}

button[kind="secondary"][data-testid="collapsedControl"]:hover {
    background-color: rgba(228, 120, 29, 0.20) !important;
    border: 1px solid rgba(228, 120, 29, 0.5) !important;
}

button[kind="secondary"][data-testid="collapsedControl"]:hover svg {
    fill: #e4781d !important;
}

/* ----- Toggle when sidebar is CLOSED (top header button) ----- */
header[data-testid="stHeader"] button {
    color: rgba(255, 255, 255, 0.7) !important;
    background: transparent !important;
    border: none !important;
    border-radius: 6px !important;
}

/* ----- Toggle when sidebar is OPEN (inside sidebar) ----- */
section[data-testid="stSidebar"] 
  div[data-testid="stSidebarCollapseButton"] 
  button {
    color: rgba(255, 255, 255, 0.7) !important;
    background: transparent !important;
    border: none !important;
    border-radius: 6px !important;
}

/* Hover — both states */
header[data-testid="stHeader"] button:hover,
section[data-testid="stSidebar"] 
  div[data-testid="stSidebarCollapseButton"] 
  button:hover {
    background: rgba(228, 120, 29, 0.12) !important;
}

/* Remove focus rings */
header[data-testid="stHeader"] button:focus-visible,
section[data-testid="stSidebar"] 
  div[data-testid="stSidebarCollapseButton"] 
  button:focus-visible {
    outline: none !important;
    box-shadow: none !important;
}
</style>
""", unsafe_allow_html=True)

# Header and container spacing adjustments - CONSOLIDATED
st.markdown("""
<style>
/* Keep header visible for sidebar toggle but minimize it */
header[data-testid="stHeader"] {
    background: radial-gradient(ellipse at bottom, #1a1a1a 0%, #0f0f0f 50%, #000000 100%) !important;
    height: 2.5rem !important;
    backdrop-filter: none !important;
    box-shadow: none !important;
    border-bottom: none !important;
    z-index: 999 !important;
}

/* Hide everything in header except sidebar toggle */
header[data-testid="stHeader"] > div:not(:first-child) {
    display: none !important;
}

/* Minimal top padding on all main containers to accommodate header */
/* Only pad the actual content containers — NOT the scroll wrapper */
/* SAFE: Only pad the *content*, not the scroll container */
.block-container {
    padding-top: 2.8rem;
    padding-left: 1rem;
    padding-right: 1rem;
    padding-bottom: 1rem !important;
}

/* DO NOT pad these — they are scroll containers */
div[data-testid="stMainBlockContainer"],
div[data-testid="stAppViewBlockContainer"] {
    padding: 0 !important;
}
            
/* Give the page breathing room at the bottom */
section[data-testid="stAppViewContainer"] > div:first-child {
    padding-bottom: 3rem !important;
}

/* Remove spacing from vertical blocks */
div[data-testid="stVerticalBlock"],
div[data-testid="stVerticalBlockBorderWrapper"] {
    gap: 0rem !important;
    margin-top: 0rem !important;
    padding-top: 0rem !important;
}

/* Remove anchor beside modal titles */
div[data-baseweb="stMarkdownContainer"] h3 a {
    display: none !important;
}
</style>
""", unsafe_allow_html=True)

# Checkbox and column selection styling
st.markdown("""
<style>
div[data-testid="stCheckbox"] span {
    background-color: #262730 !important;
    border-radius: 4px;
    border-color: #e4781d !important;
}
</style>
""", unsafe_allow_html=True)

# Multiselect selected item styling
st.markdown("""
<style>
/* COLUMN DROPDOWN — Subtle, modern, low‑orange version */
div[data-baseweb="select"] > div {
    background: linear-gradient(145deg, #1a1a1a, #0f0f0f) !important;
    border: 1.5px solid rgba(255,255,255,0.08) !important;   /* neutral border */
    border-radius: 10px !important;
    padding: 6px 10px !important;
    box-shadow:
        0 2px 8px rgba(0,0,0,0.35),
        inset 0 1px 2px rgba(255,255,255,0.05) !important;
    color: #ffffff !important;
    transition: all 0.2s ease !important;
}

/* Hover — just a whisper of orange */
div[data-baseweb="select"] > div:hover {
    border-color: rgba(228,120,29,0.35) !important;  /* subtle orange */
    box-shadow:
        0 4px 12px rgba(0,0,0,0.45),
        0 0 10px rgba(228,120,29,0.15),
        inset 0 1px 2px rgba(255,255,255,0.08) !important;
    transform: translateY(-1px);
}

/* Focus / open — slightly stronger but still not loud */
div[data-baseweb="select"] > div[aria-expanded="true"] {
    border-color: rgba(228,120,29,0.55) !important;
    box-shadow:
        0 6px 20px rgba(0,0,0,0.5),
        0 0 18px rgba(228,120,29,0.25),
        inset 0 1px 3px rgba(255,255,255,0.1) !important;
    transform: translateY(-1px) scale(1.01);
}

/* Options */
/* Option hover */
li[role="option"]:hover {
    background: rgba(255,255,255,0.06) !important;   /* neutral hover */
}/* FORCE all dropdown options to use glossy black unless hovered */
li[role="option"] {
    background: linear-gradient(145deg, #1a1a1a, #0f0f0f) !important;
    padding: 8px 12px !important;
    border-radius: 6px !important;
    color: rgba(255,255,255,0.9) !important;
    transition: all 0.15s ease !important;
}

/* KILL the orange selected-option background */
li[role="option"][aria-selected="true"] {
    background: linear-gradient(145deg, #1a1a1a, #0f0f0f) !important;
    border-left: 3px solid #e4781d !important; /* keeps your accent bar */
}
            
/* Remove horizontal scrollbar inside dropdown menus */
div[data-baseweb="menu"] {
    overflow-x: hidden !important;
}

div[data-baseweb="popover"],
div[data-baseweb="layer"],
div[data-baseweb="layer"] > div,
div[data-baseweb="popover"] > div {
    overflow-x: hidden !important;
}
</style>
""", unsafe_allow_html=True)

# Multiselect box styling
st.markdown("""
<style>
/* MULTISELECT — Modern base state with gradient border effect */
div[data-testid="stMultiSelect"] div[role="combobox"] {
    background: linear-gradient(145deg, #1e1e28, #262730) !important;
    border: 1.5px solid rgba(228, 120, 29, 0.4) !important;
    border-radius: 10px !important;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.25), 
                0 4px 16px rgba(0, 0, 0, 0.15),
                0 0 0 1px rgba(228, 120, 29, 0.1) inset,
                0 1px 2px rgba(255, 255, 255, 0.05) inset !important;
    padding: 8px 12px !important;
    margin: 4px 0 !important;
    transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
    min-height: 42px !important;
    position: relative !important;
    overflow: visible !important;
}

/* Add subtle shine effect at the top */
div[data-testid="stMultiSelect"] div[role="combobox"]::before {
    content: '' !important;
    position: absolute !important;
    top: 0 !important;
    left: 0 !important;
    right: 0 !important;
    height: 30% !important;
    background: linear-gradient(180deg, rgba(255, 255, 255, 0.03) 0%, transparent 100%) !important;
    border-radius: 10px 10px 0 0 !important;
    pointer-events: none !important;
}

/* Hover state with enhanced glow effect */
div[data-testid="stMultiSelect"] div[role="combobox"]:hover {
    border-color: rgba(228, 120, 29, 0.6) !important;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3), 
                0 6px 20px rgba(0, 0, 0, 0.2),
                0 0 25px rgba(228, 120, 29, 0.15),
                0 0 0 1px rgba(228, 120, 29, 0.2) inset,
                0 1px 3px rgba(255, 255, 255, 0.08) inset !important;
    transform: translateY(-2px) !important;
}

/* Focus / active / open with prominent glow */
div[data-testid="stMultiSelect"] div[role="combobox"][aria-expanded="true"],
div[data-testid="stMultiSelect"] div[role="combobox"]:focus,
div[data-testid="stMultiSelect"] div[role="combobox"]:focus-visible {
    outline: none !important;
    border-color: #e4781d !important;
    box-shadow: 0 6px 20px rgba(0, 0, 0, 0.35),
                0 8px 28px rgba(0, 0, 0, 0.25),
                0 0 35px rgba(228, 120, 29, 0.3),
                0 0 0 3px rgba(228, 120, 29, 0.35) !important;
    transform: translateY(-2px) scale(1.005) !important;
}

/* Dropdown menu styling */
div[data-testid="stMultiSelect"] ul[role="listbox"] {
    background: linear-gradient(145deg, #1e1e28, #262730) !important;
    border: 1.5px solid rgba(228, 120, 29, 0.4) !important;
    border-radius: 10px !important;
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4),
                0 0 40px rgba(228, 120, 29, 0.15) !important;
    padding: 8px !important;
    margin-top: 4px !important;
    backdrop-filter: blur(10px) !important;
}

/* Dropdown options */
div[data-testid="stMultiSelect"] li[role="option"] {
    border-radius: 6px !important;
    padding: 10px 12px !important;
    margin: 2px 0 !important;
    transition: all 0.2s ease !important;
    color: rgba(255, 255, 255, 0.87) !important;
}

/* Dropdown option hover */
div[data-testid="stMultiSelect"] li[role="option"]:hover {
    background: rgba(228, 120, 29, 0.15) !important;
    transform: translateX(4px) !important;
    box-shadow: 0 2px 8px rgba(228, 120, 29, 0.2) !important;
}

/* Selected dropdown option */
div[data-testid="stMultiSelect"] li[role="option"][aria-selected="true"] {
    background: rgba(228, 120, 29, 0.2) !important;
    border-left: 3px solid #e4781d !important;
    font-weight: 500 !important;
}

/* Input field inside multiselect */
div[data-testid="stMultiSelect"] input {
    color: rgba(255, 255, 255, 0.9) !important;
    font-size: 14px !important;
}

/* Arrow icon */
div[data-testid="stMultiSelect"] svg {
    fill: rgba(228, 120, 29, 0.8) !important;
    transition: transform 0.3s ease !important;
}

/* Rotate arrow when open */
div[data-testid="stMultiSelect"] div[role="combobox"][aria-expanded="true"] svg {
    transform: rotate(180deg) !important;
}

/* Remove Streamlit's default red borders */
div[data-testid="stMultiSelect"] * {
    border-color: rgba(228, 120, 29, 0.4) !important;
}

/* Label styling for multiselects */
div[data-testid="stMultiSelect"] label {
    color: rgba(255, 255, 255, 0.95) !important;
    font-weight: 500 !important;
    font-size: 14px !important;
    margin-bottom: 8px !important;
    letter-spacing: 0.02em !important;
}

/* Disabled multiselect state */
div[data-testid="stMultiSelect"]:has(div[role="combobox"][aria-disabled="true"]) div[role="combobox"] {
    background: linear-gradient(145deg, #1a1a1a, #1e1e1e) !important;
    border-color: rgba(100, 100, 100, 0.3) !important;
    box-shadow: none !important;
    opacity: 0.5 !important;
    cursor: not-allowed !important;
    transform: none !important;
}

div[data-testid="stMultiSelect"]:has(div[role="combobox"][aria-disabled="true"]) label {
    color: rgba(255, 255, 255, 0.4) !important;
}

/* Placeholder text styling */
div[data-testid="stMultiSelect"] input::placeholder {
    color: rgba(255, 255, 255, 0.4) !important;
    font-style: italic !important;
}

/* Empty state text */
div[data-testid="stMultiSelect"] div[role="combobox"] > div:first-child {
    color: rgba(255, 255, 255, 0.6) !important;
}
</style>
""", unsafe_allow_html=True)

# Modal close button fix
st.markdown("""
<style>
/* Prevent close button clipping */
div[data-baseweb="modal"] header {
    padding-top: 24px !important;
    padding-right: 24px !important;
}

div[data-baseweb="modal"] button[aria-label="Close"] {
    position: relative !important;
}
</style>
""", unsafe_allow_html=True)

# Selectbox styling
st.markdown("""
<style>
/* Add spacing between file uploader and data editor */
div[data-testid="stFileUploader"] {
    margin-bottom: 1.5rem !important;
}

/* File uploader dropzone background color */
section[data-testid="stFileUploaderDropzone"] {
    background-color: rgb(26, 26, 26) !important;
}

/* Kill Streamlit's default red outline anywhere inside the selectbox */
div[data-testid="stSelectbox"] * {
    box-shadow: none !important;
}

/* Outer container */
div[data-testid="stSelectbox"] {
    background-color: transparent !important;
}

/* BaseWeb select wrapper */
div[data-testid="stSelectbox"] div[data-baseweb="select"] {
    background-color: #262730 !important;
    border-radius: 4px !important;
}

/* The actual clickable combobox area */
div[data-testid="stSelectbox"] div[role="combobox"] {
    border: 1px solid #e4781d !important;              /* orange border */
    border-radius: 4px !important;
    padding: 2px 6px !important;
    box-shadow: 0 0 0 1px #e4781d !important;          /* orange outline */
    transition: border-color 0.15s ease, box-shadow 0.15s ease;
}

/* Hover */
div[data-testid="stSelectbox"] div[role="combobox"]:hover {
    border-color: #d66b1d !important;
    box-shadow: 0 0 0 2px rgba(214, 107, 29, 0.35) !important;
}

/* Focus / open */
div[data-testid="stSelectbox"] div[role="combobox"][aria-expanded="true"],
div[data-testid="stSelectbox"] div[role="combobox"]:focus,
div[data-testid="stSelectbox"] div[role="combobox"]:focus-visible {
    outline: none !important;
    border-color: #e4781d !important;
    box-shadow: 0 0 0 3px rgba(228, 120, 29, 0.5) !important;
}

/* Arrow icon */
div[data-testid="stSelectbox"] svg {
    fill: #e4781d !important;
}

/* Style st-ep class with orange color */
.st-ep {
    background-color: #d66b1d !important;
}

</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
/*X button inside multiselect pills */
div[data-testid="stMultiSelect"] span[data-baseweb="tag"] button {
    background: rgba(255, 255, 255, 0.1) !important;
    border-radius: 50% !important;
    width: 14px !important;
    height: 14px !important;
    min-width: 14px !important;
    min-height: 14px !important;
    padding: 0 !important;
    margin: 0 !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    transition: all 0.2s ease !important;
    flex-shrink: 0 !important;
}

div[data-testid="stMultiSelect"] span[data-baseweb="tag"] button:hover {
    background: rgba(255, 255, 255, 0.2) !important;
    transform: scale(1.1) !important;
}

/* X icon styling */
div[data-testid="stMultiSelect"] span[data-baseweb="tag"] svg {
    width: 9px !important;
    height: 9px !important;
}

div[data-testid="stMultiSelect"] span[data-baseweb="tag"] svg path {
    stroke: rgba(255, 255, 255, 0.9) !important;
    stroke-width: 2px !important;
}

/* Prevent Streamlit from recoloring on hover */
div[data-testid="stMultiSelect"] span[data-baseweb="tag"]:hover svg path,
div[data-testid="stMultiSelect"] span[data-baseweb="tag"] button:hover svg path {
    stroke: #ffffff !important;
}
</style>
""", unsafe_allow_html=True)

# Checkbox styling
st.markdown("""
<style>
/* Checkbox box (unchecked) */
label[data-baseweb="checkbox"] span {
    border-color: #e4781d !important;
}

/* Checkbox SVG icon */
label[data-baseweb="checkbox"] svg {
    stroke: #e4781d !important;
    fill: none !important;
}

/* Checked state */
label[data-baseweb="checkbox"] input:checked + span svg {
    fill: #e4781d !important;
    stroke: #e4781d !important;
}

/* Hover */
label[data-baseweb="checkbox"]:hover span {
    border-color: #f08c2e !important;
}

/* Focus ring (kill red, add orange) */
label[data-baseweb="checkbox"] input:focus-visible + span {
    outline: none !important;
    box-shadow: 0 0 0 2px rgba(228, 120, 29, 0.55) !important;
}

/* Disabled checkbox styling - gray out */
div[data-testid="stCheckbox"]:has(input:disabled) {
    opacity: 0.4 !important;
    cursor: not-allowed !important;
}

div[data-testid="stCheckbox"]:has(input:disabled) label {
    cursor: not-allowed !important;
}

div[data-testid="stCheckbox"]:has(input:disabled) > label > div:first-child {
    background-color: #1a1a1a !important;
    border-color: #555555 !important;
}

div[data-testid="stCheckbox"]:has(input:disabled) span {
    color: #666666 !important;
}
</style>
""", unsafe_allow_html=True)

# Checkbox box styling
st.markdown("""
<style>
/* Base checkbox styling */
div[data-testid="stCheckbox"] > label > div:first-child {
    background-color: #262730;     /* dark background */
    border: 1px solid #e4781d;     /* orange border */
    border-radius: 4px;
    width: 18px;
    height: 18px;
    transition: all 0.15s ease;
}

/* Hover effect for checkbox */
div[data-testid="stCheckbox"] > label > div:first-child:hover {
    border-color: #d66b1d;
    box-shadow: 0 0 0 2px rgba(228, 120, 29, 0.4);
}

/* Checked state styling */
div[data-testid="stCheckbox"] > label > input:checked + div:first-child {
    background-color: #e4781d;
    border-color: #e4781d;
}
</style>
""", unsafe_allow_html=True)


# Remove markdown header anchor links
st.markdown("""
<style>
/* Remove anchor link + hover icon from ALL markdown headers */
div[data-testid="stMarkdownContainer"] h1 a,
div[data-testid="stMarkdownContainer"] h2 a,
div[data-testid="stMarkdownContainer"] h3 a,
div[data-testid="stMarkdownContainer"] h4 a,
div[data-testid="stMarkdownContainer"] h5 a,
div[data-testid="stMarkdownContainer"] h6 a {
    display: none !important;
}

/* Also prevent pointer cursor / hover highlight */
div[data-testid="stMarkdownContainer"] h1,
div[data-testid="stMarkdownContainer"] h2,
div[data-testid="stMarkdownContainer"] h3,
div[data-testid="stMarkdownContainer"] h4,
div[data-testid="stMarkdownContainer"] h5,
div[data-testid="stMarkdownContainer"] h6 {
    cursor: default !important;
}
</style>
""", unsafe_allow_html=True)

# Pop Up Styling
st.markdown("""
<style>
/* Kill WebKit scrollbar + arrows inside that container */
div[data-testid="stModal"] div[data-testid="stVerticalBlock"]::-webkit-scrollbar {
    width: 0px !important;
    height: 0px !important;
}

div[data-testid="stModal"] div[data-testid="stVerticalBlock"]::-webkit-scrollbar-button {
    display: none !important;
}

/* Firefox fallback */
div[data-testid="stModal"] div[data-testid="stVerticalBlock"] {
    scrollbar-width: none !important;
}
</style>
""", unsafe_allow_html=True)

# Scooting the screen downward for the side bar button
st.markdown("""
<style>
.main .block-container {
    padding-top: 2.5rem !important;
    padding-bottom: 1rem !important;
}

/* Also make sure your first header isn't hidden */
.main h1:first-of-type,
.main h2:first-of-type,
.main h3:first-of-type {
    margin-top: 1rem !important;
}
</style>
""", unsafe_allow_html=True)

# Modern Faded Orange Button Styling for Main Content
st.markdown("""
<style>
/* Target main content buttons - Faded orange style like sidebar */
.main button {
    background-color: rgba(228, 120, 29, 0.12) !important;
    color: rgba(255, 255, 255, 0.9) !important;
    border: 1px solid rgba(228, 120, 29, 0.3) !important;
    border-radius: 8px !important;
    padding: 10px 20px !important;
    font-weight: 500 !important;
    font-size: 14px !important;
    letter-spacing: 0.02em !important;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2),
                inset 0 1px 0 rgba(255, 255, 255, 0.03) !important;
    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
    backdrop-filter: blur(8px) !important;
}

/* Hover state - subtle glow */
.main button:hover:not(:disabled) {
    background-color: rgba(228, 120, 29, 0.2) !important;
    border-color: rgba(228, 120, 29, 0.5) !important;
    color: #ffffff !important;
    box-shadow: 0 4px 16px rgba(228, 120, 29, 0.25),
                0 2px 8px rgba(0, 0, 0, 0.3),
                inset 0 1px 0 rgba(255, 255, 255, 0.05) !important;
    transform: translateY(-1px) !important;
}

/* Active/pressed state */
.main button:active:not(:disabled) {
    background-color: rgba(228, 120, 29, 0.25) !important;
    border-color: rgba(228, 120, 29, 0.6) !important;
    box-shadow: 0 1px 4px rgba(0, 0, 0, 0.3),
                inset 0 2px 4px rgba(0, 0, 0, 0.2) !important;
    transform: translateY(0px) !important;
}

/* Focus state */
.main button:focus-visible {
    outline: none !important;
    box-shadow: 0 0 0 3px rgba(228, 120, 29, 0.4),
                0 2px 8px rgba(0, 0, 0, 0.2) !important;
}

/* Disabled state */
.main button:disabled {
    background-color: rgba(100, 100, 100, 0.1) !important;
    border-color: rgba(100, 100, 100, 0.2) !important;
    color: rgba(255, 255, 255, 0.3) !important;
    box-shadow: none !important;
    opacity: 0.5 !important;
    cursor: not-allowed !important;
    transform: none !important;
}

/* Target st-emotion-cache button classes directly - AGGRESSIVE */
button.st-emotion-cache-1anq8dj,
button[class*="st-emotion-cache-"] {
    background-color: rgba(228, 120, 29, 0.12) !important;
    border-width: 1px !important;
    border-style: solid !important;
    border-color: rgba(228, 120, 29, 0.3) !important;
    border-radius: 0.5rem !important;
}

button.st-emotion-cache-1anq8dj:hover:not(:disabled),
button[class*="st-emotion-cache-"]:hover:not(:disabled) {
    background-color: rgba(228, 120, 29, 0.2) !important;
    border-color: rgba(228, 120, 29, 0.5) !important;
}

/* Download button - subtle green variant */
div[data-testid="stDownloadButton"] button {
    background-color: rgba(228, 120, 29, 0.12) !important;
    border-color: rgba(228, 120, 29, 0.3) !important;
}

div[data-testid="stDownloadButton"] button:hover:not(:disabled) {
    background-color: rgba(228, 120, 29, 0.2) !important;
    border-color: rgba(228, 120, 29, 0.5) !important;
    box-shadow: 0 4px 16px rgba(228, 120, 29, 0.25),
                0 2px 8px rgba(0, 0, 0, 0.3),
                inset 0 1px 0 rgba(255, 255, 255, 0.05) !important;
}

div[data-testid="stDownloadButton"] button:active:not(:disabled) {
    background-color: rgba(228, 120, 29, 0.25) !important;
    border-color: rgba(228, 120, 29, 0.6) !important;
}
</style>
""", unsafe_allow_html=True)

# Modern AG Grid Styling
st.markdown("""
<style>
.ag-theme-streamlit {
    height: auto !important;
    max-height: none !important;
    overflow: visible !important;
}
</style>
            
<style>
/* AG Grid Container - Modern Glossy Black */
.ag-theme-streamlit {
    background: linear-gradient(145deg, rgba(25, 25, 25, 0.7), rgba(15, 15, 15, 0.5)) !important;
    border-radius: 14px !important;
    border: 1px solid rgba(228, 120, 29, 0.2) !important;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.6),
                0 4px 16px rgba(0, 0, 0, 0.4),
                inset 0 1px 0 rgba(255, 255, 255, 0.05),
                0 0 0 1px rgba(255, 255, 255, 0.02) inset !important;
    backdrop-filter: blur(10px) !important;
}

/* AG Grid Header - Orange accent */
.ag-theme-streamlit .ag-header {
    background: linear-gradient(135deg, rgba(228, 120, 29, 0.2), rgba(228, 120, 29, 0.1)) !important;
    border-bottom: 2px solid rgba(228, 120, 29, 0.4) !important;
    font-weight: 600 !important;
    color: rgba(255, 255, 255, 0.95) !important;
    box-shadow: 0 2px 8px rgba(228, 120, 29, 0.15) !important;
}

.ag-theme-streamlit .ag-header-cell {
    color: rgba(255, 255, 255, 0.95) !important;
    font-weight: 600 !important;
    font-size: 14px !important;
    letter-spacing: 0.02em !important;
    padding: 12px !important;
    border-right: 1px solid rgba(255, 255, 255, 0.08) !important;
}

.ag-theme-streamlit .ag-header-cell:hover {
    background: rgba(228, 120, 29, 0.15) !important;
}

/* AG Grid Rows */
.ag-theme-streamlit .ag-row {
    background: rgba(20, 20, 20, 0.4) !important;
    border-bottom: 1px solid rgba(255, 255, 255, 0.05) !important;
    transition: all 0.2s ease !important;
}

.ag-theme-streamlit .ag-row-even {
    background: rgba(25, 25, 25, 0.4) !important;
}

.ag-theme-streamlit .ag-row:hover {
    background: rgba(228, 120, 29, 0.08) !important;
    transform: translateX(2px) !important;
    box-shadow: inset 3px 0 0 rgba(228, 120, 29, 0.6) !important;
}

/* AG Grid Cells */
.ag-theme-streamlit .ag-cell {
    color: rgba(255, 255, 255, 0.9) !important;
    padding: 10px 12px !important;
    font-size: 13px !important;
    border-right: 1px solid rgba(255, 255, 255, 0.03) !important;
}

/* Selected rows */
.ag-theme-streamlit .ag-row-selected {
    background: rgba(228, 120, 29, 0.15) !important;
    border-left: 3px solid rgba(228, 120, 29, 0.8) !important;
}

.ag-theme-streamlit .ag-row-selected:hover {
    background: rgba(228, 120, 29, 0.2) !important;
}

/* Checkboxes in AG Grid */
.ag-theme-streamlit .ag-checkbox-input-wrapper {
    background: rgba(255, 255, 255, 0.08) !important;
    border: 2px solid rgba(228, 120, 29, 0.6) !important;
    border-radius: 4px !important;
    transition: all 0.2s ease !important;
}

.ag-theme-streamlit .ag-checkbox-input-wrapper.ag-checked {
    background: linear-gradient(135deg, rgba(228, 120, 29, 0.8), rgba(228, 120, 29, 0.6)) !important;
    border-color: rgba(228, 120, 29, 0.9) !important;
}

.ag-theme-streamlit .ag-checkbox-input-wrapper:hover {
    background: rgba(228, 120, 29, 0.15) !important;
    box-shadow: 0 0 8px rgba(228, 120, 29, 0.3) !important;
}

/* Cell editing */
.ag-theme-streamlit .ag-cell-inline-editing {
    background: rgba(228, 120, 29, 0.1) !important;
    border: 2px solid rgba(228, 120, 29, 0.6) !important;
    box-shadow: 0 0 12px rgba(228, 120, 29, 0.3),
                inset 0 1px 0 rgba(255, 255, 255, 0.05) !important;
}

/* Range selection */
.ag-theme-streamlit .ag-cell-range-selected:not(.ag-cell-focus) {
    background: rgba(228, 120, 29, 0.15) !important;
    border: 1px solid rgba(228, 120, 29, 0.4) !important;
}

/* Scrollbar for AG Grid */
.ag-theme-streamlit .ag-body-horizontal-scroll,
.ag-theme-streamlit .ag-body-vertical-scroll {
    scrollbar-width: thin !important;
    scrollbar-color: rgba(228, 120, 29, 0.5) rgba(255, 255, 255, 0.05) !important;
}

.ag-theme-streamlit ::-webkit-scrollbar {
    width: 10px !important;
    height: 10px !important;
}

.ag-theme-streamlit ::-webkit-scrollbar-track {
    background: rgba(255, 255, 255, 0.05) !important;
    border-radius: 5px !important;
}

.ag-theme-streamlit ::-webkit-scrollbar-thumb {
    background: rgba(228, 120, 29, 0.5) !important;
    border-radius: 5px !important;
}

.ag-theme-streamlit ::-webkit-scrollbar-thumb:hover {
    background: rgba(228, 120, 29, 0.7) !important;
}

/* Sort indicators */
.ag-theme-streamlit .ag-icon-asc,
.ag-theme-streamlit .ag-icon-desc {
    color: rgba(228, 120, 29, 0.9) !important;
}

/* Filter icon */
.ag-theme-streamlit .ag-icon-filter {
    color: rgba(228, 120, 29, 0.8) !important;
}

/* AG Grid CSS Variables Override - Force Orange Accent */
.ag-theme-streamlit,
.ag-theme-streamlit .ag-root-wrapper,
.ag-theme-streamlit .ag-root {
    --ag-accent-color: #e4781d !important;
    --ag-selected-row-background-color: rgba(228, 120, 29, 0.15) !important;
    --ag-range-selection-background-color: rgba(228, 120, 29, 0.2) !important;
    --ag-range-selection-border-color: rgba(228, 120, 29, 0.6) !important;
    --ag-input-focus-border-color: rgba(228, 120, 29, 0.8) !important;
    --ag-checkbox-checked-color: #e4781d !important;
    --ag-checkbox-unchecked-color: rgba(228, 120, 29, 0.4) !important;
    --ag-invalid-color: #e4781d !important;
    --ag-range-selection-background-color-1: rgba(228, 120, 29, 0.2) !important;
    --ag-range-selection-background-color-2: rgba(228, 120, 29, 0.25) !important;
    --ag-range-selection-background-color-3: rgba(228, 120, 29, 0.3) !important;
    --ag-range-selection-background-color-4: rgba(228, 120, 29, 0.35) !important;
}

/* Ultra aggressive selection overrides */
.ag-theme-streamlit .ag-row-selected,
.ag-theme-streamlit .ag-row.ag-row-selected,
.ag-theme-streamlit .ag-row-selected:before,
.ag-theme-streamlit .ag-row-selected:hover,
.ag-theme-streamlit .ag-row-selected.ag-row-hover {
    background-color: rgba(228, 120, 29, 0.15) !important;
    background: rgba(228, 120, 29, 0.15) !important;
}

/* Cell range selection - all states */
.ag-theme-streamlit .ag-cell-range-selected,
.ag-theme-streamlit .ag-cell-range-selected:not(.ag-cell-inline-editing),
.ag-theme-streamlit .ag-cell.ag-cell-range-selected,
.ag-theme-streamlit .ag-cell-range-selected-1:not(.ag-cell-inline-editing),
.ag-theme-streamlit .ag-cell-range-selected-2:not(.ag-cell-inline-editing),
.ag-theme-streamlit .ag-cell-range-selected-3:not(.ag-cell-inline-editing),
.ag-theme-streamlit .ag-cell-range-selected-4:not(.ag-cell-inline-editing) {
    background-color: rgba(228, 120, 29, 0.2) !important;
    background: rgba(228, 120, 29, 0.2) !important;
}

/* Cell range borders */
.ag-theme-streamlit .ag-cell-range-selected:not(.ag-cell-inline-editing),
.ag-theme-streamlit .ag-cell-range-top,
.ag-theme-streamlit .ag-cell-range-right,
.ag-theme-streamlit .ag-cell-range-bottom,
.ag-theme-streamlit .ag-cell-range-left {
    border-color: rgba(228, 120, 29, 0.6) !important;
}

/* Focus cell */
.ag-theme-streamlit .ag-cell-focus:not(.ag-cell-range-single-cell),
.ag-theme-streamlit .ag-cell.ag-cell-focus,
.ag-theme-streamlit .ag-cell-focus {
    border: 2px solid #e4781d !important;
    outline: none !important;
}

/* Range handle (fill handle) */
.ag-theme-streamlit .ag-fill-handle,
.ag-theme-streamlit .ag-range-handle {
    background-color: #e4781d !important;
}
</style>

<style>
/* Prevent nested scrollbars inside block-container */
.block-container {
    overflow: visible !important;
}
</style>
""", unsafe_allow_html=True)

# Analysis card styling - Pinterest board aesthetic
st.markdown("""
<style>
/* Pinterest-style card grid wrapper */
.stColumn {
    padding: 0.5rem !important;
}

.analysis-card {
    background: linear-gradient(145deg, #2e2f34, #272a30);
    border: 1px solid rgba(228, 120, 29, 0.15);
    border-radius: 16px;
    padding: 2rem 2.25rem;
    box-shadow: 
        0 4px 6px rgba(0, 0, 0, 0.1),
        0 8px 16px rgba(0, 0, 0, 0.15),
        0 16px 32px rgba(0, 0, 0, 0.1);
    height: 100%;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    position: relative;
}

/* Subtle shine effect like Pinterest cards */
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

.analysis-card:hover {
    border-color: rgba(228, 120, 29, 0.35);
    box-shadow: 
        0 8px 12px rgba(0, 0, 0, 0.15),
        0 16px 24px rgba(0, 0, 0, 0.2),
        0 24px 48px rgba(0, 0, 0, 0.15),
        0 0 0 1px rgba(228, 120, 29, 0.2);
    transform: translateY(-4px) scale(1.01);
}

.analysis-title {
    font-size: 0.875rem;
    color: #b4b8c4;
    margin-bottom: 1rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    opacity: 0.85;
}

.analysis-value {
    font-size: 3.25rem;
    font-weight: 700;
    color: #fb923c;
    line-height: 0.95;
    margin-bottom: 0.75rem;
    text-shadow: 0 2px 8px rgba(251, 146, 60, 0.2);
}

.analysis-subtext {
    font-size: 0.9rem;
    color: #9ca3af;
    margin-top: 0.75rem;
    font-weight: 400;
    line-height: 1.4;
}
</style>
""", unsafe_allow_html=True)

# Hiding the streamlit default top right corner buttons
st.markdown("""
<style>
/* Fix button shrink inside columns */
div[data-testid="column"] button {
    flex: 1 1 0 !important;
    width: 100% !important;
    min-width: 0 !important;
}

/* Fix the column wrapper so it can shrink properly */
div[data-testid="column"] {
    min-width: 0 !important;   /* CRITICAL */
    flex: 1 1 0 !important;    /* allow shrinking */
}
</style>
""", unsafe_allow_html=True)

# Function to delete an analysis run
def delete_run(index):
    st.session_state.analysis_runs.pop(index)

# Main content area - Show homepage OR analysis results
if st.session_state.active_run_id:
    # Display selected analysis run
    run = next(
        (r for r in st.session_state.analysis_runs if r["id"] == st.session_state.active_run_id),
        None
    )

    if run:
        st.markdown("<div style='margin-top: 1rem;'></div>", unsafe_allow_html=True)
        st.markdown("<hr style='margin: 0; border: none; height: 1px; background: linear-gradient(90deg, transparent 0%, rgba(228, 120, 29, 0.5) 50%, transparent 100%);' />", unsafe_allow_html=True)
        st.header(f"Analysis Results — {run['name']}", anchor=False)

        st.markdown("---")

        # Build analysis cards dynamically
        analysis_cards = []

        #-----------------------------------------------------------------------------------------------------------------------------------------------
        # Add stat cards for methods
        for method in run["methods"]:
            if method == "Mean":
                # Calculate mean for each column
                for col in run["data"].select_dtypes(include=['number']).columns:
                    mean_val = run["data"][col].mean()
                    analysis_cards.append(("stat", f"<b>Mean</b>", f"{mean_val:.2f}"))
            elif method == "Median":
                for col in run["data"].select_dtypes(include=['number']).columns:
                    median_val = run["data"][col].median()
                    analysis_cards.append(("stat", f"<b>Median</b>", f"{median_val:.2f}"))
            elif method == "Mode":
                for col in run["data"].select_dtypes(include=['number']).columns:
                    mode_val = run["data"][col].mode()
                    mode_display = f"{mode_val.iloc[0]:.2f}" if len(mode_val) > 0 else "N/A"
                    analysis_cards.append(("stat", f"<b>Mode</b>", mode_display))
            elif method == "Variance":
                for col in run["data"].select_dtypes(include=['number']).columns:
                    var_val = run["data"][col].var()
                    analysis_cards.append(("stat", f"<b>Variance</b>", f"{var_val:.2f}"))
            elif method == "Standard Deviation":
                for col in run["data"].select_dtypes(include=['number']).columns:
                    std_val = run["data"][col].std()
                    analysis_cards.append(("stat", f"<b>Std Dev</b>", f"{std_val:.2f}"))
            elif method == "Percentiles":
                for col in run["data"].select_dtypes(include=['number']).columns:
                    p25 = run["data"][col].quantile(0.25)
                    p50 = run["data"][col].quantile(0.50)
                    p75 = run["data"][col].quantile(0.75)
                    analysis_cards.append(("stat", f"<b>Percentiles</b>", f"{p25:.1f} / {p50:.1f} / {p75:.1f}", "25th / 50th / 75th"))
            elif method == "Variation":
                for col in run["data"].select_dtypes(include=['number']).columns:
                    mean_val = run["data"][col].mean()
                    std_val = run["data"][col].std()
                    cv = (std_val / mean_val * 100) if mean_val != 0 else 0
                    analysis_cards.append(("stat", f"<b>Coeff. of Variation</b>", f"{cv:.2f}%"))
            elif method == "Chi-Square":
                analysis_cards.append(("stat", "<b>Chi-Square</b>", "12.24", "p-value: 0.032"))
            elif method == "Pearson":
                analysis_cards.append(("stat", "<b>Pearson's Corr.</b>", "0.87", "Strong positive"))
            elif method == "Spearman":
                analysis_cards.append(("stat", "<b>Spearman's Rank</b>", "0.82", "Strong correlation"))
            elif method == "Regression":
                analysis_cards.append(("stat", "<b>Regression</b>", "0.76", "Good fit"))
            elif method == "Binomial":
                analysis_cards.append(("stat", "<b>Binomial Prob</b>", "0.68", "n=10, p=0.5"))
        
        # Render stat cards in Pinterest-style grid
        if analysis_cards:
            st.subheader("Statistical Analysis", anchor=False)
            st.markdown("<div style='margin-bottom: 2rem;'></div>", unsafe_allow_html=True)
            
            # Render cards in rows of 3 with Pinterest-style spacing
            for i in range(0, len(analysis_cards), 3):
                cols = st.columns([1, 1, 1], gap="large")
                for j in range(3):
                    if i + j < len(analysis_cards):
                        card = analysis_cards[i + j]
                        with cols[j]:
                            if card[0] == "stat":
                                if len(card) == 4:  # Has subtext
                                    stat_card(card[1], card[2], card[3])
                                else:
                                    stat_card(card[1], card[2])
                
                # Add breathing room between rows
                st.markdown("<div style='margin-bottom: 2rem;'></div>", unsafe_allow_html=True)
            
            st.markdown("---")
        
        # Show visualizations section if any were selected
        if run.get("visualizations") and len(run["visualizations"]) > 0:
            st.subheader("Visualizations", anchor=False)
            st.markdown("<div style='margin-bottom: 1rem;'></div>", unsafe_allow_html=True)
            
            for v in run["visualizations"]:
                st.info(f"{v} visualization will be rendered here")
            
            st.markdown("---")

        st.subheader("Selected Data", anchor=False)
        st.markdown("<div style='margin-bottom: 1rem;'></div>", unsafe_allow_html=True)
        st.dataframe(run["data"], use_container_width=True)
        st.caption(f"Rows: {len(run['data'])}, Columns: {len(run['data'].columns)}")

        st.markdown("---")

        btn1, btn2, btn3 = st.columns(3)

        with btn1:
            st.button("Save This Run", use_container_width=True)

        with btn2:
            export_text = f"Analysis Results — {run['name']}\n\n"

            if run["methods"]:
                export_text += "Methods Applied:\n"
                for m in run["methods"]:
                    export_text += f"- {m}\n"
                export_text += "\n"

            if run.get("visualizations"):
                export_text += "Visualizations Applied:\n"
                for v in run["visualizations"]:
                    export_text += f"- {v}\n"
                export_text += "\n"

            export_text += "Selected Data:\n"
            export_text += df_to_ascii_table(run["data"]) + "\n\n"

            st.download_button(
                label="Export This Run",
                data=export_text,
                file_name=f"{run['name']}.txt",
                mime="text/plain",
                use_container_width=True,
            )

        with btn3:
            if st.button("Delete This Run", use_container_width=True):
                st.session_state.analysis_runs = [r for r in st.session_state.analysis_runs if r["id"] != run["id"]]
                st.session_state.active_run_id = None
                st.rerun()
else:
    # Show homepage with data input and configuration
    # Add spacing at the top so sidebar toggle isn't covered
    st.markdown("<div style='margin-top: 1rem;'></div>", unsafe_allow_html=True)
    st.markdown("<hr style='margin: 0; border: none; height: 1px; background: linear-gradient(90deg, transparent 0%, rgba(228, 120, 29, 0.5) 50%, transparent 100%);' />", unsafe_allow_html=True)
    
    left_col, right_col = st.columns([3, 2], gap="medium")

    # Data Input
    with left_col:
        st.header("Data Input & Table", anchor=False)
        if "uploaded_file" not in st.session_state:
            uploaded_file = st.file_uploader(
                "Upload CSV File",
                type="csv",
                key="uploaded_csv"
            )
            if uploaded_file is not None:
                st.session_state.uploaded_file = uploaded_file
                st.session_state.has_file = True
                st.rerun()
            # Add spacing after uploader
            st.markdown("<div style='margin-bottom: 1rem;'></div>", unsafe_allow_html=True)
        else:
            uploaded_file = st.session_state.uploaded_file
            
            # Initialize file key and load data if needed
            file_key = f"{uploaded_file.name}_{str(uploaded_file.size)}"
            if "edited_data_cache" not in st.session_state:
                st.session_state.edited_data_cache = {}
            
            # Make button smaller by using columns
            col_remove, col_download, col_spacer = st.columns([1, 1, 2])
            with col_remove:
                if st.button("Remove", key="remove_file_btn", use_container_width=True):
                    del st.session_state.uploaded_file
                    st.session_state.has_file = False
                    st.session_state.saved_table = None
                    st.session_state.edited_data_cache = {}
                    st.session_state.selected_columns = []
                    st.session_state.selected_rows = []
                    st.session_state.last_grid_selection = None
                    st.session_state.checkbox_key_onecol += 1
                    st.session_state.checkbox_key_twocol += 1
                    st.rerun()
            
            with col_download:
                # Load data into cache if not already there
                if file_key not in st.session_state.edited_data_cache:
                    uploaded_file.seek(0)
                    temp_df = pd.read_csv(uploaded_file)
                    st.session_state.edited_data_cache[file_key] = temp_df.copy()
                
                # Show download button
                csv_data = st.session_state.edited_data_cache[file_key].to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="Download",
                    data=csv_data,
                    file_name=f"edited_{uploaded_file.name}",
                    mime="text/csv",
                    use_container_width=True,
                    key="download_edited"
                )

            # Add spacing after remove button
            st.markdown("<div style='margin-bottom: 2rem;'></div>", unsafe_allow_html=True)

        # Step 2: Persist the uploaded file object itself
        if uploaded_file is not None:
            st.session_state["uploaded_file"] = uploaded_file
            st.session_state.has_file = True
        
        # Use fallback from session state
        uploaded_file = st.session_state.get("uploaded_file")

        # Step 3: Only clear when user explicitly removes it
        if uploaded_file is None and "uploaded_file" in st.session_state:
            # User clicked X
            del st.session_state["uploaded_file"]
            st.session_state.checkbox_key_onecol += 1
            st.session_state.checkbox_key_twocol += 1
            st.session_state.has_file = False
            st.session_state.saved_table = None
            st.session_state.edited_data_cache = {}
            st.session_state.selected_columns = []
            st.session_state.selected_rows = []
            st.session_state.last_grid_selection = None
            st.rerun()

        # Determine which table to use  
        edited_table = None
        
        if uploaded_file is not None:
            try:
                file_key = f"{uploaded_file.name}_{str(uploaded_file.size)}"
                
                # Initialize cache if needed
                if "edited_data_cache" not in st.session_state:
                    st.session_state.edited_data_cache = {}
                
                # Use cached edited data if available, otherwise read fresh data
                if file_key in st.session_state.edited_data_cache:
                    df = st.session_state.edited_data_cache[file_key].copy()
                else:
                    # Reset file pointer to beginning before reading
                    uploaded_file.seek(0)
                    df = pd.read_csv(uploaded_file)
                    st.session_state.edited_data_cache[file_key] = df.copy()
                
                # Prepare data for AG Grid Range
                records = df.to_dict("records")
                columns = [{"field": c} for c in df.columns]
                
                # Apply custom styling for AG Grid
                st.markdown("""
                <style>
                /* AG Grid custom theme styling */
                .ag-theme-streamlit {
                    --ag-background-color: #141414 !important;
                    --ag-odd-row-background-color: #141414 !important;
                    --ag-header-background-color: #1f1f1f !important;
                    --ag-foreground-color: #e5e7eb !important;
                    --ag-secondary-foreground-color: #9ca3af !important;
                    --ag-border-color: rgba(255,255,255,0.08) !important;
                    --ag-row-border-color: rgba(255,255,255,0.05) !important;
                    --ag-accent-color: #e4781d !important;
                    --ag-inherited-accent-color: #e4781d !important;
                    --ag-checkbox-checked-border-color: #e4781d !important;
                    --ag-checkbox-checked-shape-color: #e4781d !important;
                    --ag-row-hover-color: rgba(228,120,29,0.12) !important;
                    --ag-selected-row-background-color: rgba(228,120,29,0.22) !important;
                    --ag-range-selection-border-color: #e4781d !important;
                    --ag-range-selection-background-color: rgba(228,120,29,0.25) !important;
                    --ag-cell-editing-border: 1px solid #e4781d !important;
                    --ag-input-focus-border: 1px solid #e4781d !important;
                    --ag-column-hover-color: rgba(228,120,29,0.08) !important;
                    --ag-browser-color-scheme: dark !important;
                }
                </style>
                """, unsafe_allow_html=True)

                # Display AG Grid with range selection
                selection = aggrid_range(records, columns, key=f"grid_{file_key}")

                apply_grid_selection_to_filters(selection, df)
                
                # Cache the current data
                edited_table = df.copy()
                st.session_state.edited_data_cache[file_key] = edited_table.copy()
                
                # Show grid info
                st.markdown("")  # Add spacing
                st.caption("**Tip:** Click and drag to select a range of cells.")
                
                # Display selection output
                if selection:
                    print("\n--- Selected Ranges ---")
                    pprint.pprint(selection)
                    print("-----------------------")
                    
                    st.markdown("---")
                    st.markdown("**Selection Output**")
                    
                    with st.expander("Selected Ranges Metadata", expanded=False):
                        st.json(selection)
                    
                    # Process and display the selected data
                    for idx, rng in enumerate(selection):
                        st.write(f"**Range {idx + 1} Selection:**")
                        
                        # Extract indices and columns
                        start_row = rng.get("startRow")
                        end_row = rng.get("endRow")
                        selected_cols = rng.get("columns", [])
                        
                        if start_row is not None and end_row is not None and selected_cols:
                            # Ensure indices are integers
                            start = int(start_row)
                            end = int(end_row)
                            
                            # Validate columns exist in current dataframe
                            valid_cols = [c for c in selected_cols if c in df.columns]
                            
                            if valid_cols:
                                # Slice rows (end is inclusive in AG Grid)
                                subset = df.iloc[start : end + 1][valid_cols]
                                
                                print(f"\n--- Range {idx + 1} Data ---")
                                print(subset.to_markdown(index=False, tablefmt="grid"))
                                print("----------------------")
                                
                                st.dataframe(subset, use_container_width=True)
                            else:
                                st.warning("Selected columns not found in current data.")
                        else:
                            st.warning("Invalid selection data received.")
                else:
                    st.info("Select a range of cells in the grid to see details here.")
                
            except Exception as e:
                st.error(f"Error processing file: {e}")
                edited_table = pd.DataFrame(columns=["Enter your data..."])
        elif st.session_state.get("saved_table") is not None:
            # Restore previously edited table and display it in AG Grid
            try:
                df = st.session_state.saved_table.copy()
                
                # Prepare data for AG Grid Range
                records = df.to_dict("records")
                columns = [{"field": c} for c in df.columns]
                
                # Apply custom styling for AG Grid
                st.markdown("""
                <style>
                /* AG Grid custom theme styling */
                .ag-theme-streamlit {
                    --ag-background-color: #141414 !important;
                    --ag-odd-row-background-color: #141414 !important;
                    --ag-header-background-color: #1f1f1f !important;
                    --ag-foreground-color: #e5e7eb !important;
                    --ag-secondary-foreground-color: #9ca3af !important;
                    --ag-border-color: rgba(255,255,255,0.08) !important;
                    --ag-row-border-color: rgba(255,255,255,0.05) !important;
                    --ag-accent-color: #e4781d !important;
                    --ag-inherited-accent-color: #e4781d !important;
                    --ag-checkbox-checked-border-color: #e4781d !important;
                    --ag-checkbox-checked-shape-color: #e4781d !important;
                    --ag-row-hover-color: rgba(228,120,29,0.12) !important;
                    --ag-selected-row-background-color: rgba(228,120,29,0.22) !important;
                    --ag-range-selection-border-color: #e4781d !important;
                    --ag-range-selection-background-color: rgba(228,120,29,0.25) !important;
                    --ag-cell-editing-border: 1px solid #e4781d !important;
                    --ag-input-focus-border: 1px solid #e4781d !important;
                    --ag-column-hover-color: rgba(228,120,29,0.08) !important;
                    --ag-browser-color-scheme: dark !important;
                }
                </style>
                """, unsafe_allow_html=True)

                # Display AG Grid with range selection
                selection = aggrid_range(records, columns, key="grid_cached")

                apply_grid_selection_to_filters(selection, df)
                
                # Cache the current data
                edited_table = df.copy()
                
                # Show grid info
                st.markdown("")  # Add spacing
                st.caption("**Tip:** Click and drag to select a range of cells.")
                
                # Display selection output
                if selection:
                    print("\n--- Selected Ranges ---")
                    pprint.pprint(selection)
                    print("-----------------------")
                    
                    st.markdown("---")
                    st.markdown("**Selection Output**")
                    
                    with st.expander("Selected Ranges Metadata", expanded=False):
                        st.json(selection)
                    
                    # Process and display the selected data
                    for idx, rng in enumerate(selection):
                        st.write(f"**Range {idx + 1} Selection:**")
                        
                        # Extract indices and columns
                        start_row = rng.get("startRow")
                        end_row = rng.get("endRow")
                        selected_cols = rng.get("columns", [])
                        
                        if start_row is not None and end_row is not None and selected_cols:
                            # Ensure indices are integers
                            start = int(start_row)
                            end = int(end_row)
                            
                            # Validate columns exist in current dataframe
                            valid_cols = [c for c in selected_cols if c in df.columns]
                            
                            if valid_cols:
                                # Slice rows (end is inclusive in AG Grid)
                                subset = df.iloc[start : end + 1][valid_cols]
                                
                                print(f"\n--- Range {idx + 1} Data ---")
                                print(subset.to_markdown(index=False, tablefmt="grid"))
                                print("----------------------")
                                
                                st.dataframe(subset, use_container_width=True)
                            else:
                                st.warning("Selected columns not found in current data.")
                        else:
                            st.warning("Invalid selection data received.")
                else:
                    st.info("Select a range of cells in the grid to see details here.")
                    
            except Exception as e:
                st.error(f"Error displaying cached table: {e}")
                edited_table = st.session_state.saved_table.copy()
        else:
            edited_table = pd.DataFrame(columns=["Enter your data..."])
            st.info("Upload a CSV file to view it in the interactive grid.")
        
        # Save the edited table
        #  to session state
        if edited_table is not None:
            st.session_state.saved_table = edited_table.copy()

        data_ready = edited_table is not None and len(edited_table.columns) > 0 and len(edited_table) > 0

    # Analysis Options
    with right_col:
        st.header("Analysis Configuration", anchor=False)

        col1 = []
        col2 = []

        if edited_table is not None and len(edited_table.columns) > 0 and len(edited_table) > 0:
            available_cols = list(edited_table.columns)
            available_rows = list(range(1, len(edited_table) + 1))

            st.session_state.selected_columns = [
                c for c in st.session_state.selected_columns if c in available_cols
            ]
            st.session_state.selected_rows = [
                r for r in st.session_state.selected_rows if r in available_rows
            ]

            col1 = st.multiselect("Columns", available_cols, key="selected_columns")
            st.session_state["current_cols"] = col1  

            # --- RESET CHECKBOXES ONLY IF USER JUST CLEARED COLUMNS ---
            if "last_cols_selected" not in st.session_state:
                st.session_state.last_cols_selected = []

            if len(st.session_state.last_cols_selected) > 0 and len(col1) == 0:
                st.session_state.checkbox_key_onecol += 1

            # Save for next interaction
            st.session_state.last_cols_selected = col1

            col2 = st.multiselect("Rows", available_rows, key="selected_rows")
        else:
            col1 = []
            col2 = []
            st.multiselect("Columns", [], disabled=True)
            st.multiselect("Rows", [], disabled=True)

        # Determine how many columns/rows are selected
        num_cols_selected = len(col1)
        num_rows_selected = len(col2)

        # ---- NEW: detect transition from 2+ columns → 1 column ----
        if "last_num_cols" not in st.session_state:
            st.session_state.last_num_cols = 0

        # If user DROPPED from 2+ columns to 1 column → reset dependent checkboxes
        if st.session_state.last_num_cols >= 2 and num_cols_selected == 1:
            st.session_state.checkbox_key_twocol += 1

        # Save current count for next interaction
        st.session_state.last_num_cols = num_cols_selected

        disable_two_cols = num_cols_selected < 2
        disable_one_col = num_cols_selected < 1
        disable_one_row = num_rows_selected < 1

        st.markdown("---")

        # Computation Options
        st.header("Computation Options", anchor=False)
        c1, c2 = st.columns(2)

        with c1:
            mean = st.checkbox("Mean", disabled=not data_ready or disable_one_col, key=f"mean_c1_{st.session_state.checkbox_key_onecol}")
            median = st.checkbox("Median", disabled=not data_ready or disable_one_col, key=f"median_c1_{st.session_state.checkbox_key_onecol}")
            mode = st.checkbox("Mode", disabled=not data_ready or disable_one_col, key=f"mode_c1_{st.session_state.checkbox_key_onecol}")
            variance = st.checkbox("Variance", disabled=not data_ready or disable_one_col, key=f"variance_c1_{st.session_state.checkbox_key_onecol}")
            std_dev = st.checkbox("Standard Deviation", disabled=not data_ready or disable_one_col, key=f"std_dev_c1_{st.session_state.checkbox_key_onecol}")
            percentiles = st.checkbox("Percentiles", disabled=not data_ready or disable_one_col, key=f"percentiles_c1_{st.session_state.checkbox_key_onecol}")

        with c2:
            pearson = st.checkbox("Pearson's Correlation", disabled=not data_ready or disable_two_cols, key=f"pearson_c2_{st.session_state.checkbox_key_twocol}")
            spearman = st.checkbox("Spearman's Rank", disabled=not data_ready or disable_two_cols, key=f"spearman_c2_{st.session_state.checkbox_key_twocol}")
            regression = st.checkbox("Least Squares Regression", disabled=not data_ready or disable_two_cols, key=f"regression_c2_{st.session_state.checkbox_key_twocol}")
            chi_square = st.checkbox("Chi-Square Test", disabled=not data_ready or disable_one_col, key=f"chi_square_c2_{st.session_state.checkbox_key_onecol}")
            binomial = st.checkbox("Binomial Distribution", disabled=not data_ready or disable_one_col, key=f"binomial_c2_{st.session_state.checkbox_key_onecol}")
            variation = st.checkbox("Coefficient of Variation", disabled=not data_ready or disable_one_col, key=f"variation_c2_{st.session_state.checkbox_key_onecol}")

        st.markdown("---")

        st.header("Visualization Options", anchor=False)
        with st.container():
            # Determine if any computation method is selected
            computation_selected = any([mean, median, mode, variance, std_dev, percentiles, pearson, spearman, regression, chi_square, binomial, variation])

            disable_viz = not computation_selected  # True if no computation is selected

            if disable_viz:
                st.session_state["viz_hist"] = False
                st.session_state["viz_box"] = False
                st.session_state["viz_scatter"] = False
                st.session_state["viz_line"] = False
                st.session_state["viz_heatmap"] = False

            # Visualization Options
            v1, v2 = st.columns(2)

            with v1:
                hist = st.checkbox(
                    "Pie Chart",
                    key="viz_hist",
                    disabled=disable_viz
                )
                box = st.checkbox(
                    "Vertical Bar Chart",
                    key="viz_box",
                    disabled=disable_viz
                )
                scatter = st.checkbox(
                    "Horizontal Bar Chart",
                    key="viz_scatter",
                    disabled=disable_viz
                )

            with v2:
                line = st.checkbox(
                    "Scatter Plot",
                    key="viz_line",
                    disabled=disable_viz
                )
                heatmap = st.checkbox(
                    "Line of Best Fit Scatter Plot",
                    key="viz_heatmap",
                    disabled=disable_viz
                )

        st.markdown("---")

        st.markdown('<div class="run-analysis-anchor"></div>', unsafe_allow_html=True)

        # Make a copy with a 1-based index to match the row selector
        edited_table_for_loc = edited_table.copy()
        edited_table_for_loc.index = range(1, len(edited_table_for_loc) + 1)

        if col1 and col2:
            parsedData = edited_table_for_loc.loc[col2, col1].copy()
        elif col1:
            parsedData = edited_table_for_loc[col1].copy()
        elif col2:
            parsedData = edited_table_for_loc.loc[col2].copy()
        else:
            parsedData = edited_table_for_loc.copy()

        run_clicked = st.button(
            "Run Analysis",
            key="run_analysis",
            use_container_width=True,
            disabled=not (data_ready and computation_selected)
        )

        if run_clicked:
            non_numeric_cols = []
            numeric_required = any([
                mean, median, mode, std_dev, variance, pearson, spearman, regression, percentiles, variation,
                st.session_state.get("viz_hist", False),
                st.session_state.get("viz_box", False),
                st.session_state.get("viz_scatter", False),
                st.session_state.get("viz_line", False),
                st.session_state.get("viz_heatmap", False)
            ])

            if numeric_required:
                for col in parsedData.columns:
                    coerced = pd.to_numeric(parsedData[col], errors='coerce')
                    non_numeric_rows = parsedData[coerced.isna() & parsedData[col].notna()]
                    for row_idx, val in non_numeric_rows[col].items():
                        non_numeric_cols.append({
                            "row": row_idx,
                            "column": col,
                            "value": val
                        })

            if non_numeric_cols:
                # Prepare message
                preview = non_numeric_cols[:2]
                message = "The following non-numeric data was found:\n"
                for cell in preview:
                    message += f" - Row: {cell['row']}, Column: {cell['column']}, Value: '{cell['value']}'\n"
                if len(non_numeric_cols) > 2:
                    message += f" ...and {len(non_numeric_cols) - 2} more entries.\n"

                # Save message to session state
                st.session_state.modal_message = message

                # Open the modal immediately
                error_modal.open()

            # If all data is numeric, create the run
            else:
                run = {
                    "id": str(uuid.uuid4()),
                    "name": f"Run {len(st.session_state.analysis_runs) + 1}",
                    "table": edited_table,
                    "data": parsedData.reset_index(drop=True),
                    "columns": col1,
                    "rows": col2,
                    "methods": [
                        name for name, selected in {
                            "Mean": mean,
                            "Median": median,
                            "Mode": mode,
                            "Variance": variance,
                            "Standard Deviation": std_dev,
                            "Percentiles": percentiles,
                            "Pearson": pearson,
                            "Spearman": spearman,
                            "Regression": regression,
                            "Chi-Square": chi_square,
                            "Binomial": binomial,
                            "Variation": variation,
                        }.items() if selected
                    ],
                    "visualizations": [
                        name for name, selected in {
                            "Pie Chart": hist,
                            "Vertical Bar Chart": box,
                            "Horizontal Bar Chart": scatter,
                            "Scatter Plot": line,
                            "Line of Best Fit Scatter Plot": heatmap,
                        }.items() if selected
                    ],
                }

                st.session_state.analysis_runs.append(run)
                st.session_state.modal_message = f"Analysis '{run['name']}' has been successfully created!\nPlease see the side bar for your analysis."
                success_modal.open()

# FINAL OVERRIDE — Force transparent orange buttons with maximum specificity
st.markdown("""
<style>
/* Target BaseWeb buttons directly to override gray background - ALL MAIN CONTENT BUTTONS */
.main div[data-testid="stButton"] > button[data-baseweb="button"],
.main div[data-testid="stButton"] button[kind="primary"],
.main div[data-testid="stButton"] button[kind="secondary"] {
    background: linear-gradient(
        180deg,
        rgba(228, 120, 29, 0.18),
        rgba(228, 120, 29, 0.08)
    ) !important;
    background-image: linear-gradient(
        180deg,
        rgba(228, 120, 29, 0.18),
        rgba(228, 120, 29, 0.08)
    ) !important;
    color: #ffffff !important;
    border: 1px solid rgba(228, 120, 29, 0.6) !important;
    border-radius: 10px !important;
    backdrop-filter: blur(6px) !important;
    box-shadow: none !important;
}

/* Hover - ALL MAIN CONTENT BUTTONS */
.main div[data-testid="stButton"] > button[data-baseweb="button"]:hover:not(:disabled),
.main div[data-testid="stButton"] button[kind="primary"]:hover:not(:disabled),
.main div[data-testid="stButton"] button[kind="secondary"]:hover:not(:disabled) {
    background: rgba(228, 120, 29, 0.25) !important;
    box-shadow: 0 0 0 3px rgba(228, 120, 29, 0.35) !important;
}

/* Active - ALL MAIN CONTENT BUTTONS */
.main div[data-testid="stButton"] > button[data-baseweb="button"]:active,
.main div[data-testid="stButton"] button[kind="primary"]:active,
.main div[data-testid="stButton"] button[kind="secondary"]:active {
    background: rgba(228, 120, 29, 0.35) !important;
    transform: translateY(1px) !important;
}

/* Disabled - ALL MAIN CONTENT BUTTONS */
.main div[data-testid="stButton"] > button[data-baseweb="button"]:disabled,
.main div[data-testid="stButton"] button[kind="primary"]:disabled,
.main div[data-testid="stButton"] button[kind="secondary"]:disabled {
    background: rgba(100, 100, 100, 0.12) !important;
    background-image: none !important;
    border-color: rgba(100, 100, 100, 0.25) !important;
    color: rgba(255, 255, 255, 0.35) !important;
}
</style>
""", unsafe_allow_html=True)

# Final override to constrain scrolling to the app container and hide browser scrollbar
st.markdown("""
<style>
/* Keep header visually above the scroll container */
header[data-testid="stHeader"] {
    position: relative !important;
    z-index: 9999 !important;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
/* SAFE: Keep scrollbar visible but styled */
html {
  scrollbar-width: thin; /* Firefox */
}

html::-webkit-scrollbar {
  width: 8px; /* Chrome/Safari/Edge */
}

html::-webkit-scrollbar-thumb {
  background: rgba(228, 120, 29, 0.5);
  border-radius: 10px;
}

html::-webkit-scrollbar-thumb:hover {
  background: rgba(228, 120, 29, 0.7);
}

/* Prevent Streamlit from creating nested scroll regions */
div[data-testid="stMain"],
div[data-testid="stAppViewBlockContainer"],
div[data-testid="stVerticalBlock"],
div[data-testid="stVerticalBlockBorderWrapper"] {
    overflow: visible !important;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
/* --- SINGLE SOURCE OF TRUTH: ONLY THE BROWSER SCROLLS --- */

/* Let the browser own vertical scrolling */
html, body {
    height: auto !important;
    overflow-y: auto !important;
}

/* Kill Streamlit's internal scroll containers */
section[data-testid="stAppViewContainer"],
section[data-testid="stMain"],
div[data-testid="stAppViewBlockContainer"],
div[data-testid="stVerticalBlock"],
div[data-testid="stVerticalBlockBorderWrapper"] {
    height: auto !important;
    min-height: auto !important;
    max-height: none !important;
    overflow: visible !important;
}

/* Make sure the main content wrapper doesn't clip the bottom */
.block-container {
    height: auto !important;
    min-height: auto !important;
    max-height: none !important;
    overflow: visible !important;
}

/* Keep your global scrollbar styling, but only as a skin */
html {
    scrollbar-width: thin;
}
html::-webkit-scrollbar {
    width: 8px;
}
html::-webkit-scrollbar-thumb {
    background: rgba(228, 120, 29, 0.5);
    border-radius: 10px;
}
html::-webkit-scrollbar-thumb:hover {
    background: rgba(228, 120, 29, 0.7);
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
/* Allow columns to size independently instead of matching heights */
div[data-testid="column"] {
    align-self: flex-start !important;
}
</style>
""", unsafe_allow_html=True)

# Render modals
if error_modal.is_open():
    with error_modal.container():
        render_modal_content(
            os.path.join(BASE_DIR, "assets", "warningSquirrel.PNG"),
            st.session_state.modal_message
        )

if success_modal.is_open():
    with success_modal.container():
        render_modal_content(
            os.path.join(BASE_DIR, "assets", "huzzahAhSquirrel.png"),
            st.session_state.modal_message
        )