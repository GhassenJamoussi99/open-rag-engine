"""Domain and interfaces must not depend on infrastructure (docs/architecture/04-layers.md)."""

import ast
import sys
from pathlib import Path

import pytest

PACKAGE_ROOT = Path(__file__).parents[2] / "src" / "open_rag_engine"
THIRD_PARTY_ALLOWED = {"pydantic", "pydantic_core", "typing_extensions"}
PROJECT_ALLOWED = {
    "domain": {"open_rag_engine.domain"},
    "interfaces": {"open_rag_engine.domain", "open_rag_engine.interfaces"},
}


def _imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            assert node.level == 0, f"{path}: use absolute imports"
            modules.add(node.module or "")
    return modules


def _is_allowed(module: str, project_allowed: set[str]) -> bool:
    root = module.split(".", maxsplit=1)[0]
    if root == "open_rag_engine":
        return any(module == p or module.startswith(f"{p}.") for p in project_allowed)
    return root in sys.stdlib_module_names or root in THIRD_PARTY_ALLOWED


@pytest.mark.parametrize("package", sorted(PROJECT_ALLOWED))
def test_package_imports_only_stdlib_pydantic_and_inner_layers(package: str) -> None:
    files = sorted((PACKAGE_ROOT / package).rglob("*.py"))
    assert files, f"no modules found in {package}/"

    violations = {
        f"{path.relative_to(PACKAGE_ROOT)}: {module}"
        for path in files
        for module in _imported_modules(path)
        if not _is_allowed(module, PROJECT_ALLOWED[package])
    }

    assert not violations, "forbidden imports:\n" + "\n".join(sorted(violations))


@pytest.mark.parametrize(
    ("module", "allowed"),
    [
        ("psycopg", False),
        ("fastapi.responses", False),
        ("anthropic", False),
        ("open_rag_engine.store", False),
        ("open_rag_engine.domainx", False),
        ("open_rag_engine.domain.span", True),
        ("pydantic", True),
        ("collections.abc", True),
    ],
)
def test_checker_rejects_infrastructure_imports(module: str, allowed: bool) -> None:
    assert _is_allowed(module, PROJECT_ALLOWED["domain"]) is allowed
