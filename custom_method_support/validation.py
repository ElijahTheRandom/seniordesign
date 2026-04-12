"""Static validation for user-authored custom method code."""

from __future__ import annotations


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
    """Perform static checks on user-supplied compute code."""
    import ast as _ast
    import builtins as _builtins

    issues: list[str] = []

    if not user_code or not user_code.strip():
        issues.append("Code cannot be empty.")
        return issues

    try:
        tree = _ast.parse(user_code, filename="<custom_method>")
    except SyntaxError as exc:
        issues.append(f"Syntax error on line {exc.lineno}: {exc.msg}")
        return issues

    assigns_result = False
    for node in _ast.walk(tree):
        if isinstance(node, _ast.Assign):
            for target in node.targets:
                if isinstance(target, _ast.Name) and target.id == "result":
                    assigns_result = True
        if isinstance(node, _ast.AugAssign) and isinstance(node.target, _ast.Name):
            if node.target.id == "result":
                assigns_result = True
    if not assigns_result:
        issues.append(
            "Your code must assign to a variable called `result`. "
            "Example: result = float(np.mean(arr))"
        )

    for node in _ast.walk(tree):
        if isinstance(node, _ast.Import):
            for alias in node.names:
                top = alias.name.split(".")[0]
                if top in _BLOCKED_MODULES:
                    issues.append(
                        f"Importing `{alias.name}` is not allowed for security reasons."
                    )
        if isinstance(node, _ast.ImportFrom) and node.module:
            top = node.module.split(".")[0]
            if top in _BLOCKED_MODULES:
                issues.append(
                    f"Importing from `{node.module}` is not allowed for security reasons."
                )

    for node in _ast.walk(tree):
        if isinstance(node, _ast.Call):
            func = node.func
            if isinstance(func, _ast.Name) and func.id in _BLOCKED_BUILTINS:
                issues.append(
                    f"Calling `{func.id}()` is not allowed for security reasons."
                )

    for node in _ast.walk(tree):
        if isinstance(node, _ast.Return):
            lineno = getattr(node, "lineno", "?")
            issues.append(
                f"Line {lineno}: Do not use `return`. Instead assign to "
                "`result` and let the template handle the return."
            )

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

    for node in _ast.walk(tree):
        if isinstance(node, _ast.While):
            test = node.test
            is_true = isinstance(test, _ast.Constant) and test.value is True
            if is_true:
                has_break = any(isinstance(child, _ast.Break) for child in _ast.walk(node))
                if not has_break:
                    issues.append(
                        f"Line {node.lineno}: `while True` without a `break` "
                        "will run forever."
                    )

    template_names = {"data", "params", "np", "result", "self", "toolbox"}
    builtin_names = set(dir(_builtins))
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
        elif isinstance(node, _ast.AugAssign) and isinstance(node.target, _ast.Name):
            locally_defined.add(node.target.id)
        elif isinstance(node, _ast.For):
            target = node.target
            if isinstance(target, _ast.Name):
                locally_defined.add(target.id)
            elif isinstance(target, _ast.Tuple | _ast.List):
                for elt in target.elts:
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
        elif isinstance(node, _ast.comprehension) and isinstance(node.target, _ast.Name):
            locally_defined.add(node.target.id)
        elif isinstance(node, _ast.NamedExpr) and isinstance(node.target, _ast.Name):
            locally_defined.add(node.target.id)
        elif isinstance(node, _ast.With):
            for item in node.items:
                if item.optional_vars and isinstance(item.optional_vars, _ast.Name):
                    locally_defined.add(item.optional_vars.id)
        elif isinstance(node, _ast.ExceptHandler) and node.name:
            locally_defined.add(node.name)

    known_names = template_names | builtin_names | locally_defined
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

    if input_type == "two_column":
        if "data[0]" not in user_code and "data[1]" not in user_code:
            issues.append(
                "Hint: For a two-column method you probably want to "
                "reference `data[0]` and `data[1]`."
            )

    return issues
