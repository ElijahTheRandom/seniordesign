import streamlit as st
import pandas as pd
import uuid
import base64
from PIL import Image
from streamlit_modal import Modal

# Function to convert image to base64
def image_to_base64(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()

# Session state
if "analysis_runs" not in st.session_state:
    st.session_state.analysis_runs = []

if "modal_message" not in st.session_state:
    st.session_state.modal_message = ""

if "has_file" not in st.session_state:
    st.session_state.has_file = False

if "checkbox_key" not in st.session_state:
    st.session_state.checkbox_key = 0
    
# Page config
st.set_page_config(
    page_title="Statistical Analyzer",
    layout="wide",
)

# Create modal instance
error_modal = Modal(
    "Invalid Analysis", 
    key="error_modal",
    padding=20,
    max_width=500
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

st.markdown("""
<style>
/* Highlight selected multiselect items with orange border like checkboxes */
div[data-baseweb="select"] > div > div > div > div {
    border: 1px solid #e4781d !important;   /* orange border */
    border-radius: 4px !important;
    box-shadow: 0 0 0 2px rgba(228, 120, 29, 0.5) !important; /* similar to checkbox hover/focus */
    background-color: transparent !important; /* keep background transparent */
    color: #ffffff !important; /* keep text readable */
}
</style>
""", unsafe_allow_html=True)

# Selectbox styling
st.markdown("""
<style>
div[data-baseweb="select"] svg {
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
    font-weight: 400;
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

        # Detect when file is closed and reset checkboxes
        if not uploaded_files and st.session_state.has_file:
            st.session_state.checkbox_key += 1
            st.session_state.has_file = False
        elif uploaded_files:
            st.session_state.has_file = True

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
            hide_index=True,
        )

        data_ready = len(edited_table.columns) > 0 and len(edited_table) > 0

    # Analysis Options
    with right_col:
        st.header("Analysis Configuration", anchor=False)

        col1 = []
        col2 = []

        if len(edited_table.columns) > 0 and len(edited_table) > 0:
            col1 = st.multiselect("Columns", edited_table.columns)
            col2 = st.multiselect("Rows", edited_table.index)
        else:
            col1 = []
            col2 = []
            st.multiselect("Columns", [], disabled=True)
            st.multiselect("Rows", [], disabled=True)

        st.markdown("---")

        st.subheader("Computation Options", anchor=False)

        c1, c2 = st.columns(2)

        with c1:
            mean = st.checkbox("Mean", disabled=not data_ready, key=f"mean_{st.session_state.checkbox_key}")
            median = st.checkbox("Median", disabled=not data_ready, key=f"median_{st.session_state.checkbox_key}")
            mode = st.checkbox("Mode", disabled=not data_ready, key=f"mode_{st.session_state.checkbox_key}")
            variance = st.checkbox("Variance", disabled=not data_ready, key=f"variance_{st.session_state.checkbox_key}")
            std_dev = st.checkbox("Standard Deviation", disabled=not data_ready, key=f"std_dev_{st.session_state.checkbox_key}")
            percentiles = st.checkbox("Percentiles", disabled=not data_ready, key=f"percentiles_{st.session_state.checkbox_key}")

        with c2:
            pearson = st.checkbox("Pearson's Correlation", disabled=not data_ready, key=f"pearson_{st.session_state.checkbox_key}")
            spearman = st.checkbox("Spearman's Rank", disabled=not data_ready, key=f"spearman_{st.session_state.checkbox_key}")
            regression = st.checkbox("Least Squares Regression", disabled=not data_ready, key=f"regression_{st.session_state.checkbox_key}")
            chi_square = st.checkbox("Chi-Square Test", disabled=not data_ready, key=f"chi_square_{st.session_state.checkbox_key}")
            binomial = st.checkbox("Binomial Distribution", disabled=not data_ready, key=f"binomial_{st.session_state.checkbox_key}")
            variation = st.checkbox("Coefficient of Variation", disabled=not data_ready, key=f"variation_{st.session_state.checkbox_key}")

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
            non_numeric_cols = []
            numeric_required = mean or median or mode or std_dev or variance or pearson or spearman or regression
            if numeric_required:
                for col in parsedData.columns:
                    coerced = pd.to_numeric(parsedData[col], errors='coerce')

                    for row_idx in parsedData.index:
                        original_value = parsedData.at[row_idx, col]
                        coerced_value = coerced.at[row_idx]

                        if pd.notna(original_value) and pd.isna(coerced_value):
                            if col not in non_numeric_cols:
                                non_numeric_cols.append({
                                    "row": row_idx,
                                    "column": col,
                                    "value": original_value
                                }
                                )
            # Show modal if non-numeric data found                    
            if non_numeric_cols:
                preview = non_numeric_cols[:3]
                message = " The following non-numeric data was found:\n"

                for cell in preview:
                    message += f" - Row: {cell['row']}, Column: {cell['column']}, Value: '{cell['value']}'\n"
                
                if len(non_numeric_cols) > 3:
                    message += f" ...and {len(non_numeric_cols) - 3} more entries.\n"
                
                st.session_state.modal_message = message
                error_modal.open()
            else:
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

# Modal Dialog using streamlit_modal
if error_modal.is_open():
    with error_modal.container():
        st.markdown(
            f"""
            <style>
            /* Modal content styling */
            div[data-baseweb="modal"] > div:first-child {{
                background-color: #262730 !important;
                border: 2px solid #e4781d !important;
                border-radius: 12px !important;
                padding: 0.5rem 1rem !important;
                max-width: 500px !important;
                width: 90% !important;
            }}

            /* Modal header */
            div[data-baseweb="modal"] h3 {{
                color: #e4781d;
                margin-top: 0.5rem;
                margin-bottom: 0.5rem;
                font-size: 1.5rem;
                text-align: center;
            }}

            /* Modal message text */
            div[data-baseweb="modal"] p {{
                color: #ffffff;
                white-space: pre-wrap;
                line-height: 1.6;
                margin: 0.3rem 0 !important;
                font-size: 1rem;
                text-align: center;
            }}
            
            /* Reduce spacing around images */
            div[data-baseweb="modal"] img {{
                margin: 0 !important;
                padding: 0 !important;
            }}

            /* Close button styling */
            button[aria-label="Close"] {{
                background-color: #262730 !important;
                color: #e4781d !important;
                border: 1px solid #e4781d !important;
                border-radius: 6px !important;
                font-weight: bold;
                font-size: 1rem;
            }}

            button[aria-label="Close"]:hover {{
                background-color: #e4781d !important;
                color: #ffffff !important;
            }}
            </style>
            """,
            unsafe_allow_html=True
        )
        
        # Display warning squirrel image centered and larger
        try:
            img_base64 = image_to_base64("warningSquirrel.PNG")
            st.markdown(
                f"""
                <div style="display:flex; justify-content:center; margin: 0; padding: 0;">
                    <img 
                        src="data:image/png;base64,{img_base64}" 
                        style="width:100%; max-width:400px; pointer-events:none; margin: 0; padding: 0;"
                    />
                </div>
                """,
                unsafe_allow_html=True
            )
        except:
            st.markdown("### ⚠")
        
        st.write(st.session_state.modal_message)

