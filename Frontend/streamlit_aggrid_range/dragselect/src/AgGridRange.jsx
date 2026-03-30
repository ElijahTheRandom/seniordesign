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
    const [hasEdits, setHasEdits] = useState(false)
    const [containerHeight, setContainerHeight] = useState(() => {
        if (typeof window === "undefined") return 600
        return Math.max(550, Math.min(800, Math.round(window.innerHeight * 0.6)))
    })

    // Dynamic column definitions to apply header styling
    const displayColumnDefs = useMemo(() => {
        return columnDefs.map(col => ({
            ...col,
            headerClass: col.field === selectedColId ? 'full-column-selected' : ''
        }))
    }, [columnDefs, selectedColId])

    // Auto-resize height on mount and updates
    useEffect(() => {
        Streamlit.setFrameHeight(containerHeight + 20)
    }, [containerHeight])

    useEffect(() => {
        const handleResize = () => {
            const nextHeight = Math.max(550, Math.min(800, Math.round(window.innerHeight * 0.6)))
            setContainerHeight(nextHeight)
        }

        window.addEventListener("resize", handleResize)
        return () => window.removeEventListener("resize", handleResize)
    }, [])

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

        Streamlit.setComponentValue({
            selections: formattedRanges,
            editedData: null
        });
    }

    // Handle cell value editing
    const onCellValueChanged = (event) => {
        if (!event.api) return;

        // Collect all current row data after the edit
        const updatedRows = [];
        event.api.forEachNode(node => updatedRows.push({...node.data}));

        // Get current selections
        const cellRanges = event.api.getCellRanges() || [];
        const formattedRanges = cellRanges.map((range) => {
            let startRow = range.startRow ? range.startRow.rowIndex : 0;
            let endRow = range.endRow ? range.endRow.rowIndex : 0;
            if (startRow > endRow) {
                const temp = startRow;
                startRow = endRow;
                endRow = temp;
            }
            const columns = range.columns.map((col) => col.colId);
            return { startRow, endRow, columns };
        });

        setHasEdits(true);
        Streamlit.setComponentValue({
            selections: formattedRanges,
            editedData: updatedRows
        });
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
        editable: true,
        suppressHeaderMenuButton: true,
        suppressMenu: true,
        valueParser: (params) => {
            const val = params.newValue;
            if (val === "" || val === null || val === undefined) return val;
            const num = Number(val);
            return isNaN(num) ? val : num;
        },
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
    const containerStyle = useMemo(() => ({
        width: "100%",
        height: `${containerHeight}px`,  // your fixed height
        paddingBottom: "20px",           // reserve space for horizontal scrollbar
        boxSizing: "border-box"           // make padding count inside height
    }), [containerHeight]);

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
                onCellValueChanged={onCellValueChanged}
                suppressRowClickSelection={true}
                // Optional: extra settings for better UX
                rowSelection="multiple"
                domLayout="normal" // <--- add this line
            />
        </div>
    )
}

export default withStreamlitConnection(AgGridRange)
