

import ast
import re
from typing import Literal

SevType = Literal["error", "warning", "info", "style"]




class _CodeVisitor(ast.NodeVisitor):
    """Walk Python AST to collect defined and used names."""

    PYTHON_BUILTINS = frozenset({
        "print", "len", "range", "int", "str", "list", "dict", "set",
        "tuple", "bool", "float", "type", "isinstance", "hasattr",
        "getattr", "setattr", "input", "open", "enumerate", "zip", "map",
        "filter", "sorted", "reversed", "min", "max", "sum", "abs",
        "round", "format", "repr", "id", "hash", "iter", "next", "any",
        "all", "vars", "dir", "help", "super", "object", "property",
        "staticmethod", "classmethod", "True", "False", "None",
        "Exception", "ValueError", "TypeError", "KeyError", "IndexError",
        "AttributeError", "NotImplementedError", "StopIteration",
        "self", "cls", "__init__", "__name__", "__main__", "__str__",
        "__repr__", "__all__", "__doc__", "__file__",
    })

    def __init__(self):
        self.imports: dict[str, int] = {}        # name -> line
        self.functions: dict[str, int] = {}      # name -> line
        self.variables: dict[str, int] = {}      # name -> line
        self.used: set[str] = set()
        self.defined: set[str] = set()

    # --- imports ---
    def visit_Import(self, node):
        for alias in node.names:
            name = alias.asname or alias.name.split('.')[0]
            if name not in self.PYTHON_BUILTINS:
                self.imports[name] = node.lineno
                self.defined.add(name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        for alias in node.names:
            name = alias.asname or alias.name
            if name not in self.PYTHON_BUILTINS and name != '*':
                self.imports[name] = node.lineno
                self.defined.add(name)
        self.generic_visit(node)

    # --- functions ---
    def visit_FunctionDef(self, node):
        if not node.name.startswith('_'):
            self.functions[node.name] = node.lineno
            self.defined.add(node.name)
        self.generic_visit(node)

    visit_AsyncFunctionDef = visit_FunctionDef

    # --- variables (assignments) ---
    def visit_Assign(self, node):
        for target in node.targets:
            if isinstance(target, ast.Name):
                name = target.id
                if (not name.startswith('_') and
                        name not in self.PYTHON_BUILTINS):
                    self.variables[name] = node.lineno
                    self.defined.add(name)
        self.generic_visit(node)

    def visit_AnnAssign(self, node):
        if isinstance(node.target, ast.Name):
            name = node.target.id
            if not name.startswith('_') and name not in self.PYTHON_BUILTINS:
                self.variables[name] = node.lineno
                self.defined.add(name)
        self.generic_visit(node)

    # --- usages ---
    def visit_Name(self, node):
        if isinstance(node.ctx, ast.Load):
            self.used.add(node.id)
        self.generic_visit(node)

    def visit_Attribute(self, node):
        self.used.add(node.attr)
        self.generic_visit(node)

    def visit_Call(self, node):
        if isinstance(node.func, ast.Name):
            self.used.add(node.func.id)
        self.generic_visit(node)


def _issue(text: str, line: int, sev: SevType) -> dict:
    return {"text": text, "line": line, "severity": sev}


# ─────────────────────────────────────────
#  Python static analysis
# ─────────────────────────────────────────

def _analyze_python(code: str, tree) -> dict:
    visitor = _CodeVisitor()
    visitor.visit(tree)

    unused_imports: list[str] = []
    unused_functions: list[str] = []
    unused_variables: list[str] = []
    style_violations: list[str] = []
    issues: list[dict] = []

    # Unused imports
    for name, line in visitor.imports.items():
        if name not in visitor.used:
            unused_imports.append(name)
            issues.append(_issue(
                f"Import '{name}' is imported but never used.",
                line, "warning"
            ))

    # Unused functions (skip main, __init__, index, about etc.)
    SKIP_FN = {"main", "index", "about", "posts", "header", "footer",
                "navbar", "assistant", "history"}
    for name, line in visitor.functions.items():
        if name not in visitor.used and name not in SKIP_FN:
            unused_functions.append(name)
            issues.append(_issue(
                f"Function '{name}' is defined but never called.",
                line, "warning"
            ))

    # Unused variables
    for name, line in visitor.variables.items():
        if name not in visitor.used:
            unused_variables.append(name)
            issues.append(_issue(
                f"Variable '{name}' is assigned but never used.",
                line, "info"
            ))

    # Style violations (PEP8 inspired)
    lines = code.split('\n')
    for i, line in enumerate(lines, 1):
        t = line.rstrip()
        stripped = t.strip()
        if not stripped or stripped.startswith('#'):
            continue

        if len(t) > 79:
            style_violations.append(f"line {i} > 79 chars ({len(t)})")
            issues.append(_issue(f"Line {i} exceeds 79 characters ({len(t)} chars).", i, "style"))

        if re.search(r'for\s+\w+\s+in\s+range\(len\(', stripped):
            style_violations.append("range(len(...))")
            issues.append(_issue("Use enumerate() instead of range(len(...)).", i, "style"))

        if re.match(r'^\s*except:\s*$', line):
            style_violations.append("bare except")
            issues.append(_issue("Bare 'except:' catches all exceptions — specify exception type.", i, "style"))

        if re.search(r'\t', line):
            style_violations.append("tab indentation")
            issues.append(_issue("Use 4 spaces instead of tabs for indentation.", i, "style"))

        if re.search(r'\bprint\s*\(', stripped) and not stripped.startswith('#'):
            pass  # print statements are fine in student code

    return {
        "unused_imports": unused_imports,
        "unused_functions": unused_functions,
        "unused_variables": unused_variables,
        "style_violations": style_violations,
        "issues": issues,
        "created_vars": sorted(visitor.defined),
        "used_vars": sorted(visitor.used),
    }


# ─────────────────────────────────────────
#  Generic static analysis (other langs)
# ─────────────────────────────────────────

def _analyze_generic(code: str, lang: str) -> dict:
    lines = code.split('\n')
    issues: list[dict] = []
    unused_imports: list[str] = []
    unused_functions: list[str] = []
    unused_variables: list[str] = []
    style_violations: list[str] = []
    defined: set[str] = set()
    used: set[str] = set()

    # Collect all words (rough usage tracking)
    all_words = re.findall(r'[a-zA-Z_]\w*', code)
    word_count: dict[str, int] = {}
    for w in all_words:
        word_count[w] = word_count.get(w, 0) + 1

    if lang in ("javascript", "typescript"):
        for i, line in enumerate(lines, 1):
            t = line.strip()
            if not t or t.startswith('//'):
                continue
            # var usage
            m = re.match(r'^var\s+(\w+)', t)
            if m:
                style_violations.append("var usage")
                issues.append(_issue("Use 'const' or 'let' instead of 'var'.", i, "style"))
            # import detection
            m = re.match(r"^import\s+.*\s+from\s+'(.+)'", t)
            if not m:
                m = re.match(r'^const\s+(\w+)\s*=\s*require\(', t)
            if m:
                name = m.group(1)
                if word_count.get(name, 0) <= 1:
                    unused_imports.append(name)
                    issues.append(_issue(f"'{name}' may be imported but unused.", i, "warning"))
            # console.log in production
            if re.search(r'console\.log', t):
                issues.append(_issue("console.log found — remove before production.", i, "info"))

    elif lang == "java":
        for i, line in enumerate(lines, 1):
            t = line.strip()
            if not t or t.startswith('//'):
                continue
            m = re.match(r'^import\s+([\w.]+);', t)
            if m:
                name = m.group(1).split('.')[-1]
                if word_count.get(name, 0) <= 1:
                    unused_imports.append(name)
                    issues.append(_issue(f"Import '{name}' may be unused.", i, "warning"))
            if re.search(r'System\.out\.print', t):
                issues.append(_issue("System.out.println found — use a logger in production.", i, "info"))

    elif lang == "go":
        for i, line in enumerate(lines, 1):
            t = line.strip()
            if not t or t.startswith('//'):
                continue
            m = re.match(r'^import\s+"([\w/]+)"', t)
            if m:
                name = m.group(1).split('/')[-1]
                if word_count.get(name, 0) <= 1:
                    unused_imports.append(name)
                    issues.append(_issue(f"Package '{name}' imported but possibly unused.", i, "warning"))
            if re.search(r'for\s+\w+\s*:=\s*0;\s*\w+\s*<\s*len\(', t):
                style_violations.append("index loop")
                issues.append(_issue("Prefer range-based for loop over index loop.", i, "style"))

    elif lang == "rust":
        for i, line in enumerate(lines, 1):
            t = line.strip()
            if not t or t.startswith('//'):
                continue
            if re.match(r'^use\s+', t):
                name = t.rstrip(';').split('::')[-1].strip('{}').split(',')[0].strip()
                if name and word_count.get(name, 0) <= 1:
                    unused_imports.append(name)
                    issues.append(_issue(f"Use statement '{name}' may be unused.", i, "warning"))
            m = re.match(r'^\s*let\s+(\w+)\s*=', t)
            if m:
                vname = m.group(1)
                defined.add(vname)
                if word_count.get(vname, 0) <= 1:
                    unused_variables.append(vname)
                    issues.append(_issue(f"Variable '{vname}' is bound but never used.", i, "warning"))

    elif lang in ("c", "cpp"):
        for i, line in enumerate(lines, 1):
            t = line.strip()
            if not t or t.startswith('//') or t.startswith('#'):
                continue
            if re.match(r'#include\s+[<"](.+)[>"]', line.strip()):
                name = re.match(r'#include\s+[<"](.+)[>"]', line.strip()).group(1).replace('.h', '')
                if word_count.get(name, 0) <= 1:
                    unused_imports.append(name)
                    issues.append(_issue(f"Header '{name}' may be unused.", i, "warning"))
            if re.search(r'\bgets\s*\(', t):
                issues.append(_issue("Avoid gets() — use fgets() instead (buffer overflow risk).", i, "error"))
            if re.search(r'\bscanf\s*\(', t):
                issues.append(_issue("scanf() is unsafe — validate input length.", i, "warning"))

    # Generic: long lines
    for i, line in enumerate(lines, 1):
        if len(line.rstrip()) > 100:
            style_violations.append(f"line {i} too long")
            issues.append(_issue(f"Line {i} exceeds 100 characters.", i, "style"))

    return {
        "unused_imports": list(set(unused_imports)),
        "unused_functions": unused_functions,
        "unused_variables": list(set(unused_variables)),
        "style_violations": list(set(style_violations)),
        "issues": issues,
        "created_vars": sorted(defined),
        "used_vars": [],
    }


# ─────────────────────────────────────────
#  Public API
# ─────────────────────────────────────────

def get_static_errors(tree, code: str = "", language: str = "python") -> dict:
    """
    Run static analysis on parsed code.

    Args:
        tree:     AST tree (Python only) or None for other languages.
        code:     Raw source code string.
        language: Target language.

    Returns:
        dict with unused_imports, unused_functions, unused_variables,
        style_violations, issues, created_vars, used_vars.
    """
    lang = language.lower()
    if lang == "python" and tree is not None:
        return _analyze_python(code, tree)
    else:
        return _analyze_generic(code, lang)


def calculate_quality_grade(issue_count: int) -> str:
    """Return letter grade based on issue count."""
    if issue_count == 0:
        return "A"
    elif issue_count <= 2:
        return "B"
    elif issue_count <= 5:
        return "C"
    else:
        return "D"


def get_linter_tools(language: str) -> list[dict]:
    """Return expected external linter tools for a language."""
    tools_map = {
        "python":     [{"name": "pyflakes", "desc": "Unused imports & variables"},
                       {"name": "pylint",   "desc": "Full PEP8 compliance"}],
        "javascript": [{"name": "ESLint",   "desc": "JS/ES6 linting"},
                       {"name": "jshint",   "desc": "Syntax & style"}],
        "typescript": [{"name": "ESLint",   "desc": "TS linting"},
                       {"name": "tsc",      "desc": "Type checking"}],
        "java":       [{"name": "javac",    "desc": "Compile-time errors"},
                       {"name": "checkstyle","desc": "Style enforcement"}],
        "go":         [{"name": "go vet",   "desc": "Vet checks"},
                       {"name": "golangci-lint", "desc": "Meta-linter"}],
        "rust":       [{"name": "rustc",    "desc": "Compiler warnings"},
                       {"name": "clippy",   "desc": "Idiomatic Rust"}],
        "c":          [{"name": "gcc -Wall","desc": "Compiler warnings"},
                       {"name": "cppcheck", "desc": "Static analysis"}],
        "cpp":        [{"name": "g++ -Wall","desc": "Compiler warnings"},
                       {"name": "cppcheck", "desc": "Static analysis"}],
    }
    return tools_map.get(language.lower(), [])
