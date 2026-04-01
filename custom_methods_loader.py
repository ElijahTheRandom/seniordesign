"""
custom_methods_loader.py
------------------------
Shared utility for loading custom statistical methods from the
persistence folder (results_cache/custom_methods/).

Used by:
    - backend_handler.py  → to merge custom classes into the methods registry
    - frontend_handler.py → to build display name mappings
    - run_manager.py      → to extend METHOD_NAMES dynamically
    - homepage.py         → to render custom method checkboxes

This module has NO Streamlit dependency — it is safe to import anywhere.
"""

import importlib.util
import json
import os
import re
import sys
from datetime import datetime

# Absolute path to the custom_methods folder, resolved relative to this file
_CUSTOM_METHODS_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "results_cache",
    "custom_methods",
)
_CUSTOM_METHODS_JSON = os.path.join(_CUSTOM_METHODS_DIR, "custom_methods.json")


def _ensure_dir():
    """Create the custom_methods directory and JSON file if they don't exist."""
    os.makedirs(_CUSTOM_METHODS_DIR, exist_ok=True)
    if not os.path.isfile(_CUSTOM_METHODS_JSON):
        with open(_CUSTOM_METHODS_JSON, "w", encoding="utf-8") as f:
            json.dump([], f)


def load_custom_methods_registry() -> list[dict]:
    """
    Read the custom_methods.json registry and return the list of entries.

    Each entry is a dict with keys:
        id, display_name, description, input_type, output_type,
        filename, class_name, created_at
    """
    _ensure_dir()
    try:
        with open(_CUSTOM_METHODS_JSON, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return []


def load_custom_method_classes() -> dict:
    """
    Dynamically import all custom method .py files and return a dict
    mapping method_id → class reference, matching the shape of
    methods.methods.methods_list.
    """
    registry = load_custom_methods_registry()
    classes = {}
    for entry in registry:
        method_id = entry["id"]
        filename = entry["filename"]
        class_name = entry["class_name"]

        # Security: only allow filenames that are purely alphanumeric + underscores
        if not re.match(r"^[A-Za-z0-9_]+\.py$", filename):
            continue

        filepath = os.path.join(_CUSTOM_METHODS_DIR, filename)
        if not os.path.isfile(filepath):
            continue

        # Resolve to absolute and verify it's inside the custom_methods dir
        abs_filepath = os.path.realpath(filepath)
        abs_dir = os.path.realpath(_CUSTOM_METHODS_DIR)
        if not abs_filepath.startswith(abs_dir + os.sep):
            continue

        try:
            module_name = f"custom_methods.{method_id}"
            spec = importlib.util.spec_from_file_location(module_name, abs_filepath)
            if spec is None or spec.loader is None:
                continue
            module = importlib.util.module_from_spec(spec)
            # Don't pollute sys.modules with user code
            spec.loader.exec_module(module)
            cls = getattr(module, class_name, None)
            if cls is not None:
                classes[method_id] = cls
        except Exception:
            # Skip broken custom methods — don't crash the app
            continue

    return classes


def get_custom_display_names() -> dict[str, str]:
    """
    Return a dict mapping custom method IDs → display names,
    suitable for merging into _ID_TO_DISPLAY or METHOD_NAMES.
    """
    registry = load_custom_methods_registry()
    return {entry["id"]: entry["display_name"] for entry in registry}


def get_custom_input_types() -> dict[str, str]:
    """
    Return a dict mapping custom method IDs → input_type
    ('one_column' or 'two_column').
    """
    registry = load_custom_methods_registry()
    return {entry["id"]: entry["input_type"] for entry in registry}


def _sanitize_id(name: str) -> str:
    """
    Convert a human-readable method name to a safe snake_case ID.
    Always prefixed with 'custom_'.
    """
    # Lowercase, replace non-alphanumeric with underscore, collapse runs
    slug = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    if not slug:
        slug = "unnamed"
    return f"custom_{slug}"


def _to_class_name(method_id: str) -> str:
    """Convert a method_id like 'custom_my_method' to 'CustomMyMethod'."""
    return "".join(part.capitalize() for part in method_id.split("_"))


# ---------------------------------------------------------------------------
# Blocked modules / attributes that must never appear in user code.
# ---------------------------------------------------------------------------
_BLOCKED_MODULES = frozenset({
    "os", "sys", "subprocess", "shutil", "pathlib",
    "socket", "http", "urllib", "requests",
    "ctypes", "multiprocessing", "threading",
    "pickle", "shelve", "marshal",
})

_BLOCKED_BUILTINS = frozenset({
    "exec", "eval", "compile", "__import__",
    "open", "input", "breakpoint", "globals", "locals",
})


def validate_user_code(
    user_code: str,
    input_type: str = "one_column",
) -> list[str]:
    """
    Perform static checks on user-supplied compute code.

    Returns a list of human-readable warning / error strings.
    An empty list means no issues were found.
    """
    import ast as _ast
    import builtins as _builtins

    issues: list[str] = []

    if not user_code or not user_code.strip():
        issues.append("Code cannot be empty.")
        return issues

    # --- 1. Syntax check ---
    try:
        tree = _ast.parse(user_code, filename="<custom_method>")
    except SyntaxError as e:
        issues.append(f"Syntax error on line {e.lineno}: {e.msg}")
        return issues  # can't do further AST analysis

    # --- 2. Check that `result` is assigned somewhere ---
    assigns_result = False
    for node in _ast.walk(tree):
        if isinstance(node, _ast.Assign):
            for target in node.targets:
                if isinstance(target, _ast.Name) and target.id == "result":
                    assigns_result = True
        if isinstance(node, _ast.AugAssign):
            if isinstance(node.target, _ast.Name) and node.target.id == "result":
                assigns_result = True
    if not assigns_result:
        issues.append(
            "Your code must assign to a variable called `result`. "
            "Example: result = float(np.mean(arr))"
        )

    # --- 3. Blocked imports ---
    for node in _ast.walk(tree):
        if isinstance(node, _ast.Import):
            for alias in node.names:
                top = alias.name.split(".")[0]
                if top in _BLOCKED_MODULES:
                    issues.append(
                        f"Importing `{alias.name}` is not allowed for security reasons."
                    )
        if isinstance(node, _ast.ImportFrom):
            if node.module:
                top = node.module.split(".")[0]
                if top in _BLOCKED_MODULES:
                    issues.append(
                        f"Importing from `{node.module}` is not allowed for security reasons."
                    )

    # --- 4. Blocked built-in calls ---
    for node in _ast.walk(tree):
        if isinstance(node, _ast.Call):
            func = node.func
            if isinstance(func, _ast.Name) and func.id in _BLOCKED_BUILTINS:
                issues.append(
                    f"Calling `{func.id}()` is not allowed for security reasons."
                )

    # --- 5. `return` statements ---
    # User code is injected inside a try-block in compute(); a bare return
    # would exit compute() and bypass the result structure.
    for node in _ast.walk(tree):
        if isinstance(node, _ast.Return):
            lineno = getattr(node, "lineno", "?")
            issues.append(
                f"Line {lineno}: Do not use `return`. Instead assign to "
                "`result` and let the template handle the return."
            )

    # --- 6. `class` / `def` definitions ---
    # They technically work but are almost always a mistake in this context.
    for node in _ast.iter_child_nodes(tree):
        if isinstance(node, _ast.FunctionDef | _ast.AsyncFunctionDef):
            issues.append(
                f"Line {node.lineno}: Defining function `{node.name}()` "
                "inside a custom method is not recommended. Write your "
                "logic inline instead."
            )
        if isinstance(node, _ast.ClassDef):
            issues.append(
                f"Line {node.lineno}: Defining class `{node.name}` "
                "inside a custom method is not supported."
            )

    # --- 7. Likely infinite loops (while True with no break) ---
    for node in _ast.walk(tree):
        if isinstance(node, _ast.While):
            # Check for `while True`
            test = node.test
            is_true = (isinstance(test, _ast.Constant) and test.value is True)
            if is_true:
                has_break = any(
                    isinstance(child, _ast.Break)
                    for child in _ast.walk(node)
                )
                if not has_break:
                    issues.append(
                        f"Line {node.lineno}: `while True` without a `break` "
                        "will run forever."
                    )

    # --- 8. Undefined-name detection ---
    # Collect all names that are *written to* (assigned / imported / loop
    # targets / comprehension targets) and then check every Name in Load
    # context.  Names provided by the template: data, params, np, result,
    # self, plus Python builtins.
    _TEMPLATE_NAMES = {"data", "params", "np", "result", "self", "toolbox"}
    builtin_names = set(dir(_builtins))

    # Gather locally-defined names
    locally_defined: set[str] = set()
    for node in _ast.walk(tree):
        if isinstance(node, _ast.Assign):
            for target in node.targets:
                if isinstance(target, _ast.Name):
                    locally_defined.add(target.id)
                elif isinstance(target, _ast.Tuple | _ast.List):
                    for elt in target.elts:
                        if isinstance(elt, _ast.Name):
                            locally_defined.add(elt.id)
        elif isinstance(node, _ast.AugAssign):
            if isinstance(node.target, _ast.Name):
                locally_defined.add(node.target.id)
        elif isinstance(node, _ast.For):
            t = node.target
            if isinstance(t, _ast.Name):
                locally_defined.add(t.id)
            elif isinstance(t, _ast.Tuple | _ast.List):
                for elt in t.elts:
                    if isinstance(elt, _ast.Name):
                        locally_defined.add(elt.id)
        elif isinstance(node, _ast.Import):
            for alias in node.names:
                locally_defined.add(alias.asname or alias.name.split(".")[0])
        elif isinstance(node, _ast.ImportFrom):
            for alias in node.names:
                locally_defined.add(alias.asname or alias.name)
        elif isinstance(node, _ast.FunctionDef | _ast.AsyncFunctionDef):
            locally_defined.add(node.name)
        elif isinstance(node, _ast.comprehension):
            t = node.target
            if isinstance(t, _ast.Name):
                locally_defined.add(t.id)
        elif isinstance(node, _ast.NamedExpr):  # walrus :=
            if isinstance(node.target, _ast.Name):
                locally_defined.add(node.target.id)
        elif isinstance(node, _ast.With):
            for item in node.items:
                if item.optional_vars and isinstance(item.optional_vars, _ast.Name):
                    locally_defined.add(item.optional_vars.id)
        elif isinstance(node, _ast.ExceptHandler):
            if node.name:
                locally_defined.add(node.name)

    known_names = _TEMPLATE_NAMES | builtin_names | locally_defined

    undefined_reported: set[str] = set()
    for node in _ast.walk(tree):
        if (
            isinstance(node, _ast.Name)
            and isinstance(node.ctx, _ast.Load)
            and node.id not in known_names
            and node.id not in undefined_reported
            and not node.id.startswith("_")
        ):
            undefined_reported.add(node.id)
            issues.append(
                f"Line {node.lineno}: `{node.id}` is not defined. "
                "Available variables: `data`, `params`, `np`."
            )

    # --- 9. Input-type hint ---
    if input_type == "two_column":
        if "data[0]" not in user_code and "data[1]" not in user_code:
            issues.append(
                "Hint: For a two-column method you probably want to "
                "reference `data[0]` and `data[1]`."
            )

    return issues


def save_custom_method(
    name: str,
    description: str,
    input_type: str,
    output_type: str,
    user_code: str,
    dependencies: list[str] | None = None,
) -> tuple[bool, str]:
    """
    Validate, generate, and persist a new custom statistical method.

    Args:
        name:        Human-readable method name.
        description: User's description of what the method does.
        input_type:  'one_column' or 'two_column'.
        output_type: 'scalar', 'list', or 'dictionary'.
        user_code:   The body of the compute logic written by the user.

    Returns:
        (success: bool, message: str)
    """
    _ensure_dir()

    # --- Validate name ---
    if not name or not name.strip():
        return False, "Method name cannot be empty."

    method_id = _sanitize_id(name.strip())
    class_name = _to_class_name(method_id)
    filename = f"{method_id}.py"

    # Check for collision with existing custom methods
    registry = load_custom_methods_registry()
    existing_ids = {e["id"] for e in registry}
    if method_id in existing_ids:
        return False, f"A custom method with ID '{method_id}' already exists."

    # Check display name uniqueness (two different names could sanitize to
    # different IDs but still look identical to the user in the UI).
    existing_names = {e["display_name"].strip().lower() for e in registry}
    if name.strip().lower() in existing_names:
        return False, f"A custom method named '{name.strip()}' already exists."

    # --- Validate user code ---
    issues = validate_user_code(user_code, input_type)
    errors = [i for i in issues if not i.startswith("Hint:")]
    if errors:
        return False, "\n".join(errors)

    # --- Validate dependencies (no cycles) ---
    if dependencies:
        cycle_err = detect_dependency_cycles(method_id, dependencies)
        if cycle_err:
            return False, cycle_err

    # --- Generate the full .py file ---
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

    # Indent user code by 12 spaces (inside compute method's try block)
    indented_code = "\n".join(
        "            " + line if line.strip() else ""
        for line in user_code.splitlines()
    )

    file_content = f'''import numpy as np


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

    # --- Write the .py file ---
    filepath = os.path.join(_CUSTOM_METHODS_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(file_content)

    # --- Update the registry JSON ---
    entry = {
        "id": method_id,
        "display_name": name.strip(),
        "description": description.strip(),
        "input_type": input_type,
        "output_type": output_type,
        "filename": filename,
        "class_name": class_name,
        "dependencies": dependencies or [],
        "created_at": datetime.now().isoformat(),
    }
    registry.append(entry)
    with open(_CUSTOM_METHODS_JSON, "w", encoding="utf-8") as f:
        json.dump(registry, f, indent=2)

    return True, f"Method '{name.strip()}' saved successfully!"


def get_user_code(method_id: str) -> str | None:
    """
    Extract the user-written code block from a saved custom method .py file.

    Returns the code between the ``data = self.data`` /
    ``params = self.params`` header and the ``except Exception`` footer
    inside ``compute()``, or *None* if the file cannot be read.
    """
    registry = load_custom_methods_registry()
    entry = next((e for e in registry if e["id"] == method_id), None)
    if entry is None:
        return None

    filename = entry["filename"]
    if not re.match(r"^[A-Za-z0-9_]+\.py$", filename):
        return None

    filepath = os.path.join(_CUSTOM_METHODS_DIR, filename)
    if not os.path.isfile(filepath):
        return None

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except OSError:
        return None

    # Find the user-code region between the two sentinel lines
    start_idx = None
    end_idx = None
    for i, line in enumerate(lines):
        if "params = self.params" in line:
            start_idx = i + 1
        if start_idx is not None and "except Exception" in line:
            end_idx = i
            break

    if start_idx is None or end_idx is None or start_idx >= end_idx:
        return None

    # Strip the 12-space indentation added by save_custom_method
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


def update_custom_method(
    method_id: str,
    name: str,
    description: str,
    input_type: str,
    output_type: str,
    user_code: str,
    dependencies: list[str] | None = None,
) -> tuple[bool, str]:
    """
    Update an existing custom method's metadata, code, and generated .py file.

    Replaces the registry entry in-place (preserving ``created_at``) and
    regenerates the .py file from the new parameters.

    Returns:
        (success: bool, message: str)
    """
    _ensure_dir()
    registry = load_custom_methods_registry()
    idx = next((i for i, e in enumerate(registry) if e["id"] == method_id), None)
    if idx is None:
        return False, f"Method '{method_id}' not found."

    # --- Validate name ---
    if not name or not name.strip():
        return False, "Method name cannot be empty."

    # Check display name uniqueness (exclude the method being edited)
    for i, e in enumerate(registry):
        if i != idx and e["display_name"].strip().lower() == name.strip().lower():
            return False, f"Another custom method named '{name.strip()}' already exists."

    # Validate user code
    issues = validate_user_code(user_code, input_type)
    errors = [i for i in issues if not i.startswith("Hint:")]
    if errors:
        return False, "\n".join(errors)

    # --- Validate dependencies (no cycles) ---
    if dependencies:
        cycle_err = detect_dependency_cycles(method_id, dependencies)
        if cycle_err:
            return False, cycle_err

    old_entry = registry[idx]
    class_name = old_entry["class_name"]
    filename = old_entry["filename"]

    # Regenerate the .py file using the same template as save_custom_method
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

    file_content = f'''import numpy as np


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

    filepath = os.path.join(_CUSTOM_METHODS_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(file_content)

    # Invalidate any cached module so the next import picks up new code
    mod_key = f"custom_methods.{method_id}"
    sys.modules.pop(mod_key, None)

    # Update the registry entry (preserve id, filename, class_name, created_at)
    registry[idx] = {
        "id": method_id,
        "display_name": name.strip(),
        "description": description.strip(),
        "input_type": input_type,
        "output_type": output_type,
        "filename": filename,
        "class_name": class_name,
        "dependencies": dependencies or [],
        "created_at": old_entry["created_at"],
    }
    with open(_CUSTOM_METHODS_JSON, "w", encoding="utf-8") as f:
        json.dump(registry, f, indent=2)

    return True, f"Method '{name.strip()}' updated successfully!"


def delete_custom_method(method_id: str) -> tuple[bool, str]:
    """
    Thoroughly remove a custom method:
        1. Delete the generated .py file
        2. Remove the entry from custom_methods.json
        3. Scrub the method from any saved runs in saved_runs.json
        4. Remove the cached module from sys.modules

    Returns:
        (success: bool, message: str)
    """
    _ensure_dir()
    registry = load_custom_methods_registry()
    entry = next((e for e in registry if e["id"] == method_id), None)
    if entry is None:
        return False, f"Method '{method_id}' not found."

    display_name = entry["display_name"]

    # Check if other methods depend on this one
    dependents = [
        e["display_name"] for e in registry
        if e["id"] != method_id and method_id in e.get("dependencies", [])
    ]
    if dependents:
        names = ", ".join(f"'{n}'" for n in dependents)
        return False, (
            f"Cannot delete '{display_name}' because the following methods "
            f"depend on it: {names}. Remove those dependencies first."
        )

    # 1) Delete the .py file
    filename = entry["filename"]
    if re.match(r"^[A-Za-z0-9_]+\.py$", filename):
        filepath = os.path.join(_CUSTOM_METHODS_DIR, filename)
        abs_filepath = os.path.realpath(filepath)
        abs_dir = os.path.realpath(_CUSTOM_METHODS_DIR)
        if abs_filepath.startswith(abs_dir + os.sep) and os.path.isfile(abs_filepath):
            os.remove(abs_filepath)

    # 2) Remove from registry
    registry = [e for e in registry if e["id"] != method_id]
    with open(_CUSTOM_METHODS_JSON, "w", encoding="utf-8") as f:
        json.dump(registry, f, indent=2)

    # 3) Scrub from saved_runs.json so past runs don't reference a ghost method
    saved_runs_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "results_cache", "saved_runs.json",
    )
    if os.path.isfile(saved_runs_path):
        try:
            with open(saved_runs_path, "r", encoding="utf-8") as f:
                runs = json.load(f)
            changed = False
            for run in runs:
                old_len = len(run.get("methods", []))
                run["methods"] = [
                    m for m in run.get("methods", [])
                    if m.get("id") != method_id
                ]
                if len(run["methods"]) != old_len:
                    changed = True
            if changed:
                with open(saved_runs_path, "w", encoding="utf-8") as f:
                    json.dump(runs, f, indent=2)
        except (json.JSONDecodeError, OSError):
            pass  # best-effort cleanup

    # 4) Evict cached module
    sys.modules.pop(f"custom_methods.{method_id}", None)

    return True, f"Method '{display_name}' deleted."


# ---------------------------------------------------------------------------
# Toolbox helpers — allow custom methods to call each other
# ---------------------------------------------------------------------------

def get_available_tools_info(exclude_id: str | None = None) -> list[dict]:
    """
    Return a list of dicts describing available custom methods that can
    be used as tools in the toolbox.

    Each dict has: id, display_name, description, input_type.
    If *exclude_id* is given, that method is omitted (used when editing
    a method so it doesn't list itself as a dependency).
    """
    registry = load_custom_methods_registry()
    tools = []
    for entry in registry:
        if exclude_id and entry["id"] == exclude_id:
            continue
        tools.append({
            "id": entry["id"],
            "display_name": entry["display_name"],
            "description": entry.get("description", ""),
            "input_type": entry.get("input_type", "one_column"),
        })
    return tools


def detect_dependency_cycles(
    method_id: str,
    proposed_deps: list[str],
) -> str | None:
    """
    Check whether *proposed_deps* for *method_id* would create a cycle
    in the dependency graph.

    Returns an error message string if a cycle is found, or None if safe.
    """
    registry = load_custom_methods_registry()
    dep_map: dict[str, list[str]] = {
        e["id"]: list(e.get("dependencies", []))
        for e in registry
    }
    # Insert the proposed state
    dep_map[method_id] = list(proposed_deps)

    visited: set[str] = set()
    in_stack: set[str] = set()

    def _dfs(node: str) -> bool:
        if node in in_stack:
            return True  # cycle detected
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
