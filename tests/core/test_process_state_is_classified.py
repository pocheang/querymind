"""Tests verifying that all process-level in-memory states are classified.

ARC-01 Phase 0 Guardrail:
1. test_every_process_state_is_classified
2. test_inventory_has_no_stale_entries
3. test_every_entry_has_a_category_and_a_reason
4. test_cached_functions_are_only_B_or_D
5. test_the_scanner_can_see_every_shape
"""

import ast
import importlib.util
from pathlib import Path

_inventory_path = Path(__file__).parent / "process_state_inventory.py"
_spec = importlib.util.spec_from_file_location("process_state_inventory", _inventory_path)
assert _spec is not None
assert _spec.loader is not None
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
INVENTORY = _mod.INVENTORY

SYNC_PRIMITIVES = {
    "Lock",
    "RLock",
    "Semaphore",
    "BoundedSemaphore",
    "Event",
    "Condition",
    "ThreadPoolExecutor",
    "ProcessPoolExecutor",
    "Queue",
}

CONTAINER_CALLS = {
    "dict",
    "list",
    "set",
    "deque",
    "OrderedDict",
    "defaultdict",
    "Counter",
}

MUTATING_METHODS = {
    "append",
    "appendleft",
    "extend",
    "insert",
    "pop",
    "popleft",
    "popitem",
    "remove",
    "clear",
    "update",
    "setdefault",
    "add",
    "discard",
    "move_to_end",
}


def scan_source(code: str, path_str: str) -> set[tuple[str, str]]:
    """Scan python source code for process-level state according to rules R1-R5."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return set()

    found: set[tuple[str, str]] = set()

    # R1: global X within functions
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for child in ast.walk(node):
                if isinstance(child, ast.Global):
                    for name in child.names:
                        found.add((f"{path_str}::{name}", "R1"))

    # Track in-place mutations for mutable containers (R2)
    modified_names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Subscript) and isinstance(t.value, ast.Name):
                    modified_names.add(t.value.id)
        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Subscript) and isinstance(node.target.value, ast.Name):
                modified_names.add(node.target.value.id)
        elif isinstance(node, ast.AugAssign):
            if isinstance(node.target, ast.Subscript) and isinstance(node.target.value, ast.Name):
                modified_names.add(node.target.value.id)
            elif isinstance(node.target, ast.Name) and isinstance(node.op, (ast.BitOr, ast.Add)):
                modified_names.add(node.target.id)
        elif isinstance(node, ast.Delete):
            for t in node.targets:
                if isinstance(t, ast.Subscript) and isinstance(t.value, ast.Name):
                    modified_names.add(t.value.id)
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
                if node.func.attr in MUTATING_METHODS:
                    modified_names.add(node.func.value.id)

    # Classes in module & imports from app (for R5)
    local_classes = {n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)}
    app_imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if (node.module and (node.module.startswith("app.") or node.module == "app")) or node.level > 0:
                for alias in node.names:
                    app_imported.add(alias.asname or alias.name)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("app.") or alias.name == "app":
                    app_imported.add(alias.asname or alias.name)

    # Top-level statements helper
    def iter_top_stmts(stmts):
        for s in stmts:
            yield s
            if isinstance(s, ast.If):
                yield from iter_top_stmts(s.body)
                yield from iter_top_stmts(s.orelse)
            elif isinstance(s, ast.Try):
                yield from iter_top_stmts(s.body)
                yield from iter_top_stmts(s.orelse)
                yield from iter_top_stmts(s.finalbody)
                for h in s.handlers:
                    yield from iter_top_stmts(h.body)

    for stmt in iter_top_stmts(tree.body):
        targets = []
        val = None
        if isinstance(stmt, ast.Assign):
            targets = [t.id for t in stmt.targets if isinstance(t, ast.Name)]
            val = stmt.value
        elif isinstance(stmt, ast.AnnAssign):
            if isinstance(stmt.target, ast.Name):
                targets = [stmt.target.id]
            val = stmt.value

        for tname in targets:
            # Check R2 sync primitives & container calls
            if isinstance(val, ast.Call):
                func_last = None
                if isinstance(val.func, ast.Name):
                    func_last = val.func.id
                elif isinstance(val.func, ast.Attribute):
                    func_last = val.func.attr
                if func_last in SYNC_PRIMITIVES:
                    found.add((f"{path_str}::{tname}", "R2"))
                elif func_last in CONTAINER_CALLS:
                    if tname in modified_names:
                        found.add((f"{path_str}::{tname}", "R2"))
                # Check R5 internal class instantiation (supporting leading underscores)
                if (
                    func_last
                    and func_last.lstrip("_")[:1].isupper()
                    and (func_last in local_classes or func_last in app_imported)
                ):
                    found.add((f"{path_str}::{tname}", "R5"))

            # Check R2 container literals
            if isinstance(val, (ast.Dict, ast.List, ast.Set)):
                if tname in modified_names:
                    found.add((f"{path_str}::{tname}", "R2"))

    # R3: Cached functions (@lru_cache, @cache)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for dec in node.decorator_list:
                name = None
                if isinstance(dec, ast.Name):
                    name = dec.id
                elif isinstance(dec, ast.Attribute):
                    name = dec.attr
                elif isinstance(dec, ast.Call):
                    if isinstance(dec.func, ast.Name):
                        name = dec.func.id
                    elif isinstance(dec.func, ast.Attribute):
                        name = dec.func.attr
                if name in {"lru_cache", "cache"}:
                    found.add((f"{path_str}::{node.name}", "R3"))

    # R4: Class level _instance / _instances
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            for s in node.body:
                if isinstance(s, ast.Assign):
                    for t in s.targets:
                        if isinstance(t, ast.Name) and t.id in {"_instance", "_instances"}:
                            found.add((f"{path_str}::{node.name}.{t.id}", "R4"))
                elif isinstance(s, ast.AnnAssign):
                    if isinstance(s.target, ast.Name) and s.target.id in {"_instance", "_instances"}:
                        found.add((f"{path_str}::{node.name}.{s.target.id}", "R4"))

    return found


REPO_ROOT = Path(__file__).resolve().parents[2]
APP_DIR = REPO_ROOT / "app"


def scan_repo(root: Path | None = None) -> dict[str, set[str]]:
    """Scan all python files in root and return mapping from target key to set of matched rules."""
    target_dir = root or APP_DIR
    results: dict[str, set[str]] = {}
    for p in target_dir.rglob("*.py"):
        rel_posix = p.relative_to(REPO_ROOT).as_posix() if p.is_relative_to(REPO_ROOT) else p.as_posix()
        code = p.read_text(encoding="utf-8")
        matches = scan_source(code, rel_posix)
        for key, rule in matches:
            results.setdefault(key, set()).add(rule)
    return results


def test_every_process_state_is_classified():
    """Verify that every process-level in-memory state in app/ is classified in INVENTORY."""
    scanned = scan_repo()
    scanned_keys = set(scanned.keys())
    inventory_keys = set(INVENTORY.keys())

    unclassified = sorted(scanned_keys - inventory_keys)
    assert not unclassified, (
        f"Found {len(unclassified)} unclassified process states in app/.\n"
        "Please add them to tests/core/process_state_inventory.py with category and reason:\n"
        + "\n".join(f"  - {k} (detected by {sorted(scanned[k])})" for k in unclassified)
    )


def test_inventory_has_no_stale_entries():
    """Verify that INVENTORY contains no stale entries that no longer exist in code."""
    scanned = scan_repo()
    scanned_keys = set(scanned.keys())
    inventory_keys = set(INVENTORY.keys())

    stale = sorted(inventory_keys - scanned_keys)
    assert not stale, (
        f"Found {len(stale)} stale entries in tests/core/process_state_inventory.py "
        "that no longer match scanner rules:\n" + "\n".join(f"  - {k}" for k in stale)
    )


def test_every_entry_has_a_category_and_a_reason():
    """Verify that every inventory entry has a valid category (A, B, C, D) and a meaningful reason."""
    trivial_words = {"cache", "state", "缓存", "状态"}

    for key, (category, reason) in INVENTORY.items():
        assert category in {
            "A",
            "B",
            "C",
            "D",
        }, f"Invalid category '{category}' for {key}. Must be A, B, C, or D."
        assert isinstance(reason, str), f"Reason for {key} must be a string."
        stripped_reason = reason.strip()
        assert len(stripped_reason) >= 12, (
            f"Reason for {key} is too brief ('{stripped_reason}'). "
            "Must be at least 12 characters explaining why it belongs to this category."
        )
        assert stripped_reason.lower() not in trivial_words, (
            f"Reason for {key} is too trivial ('{stripped_reason}'). "
            "Must provide specific rationale for ARC-01 migration."
        )


def test_cached_functions_are_only_B_or_D():
    """Verify that functions detected via cache decorators (R3) are only categorized as B or D."""
    scanned = scan_repo()
    for key, rules in scanned.items():
        if "R3" in rules:
            assert key in INVENTORY, f"Cached function {key} not found in INVENTORY."
            cat, reason = INVENTORY[key]
            assert cat in {
                "B",
                "D",
            }, f"Cached function {key} was categorized as '{cat}'. Cache decorators can only be B or D."


def test_the_scanner_can_see_every_shape():
    """Unit test for the scanner verifying it detects artificial snippets for rules R1 to R5 and passes counter-examples."""
    # R1: global X within function
    code_r1 = """
_state = 0
def update_state():
    global _state
    _state += 1
"""
    r1_matches = scan_source(code_r1, "dummy/r1.py")
    assert ("dummy/r1.py::_state", "R1") in r1_matches

    # R2: sync primitives & mutable containers with in-place mutation
    code_r2 = """
import threading
_LOCK = threading.Lock()
_BUFFER = []
def add_item(item):
    _BUFFER.append(item)
"""
    r2_matches = scan_source(code_r2, "dummy/r2.py")
    assert ("dummy/r2.py::_LOCK", "R2") in r2_matches
    assert ("dummy/r2.py::_BUFFER", "R2") in r2_matches

    # R3: @lru_cache and @cache decorators
    code_r3 = """
from functools import lru_cache

@lru_cache(maxsize=128)
def compute_heavy(x: int) -> int:
    return x * 2
"""
    r3_matches = scan_source(code_r3, "dummy/r3.py")
    assert ("dummy/r3.py::compute_heavy", "R3") in r3_matches

    # R4: class-level _instance / _instances
    code_r4 = """
class SingletonService:
    _instance = None
    _instances: dict = {}
"""
    r4_matches = scan_source(code_r4, "dummy/r4.py")
    assert ("dummy/r4.py::SingletonService._instance", "R4") in r4_matches
    assert ("dummy/r4.py::SingletonService._instances", "R4") in r4_matches

    # R5: top-level instantiation of internal classes
    code_r5 = """
class InternalEngine:
    pass

_engine = InternalEngine()
"""
    r5_matches = scan_source(code_r5, "dummy/r5.py")
    assert ("dummy/r5.py::_engine", "R5") in r5_matches

    # R5 regression: leading underscore internal class instantiation (Round 2 item 3)
    code_r5_underscore = """
class _TTLCache:
    def __init__(self, size):
        pass

_cache = _TTLCache(3)
"""
    r5_underscore_matches = scan_source(code_r5_underscore, "dummy/r5_under.py")
    assert ("dummy/r5_under.py::_cache", "R5") in r5_underscore_matches

    # Counter-examples that must NOT be matched (Round 2 item 4)
    code_counter_examples = """
import logging
from fastapi import APIRouter
from pydantic import ToolDefinition

# 1. Read-only table with no in-place modifications
_TABLE = {"a": 1}

# 2. Third-party class instantiation
router = APIRouter()

# 3. Lowercase factory function
logger = logging.getLogger(__name__)

# 4. Local variables inside function
def f():
    items = []
    items.append(1)

# 5. Non-repo class from external package
_TOOL = ToolDefinition(name="test")
"""
    counter_matches = scan_source(code_counter_examples, "dummy/counter.py")
    matched_names = {k.split("::")[-1] for k, _ in counter_matches}
    assert "_TABLE" not in matched_names, f"_TABLE should not be detected: {counter_matches}"
    assert "router" not in matched_names, f"router should not be detected: {counter_matches}"
    assert "logger" not in matched_names, f"logger should not be detected: {counter_matches}"
    assert "items" not in matched_names, f"items should not be detected: {counter_matches}"
    assert "_TOOL" not in matched_names, f"_TOOL should not be detected: {counter_matches}"
    assert len(counter_matches) == 0, f"Expected zero matches in counter-examples, got {counter_matches}"
