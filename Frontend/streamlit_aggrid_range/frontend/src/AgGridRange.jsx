import React, { useEffect, useState, useMemo } from "react"
import {
    Streamlit,
    withStreamlitConnection,
} from "streamlit-component-lib"
import { AgGridReact } from "ag-grid-react"
import "ag-grid-enterprise"
import "ag-grid-community/styles/ag-grid.css"
import "ag-grid-community/styles/ag-theme-alpine.css"
import "./styles.css"

const AgGridRange = (props) => {
    // Destructure props (args are passed via specialized 'args' prop in withStreamlitConnection wrapper usually, 
    // but simpler wrapping passes them directly if customized, 
    // checking standard streamlit-component-lib usage: props.args)
    const { rowData, columnDefs } = props.args

    // State for grid api to access later
    const [gridApi, setGridApi] = useState(null)
    const [selectedColId, setSelectedColId] = useState(null)

    // Dynamic column definitions to apply header styling
    const displayColumnDefs = useMemo(() => {
        return columnDefs.map(col => ({
            ...col,
            headerClass: col.field === selectedColId ? 'full-column-selected' : ''
        }))
    }, [columnDefs, selectedColId])

    // Auto-resize height on mount and updates
    useEffect(() => {
        Streamlit.setFrameHeight()
    })

    const onGridReady = (params) => {
        setGridApi(params.api)
        Streamlit.setFrameHeight()
    }

    // Handle selection changes
    const onRangeSelectionChanged = (event) => {
        if (!event.api) return;

        const cellRanges = event.api.getCellRanges();
        const rowCount = event.api.getDisplayedRowCount();

        // Check if we have a single range that covers the full height and exactly one column
        let newSelectedColId = null;
        if (cellRanges.length === 1) {
            const r = cellRanges[0];
            if (r.startRow && r.endRow) {
                const s = r.startRow.rowIndex;
                const e = r.endRow.rowIndex;
                const height = Math.abs(e - s) + 1;

                // Check if full height
                if (height === rowCount && r.columns.length === 1) {
                    newSelectedColId = r.columns[0].getColId();
                }
            }
        }

        // Update visual state if changed
        if (newSelectedColId !== selectedColId) {
            setSelectedColId(newSelectedColId);
            // Force refresh of headers to apply new class immediately
            event.api.refreshHeader();
        }

        // Map ranges to a serializable format
        const formattedRanges = cellRanges.map((range) => {
            // Get start and end row indices
            let startRow = range.startRow ? range.startRow.rowIndex : 0;
            let endRow = range.endRow ? range.endRow.rowIndex : 0;

            // Ensure start is always <= end for simpler python logic
            if (startRow > endRow) {
                const temp = startRow;
                startRow = endRow;
                endRow = temp;
            }

            // Get column IDs
            const columns = range.columns.map((col) => col.colId);

            return {
                startRow,
                endRow,
                columns
            };
        });

        Streamlit.setComponentValue(formattedRanges);
    }

    // Handle ESC key to clear selection
    useEffect(() => {
        const handleKeyDown = (event) => {
            if (event.key === "Escape" && gridApi) {
                gridApi.clearRangeSelection()
            }
        }

        document.addEventListener("keydown", handleKeyDown)

        return () => {
            document.removeEventListener("keydown", handleKeyDown)
        }
    }, [gridApi])

    // Disable sort and filter by default, and hide menu
    const defaultColDef = useMemo(() => ({
        sortable: false,
        filter: false,
        resizable: true,
        suppressHeaderMenuButton: true,
        suppressMenu: true,
    }), [])

    const onColumnHeaderClicked = (params) => {
        // Select the entire column when header is clicked
        if (params.api) {
            const colId = params.column.getColId();
            const rowCount = params.api.getDisplayedRowCount();

            params.api.clearRangeSelection();
            params.api.addCellRange({
                columns: [colId],
                rowStartIndex: 0,
                rowEndIndex: rowCount - 1
            });
        }
    }

    // Container style - ensure it has height for grid to render if not autoHeight
    // Using autoHeight often requires DOM layout adjustment, but let's try fixed constraint or full width 
    // with autoHeight for Streamlit smooth embedding.
    const containerStyle = useMemo(() => ({ width: "100%", height: "70vh" }), []);

    // If we want dynamic height, we can use domLayout='autoHeight' and call setFrameHeight repeatedly.

    return (
        <div className="ag-theme-alpine" style={containerStyle}>
            <AgGridReact
                rowData={rowData}
                columnDefs={displayColumnDefs}
                defaultColDef={defaultColDef}
                onGridReady={onGridReady}
                enableRangeSelection={true}
                onRangeSelectionChanged={onRangeSelectionChanged}
                onColumnHeaderClicked={onColumnHeaderClicked}
                suppressRowClickSelection={true}
                // Optional: extra settings for better UX
                rowSelection="multiple"
            />
        </div>
    )
}

export default withStreamlitConnection(AgGridRange)
