# Streamlit AG Grid CSV Range Selection

This project demonstrates how to use AG Grid in Streamlit to import a CSV, select a range of cells, and process the selected data in Python.

## Features

- **CSV Import**: Upload any CSV file.
- **AG Grid Display**: Interactive grid with range selection enabled.
- **Range Selection**: Select cells by clicking and dragging.
- **Data Feedback**: Selected data is sent back to Python for processing/display.

### Installation

1.  **Install Python dependencies**:

Open the Terminal app.
Install the frontend dependencies:
    ```bash
    pip install -r requirements.txt   ```
Install Homebrew if you don't have it:
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
Install Node.js using Homebrew:
    brew install node
    npm install
Navigate to your project directory:
    Example: cd /Users/hyattkamel/Downloads/Streamlit/streamlit_aggrid_range/frontend


3.  **Build the Frontend Component**:
    The custom component requires a React build.
    ```bash
    cd streamlit_aggrid_range/frontend
    npm install
    npm run build
    cd ../..
    ```

## Usage

1.  **Run the Streamlit App**:
    ```bash
    streamlit run app.py
    ```

2.  **Interact**:
    - Upload a CSV using the file uploader.
    - Drag your mouse across cells in the grid to select a range.
    - View the selected data subset below the grid.

## Project Structure

- `app.py`: The main Streamlit application.
- `streamlit_aggrid_range/`: The custom component package.
    - `__init__.py`: Python wrapper for the component.
    - `frontend/`: React source code.
        - `src/AgGridRange.jsx`: Main React component using `ag-grid-react`.

## Development

To modify the frontend:
1.  Edit files in `streamlit_aggrid_range/frontend/src`.
2.  Rebuild: `npm run build` inside the frontend directory.
3.  Refresh the Streamlit app.
