import ast
from pathlib import Path


def test_gui_does_not_import_concrete_backends() -> None:
    gui_root = Path("src/agentle/gui")
    prohibited = (
        "agentle.agents.adapters",
        "agentle.execution",
        "agentle.models.adapters",
        "agentle.persistence",
        "agentle.tools",
        "openai",
        "pydantic_ai",
        "sqlite3",
        "subprocess",
    )
    for source_path in gui_root.glob("*.py"):
        tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))
        imported: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module is not None:
                imported.append(node.module)
        assert not [
            name
            for name in imported
            if any(name == item or name.startswith(f"{item}.") for item in prohibited)
        ], source_path


def test_public_contracts_do_not_import_external_framework_types() -> None:
    contract_paths = (
        Path("src/agentle/agents/contracts.py"),
        Path("src/agentle/context/contracts.py"),
        Path("src/agentle/execution/contracts.py"),
        Path("src/agentle/models/contracts.py"),
        Path("src/agentle/persistence/contracts.py"),
        Path("src/agentle/runtime/commands.py"),
        Path("src/agentle/runtime/events.py"),
        Path("src/agentle/tools/contracts.py"),
    )
    external_roots = {"PyQt6", "openai", "pydantic_ai", "sqlite3"}
    for source_path in contract_paths:
        tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))
        imported: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.partition(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module is not None:
                imported.add(node.module.partition(".")[0])
        assert imported.isdisjoint(external_roots), source_path
