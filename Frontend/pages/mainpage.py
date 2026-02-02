import streamlit as st
import pandas as pd
import uuid
import base64
import html
import os
import io

BASE_DIR = os.path.dirname(__file__)

from PIL import Image
from streamlit_modal import Modal


# Function to convert image to base64
def image_to_base64(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()

def render_modal_content(img_path, message):
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        if os.path.exists(img_path):
            img = Image.open(img_path)
            st.image(img, width=300)
        else:
            st.error(f"Image not found: {img_path}")

    st.markdown("---")

    for line in message.split("\n"):
        st.markdown(line if line.strip() else "")

# Session state
if "analysis_runs" not in st.session_state:
    st.session_state.analysis_runs = []

if "modal_message" not in st.session_state:
    st.session_state.modal_message = ""

if "has_file" not in st.session_state:
    st.session_state.has_file = False

if "checkbox_key" not in st.session_state:
    st.session_state.checkbox_key = 0

if "show_invalid_modal" not in st.session_state:
    st.session_state.show_invalid_modal = False

if "show_success_modal" not in st.session_state:
    st.session_state.show_success_modal = False
    
# Page config
st.set_page_config(
    page_title="Statistical Analyzer",
    layout="wide",
)

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
</style>
""", unsafe_allow_html=True)

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
    margin-top: -3.5rem !important;
    margin-bottom: -3.5rem !important;
}
            
/* Remove anchor beside the modal title */
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

# Multiselect box styling
st.markdown("""
<style>
/* MULTISELECT — base state */
div[data-testid="stMultiSelect"] div[role="combobox"] {
    background-color: #262730 !important;
    border: 1px solid #e4781d !important;
    border-radius: 6px !important;
    box-shadow: none !important;
    transition: border-color 0.15s ease, box-shadow 0.15s ease;
}

/* Hover */
div[data-testid="stMultiSelect"] div[role="combobox"]:hover {
    border-color: #d66b1d !important;
    box-shadow: 0 0 0 2px rgba(214, 107, 29, 0.35) !important;
}

/* Focus / active / open */
div[data-testid="stMultiSelect"] div[role="combobox"][aria-expanded="true"],
div[data-testid="stMultiSelect"] div[role="combobox"]:focus,
div[data-testid="stMultiSelect"] div[role="combobox"]:focus-visible {
    outline: none !important;
    border-color: #e4781d !important;
    box-shadow: 0 0 0 3px rgba(228, 120, 29, 0.5) !important;
}

/* Remove Streamlit's red internal borders */
div[data-testid="stMultiSelect"] * {
    border-color: #e4781d !important;
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

st.markdown("""
<style>
/* HARD override for the X inside multiselect pills */
div[data-testid="stMultiSelect"] span[data-baseweb="tag"] svg path {
    stroke: white !important;
    stroke-width: 2px !important;
}

/* Prevent Streamlit from recoloring it on hover/focus */
div[data-testid="stMultiSelect"] span[data-baseweb="tag"]:hover svg path,
div[data-testid="stMultiSelect"] span[data-baseweb="tag"] button:hover svg path {
    stroke: white !important;
}
</style>
""", unsafe_allow_html=True)

# Data editor checkbox styling
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

div[data-testid="stDataEditor"] label[data-baseweb="checkbox"] span {
    border-color: #e4781d !important;
}

div[data-testid="stDataEditor"] label[data-baseweb="checkbox"] svg {
    stroke: #e4781d !important;
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

st.markdown("""
<style>
/* Force the download button container and link to match primary buttons */
div[data-testid="stDownloadButton"] {
    width: 100% !important;
    display: block !important;
}

div[data-testid="stDownloadButton"] a {
    display: inline-flex !important;
    justify-content: center !important;
    align-items: center !important;
    width: 100% !important;           /* full width */
    min-height: 38px !important;      /* match st.button height */
    padding: 8px 16px !important;
    background-color: #d66b1d !important;  /* orange primary color */
    color: #ffffff !important;
    border: 1px solid #d66b1d !important;
    border-radius: 6px !important;
    font-weight: 400;
    text-decoration: none !important;
    cursor: pointer !important;
    box-sizing: border-box !important;
    transition: background-color 0.15s ease, box-shadow 0.15s ease;
}

/* Hover */
div[data-testid="stDownloadButton"] a:hover {
    background-color: #e4781d !important;
    border-color: #e4781d !important;
    box-shadow: 0 0 0 3px rgba(214,107,29,0.35) !important;
}

/* Focus */
div[data-testid="stDownloadButton"] a:focus-visible {
    outline: none !important;
    box-shadow: 0 0 0 3px rgba(214,107,29,0.5) !important;
}

/* Active */
div[data-testid="stDownloadButton"] a:active {
    background-color: #b85b18 !important;
    border-color: #b85b18 !important;
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
/* ---- FINAL KILL FOR THE ARROW SCROLLBAR ---- */

/* This is the actual Streamlit content container inside the modal */
div[data-testid="stModal"] div[data-testid="stVerticalBlock"] {
    overflow: hidden !important;
}

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

# Function to delete an analysis run
def delete_run(index):
    st.session_state.analysis_runs.pop(index)

# Function to save the analysis run

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
        edited_table.index = edited_table.index + 1

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

        # Determine how many columns/rows are selected
        num_cols_selected = len(col1)
        num_rows_selected = len(col2)

        disable_two_cols = num_cols_selected < 2
        disable_one_col = num_cols_selected < 1
        disable_one_row = num_rows_selected < 1

        # Computation Options
        st.subheader("Computation Options", anchor=False)
        c1, c2 = st.columns(2)

        with c1:
            mean = st.checkbox("Mean", disabled=not data_ready or disable_one_col, key=f"mean_c1_{st.session_state.checkbox_key}")
            median = st.checkbox("Median", disabled=not data_ready or disable_one_col, key=f"median_c1_{st.session_state.checkbox_key}")
            mode = st.checkbox("Mode", disabled=not data_ready or disable_one_col, key=f"mode_c1_{st.session_state.checkbox_key}")
            variance = st.checkbox("Variance", disabled=not data_ready or disable_one_col, key=f"variance_c1_{st.session_state.checkbox_key}")
            std_dev = st.checkbox("Standard Deviation", disabled=not data_ready or disable_one_col, key=f"std_dev_c1_{st.session_state.checkbox_key}")
            percentiles = st.checkbox("Percentiles", disabled=not data_ready or disable_one_col, key=f"percentiles_c1_{st.session_state.checkbox_key}")

        with c2:
            pearson = st.checkbox("Pearson's Correlation", disabled=not data_ready or disable_two_cols, key=f"pearson_c2_{st.session_state.checkbox_key}")
            spearman = st.checkbox("Spearman's Rank", disabled=not data_ready or disable_two_cols, key=f"spearman_c2_{st.session_state.checkbox_key}")
            regression = st.checkbox("Least Squares Regression", disabled=not data_ready or disable_two_cols, key=f"regression_c2_{st.session_state.checkbox_key}")
            chi_square = st.checkbox("Chi-Square Test", disabled=not data_ready or disable_one_col, key=f"chi_square_c2_{st.session_state.checkbox_key}")
            binomial = st.checkbox("Binomial Distribution", disabled=not data_ready or disable_one_col, key=f"binomial_c2_{st.session_state.checkbox_key}")
            variation = st.checkbox("Coefficient of Variation", disabled=not data_ready or disable_one_col, key=f"variation_c2_{st.session_state.checkbox_key}")

        st.markdown("---")

        st.subheader("Visualization Options", anchor=False)
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

        st.markdown('<div class="run-analysis-anchor">', unsafe_allow_html=True)

        # Make a copy with shifted index for row selection
        edited_table_for_loc = edited_table.copy()
        edited_table_for_loc.index = edited_table_for_loc.index + 1

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
                st.session_state.modal_message = f"Analysis tab '{run['name']}' has been successfully created!"
                st.session_state.show_success_modal = True
                success_modal.open()


# Analysis Result Tabs
for i, tab in enumerate(tabs[1:]):
    with tab:
        run = st.session_state.analysis_runs[i]

        st.header(f"Analysis Results — {run['name']}", anchor=False)

        st.markdown("### Methods Applied", )
        for m in run["methods"]:
            st.write("•", m)

        st.markdown("---")

        # Visualization Methods
        # Visualization Methods — only show if something was selected
        viz_methods = run.get("visualizations", [])

        if viz_methods:   # <-- key line
            st.markdown("### Visualizations Applied")
            for v in viz_methods:
                st.write("•", v)

            st.markdown("---")

        st.markdown("### Selected Cell Data")
        st.dataframe(run["data"], use_container_width=True)
        st.caption(f"Rows: {run['rows']}, Columns: {run['columns']}")

        st.markdown("---")

        col1, col2, col3, col4 = st.columns([1, 1, 1, 1], gap="small")
        with col1:
            st.button("Update Run Name", key=f"name_{i}", use_container_width=True)
        with col2:
            st.button("Save Run Locally", key=f"save_{i}", use_container_width=True)
        with col3:
            # Create the text content for export
            export_text = f"Analysis Results — {run['name']}\n\n"

            if run["methods"]:
                export_text += "Methods Applied:\n"
                for method in run["methods"]:
                    export_text += f"- {method}\n"
                export_text += "\n"

            if run.get("visualizations"):
                export_text += "Visualizations Applied:\n"
                for viz in run["visualizations"]:
                    export_text += f"- {viz}\n"
                export_text += "\n"

            export_text += "Selected Cell Data:\n"
            export_text += run["data"].to_csv(sep="\t", index=True)

            st.download_button(
                label="Export Run",
                data=export_text,
                file_name=f"{run['name']}.txt",
                mime="text/plain",
                use_container_width=True,
                key=f"export_{i}",
            )
        with col4:
            if st.button("Delete Run", key=f"delete_{i}", use_container_width=True):
                st.session_state.analysis_runs.pop(i)
                st.rerun()

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

