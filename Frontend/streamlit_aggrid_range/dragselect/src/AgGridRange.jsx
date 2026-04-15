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
    const { rowData, columnDefs, serverUrl, dataKey, totalRows: totalRowsProp } = props.args

    // Server mode: use Infinite Row Model + HTTP datasource
    const isServerMode = Boolean(serverUrl && dataKey)
    const serverTotalRows = isServerMode ? (totalRowsProp || 0) : 0

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
    // Persists the last-known formatted ranges so we can restore them after
    // AG Grid clears its range selection on rowData prop updates.
    const lastKnownRanges = useRef([])

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
        return columnDefs.map(col => {
            const renamed = renamedHeaders[col.field]
            return {
                ...col,
                headerName: renamed || col.field,
                headerClass: selectedColIds.has(col.field) ? 'full-column-selected' : ''
            }
        })
    }, [columnDefs, selectedColIds, renamedHeaders])

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

    // Server-mode infinite datasource — recreated only when server params change
    const serverDatasource = useMemo(() => {
        if (!isServerMode) return null
        return {
            getRows: async (params) => {
                try {
                    const end = params.endRow - 1
                    const url = `${serverUrl}/rows?key=${encodeURIComponent(dataKey)}&start=${params.startRow}&end=${end}`
                    const resp = await fetch(url)
                    if (!resp.ok) { params.failCallback(); return }
                    const rows = await resp.json()
                    // Passing serverTotalRows tells AG Grid the full row count
                    // so the scroll bar is accurate from the first block load.
                    params.successCallback(rows, serverTotalRows)
                } catch (e) {
                    params.failCallback()
                }
            }
        }
    }, [isServerMode, serverUrl, dataKey, serverTotalRows])

    const onGridReady = (params) => {
        setGridApi(params.api)
        Streamlit.setFrameHeight()
    }

    // Handle selection changes
    const onRangeSelectionChanged = (event) => {
        if (!event.api) return

        const cellRanges = event.api.getCellRanges()
        // In server mode use the known total; in client mode use displayed count
        const rowCount = isServerMode ? serverTotalRows : event.api.getDisplayedRowCount()

        // Collect all columns that have a full-height single-column range
        const newSelectedColIds = new Set()
        for (const r of cellRanges) {
            if (r.startRow && r.endRow && r.columns.length === 1) {
                const s = r.startRow.rowIndex
                const e = r.endRow.rowIndex
                if (Math.abs(e - s) + 1 === rowCount) {
                    newSelectedColIds.add(r.columns[0].getColId())
                }
            }
        }

        // Update visual state if changed
        const prev = selectedColIds
        const changed = newSelectedColIds.size !== prev.size ||
            [...newSelectedColIds].some(id => !prev.has(id))
        if (changed) {
            setSelectedColIds(newSelectedColIds)
            event.api.refreshHeader()
        }

        // Map ranges to a serializable format
        const formattedRanges = cellRanges.map((range) => {
            let startRow = range.startRow ? range.startRow.rowIndex : 0
            let endRow = range.endRow ? range.endRow.rowIndex : 0
            if (startRow > endRow) {
                const temp = startRow; startRow = endRow; endRow = temp
            }
            const columns = range.columns.map((col) => col.colId)
            return { startRow, endRow, columns }
        })

        // In client mode, if edits exist, include current row data so a
        // selection event doesn't overwrite prior cell edits in Streamlit state.
        let currentEditedData = null
        if (!isServerMode && hasEdits && event.api) {
            const updatedRows = []
            event.api.forEachNode(node => updatedRows.push({ ...node.data }))
            currentEditedData = updatedRows
        }

        // Persist so onRowDataUpdated can restore after a rowData prop change
        lastKnownRanges.current = formattedRanges

        Streamlit.setComponentValue({
            selections: formattedRanges,
            editedData: currentEditedData,
            renamedHeaders: Object.keys(renamedHeaders).length > 0 ? renamedHeaders : null
        })
    }

    // Handle cell value editing (client mode only)
    const onCellValueChanged = (event) => {
        if (isServerMode || !event.api) return

        const updatedRows = []
        event.api.forEachNode(node => updatedRows.push({ ...node.data }))

        const cellRanges = event.api.getCellRanges() || []
        const formattedRanges = cellRanges.map((range) => {
            let startRow = range.startRow ? range.startRow.rowIndex : 0
            let endRow = range.endRow ? range.endRow.rowIndex : 0
            if (startRow > endRow) { const temp = startRow; startRow = endRow; endRow = temp }
            const columns = range.columns.map((col) => col.colId)
            return { startRow, endRow, columns }
        })

        setHasEdits(true)
        Streamlit.setComponentValue({
            selections: formattedRanges,
            editedData: updatedRows,
            renamedHeaders: Object.keys(renamedHeaders).length > 0 ? renamedHeaders : null
        })
    }

    // Handle ESC key to clear selection
    useEffect(() => {
        const handleKeyDown = (event) => {
            if (event.key === "Escape" && gridApi) {
                gridApi.clearRangeSelection()
            }
        }
        document.addEventListener("keydown", handleKeyDown)
        return () => document.removeEventListener("keydown", handleKeyDown)
    }, [gridApi])

    // Disable sort/filter/menu; disable editing in server mode
    const defaultColDef = useMemo(() => ({
        sortable: false,
        filter: false,
        resizable: true,
        editable: !isServerMode,
        suppressHeaderMenuButton: true,
        suppressMenu: true,
        valueParser: isServerMode ? undefined : (params) => {
            const val = params.newValue
            if (val === "" || val === null || val === undefined) return val
            const num = Number(val)
            return isNaN(num) ? val : num
        },
    }), [isServerMode])

    // Helper: send current state to Streamlit
    const sendValue = useCallback((api, overrideEdited) => {
        const cellRanges = api.getCellRanges() || []
        const formattedRanges = cellRanges.map((range) => {
            let startRow = range.startRow ? range.startRow.rowIndex : 0
            let endRow = range.endRow ? range.endRow.rowIndex : 0
            if (startRow > endRow) { const t = startRow; startRow = endRow; endRow = t }
            const columns = range.columns.map((col) => col.colId)
            return { startRow, endRow, columns }
        })
        Streamlit.setComponentValue({
            selections: formattedRanges,
            editedData: overrideEdited !== undefined ? overrideEdited : null,
            renamedHeaders: Object.keys(renamedHeaders).length > 0 ? renamedHeaders : null
        })
    }, [renamedHeaders])

    // After AG Grid processes a rowData prop update it clears its internal range
    // selection. Restore the last known selection. Not needed in server mode.
    const onRowDataUpdated = useCallback((event) => {
        if (isServerMode || !event.api || lastKnownRanges.current.length === 0) return
        event.api.clearRangeSelection()
        lastKnownRanges.current.forEach(r => {
            event.api.addCellRange({
                columns: r.columns,
                rowStartIndex: r.startRow,
                rowEndIndex: r.endRow,
            })
        })
    }, [isServerMode])

    // Header click: single = select column, double = rename
    const onColumnHeaderClicked = useCallback((params) => {
        if (!params.api) return
        const colId = params.column.getColId()

        // Check for double-click (two clicks within 300ms)
        if (headerClickTimers.current[colId]) {
            clearTimeout(headerClickTimers.current[colId])
            headerClickTimers.current[colId] = null

            const headerEl = document.querySelector(`.ag-header-cell[col-id="${colId}"]`)
            if (headerEl) {
                const rect = headerEl.getBoundingClientRect()
                const gridEl = headerEl.closest('.ag-theme-alpine')
                const gridRect = gridEl ? gridEl.getBoundingClientRect() : { top: 0, left: 0 }
                setEditPos({
                    top: rect.top - gridRect.top,
                    left: rect.left - gridRect.left,
                    width: rect.width,
                    height: rect.height
                })
            }
            setEditingColId(colId)
            setEditValue(renamedHeaders[colId] || colId)
            return
        }

        headerClickTimers.current[colId] = setTimeout(() => {
            headerClickTimers.current[colId] = null
        }, 300)

        // In server mode use the known total rows; in client mode use displayed count
        const rowCount = isServerMode
            ? serverTotalRows
            : params.api.getDisplayedRowCount()

        const isMulti = ctrlPressed.current || (params.event && (params.event.ctrlKey || params.event.metaKey))

        if (isMulti) {
            const existingRanges = params.api.getCellRanges() || []
            const alreadySelected = existingRanges.some(r => {
                if (r.columns.length !== 1) return false
                const rCol = r.columns[0].getColId()
                if (rCol !== colId) return false
                const s = r.startRow ? r.startRow.rowIndex : 0
                const e = r.endRow ? r.endRow.rowIndex : 0
                return Math.abs(e - s) + 1 === rowCount
            })

            if (alreadySelected) {
                const keep = existingRanges.filter(r => {
                    if (r.columns.length === 1 && r.columns[0].getColId() === colId) {
                        const s = r.startRow ? r.startRow.rowIndex : 0
                        const e = r.endRow ? r.endRow.rowIndex : 0
                        return Math.abs(e - s) + 1 !== rowCount
                    }
                    return true
                })
                params.api.clearRangeSelection()
                keep.forEach(r => {
                    let startRow = r.startRow ? r.startRow.rowIndex : 0
                    let endRow = r.endRow ? r.endRow.rowIndex : 0
                    params.api.addCellRange({
                        columns: r.columns.map(c => c.getColId()),
                        rowStartIndex: Math.min(startRow, endRow),
                        rowEndIndex: Math.max(startRow, endRow),
                    })
                })
            } else {
                params.api.addCellRange({
                    columns: [colId],
                    rowStartIndex: 0,
                    rowEndIndex: rowCount - 1,
                })
            }
        } else {
            params.api.clearRangeSelection()
            params.api.addCellRange({
                columns: [colId],
                rowStartIndex: 0,
                rowEndIndex: rowCount - 1
            })
        }
    }, [renamedHeaders, isServerMode, serverTotalRows])

    // Focus the rename input when it appears
    useEffect(() => {
        if (editingColId && editInputRef.current) {
            editInputRef.current.focus()
            editInputRef.current.select()
        }
    }, [editingColId])

    // Commit header rename
    const commitRename = useCallback(() => {
        if (!editingColId) return
        const trimmed = editValue.trim()
        if (trimmed && trimmed !== editingColId) {
            const updated = { ...renamedHeaders, [editingColId]: trimmed }
            setRenamedHeaders(updated)
            if (gridApi) {
                const cellRanges = gridApi.getCellRanges() || []
                const formattedRanges = cellRanges.map((range) => {
                    let startRow = range.startRow ? range.startRow.rowIndex : 0
                    let endRow = range.endRow ? range.endRow.rowIndex : 0
                    if (startRow > endRow) { const t = startRow; startRow = endRow; endRow = t }
                    const columns = range.columns.map((col) => col.colId)
                    return { startRow, endRow, columns }
                })
                Streamlit.setComponentValue({
                    selections: formattedRanges,
                    editedData: null,
                    renamedHeaders: updated
                })
            }
        }
        setEditingColId(null)
        setEditValue("")
    }, [editingColId, editValue, renamedHeaders, gridApi])

    const cancelRename = useCallback(() => {
        setEditingColId(null)
        setEditValue("")
    }, [])

    const containerStyle = useMemo(() => ({
        width: "100%",
        height: `${containerHeight}px`,
        paddingBottom: "20px",
        boxSizing: "border-box"
    }), [containerHeight])

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
                            if (e.key === "Enter") commitRename()
                            if (e.key === "Escape") cancelRename()
                        }}
                        onBlur={commitRename}
                    />
                </div>
            )}

            {isServerMode ? (
                // ── Server / Infinite Row Model ──────────────────────────────
                // Data is fetched in blocks from the Python data server.
                // Cell editing is disabled; all other interactions are preserved.
                <AgGridReact
                    columnDefs={effectiveColumnDefs}
                    defaultColDef={defaultColDef}
                    rowModelType="infinite"
                    datasource={serverDatasource}
                    cacheBlockSize={500}
                    maxBlocksInCache={20}
                    infiniteInitialRowCount={serverTotalRows}
                    onGridReady={onGridReady}
                    enableRangeSelection={true}
                    onRangeSelectionChanged={onRangeSelectionChanged}
                    onColumnHeaderClicked={onColumnHeaderClicked}
                    suppressRowClickSelection={true}
                    rowSelection="multiple"
                    domLayout="normal"
                />
            ) : (
                // ── Client-Side Row Model (small files) ──────────────────────
                <AgGridReact
                    rowData={rowData}
                    columnDefs={effectiveColumnDefs}
                    defaultColDef={defaultColDef}
                    onGridReady={onGridReady}
                    enableRangeSelection={true}
                    onRangeSelectionChanged={onRangeSelectionChanged}
                    onRowDataUpdated={onRowDataUpdated}
                    onColumnHeaderClicked={onColumnHeaderClicked}
                    onCellValueChanged={onCellValueChanged}
                    suppressRowClickSelection={true}
                    rowSelection="multiple"
                    domLayout="normal"
                />
            )}
        </div>
    )
}

export default withStreamlitConnection(AgGridRange)
