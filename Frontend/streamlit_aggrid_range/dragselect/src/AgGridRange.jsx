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
    const { rowData, columnDefs, expandable } = props.args

    const [gridApi, setGridApi] = useState(null)
    const [selectedColIds, setSelectedColIds] = useState(new Set())
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
    const ctrlPressed = useRef(false)

    // ---------------------------------------------------------------------------
    // Local column / row state for Tab/Enter expansion (blank tables only)
    // ---------------------------------------------------------------------------
    // We keep a local copy of column defs and row data so that when the user
    // expands the table (Tab → new column, Enter → new row) the grid re-renders
    // immediately without waiting for the Python rerun.  Python is notified via
    // setComponentValue so that it can persist the new structure.
    //
    // Sync strategy: only re-initialize from props when the *shape* of the data
    // changes (different number of columns or rows).  This prevents Python's
    // echo-back after a setComponentValue call from wiping out a local expansion
    // the user just made.
    const [localCols, setLocalCols] = useState(() => columnDefs)
    const [localRows, setLocalRows] = useState(() => rowData)

    // Track the last shape we received from Python so we can detect genuine
    // prop changes vs. echoed-back data.
    const lastPropsShapeRef = useRef(
        JSON.stringify({ c: columnDefs.map(d => d.field), r: rowData.length })
    )

    useEffect(() => {
        const shape = JSON.stringify({ c: columnDefs.map(d => d.field), r: rowData.length })
        if (shape !== lastPropsShapeRef.current) {
            lastPropsShapeRef.current = shape
            setLocalCols(columnDefs)
            setLocalRows(rowData)
            setRenamedHeaders({})
            setHasEdits(false)
        }
    }, [columnDefs, rowData])

    // Track Ctrl/Meta key state reliably via global listeners
    useEffect(() => {
        const onKeyDown = (e) => {
            if (e.key === "Control" || e.key === "Meta") ctrlPressed.current = true
        }
        const onKeyUp = (e) => {
            if (e.key === "Control" || e.key === "Meta") ctrlPressed.current = false
        }
        window.addEventListener("keydown", onKeyDown)
        window.addEventListener("keyup", onKeyUp)
        return () => {
            window.removeEventListener("keydown", onKeyDown)
            window.removeEventListener("keyup", onKeyUp)
        }
    }, [])

    // Track renamed headers — merge incoming columnDefs field names with renames
    const effectiveColumnDefs = useMemo(() => {
        return localCols.map(col => {
            const renamed = renamedHeaders[col.field]
            return {
                ...col,
                headerName: renamed || col.field,
                headerClass: selectedColIds.has(col.field) ? 'full-column-selected' : ''
            }
        })
    }, [localCols, selectedColIds, renamedHeaders])

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

        // Collect all columns that have a full-height single-column range
        const newSelectedColIds = new Set();
        for (const r of cellRanges) {
            if (r.startRow && r.endRow && r.columns.length === 1) {
                const s = r.startRow.rowIndex;
                const e = r.endRow.rowIndex;
                if (Math.abs(e - s) + 1 === rowCount) {
                    newSelectedColIds.add(r.columns[0].getColId());
                }
            }
        }

        // Update visual state if changed
        const prev = selectedColIds;
        const changed = newSelectedColIds.size !== prev.size ||
            [...newSelectedColIds].some(id => !prev.has(id));
        if (changed) {
            setSelectedColIds(newSelectedColIds);
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
        // Also sync localRows so expansion logic sees the latest data
        setLocalRows(updatedRows);
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
    const sendValue = useCallback((api, overrideEdited, extraCols) => {
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
            renamedHeaders: Object.keys(renamedHeaders).length > 0 ? renamedHeaders : null,
            newColumns: extraCols || null,
        });
    }, [renamedHeaders]);

    // -------------------------------------------------------------------------
    // Tab/Enter expansion helpers (only active when expandable === true)
    // -------------------------------------------------------------------------

    // Generate a unique column name that doesn't clash with existing ones
    const nextColName = useCallback((cols) => {
        const existingNums = cols
            .map(c => {
                const m = c.field.match(/^Col\s+(\d+)$/i)
                return m ? parseInt(m[1], 10) : 0
            })
        const max = existingNums.length > 0 ? Math.max(...existingNums) : cols.length
        return `Col ${max + 1}`
    }, [])

    // Add a new column to the right of the current grid
    const addColumn = useCallback((api) => {
        const newField = nextColName(localCols)
        const newCol = { field: newField }
        const updatedCols = [...localCols, newCol]

        // Collect current row data from the grid (includes any unsaved edits)
        const currentRows = []
        if (api) {
            api.forEachNode(node => currentRows.push({ ...node.data }))
        } else {
            currentRows.push(...localRows)
        }
        // Append the new column key with an empty value to every row
        const updatedRows = currentRows.map(row => ({ ...row, [newField]: "" }))

        // Update local state so the grid re-renders immediately
        setLocalCols(updatedCols)
        setLocalRows(updatedRows)
        setHasEdits(true)

        // Update the shape ref so the next prop sync doesn't reset us
        lastPropsShapeRef.current = JSON.stringify({
            c: updatedCols.map(d => d.field),
            r: updatedRows.length
        })

        // Notify Python
        const formattedRanges = api ? (api.getCellRanges() || []).map(range => {
            let s = range.startRow ? range.startRow.rowIndex : 0
            let e = range.endRow ? range.endRow.rowIndex : 0
            if (s > e) { const t = s; s = e; e = t; }
            return { startRow: s, endRow: e, columns: range.columns.map(c => c.colId) }
        }) : []

        Streamlit.setComponentValue({
            selections: formattedRanges,
            editedData: updatedRows,
            renamedHeaders: Object.keys(renamedHeaders).length > 0 ? renamedHeaders : null,
            newColumns: updatedCols.map(c => c.field),
        })

        return newField
    }, [localCols, localRows, renamedHeaders, nextColName])

    // Add a new empty row at the bottom of the grid
    const addRow = useCallback((api) => {
        const emptyRow = Object.fromEntries(localCols.map(c => [c.field, ""]))

        const currentRows = []
        if (api) {
            api.forEachNode(node => currentRows.push({ ...node.data }))
        } else {
            currentRows.push(...localRows)
        }
        const updatedRows = [...currentRows, emptyRow]

        setLocalRows(updatedRows)
        setHasEdits(true)

        // Update the shape ref
        lastPropsShapeRef.current = JSON.stringify({
            c: localCols.map(d => d.field),
            r: updatedRows.length
        })

        const formattedRanges = api ? (api.getCellRanges() || []).map(range => {
            let s = range.startRow ? range.startRow.rowIndex : 0
            let e = range.endRow ? range.endRow.rowIndex : 0
            if (s > e) { const t = s; s = e; e = t; }
            return { startRow: s, endRow: e, columns: range.columns.map(c => c.colId) }
        }) : []

        Streamlit.setComponentValue({
            selections: formattedRanges,
            editedData: updatedRows,
            renamedHeaders: Object.keys(renamedHeaders).length > 0 ? renamedHeaders : null,
            newColumns: null,
        })

        return updatedRows.length - 1  // index of new row
    }, [localCols, localRows, renamedHeaders])

    // tabToNextCell: intercept Tab on the last column when expandable
    const tabToNextCell = useCallback((params) => {
        if (!expandable) return params.nextCellPosition

        const api = params.api || gridApi
        if (!api) return params.nextCellPosition

        const allCols = api.getAllDisplayedColumns()
        const lastCol = allCols.length > 0 ? allCols[allCols.length - 1] : null
        const currentColId = params.previousCellPosition?.column?.getColId()

        if (lastCol && currentColId === lastCol.getColId()) {
            // Pressed Tab while on the last column — add a new column
            const newField = addColumn(api)

            // After React re-renders with the new column, try to focus its
            // first cell in the same row.  We use a short timeout to allow
            // the grid to process the new columnDef before calling setFocusedCell.
            const rowIndex = params.previousCellPosition?.rowIndex ?? 0
            setTimeout(() => {
                if (api) {
                    api.setFocusedCell(rowIndex, newField)
                    api.startEditingCell({ rowIndex, colKey: newField })
                }
            }, 50)

            return null  // Prevent default AG Grid Tab navigation
        }

        return params.nextCellPosition
    }, [expandable, gridApi, addColumn])

    // onCellKeyDown: intercept Enter on the last row when expandable
    const onCellKeyDown = useCallback((params) => {
        if (!expandable) return
        if (params.event?.key !== "Enter") return

        const api = params.api
        if (!api) return

        const rowCount = api.getDisplayedRowCount()
        const currentRowIndex = params.rowIndex

        if (currentRowIndex === rowCount - 1) {
            // Pressed Enter on the last row — add a new row
            params.event.preventDefault()
            params.event.stopPropagation()

            const newRowIndex = addRow(api)
            const colId = params.column?.getColId()

            setTimeout(() => {
                if (api) {
                    api.setFocusedCell(newRowIndex, colId)
                    api.startEditingCell({ rowIndex: newRowIndex, colKey: colId })
                }
            }, 50)
        }
    }, [expandable, addRow])

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

        const rowCount = params.api.getDisplayedRowCount();
        const isMulti = ctrlPressed.current || (params.event && (params.event.ctrlKey || params.event.metaKey));

        if (isMulti) {
            // Ctrl/Cmd+click: toggle this column in the current selection
            const existingRanges = params.api.getCellRanges() || [];
            // Check if this column is already fully selected
            const alreadySelected = existingRanges.some(r => {
                if (r.columns.length !== 1) return false;
                const rCol = r.columns[0].getColId();
                if (rCol !== colId) return false;
                const s = r.startRow ? r.startRow.rowIndex : 0;
                const e = r.endRow ? r.endRow.rowIndex : 0;
                return Math.abs(e - s) + 1 === rowCount;
            });

            if (alreadySelected) {
                // Deselect: rebuild ranges without this column
                const keep = existingRanges.filter(r => {
                    if (r.columns.length === 1 && r.columns[0].getColId() === colId) {
                        const s = r.startRow ? r.startRow.rowIndex : 0;
                        const e = r.endRow ? r.endRow.rowIndex : 0;
                        return Math.abs(e - s) + 1 !== rowCount;
                    }
                    return true;
                });
                params.api.clearRangeSelection();
                keep.forEach(r => {
                    let startRow = r.startRow ? r.startRow.rowIndex : 0;
                    let endRow = r.endRow ? r.endRow.rowIndex : 0;
                    params.api.addCellRange({
                        columns: r.columns.map(c => c.getColId()),
                        rowStartIndex: Math.min(startRow, endRow),
                        rowEndIndex: Math.max(startRow, endRow),
                    });
                });
            } else {
                // Add this column to the selection
                params.api.addCellRange({
                    columns: [colId],
                    rowStartIndex: 0,
                    rowEndIndex: rowCount - 1,
                });
            }
        } else {
            // Normal click: clear existing selection and select just this column
            params.api.clearRangeSelection();
            params.api.addCellRange({
                columns: [colId],
                rowStartIndex: 0,
                rowEndIndex: rowCount - 1
            });
        }
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

    // Container style
    const containerStyle = useMemo(() => ({
        width: "100%",
        height: `${containerHeight}px`,
        paddingBottom: "20px",
        boxSizing: "border-box"
    }), [containerHeight]);

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
                rowData={localRows}
                columnDefs={effectiveColumnDefs}
                defaultColDef={defaultColDef}
                onGridReady={onGridReady}
                enableRangeSelection={true}
                onRangeSelectionChanged={onRangeSelectionChanged}
                onColumnHeaderClicked={onColumnHeaderClicked}
                onCellValueChanged={onCellValueChanged}
                onCellKeyDown={onCellKeyDown}
                tabToNextCell={tabToNextCell}
                suppressRowClickSelection={true}
                rowSelection="multiple"
                domLayout="normal"
            />
        </div>
    )
}

export default withStreamlitConnection(AgGridRange)
