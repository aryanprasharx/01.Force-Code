import ast
import logging
import os

from src.memory.graph_manager import CodeGraph

logger = logging.getLogger(__name__)


def _module_name_from_path(filepath: str, root: str) -> str:
    """Convert a .py file path into its dotted module name relative to root."""
    rel = os.path.relpath(filepath, root)
    rel_no_ext, _ = os.path.splitext(rel)
    parts = rel_no_ext.split(os.sep)
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def _collect_python_files(directory_path: str) -> list:
    """Recursively find all .py files under directory_path."""
    py_files = []
    for dirpath, _dirnames, filenames in os.walk(directory_path):
        for name in filenames:
            if name.endswith(".py"):
                # FORCE PATH NORMALIZATION HERE
                full_path = os.path.normpath(os.path.join(dirpath, name))
                py_files.append(full_path)
    return py_files


def _resolve_module(module: str, module_map: dict) -> str:
    """Resolve a dotted module name to a local file path, or None if external.

    Handles both `import pkg.mod` (where pkg.mod maps to a module) and
    `from pkg.mod import name` (where `name` may itself be a submodule, but
    pkg.mod is the file that holds the dependency).
    """
    if module in module_map:
        return module_map[module]
    # Walk up the dotted path: `a.b.c` -> try `a.b`, then `a`. This catches
    # `from a.b import c` where c is an attribute defined in a/b.py.
    parts = module.split(".")
    while parts:
        parts.pop()
        candidate = ".".join(parts)
        if candidate and candidate in module_map:
            return module_map[candidate]
    return None


def build_graph_from_directory(directory_path: str, graph: CodeGraph):
    """Parse every .py file under directory_path and record local import edges."""
    # FORCE DIRECTORY NORMALIZATION HERE
    directory_path = os.path.normpath(directory_path)
    py_files = _collect_python_files(directory_path)
    
    # Map dotted module name -> file path for every local module.
    module_map = {}
    for filepath in py_files:
        module_name = _module_name_from_path(filepath, directory_path)
        if module_name:
            module_map[module_name] = filepath
            
    for current_file in py_files:
        graph.add_file_node(current_file)
        
        try:
            with open(current_file, "r", encoding="utf-8") as f:
                source = f.read()
            tree = ast.parse(source, filename=current_file)
        except SyntaxError as exc:
            logger.warning("Skipping %s due to SyntaxError: %s", current_file, exc)
            continue
        except (OSError, UnicodeDecodeError) as exc:
            logger.warning("Skipping %s, could not read: %s", current_file, exc)
            continue

        current_module = _module_name_from_path(current_file, directory_path)
        imported_modules = set()

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported_modules.add(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.level and node.level > 0:
                    # Relative import: resolve against the current package.
                    base_parts = current_module.split(".") if current_module else []
                    # level 1 == current package, so drop `level` trailing parts.
                    base_parts = base_parts[: len(base_parts) - node.level]
                    prefix = ".".join(base_parts)
                    if node.module:
                        full = f"{prefix}.{node.module}" if prefix else node.module
                    else:
                        full = prefix
                    if full:
                        imported_modules.add(full)
                elif node.module:
                    imported_modules.add(node.module)

        for module in imported_modules:
            imported_file = _resolve_module(module, module_map)
            if imported_file and imported_file != current_file:
                graph.add_dependency(current_file, imported_file)
