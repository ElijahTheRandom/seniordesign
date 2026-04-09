"""Lifecycle and bundle operations for custom methods."""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime

from .constants import BUNDLE_SCHEMA_VERSION


def render_method_file_content(
    *,
    method_id: str,
    class_name: str,
    name: str,
    description: str,
    input_type: str,
    user_code: str,
) -> str:
    """Render the generated Python file for a custom method."""
    if input_type == "two_column":
        applicable_check = (
            '        if self.data is None or len(self.data) < 2:\n'
            '            return "Requires at least 2 columns of data"\n'
            '        return None'
        )
    else:
        applicable_check = (
            '        if self.data is None or len(self.data) == 0:\n'
            '            return "No data provided"\n'
            '        return None'
        )

    indented_code = "\n".join(
        "            " + line if line.strip() else ""
        for line in user_code.splitlines()
    )

    return f'''import numpy as np


class {class_name}:
    """Custom method: {name}
    
    {description}
    """

    def __init__(self, data, metadata, params=None, toolbox=None):
        self.stat_id = "{method_id}"
        self.data = data
        self.metadata = metadata
        self.params = params or {{}}
        self.toolbox = toolbox or {{}}

    def _applicable(self):
{applicable_check}

    def _generate_return_structure(self, value):
        return {{
            "id": self.stat_id,
            "ok": True,
            "value": value,
            "error": None,
            "loss_of_precision": False,
            "params_used": self.params
        }}

    def _generate_return_structure_error(self, error_message):
        return {{
            "id": self.stat_id,
            "ok": False,
            "value": None,
            "error": error_message,
            "loss_of_precision": False,
            "params_used": self.params
        }}

    def compute(self):
        reason = self._applicable()
        if reason is not None:
            return self._generate_return_structure_error(reason)
        try:
            data = self.data
            params = self.params
            toolbox = self.toolbox
{indented_code}
        except Exception as e:
            return self._generate_return_structure_error(str(e))
        return self._generate_return_structure(result)

    def create_graphic(self, results):
        pass
'''


def save_custom_method(
    *,
    custom_dir: str,
    custom_json_path: str,
    registry: list[dict],
    load_registry,
    write_registry,
    sanitize_id,
    to_class_name,
    validate_user_code,
    detect_dependency_cycles,
    name: str,
    description: str,
    input_type: str,
    output_type: str,
    user_code: str,
    dependencies: list[str] | None = None,
    method_id_override: str | None = None,
) -> tuple[bool, str]:
    """Validate, generate, and persist a new custom statistical method."""
    if not name or not name.strip():
        return False, "Method name cannot be empty."

    method_id = method_id_override or sanitize_id(name.strip())
    if not re.match(r"^custom_[a-z0-9_]+$", method_id):
        return False, "Custom method ID must start with 'custom_' and use lowercase letters, numbers, or underscores."

    class_name = to_class_name(method_id)
    filename = f"{method_id}.py"

    existing_ids = {entry["id"] for entry in registry}
    if method_id in existing_ids:
        return False, f"A custom method with ID '{method_id}' already exists."

    existing_names = {entry["display_name"].strip().lower() for entry in registry}
    if name.strip().lower() in existing_names:
        return False, f"A custom method named '{name.strip()}' already exists."

    issues = validate_user_code(user_code, input_type)
    errors = [issue for issue in issues if not issue.startswith("Hint:")]
    if errors:
        return False, "\n".join(errors)

    if dependencies:
        cycle_err = detect_dependency_cycles(load_registry(), method_id, dependencies)
        if cycle_err:
            return False, cycle_err

    file_content = render_method_file_content(
        method_id=method_id,
        class_name=class_name,
        name=name,
        description=description,
        input_type=input_type,
        user_code=user_code,
    )

    filepath = os.path.join(custom_dir, filename)
    with open(filepath, "w", encoding="utf-8") as handle:
        handle.write(file_content)

    updated_registry = list(registry)
    updated_registry.append({
        "id": method_id,
        "display_name": name.strip(),
        "description": description.strip(),
        "input_type": input_type,
        "output_type": output_type,
        "filename": filename,
        "class_name": class_name,
        "dependencies": dependencies or [],
        "created_at": datetime.now().isoformat(),
    })
    write_registry(custom_json_path, updated_registry)
    return True, f"Method '{name.strip()}' saved successfully!"


def update_custom_method(
    *,
    custom_dir: str,
    custom_json_path: str,
    registry: list[dict],
    write_registry,
    validate_user_code,
    detect_dependency_cycles,
    method_id: str,
    name: str,
    description: str,
    input_type: str,
    output_type: str,
    user_code: str,
    dependencies: list[str] | None = None,
) -> tuple[bool, str]:
    """Update an existing custom method's metadata and generated file."""
    idx = next((i for i, entry in enumerate(registry) if entry["id"] == method_id), None)
    if idx is None:
        return False, f"Method '{method_id}' not found."

    if not name or not name.strip():
        return False, "Method name cannot be empty."

    for i, entry in enumerate(registry):
        if i != idx and entry["display_name"].strip().lower() == name.strip().lower():
            return False, f"Another custom method named '{name.strip()}' already exists."

    issues = validate_user_code(user_code, input_type)
    errors = [issue for issue in issues if not issue.startswith("Hint:")]
    if errors:
        return False, "\n".join(errors)

    if dependencies:
        cycle_err = detect_dependency_cycles(registry, method_id, dependencies)
        if cycle_err:
            return False, cycle_err

    old_entry = registry[idx]
    file_content = render_method_file_content(
        method_id=method_id,
        class_name=old_entry["class_name"],
        name=name,
        description=description,
        input_type=input_type,
        user_code=user_code,
    )

    filepath = os.path.join(custom_dir, old_entry["filename"])
    with open(filepath, "w", encoding="utf-8") as handle:
        handle.write(file_content)

    sys.modules.pop(f"custom_methods.{method_id}", None)

    updated_registry = list(registry)
    updated_registry[idx] = {
        "id": method_id,
        "display_name": name.strip(),
        "description": description.strip(),
        "input_type": input_type,
        "output_type": output_type,
        "filename": old_entry["filename"],
        "class_name": old_entry["class_name"],
        "dependencies": dependencies or [],
        "created_at": old_entry["created_at"],
    }
    write_registry(custom_json_path, updated_registry)
    return True, f"Method '{name.strip()}' updated successfully!"


def delete_custom_method(
    *,
    custom_dir: str,
    custom_json_path: str,
    registry: list[dict],
    write_registry,
    method_id: str,
    saved_runs_path: str,
) -> tuple[bool, str]:
    """Delete a custom method and clean up saved runs references."""
    entry = next((item for item in registry if item["id"] == method_id), None)
    if entry is None:
        return False, f"Method '{method_id}' not found."

    display_name = entry["display_name"]
    dependents = [
        item["display_name"] for item in registry
        if item["id"] != method_id and method_id in item.get("dependencies", [])
    ]
    if dependents:
        names = ", ".join(f"'{name}'" for name in dependents)
        return False, (
            f"Cannot delete '{display_name}' because the following methods "
            f"depend on it: {names}. Remove those dependencies first."
        )

    filename = entry["filename"]
    if re.match(r"^[A-Za-z0-9_]+\.py$", filename):
        filepath = os.path.join(custom_dir, filename)
        abs_filepath = os.path.realpath(filepath)
        abs_dir = os.path.realpath(custom_dir)
        if abs_filepath.startswith(abs_dir + os.sep) and os.path.isfile(abs_filepath):
            os.remove(abs_filepath)

    updated_registry = [item for item in registry if item["id"] != method_id]
    write_registry(custom_json_path, updated_registry)

    if os.path.isfile(saved_runs_path):
        try:
            with open(saved_runs_path, "r", encoding="utf-8") as handle:
                runs = json.load(handle)
            changed = False
            for run in runs:
                old_len = len(run.get("methods", []))
                run["methods"] = [
                    method for method in run.get("methods", [])
                    if method.get("id") != method_id
                ]
                if len(run["methods"]) != old_len:
                    changed = True
            if changed:
                with open(saved_runs_path, "w", encoding="utf-8") as handle:
                    json.dump(runs, handle, indent=2)
        except (json.JSONDecodeError, OSError):
            pass

    sys.modules.pop(f"custom_methods.{method_id}", None)
    return True, f"Method '{display_name}' deleted."


def export_custom_methods_bundle(
    *,
    registry: list[dict],
    get_user_code,
    resolve_export_method_ids,
    selected_method_ids: list[str] | None = None,
    include_dependencies: bool = True,
) -> str:
    """Serialize selected custom methods into a portable JSON bundle."""
    export_ids = set(
        resolve_export_method_ids(
            registry,
            selected_method_ids=selected_method_ids,
            include_dependencies=include_dependencies,
        )
    )
    methods: list[dict] = []

    for entry in sorted(registry, key=lambda item: item["id"]):
        if entry["id"] not in export_ids:
            continue
        user_code = get_user_code(entry["id"])
        if user_code is None:
            continue
        methods.append({
            "id": entry["id"],
            "display_name": entry["display_name"],
            "description": entry.get("description", ""),
            "input_type": entry["input_type"],
            "output_type": entry["output_type"],
            "dependencies": list(entry.get("dependencies", [])),
            "user_code": user_code,
        })

    bundle = {
        "schema_version": BUNDLE_SCHEMA_VERSION,
        "exported_at": datetime.now().isoformat(),
        "selected_method_ids": sorted(selected_method_ids) if selected_method_ids is not None else None,
        "included_dependency_ids": sorted(export_ids - set(selected_method_ids or [])),
        "methods": methods,
    }
    return json.dumps(bundle, indent=2)


def import_custom_methods_bundle(
    *,
    bundle: str | bytes | dict,
    load_registry,
    save_custom_method,
    validate_user_code,
    detect_dependency_cycles,
    builtin_ids: set[str],
) -> dict:
    """Import custom methods from an exported bundle."""
    if isinstance(bundle, bytes):
        try:
            bundle = bundle.decode("utf-8")
        except UnicodeDecodeError:
            return {
                "ok": False,
                "imported": [],
                "skipped_duplicates": [],
                "skipped_invalid": [{"id": None, "display_name": None, "reason": "Import file must be valid UTF-8 JSON."}],
            }

    if isinstance(bundle, str):
        try:
            bundle = json.loads(bundle)
        except json.JSONDecodeError as exc:
            return {
                "ok": False,
                "imported": [],
                "skipped_duplicates": [],
                "skipped_invalid": [{"id": None, "display_name": None, "reason": f"Invalid JSON: {exc.msg}"}],
            }

    if not isinstance(bundle, dict):
        return {
            "ok": False,
            "imported": [],
            "skipped_duplicates": [],
            "skipped_invalid": [{"id": None, "display_name": None, "reason": "Import bundle must be a JSON object."}],
        }

    methods = bundle.get("methods")
    if not isinstance(methods, list):
        return {
            "ok": False,
            "imported": [],
            "skipped_duplicates": [],
            "skipped_invalid": [{"id": None, "display_name": None, "reason": "Import bundle is missing a 'methods' list."}],
        }

    existing_registry = load_registry()
    existing_ids = {entry["id"] for entry in existing_registry}
    existing_names = {entry["display_name"].strip().lower() for entry in existing_registry}
    bundle_ids = {
        entry["id"]
        for entry in methods
        if isinstance(entry, dict) and isinstance(entry.get("id"), str)
    }

    imported: list[dict] = []
    skipped_duplicates: list[dict] = []
    skipped_invalid: list[dict] = []
    pending: list[dict] = []
    seen_bundle_ids: set[str] = set()

    required_fields = {
        "id", "display_name", "description",
        "input_type", "output_type", "dependencies", "user_code",
    }
    valid_input_types = {"one_column", "two_column"}
    valid_output_types = {"scalar", "list", "dictionary"}

    for raw_entry in methods:
        if not isinstance(raw_entry, dict):
            skipped_invalid.append({"id": None, "display_name": None, "reason": "Each imported method entry must be an object."})
            continue

        missing_fields = sorted(required_fields - set(raw_entry.keys()))
        method_id = raw_entry.get("id")
        display_name = raw_entry.get("display_name")
        if missing_fields:
            skipped_invalid.append({
                "id": method_id,
                "display_name": display_name,
                "reason": f"Missing required fields: {', '.join(missing_fields)}.",
            })
            continue

        if not isinstance(method_id, str) or not re.match(r"^custom_[a-z0-9_]+$", method_id):
            skipped_invalid.append({
                "id": method_id,
                "display_name": display_name,
                "reason": "Method ID must start with 'custom_' and use lowercase letters, numbers, or underscores.",
            })
            continue

        if method_id in seen_bundle_ids:
            skipped_invalid.append({
                "id": method_id,
                "display_name": display_name,
                "reason": "Duplicate method ID found inside the import bundle.",
            })
            continue
        seen_bundle_ids.add(method_id)

        if not isinstance(display_name, str) or not display_name.strip():
            skipped_invalid.append({"id": method_id, "display_name": display_name, "reason": "Display name cannot be empty."})
            continue

        if method_id in existing_ids:
            skipped_duplicates.append({
                "id": method_id,
                "display_name": display_name,
                "reason": "A local custom method with this ID already exists.",
            })
            continue

        if display_name.strip().lower() in existing_names:
            skipped_duplicates.append({
                "id": method_id,
                "display_name": display_name,
                "reason": "A local custom method with this name already exists.",
            })
            continue

        input_type = raw_entry.get("input_type")
        output_type = raw_entry.get("output_type")
        dependencies = raw_entry.get("dependencies")
        user_code = raw_entry.get("user_code")

        if input_type not in valid_input_types:
            skipped_invalid.append({"id": method_id, "display_name": display_name, "reason": "Input type must be 'one_column' or 'two_column'."})
            continue

        if output_type not in valid_output_types:
            skipped_invalid.append({"id": method_id, "display_name": display_name, "reason": "Output type must be 'scalar', 'list', or 'dictionary'."})
            continue

        if not isinstance(dependencies, list) or not all(isinstance(dep, str) for dep in dependencies):
            skipped_invalid.append({"id": method_id, "display_name": display_name, "reason": "Dependencies must be a list of method IDs."})
            continue

        if not isinstance(user_code, str):
            skipped_invalid.append({"id": method_id, "display_name": display_name, "reason": "User code must be a string."})
            continue

        missing_deps = [
            dep for dep in dependencies
            if dep not in existing_ids and dep not in bundle_ids and dep not in builtin_ids
        ]
        if missing_deps:
            skipped_invalid.append({
                "id": method_id,
                "display_name": display_name,
                "reason": f"Missing dependencies: {', '.join(sorted(missing_deps))}.",
            })
            continue

        issues = validate_user_code(user_code, input_type)
        errors = [issue for issue in issues if not issue.startswith("Hint:")]
        if errors:
            skipped_invalid.append({"id": method_id, "display_name": display_name, "reason": " ".join(errors)})
            continue

        cycle_err = detect_dependency_cycles(existing_registry, method_id, dependencies)
        if cycle_err:
            skipped_invalid.append({"id": method_id, "display_name": display_name, "reason": cycle_err})
            continue

        pending.append({
            "id": method_id,
            "display_name": display_name.strip(),
            "description": raw_entry.get("description", "").strip(),
            "input_type": input_type,
            "output_type": output_type,
            "dependencies": dependencies,
            "user_code": user_code,
        })

    dep_map: dict[str, list[str]] = {
        entry["id"]: list(entry.get("dependencies", []))
        for entry in existing_registry
    }
    dep_map.update({entry["id"]: list(entry["dependencies"]) for entry in pending})

    def _has_cycle(start_id: str) -> bool:
        visited: set[str] = set()
        stack: set[str] = set()

        def _dfs(node: str) -> bool:
            if node in stack:
                return True
            if node in visited:
                return False
            visited.add(node)
            stack.add(node)
            for dep in dep_map.get(node, []):
                if dep in dep_map and _dfs(dep):
                    return True
            stack.discard(node)
            return False

        return _dfs(start_id)

    cycle_ids = {entry["id"] for entry in pending if _has_cycle(entry["id"])}
    if cycle_ids:
        still_pending = []
        for entry in pending:
            if entry["id"] in cycle_ids:
                skipped_invalid.append({
                    "id": entry["id"],
                    "display_name": entry["display_name"],
                    "reason": (
                        "Circular dependency detected — these dependencies would "
                        "create a cycle. Please remove at least one dependency "
                        "to break the loop."
                    ),
                })
            else:
                still_pending.append(entry)
        pending = still_pending

    imported_ids: set[str] = set()
    while pending:
        progressed = False
        remaining: list[dict] = []

        for entry in pending:
            unresolved = [
                dep for dep in entry["dependencies"]
                if dep not in existing_ids and dep not in imported_ids and dep not in builtin_ids
            ]
            if unresolved:
                remaining.append(entry)
                continue

            ok, message = save_custom_method(
                name=entry["display_name"],
                description=entry["description"],
                input_type=entry["input_type"],
                output_type=entry["output_type"],
                user_code=entry["user_code"],
                dependencies=entry["dependencies"],
                method_id_override=entry["id"],
            )
            if ok:
                imported_ids.add(entry["id"])
                existing_ids.add(entry["id"])
                existing_names.add(entry["display_name"].lower())
                imported.append({
                    "id": entry["id"],
                    "display_name": entry["display_name"],
                    "reason": message,
                })
                progressed = True
            else:
                skipped_invalid.append({
                    "id": entry["id"],
                    "display_name": entry["display_name"],
                    "reason": message,
                })

        if progressed:
            pending = remaining
            continue

        for entry in remaining:
            unresolved = [
                dep for dep in entry["dependencies"]
                if dep not in existing_ids and dep not in imported_ids and dep not in builtin_ids
            ]
            skipped_invalid.append({
                "id": entry["id"],
                "display_name": entry["display_name"],
                "reason": f"Dependencies could not be resolved during import: {', '.join(sorted(unresolved))}.",
            })
        break

    return {
        "ok": bool(imported),
        "imported": imported,
        "skipped_duplicates": skipped_duplicates,
        "skipped_invalid": skipped_invalid,
    }
