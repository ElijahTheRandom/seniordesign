import streamlit as st
import pandas as pd
import uuid
import time
from PIL import Image


# Session state
if "analysis_runs" not in st.session_state:
    st.session_state.analysis_runs = []

# Page config
st.set_page_config(
    page_title="Statistical Analyzer",
    layout="wide",
)

# Styling
st.markdown("""
<style>
header[data-testid="stHeader"] { display: none; }
.block-container {
    padding-top: 0rem !important;
    padding-left: 1rem;
    padding-right: 1rem;
    margin-top: -3rem !important;
    margin-bottom: -3rem !important;
}
div[data-testid="stTabs"] {
    margin-top: -2rem !important;
    margin-bottom: -3rem !important;
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

# Selectbox styling
st.markdown("""
<style>
/* Base selectbox styling */
div[data-testid="stSelectbox"] > div {
    background-color: #262730 !important;
    border: 1px solid #e4781d !important;
    border-radius: 6px !important;
}

/* Hover and focus effects */
div[data-testid="stSelectbox"] > div:hover {
    border-color: #d66b1d !important;
}

/* Focused state */
div[data-testid="stSelectbox"] > div:has(input:focus) {
    border-color: #e4781d !important;
    box-shadow: 0 0 0 1px #e4781d !important;
}

/* Dropdown menu styling */
div[data-testid="stSelectbox"] svg {
    fill: #e4781d !important;
}
</style>
""", unsafe_allow_html=True)

# Column styling
st.markdown("""
<style>

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

# Multiselect styling
st.markdown("""
<style>
.st-c1 {
    background-color: #e4781d !important;
    color: white !important;
}
</style>
""", unsafe_allow_html=True)

# Button styling
st.markdown("""
<style>
/* Base button styling */
div[data-testid="stButton"] button,
div[data-testid="stFileUploader"] button {
    background-color: #d66b1d !important;
    color: #ffffff !important;
    border: 1px solid #d66b1d !important;
    border-radius: 6px !important;
    font-weight: 600;
    padding: 8px 16px;
    transition: background-color 0.15s ease, box-shadow 0.15s ease;
}

/* Hover */
div[data-testid="stButton"] button:hover,
div[data-testid="stFileUploader"] button:hover {
    background-color: #e4781d !important;
    border-color: #e4781d !important;
    box-shadow: 0 0 0 3px rgba(214, 107, 29, 0.35);
}

/* Focus Visible */
div[data-testid="stButton"] button:focus-visible,
div[data-testid="stFileUploader"] button:focus-visible {
    outline: none !important;
    box-shadow: 0 0 0 3px rgba(214, 107, 29, 0.5);
}

/* Active */ 
div[data-testid="stButton"] button:active,
div[data-testid="stFileUploader"] button:active {
    background-color: #b85b18 !important;
    border-color: #b85b18 !important;
}
</style>
""", unsafe_allow_html=True)

# Function to delete an analysis run
def delete_run(index):
    st.session_state.analysis_runs.pop(index)

# Build tabs
tab_labels = ["Main Workspace"]
tab_labels += [run["name"] for run in st.session_state.analysis_runs]

tabs = st.tabs(tab_labels)

# Tab styling
st.markdown("""
<style>
/* Base tab styling */
div[data-testid="stTabs"] button[role="tab"] {
    color: #e4781d !important;
    font-weight: 600 !important;
    background: transparent !important;
}

/* Hover effect for tabs */
div[data-testid="stTabs"] button[role="tab"]:hover {
    color: #d66b1d !important;
}

/* Selected tab styling */            
div[data-testid="stTabs"] button[role="tab"][aria-selected="true"] {
    color: #e4781d !important;
}

/* Underline for selected tab */            
div[data-testid="stTabs"] div[role="tablist"] > div:last-child {
    background-color: #d66b1d !important;
    height: 3px !important;
    border-radius: 2px !important;
}
</style>
""", unsafe_allow_html=True)


# Main Workspace Tab
with tabs[0]:
    left_col, right_col = st.columns([3, 2], gap="medium")

    # Data Input
    with left_col:
        st.header("Data Input & Table", anchor=False)

        uploaded_files = st.file_uploader(
            "Upload CSV Files",
            accept_multiple_files=True,
            type="csv",
        )

        if uploaded_files:
            df = pd.read_csv(uploaded_files[-1])
            table = df.copy()
        else:
            table = pd.DataFrame(columns=["Enter your data..."])

        edited_table = st.data_editor(
            table,
            num_rows="dynamic",
            use_container_width=True,
            height=754,
        )

        data_ready = len(edited_table.columns) > 0 and len(edited_table) > 0

    # Analysis Options
    with right_col:
        st.header("Analysis Configuration", anchor=False)

        if len(edited_table.columns) > 0 and len(edited_table) > 0:
            col1 = st.multiselect("Columns", edited_table.columns)
            col2 = st.multiselect("Rows", edited_table.index)
        else:
            st.multiselect("Columns", [], disabled=True)
            st.multiselect("Rows", [], disabled=True)

        st.markdown("---")

        st.subheader("Computation Options", anchor=False)

        c1, c2 = st.columns(2)

        with c1:
            mean = st.checkbox("Mean", disabled=not data_ready)
            median = st.checkbox("Median", disabled=not data_ready)
            mode = st.checkbox("Mode", disabled=not data_ready)
            variance = st.checkbox("Variance", disabled=not data_ready)
            std_dev = st.checkbox("Standard Deviation", disabled=not data_ready)
            percentiles = st.checkbox("Percentiles", disabled=not data_ready)

        with c2:
            pearson = st.checkbox("Pearson's Correlation", disabled=not data_ready)
            spearman = st.checkbox("Spearman's Rank", disabled=not data_ready)
            regression = st.checkbox("Least Squares Regression", disabled=not data_ready)
            chi_square = st.checkbox("Chi-Square Test", disabled=not data_ready)
            binomial = st.checkbox("Binomial Distribution", disabled=not data_ready)
            variation = st.checkbox("Coefficient of Variation", disabled=not data_ready)

        st.markdown("---")

        st.subheader("Visualization Options", anchor=False)

        v1, v2 = st.columns(2)

        with v1:
            hist = st.checkbox(
                "Pie Chart",
                key="viz_hist",
                disabled=not data_ready
            )
            box = st.checkbox(
                "Vertical Bar Chart",
                key="viz_box",
                disabled=not data_ready
            )
            scatter = st.checkbox(
                "Horizontal Bar Chart",
                key="viz_scatter",
                disabled=not data_ready
            )

        with v2:
            line = st.checkbox(
                "Scatter Plot",
                key="viz_line",
                disabled=not data_ready
            )
            heatmap = st.checkbox(
                "Line of Best Fit Scatter Plot",
                key="viz_heatmap",
                disabled=not data_ready
            )

        st.markdown("---")

        st.markdown('<div class="run-analysis-anchor">', unsafe_allow_html=True)

        if col1 and col2:
            parsedData = edited_table.loc[col2, col1].copy()
        elif col1:
            parsedData = edited_table[col1].copy()
        elif col2:
            parsedData = edited_table.loc[col2].copy()
        else:
            parsedData = edited_table.copy()

        run_clicked = st.button(
            "Run Analysis",
            key="run_analysis",
            use_container_width=True,
            disabled=not data_ready
        )

        if run_clicked:
            run = {
                "id": str(uuid.uuid4()),
                "name": f"Run {len(st.session_state.analysis_runs) + 1}",
                "table": edited_table,
                "data": parsedData,
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
            }

            st.markdown('</div>', unsafe_allow_html=True)

            st.session_state.analysis_runs.append(run)
            st.rerun()

# Analysis Result Tabs
for i, tab in enumerate(tabs[1:]):
    with tab:
        run = st.session_state.analysis_runs[i]

        st.header(f"Analysis Results — {run['name']}", anchor=False)

        st.markdown("### Methods Applied")
        for m in run["methods"]:
            st.write("•", m)

        st.markdown("### Selected Cell Data")
        st.dataframe(run["data"], use_container_width=True)
        st.caption(f"Rows: {run['rows']}, Columns: {run['columns']}")

        st.markdown("---")

        if st.button("Delete This Run", key=f"delete_{i}"):
            st.session_state.analysis_runs.pop(i)
            st.rerun()
