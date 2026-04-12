"""Dependency and toolbox helpers for custom methods."""

from __future__ import annotations


def resolve_export_method_ids(
    registry: list[dict],
    selected_method_ids: list[str] | None = None,
    include_dependencies: bool = True,
) -> list[str]:
    """Resolve the custom method IDs that should be exported."""
    entry_by_id = {entry["id"]: entry for entry in registry}

    if selected_method_ids is None:
        export_ids = set(entry_by_id.keys())
    else:
        export_ids = {method_id for method_id in selected_method_ids if method_id in entry_by_id}

    if include_dependencies:
        stack = list(export_ids)
        while stack:
            current_id = stack.pop()
            entry = entry_by_id.get(current_id)
            if entry is None:
                continue
            for dep_id in entry.get("dependencies", []):
                if dep_id in entry_by_id and dep_id not in export_ids:
                    export_ids.add(dep_id)
                    stack.append(dep_id)

    return sorted(export_ids)


def get_available_tools_info(
    registry: list[dict],
    builtin_tool_info: list[dict],
    exclude_id: str | None = None,
) -> list[dict]:
    """Return built-in plus custom toolbox options."""
    tools: list[dict] = []
    for tool in builtin_tool_info:
        if exclude_id and tool["id"] == exclude_id:
            continue
        tools.append(tool)

    for entry in registry:
        if exclude_id and entry["id"] == exclude_id:
            continue
        tools.append({
            "id": entry["id"],
            "display_name": entry["display_name"],
            "description": entry.get("description", ""),
            "input_type": entry.get("input_type", "one_column"),
            "source": "custom",
        })
    return tools


def detect_dependency_cycles(
    registry: list[dict],
    method_id: str,
    proposed_deps: list[str],
) -> str | None:
    """Check whether proposed dependencies would create a cycle."""
    dep_map: dict[str, list[str]] = {
        entry["id"]: list(entry.get("dependencies", []))
        for entry in registry
    }
    dep_map[method_id] = list(proposed_deps)

    visited: set[str] = set()
    in_stack: set[str] = set()

    def _dfs(node: str) -> bool:
        if node in in_stack:
            return True
        if node in visited:
            return False
        visited.add(node)
        in_stack.add(node)
        for dep in dep_map.get(node, []):
            if _dfs(dep):
                return True
        in_stack.discard(node)
        return False

    if _dfs(method_id):
        return (
            "Circular dependency detected — these dependencies would "
            "create a cycle. Please remove at least one dependency "
            "to break the loop."
        )
    return None
