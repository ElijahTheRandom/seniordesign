import os
import streamlit.components.v1 as components

_RELEASE = True

if not _RELEASE:
    _component_func = components.declare_component(
        "aggrid_range",
        url="http://localhost:3000",
    )
else:
    parent_dir = os.path.dirname(os.path.abspath(__file__))
    build_dir = os.path.join(parent_dir, "dragselect/build")
    _component_func = components.declare_component("aggrid_range", path=build_dir)


def aggrid_range(data, columns, key=None, server_url=None, data_key=None, total_rows=None):
    """Create a new instance of "aggrid_range".

    Parameters
    ----------
    data : list of dict
        Row data for client-side mode.  Pass [] when using server_url.
    columns : list of dict
        Column definitions (field names).
    key : str or None
        Unique component key.
    server_url : str or None
        Base URL of the Python data server (e.g. "http://127.0.0.1:54321").
        When provided the component uses AG Grid's Infinite Row Model and
        fetches rows from the server instead of reading rowData.
    data_key : str or None
        Key that identifies the DataFrame in the data server.
    total_rows : int or None
        Total row count, used to make the scroll bar accurate in server mode.

    Returns
    -------
    dict
        {"selections": [...], "editedData": [...] | null, "renamedHeaders": {...} | null}
    """
    component_value = _component_func(
        rowData=data,
        columnDefs=columns,
        serverUrl=server_url,
        dataKey=data_key,
        totalRows=total_rows,
        key=key,
        default={"selections": [], "editedData": None},
    )
    return component_value
