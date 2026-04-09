"""Filesystem and registry helpers for custom methods."""

from __future__ import annotations

import importlib.util
import json
import os
import re


def ensure_dir(custom_dir: str, custom_json_path: str) -> None:
    """Create the custom methods directory and JSON file if missing."""
    os.makedirs(custom_dir, exist_ok=True)
    if not os.path.isfile(custom_json_path):
        with open(custom_json_path, "w", encoding="utf-8") as handle:
            json.dump([], handle)


def load_registry(custom_dir: str, custom_json_path: str) -> list[dict]:
    """Load the registry JSON, returning an empty list on corruption."""
    ensure_dir(custom_dir, custom_json_path)
    try:
        with open(custom_json_path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except (json.JSONDecodeError, FileNotFoundError):
        return []


def write_registry(custom_json_path: str, registry: list[dict]) -> None:
    """Persist the current registry to disk."""
    with open(custom_json_path, "w", encoding="utf-8") as handle:
        json.dump(registry, handle, indent=2)


def load_method_classes(custom_dir: str, registry: list[dict]) -> dict:
    """Load all valid custom method classes from their generated files."""
    classes = {}
    for entry in registry:
        method_id = entry["id"]
        filename = entry["filename"]
        class_name = entry["class_name"]

        if not re.match(r"^[A-Za-z0-9_]+\.py$", filename):
            continue

        filepath = os.path.join(custom_dir, filename)
        if not os.path.isfile(filepath):
            continue

        abs_filepath = os.path.realpath(filepath)
        abs_dir = os.path.realpath(custom_dir)
        if not abs_filepath.startswith(abs_dir + os.sep):
            continue

        try:
            module_name = f"custom_methods.{method_id}"
            spec = importlib.util.spec_from_file_location(module_name, abs_filepath)
            if spec is None or spec.loader is None:
                continue
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            cls = getattr(module, class_name, None)
            if cls is not None:
                classes[method_id] = cls
        except Exception:
            continue

    return classes


def get_custom_display_names(registry: list[dict]) -> dict[str, str]:
    """Return a registry-derived mapping of method IDs to display names."""
    return {entry["id"]: entry["display_name"] for entry in registry}


def get_custom_input_types(registry: list[dict]) -> dict[str, str]:
    """Return a registry-derived mapping of method IDs to input types."""
    return {entry["id"]: entry["input_type"] for entry in registry}


def sanitize_id(name: str) -> str:
    """Convert a human-readable method name to a safe custom-method ID."""
    slug = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    if not slug:
        slug = "unnamed"
    return f"custom_{slug}"


def to_class_name(method_id: str) -> str:
    """Convert a method_id like 'custom_my_method' to 'CustomMyMethod'."""
    return "".join(part.capitalize() for part in method_id.split("_"))


def get_user_code(custom_dir: str, registry: list[dict], method_id: str) -> str | None:
    """Extract the user-authored code region from a generated method file."""
    entry = next((item for item in registry if item["id"] == method_id), None)
    if entry is None:
        return None

    filename = entry["filename"]
    if not re.match(r"^[A-Za-z0-9_]+\.py$", filename):
        return None

    filepath = os.path.join(custom_dir, filename)
    if not os.path.isfile(filepath):
        return None

    try:
        with open(filepath, "r", encoding="utf-8") as handle:
            lines = handle.readlines()
    except OSError:
        return None

    start_idx = None
    end_idx = None
    for index, line in enumerate(lines):
        if "toolbox = self.toolbox" in line:
            start_idx = index + 1
        if start_idx is not None and "except Exception" in line:
            end_idx = index
            break

    if start_idx is None or end_idx is None or start_idx >= end_idx:
        return None

    raw = []
    for line in lines[start_idx:end_idx]:
        stripped = line.rstrip("\n")
        if stripped == "":
            raw.append("")
        elif stripped.startswith("            "):
            raw.append(stripped[12:])
        else:
            raw.append(stripped.lstrip())
    return "\n".join(raw)
