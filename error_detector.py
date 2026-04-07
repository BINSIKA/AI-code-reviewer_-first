import ast

class Detector(ast.NodeVisitor):
    def __init__(self):
        self.defined = set()
        self.used = set()

    def visit_Import(self, node):
        for n in node.names:
            self.defined.add(n.asname or n.name)

    def visit_Name(self, node):
        if isinstance(node.ctx, ast.Store):
            self.defined.add(node.id)
        if isinstance(node.ctx, ast.Load):
            self.used.add(node.id)

def analyze_code_errors(tree):
    d = Detector()
    d.visit(tree)
    builtins = {"print", "len", "range", "str", "int", "list", "dict", "sum"}
    unused = d.defined - d.used - builtins

    suggestions = [f"Variable '{v}' is defined but never used." for v in unused if not v.startswith("_")]
    return {"suggestions": suggestions}
