"""
custom_methods_loader.py
------------------------
Compatibility facade for custom method persistence and import/export helpers.

The implementation now lives in smaller support modules under
`custom_method_support/`, but this top-level module keeps the original public
API and mutable path globals intact so existing imports and tests continue to
work without changes.
"""

from __future__ import annotations

import os

from custom_method_support.constants import (
    BUILTIN_TOOL_INFO as _BUILTIN_TOOL_INFO,
    BUNDLE_SCHEMA_VERSION as _BUNDLE_SCHEMA_VERSION,
)
from custom_method_support.dependencies import (
    detect_dependency_cycles as _detect_dependency_cycles,
    get_available_tools_info as _get_available_tools_info,
    resolve_export_method_ids as _resolve_export_method_ids_impl,
)
from custom_method_support.operations import (
    delete_custom_method as _delete_custom_method_impl,
    export_custom_methods_bundle as _export_custom_methods_bundle_impl,
    import_custom_methods_bundle as _import_custom_methods_bundle_impl,
    save_custom_method as _save_custom_method_impl,
    update_custom_method as _update_custom_method_impl,
)
from custom_method_support.store import (
    ensure_dir as _ensure_dir_impl,
    get_custom_display_names as _get_custom_display_names_impl,
    get_custom_input_types as _get_custom_input_types_impl,
    get_user_code as _get_user_code_impl,
    load_method_classes as _load_method_classes_impl,
    load_registry as _load_registry_impl,
    sanitize_id as _sanitize_id,
    to_class_name as _to_class_name,
    write_registry as _write_registry_impl,
)
from custom_method_support.validation import validate_user_code


_CUSTOM_METHODS_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "results_cache",
    "custom_methods",
)
_CUSTOM_METHODS_JSON = os.path.join(_CUSTOM_METHODS_DIR, "custom_methods.json")


def _saved_runs_path() -> str:
    return os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "results_cache",
        "saved_runs.json",
    )


def _ensure_dir() -> None:
    _ensure_dir_impl(_CUSTOM_METHODS_DIR, _CUSTOM_METHODS_JSON)


def load_custom_methods_registry() -> list[dict]:
    return _load_registry_impl(_CUSTOM_METHODS_DIR, _CUSTOM_METHODS_JSON)


def load_custom_method_classes() -> dict:
    return _load_method_classes_impl(_CUSTOM_METHODS_DIR, load_custom_methods_registry())


def get_builtin_tool_info() -> list[dict]:
    return [{"id": method_id, **info} for method_id, info in _BUILTIN_TOOL_INFO.items()]


def get_builtin_tool_ids() -> set[str]:
    return set(_BUILTIN_TOOL_INFO.keys())


def _resolve_export_method_ids(
    selected_method_ids: list[str] | None = None,
    include_dependencies: bool = True,
) -> list[str]:
    return _resolve_export_method_ids_impl(
        load_custom_methods_registry(),
        selected_method_ids=selected_method_ids,
        include_dependencies=include_dependencies,
    )


def get_custom_display_names() -> dict[str, str]:
    return _get_custom_display_names_impl(load_custom_methods_registry())


def get_custom_input_types() -> dict[str, str]:
    return _get_custom_input_types_impl(load_custom_methods_registry())


def save_custom_method(
    name: str,
    description: str,
    input_type: str,
    output_type: str,
    user_code: str,
    dependencies: list[str] | None = None,
    method_id_override: str | None = None,
) -> tuple[bool, str]:
    _ensure_dir()
    return _save_custom_method_impl(
        custom_dir=_CUSTOM_METHODS_DIR,
        custom_json_path=_CUSTOM_METHODS_JSON,
        registry=load_custom_methods_registry(),
        load_registry=load_custom_methods_registry,
        write_registry=_write_registry_impl,
        sanitize_id=_sanitize_id,
        to_class_name=_to_class_name,
        validate_user_code=validate_user_code,
        detect_dependency_cycles=_detect_dependency_cycles,
        name=name,
        description=description,
        input_type=input_type,
        output_type=output_type,
        user_code=user_code,
        dependencies=dependencies,
        method_id_override=method_id_override,
    )


def export_custom_methods_bundle(
    selected_method_ids: list[str] | None = None,
    include_dependencies: bool = True,
) -> str:
    registry = load_custom_methods_registry()
    return _export_custom_methods_bundle_impl(
        registry=registry,
        get_user_code=lambda method_id: _get_user_code_impl(_CUSTOM_METHODS_DIR, registry, method_id),
        resolve_export_method_ids=_resolve_export_method_ids_impl,
        selected_method_ids=selected_method_ids,
        include_dependencies=include_dependencies,
    )


def import_custom_methods_bundle(bundle: str | bytes | dict) -> dict:
    return _import_custom_methods_bundle_impl(
        bundle=bundle,
        load_registry=load_custom_methods_registry,
        save_custom_method=lambda **kwargs: save_custom_method(**kwargs),
        validate_user_code=validate_user_code,
        detect_dependency_cycles=_detect_dependency_cycles,
        builtin_ids=get_builtin_tool_ids(),
    )


def get_user_code(method_id: str) -> str | None:
    return _get_user_code_impl(_CUSTOM_METHODS_DIR, load_custom_methods_registry(), method_id)


def update_custom_method(
    method_id: str,
    name: str,
    description: str,
    input_type: str,
    output_type: str,
    user_code: str,
    dependencies: list[str] | None = None,
) -> tuple[bool, str]:
    _ensure_dir()
    return _update_custom_method_impl(
        custom_dir=_CUSTOM_METHODS_DIR,
        custom_json_path=_CUSTOM_METHODS_JSON,
        registry=load_custom_methods_registry(),
        write_registry=_write_registry_impl,
        validate_user_code=validate_user_code,
        detect_dependency_cycles=_detect_dependency_cycles,
        method_id=method_id,
        name=name,
        description=description,
        input_type=input_type,
        output_type=output_type,
        user_code=user_code,
        dependencies=dependencies,
    )


def delete_custom_method(method_id: str) -> tuple[bool, str]:
    _ensure_dir()
    return _delete_custom_method_impl(
        custom_dir=_CUSTOM_METHODS_DIR,
        custom_json_path=_CUSTOM_METHODS_JSON,
        registry=load_custom_methods_registry(),
        write_registry=_write_registry_impl,
        method_id=method_id,
        saved_runs_path=_saved_runs_path(),
    )


def get_available_tools_info(exclude_id: str | None = None) -> list[dict]:
    return _get_available_tools_info(
        load_custom_methods_registry(),
        get_builtin_tool_info(),
        exclude_id=exclude_id,
    )


def detect_dependency_cycles(
    method_id: str,
    proposed_deps: list[str],
) -> str | None:
    return _detect_dependency_cycles(
        load_custom_methods_registry(),
        method_id,
        proposed_deps,
    )
