import React, { useEffect, useState, useMemo, useRef, useCallback } from "react"
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
    const { rowData, columnDefs } = props.args

    const [gridApi, setGridApi] = useState(null)
    const [selectedColId, setSelectedColId] = useState(null)
    const [hasEdits, setHasEdits] = useState(false)
    const [containerHeight, setContainerHeight] = useState(() => {
        if (typeof window === "undefined") return 600
        return Math.max(550, Math.min(800, Math.round(window.innerHeight * 0.6)))
    })

    // Header rename state
    const [renamedHeaders, setRenamedHeaders] = useState({})
    const [editingColId, setEditingColId] = useState(null)
    const [editValue, setEditValue] = useState("")
    const [editPos, setEditPos] = useState({ top: 0, left: 0, width: 0 })
    const editInputRef = useRef(null)
    const headerClickTimers = useRef({})

    // Track renamed headers — merge incoming columnDefs field names with renames
    const effectiveColumnDefs = useMemo(() => {
        return columnDefs.map(col => {
            const renamed = renamedHeaders[col.field]
            return {
                ...col,
                headerName: renamed || col.field,
                headerClass: col.field === selectedColId ? 'full-column-selected' : ''
            }
        })
    }, [columnDefs, selectedColId, renamedHeaders])

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

        // If the user has made edits, include the current row data so that
        // a selection event never overwrites a prior cell edit in Streamlit's
        // component state.  Without this, onRangeSelectionChanged would send
        // editedData: null and Python would see no edits on the next rerun.
        let currentEditedData = null;
        if (hasEdits && event.api) {
            const updatedRows = [];
            event.api.forEachNode(node => updatedRows.push({...node.data}));
            currentEditedData = updatedRows;
        }

        Streamlit.setComponentValue({
            selections: formattedRanges,
            editedData: currentEditedData,
            renamedHeaders: Object.keys(renamedHeaders).length > 0 ? renamedHeaders : null
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
            editedData: updatedRows,
            renamedHeaders: Object.keys(renamedHeaders).length > 0 ? renamedHeaders : null
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

    // Helper: send current state to Streamlit
    const sendValue = useCallback((api, overrideEdited) => {
        const cellRanges = api.getCellRanges() || [];
        const formattedRanges = cellRanges.map((range) => {
            let startRow = range.startRow ? range.startRow.rowIndex : 0;
            let endRow = range.endRow ? range.endRow.rowIndex : 0;
            if (startRow > endRow) { const t = startRow; startRow = endRow; endRow = t; }
            const columns = range.columns.map((col) => col.colId);
            return { startRow, endRow, columns };
        });
        Streamlit.setComponentValue({
            selections: formattedRanges,
            editedData: overrideEdited !== undefined ? overrideEdited : null,
            renamedHeaders: Object.keys(renamedHeaders).length > 0 ? renamedHeaders : null
        });
    }, [renamedHeaders]);

    // Header click: single = select column, double = rename
    const onColumnHeaderClicked = useCallback((params) => {
        if (!params.api) return;
        const colId = params.column.getColId();

        // Check for double-click (two clicks within 300ms)
        if (headerClickTimers.current[colId]) {
            // Double-click detected — open rename editor
            clearTimeout(headerClickTimers.current[colId]);
            headerClickTimers.current[colId] = null;

            // Find the header cell element to position the input
            const headerEl = document.querySelector(`.ag-header-cell[col-id="${colId}"]`);
            if (headerEl) {
                const rect = headerEl.getBoundingClientRect();
                const gridEl = headerEl.closest('.ag-theme-alpine');
                const gridRect = gridEl ? gridEl.getBoundingClientRect() : { top: 0, left: 0 };
                setEditPos({
                    top: rect.top - gridRect.top,
                    left: rect.left - gridRect.left,
                    width: rect.width,
                    height: rect.height
                });
            }
            setEditingColId(colId);
            setEditValue(renamedHeaders[colId] || colId);
            return;
        }

        // First click — start timer, and select column
        headerClickTimers.current[colId] = setTimeout(() => {
            headerClickTimers.current[colId] = null;
        }, 300);

        // Select the entire column
        const rowCount = params.api.getDisplayedRowCount();
        params.api.clearRangeSelection();
        params.api.addCellRange({
            columns: [colId],
            rowStartIndex: 0,
            rowEndIndex: rowCount - 1
        });
    }, [renamedHeaders]);

    // Focus the rename input when it appears
    useEffect(() => {
        if (editingColId && editInputRef.current) {
            editInputRef.current.focus();
            editInputRef.current.select();
        }
    }, [editingColId]);

    // Commit header rename
    const commitRename = useCallback(() => {
        if (!editingColId) return;
        const trimmed = editValue.trim();
        if (trimmed && trimmed !== editingColId) {
            const updated = { ...renamedHeaders, [editingColId]: trimmed };
            setRenamedHeaders(updated);
            // Send rename data to Streamlit immediately
            if (gridApi) {
                const cellRanges = gridApi.getCellRanges() || [];
                const formattedRanges = cellRanges.map((range) => {
                    let startRow = range.startRow ? range.startRow.rowIndex : 0;
                    let endRow = range.endRow ? range.endRow.rowIndex : 0;
                    if (startRow > endRow) { const t = startRow; startRow = endRow; endRow = t; }
                    const columns = range.columns.map((col) => col.colId);
                    return { startRow, endRow, columns };
                });
                Streamlit.setComponentValue({
                    selections: formattedRanges,
                    editedData: null,
                    renamedHeaders: updated
                });
            }
        }
        setEditingColId(null);
        setEditValue("");
    }, [editingColId, editValue, renamedHeaders, gridApi]);

    // Cancel rename
    const cancelRename = useCallback(() => {
        setEditingColId(null);
        setEditValue("");
    }, []);

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
        <div className="ag-theme-alpine" style={{ ...containerStyle, position: "relative" }}>
            {/* Inline header rename overlay */}
            {editingColId && (
                <div
                    className="header-rename-overlay"
                    style={{
                        position: "absolute",
                        top: editPos.top,
                        left: editPos.left,
                        width: editPos.width,
                        height: editPos.height || 32,
                        zIndex: 1000,
                    }}
                >
                    <input
                        ref={editInputRef}
                        className="header-rename-input"
                        type="text"
                        value={editValue}
                        onChange={(e) => setEditValue(e.target.value)}
                        onKeyDown={(e) => {
                            if (e.key === "Enter") commitRename();
                            if (e.key === "Escape") cancelRename();
                        }}
                        onBlur={commitRename}
                    />
                </div>
            )}
            <AgGridReact
                rowData={rowData}
                columnDefs={effectiveColumnDefs}
                defaultColDef={defaultColDef}
                onGridReady={onGridReady}
                enableRangeSelection={true}
                onRangeSelectionChanged={onRangeSelectionChanged}
                onColumnHeaderClicked={onColumnHeaderClicked}
                onCellValueChanged={onCellValueChanged}
                suppressRowClickSelection={true}
                rowSelection="multiple"
                domLayout="normal"
            />
        </div>
    )
}

export default withStreamlitConnection(AgGridRange)
