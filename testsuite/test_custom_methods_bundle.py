import json
import os
import sys

import pytest


sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import custom_methods_loader as cml  # noqa: E402


VALID_ONE_COL_CODE = """arr = np.array(data, dtype=float)
result = float(np.mean(arr))
"""


@pytest.fixture
def isolated_custom_methods_store(tmp_path, monkeypatch):
    custom_dir = tmp_path / "custom_methods"
    custom_json = custom_dir / "custom_methods.json"

    monkeypatch.setattr(cml, "_CUSTOM_METHODS_DIR", str(custom_dir))
    monkeypatch.setattr(cml, "_CUSTOM_METHODS_JSON", str(custom_json))

    for mod_name in list(sys.modules):
        if mod_name.startswith("custom_methods."):
            sys.modules.pop(mod_name, None)

    cml._ensure_dir()
    yield tmp_path

    for mod_name in list(sys.modules):
        if mod_name.startswith("custom_methods."):
            sys.modules.pop(mod_name, None)


def test_export_returns_valid_bundle(isolated_custom_methods_store):
    ok, _ = cml.save_custom_method(
        name="Geometric Mean",
        description="Average in multiplicative space.",
        input_type="one_column",
        output_type="scalar",
        user_code=VALID_ONE_COL_CODE,
    )
    assert ok is True

    bundle_json = cml.export_custom_methods_bundle()
    bundle = json.loads(bundle_json)

    assert bundle["schema_version"] == 1
    assert "exported_at" in bundle
    assert len(bundle["methods"]) == 1
    assert bundle["methods"][0]["id"] == "custom_geometric_mean"
    assert bundle["methods"][0]["user_code"].strip() == VALID_ONE_COL_CODE.strip()


def test_export_can_limit_to_selected_methods_with_dependencies(isolated_custom_methods_store):
    ok, _ = cml.save_custom_method(
        name="Parent Helper",
        description="Dependency helper.",
        input_type="one_column",
        output_type="scalar",
        user_code=VALID_ONE_COL_CODE,
    )
    assert ok is True
    ok, _ = cml.save_custom_method(
        name="Child Export",
        description="Depends on another custom method.",
        input_type="one_column",
        output_type="scalar",
        user_code="""value = toolbox["custom_parent_helper"](data)
result = float(value)
""",
        dependencies=["custom_parent_helper"],
    )
    assert ok is True

    bundle = json.loads(
        cml.export_custom_methods_bundle(
            selected_method_ids=["custom_child_export"],
            include_dependencies=True,
        )
    )

    exported_ids = [entry["id"] for entry in bundle["methods"]]
    assert exported_ids == ["custom_child_export", "custom_parent_helper"]
    assert bundle["included_dependency_ids"] == ["custom_parent_helper"]


def test_import_restores_methods_into_empty_store(isolated_custom_methods_store):
    bundle = {
        "schema_version": 1,
        "exported_at": "2026-04-09T12:00:00",
        "methods": [
            {
                "id": "custom_restored_method",
                "display_name": "Restored Method",
                "description": "Imported from bundle.",
                "input_type": "one_column",
                "output_type": "scalar",
                "dependencies": [],
                "user_code": VALID_ONE_COL_CODE,
            }
        ],
    }

    summary = cml.import_custom_methods_bundle(bundle)
    registry = cml.load_custom_methods_registry()

    assert summary["ok"] is True
    assert [entry["id"] for entry in summary["imported"]] == ["custom_restored_method"]
    assert [entry["id"] for entry in registry] == ["custom_restored_method"]
    assert cml.get_user_code("custom_restored_method").strip() == VALID_ONE_COL_CODE.strip()


def test_import_skips_duplicates(isolated_custom_methods_store):
    ok, _ = cml.save_custom_method(
        name="Existing Method",
        description="Already local.",
        input_type="one_column",
        output_type="scalar",
        user_code=VALID_ONE_COL_CODE,
    )
    assert ok is True

    bundle = {
        "schema_version": 1,
        "exported_at": "2026-04-09T12:00:00",
        "methods": [
            {
                "id": "custom_existing_method",
                "display_name": "Existing Method",
                "description": "Duplicate entry.",
                "input_type": "one_column",
                "output_type": "scalar",
                "dependencies": [],
                "user_code": VALID_ONE_COL_CODE,
            }
        ],
    }

    summary = cml.import_custom_methods_bundle(bundle)

    assert summary["imported"] == []
    assert len(summary["skipped_duplicates"]) == 1
    assert summary["skipped_duplicates"][0]["id"] == "custom_existing_method"


def test_import_rejects_invalid_code(isolated_custom_methods_store):
    bundle = {
        "schema_version": 1,
        "exported_at": "2026-04-09T12:00:00",
        "methods": [
            {
                "id": "custom_bad_code",
                "display_name": "Bad Code",
                "description": "Missing result assignment.",
                "input_type": "one_column",
                "output_type": "scalar",
                "dependencies": [],
                "user_code": "x = 5",
            }
        ],
    }

    summary = cml.import_custom_methods_bundle(bundle)

    assert summary["imported"] == []
    assert len(summary["skipped_invalid"]) == 1
    assert summary["skipped_invalid"][0]["id"] == "custom_bad_code"


def test_import_skips_missing_dependencies(isolated_custom_methods_store):
    bundle = {
        "schema_version": 1,
        "exported_at": "2026-04-09T12:00:00",
        "methods": [
            {
                "id": "custom_dependent_method",
                "display_name": "Dependent Method",
                "description": "Needs another custom method.",
                "input_type": "one_column",
                "output_type": "scalar",
                "dependencies": ["custom_missing_parent"],
                "user_code": VALID_ONE_COL_CODE,
            }
        ],
    }

    summary = cml.import_custom_methods_bundle(bundle)

    assert summary["imported"] == []
    assert len(summary["skipped_invalid"]) == 1
    assert "Missing dependencies" in summary["skipped_invalid"][0]["reason"]


def test_import_resolves_dependency_chain_in_bundle(isolated_custom_methods_store):
    bundle = {
        "schema_version": 1,
        "exported_at": "2026-04-09T12:00:00",
        "methods": [
            {
                "id": "custom_child_method",
                "display_name": "Child Method",
                "description": "Calls the parent.",
                "input_type": "one_column",
                "output_type": "scalar",
                "dependencies": ["custom_parent_method"],
                "user_code": """value = toolbox["custom_parent_method"](data)
result = float(value)
""",
            },
            {
                "id": "custom_parent_method",
                "display_name": "Parent Method",
                "description": "Base method.",
                "input_type": "one_column",
                "output_type": "scalar",
                "dependencies": [],
                "user_code": VALID_ONE_COL_CODE,
            },
        ],
    }

    summary = cml.import_custom_methods_bundle(bundle)
    imported_ids = [entry["id"] for entry in summary["imported"]]

    assert summary["ok"] is True
    assert imported_ids == ["custom_parent_method", "custom_child_method"]


def test_import_accepts_standard_method_dependencies(isolated_custom_methods_store):
    bundle = {
        "schema_version": 1,
        "exported_at": "2026-04-09T12:00:00",
        "methods": [
            {
                "id": "custom_uses_mean",
                "display_name": "Uses Mean",
                "description": "Calls the built-in mean method.",
                "input_type": "one_column",
                "output_type": "scalar",
                "dependencies": ["mean"],
                "user_code": """value = toolbox["mean"](data)
result = float(value)
""",
            }
        ],
    }

    summary = cml.import_custom_methods_bundle(bundle)

    assert summary["ok"] is True
    assert [entry["id"] for entry in summary["imported"]] == ["custom_uses_mean"]


def test_import_rejects_circular_dependencies(isolated_custom_methods_store):
    bundle = {
        "schema_version": 1,
        "exported_at": "2026-04-09T12:00:00",
        "methods": [
            {
                "id": "custom_first_cycle",
                "display_name": "First Cycle",
                "description": "Part of a cycle.",
                "input_type": "one_column",
                "output_type": "scalar",
                "dependencies": ["custom_second_cycle"],
                "user_code": VALID_ONE_COL_CODE,
            },
            {
                "id": "custom_second_cycle",
                "display_name": "Second Cycle",
                "description": "Part of a cycle.",
                "input_type": "one_column",
                "output_type": "scalar",
                "dependencies": ["custom_first_cycle"],
                "user_code": VALID_ONE_COL_CODE,
            },
        ],
    }

    summary = cml.import_custom_methods_bundle(bundle)

    assert summary["imported"] == []
    assert len(summary["skipped_invalid"]) == 2
    assert all(
        "Circular dependency detected" in entry["reason"]
        for entry in summary["skipped_invalid"]
    )
