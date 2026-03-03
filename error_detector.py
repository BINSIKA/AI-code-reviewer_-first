import ast

class ProjectErrorDetector(ast.NodeVisitor):
    def __init__(self):
        # List A: Collect every variable being defined (Store) [cite: 140]
        self.defined_vars = set()
        # List B: Collect every variable being used (Load) [cite: 141]
        self.used_vars = set()
        self.imports = []
        self.errors = []

    def visit_Import(self, node):
        """Alarm for standard imports like 'import os' [cite: 94, 96]"""
        for alias in node.names:
            self.imports.append(alias.name)
            # In a real review, we'd also track if these are used [cite: 72]
        self.generic_visit(node) # Keep walking the tree [cite: 101, 122]

    def visit_ImportFrom(self, node):
        """Alarm for 'from' imports like 'from datetime import ...' [cite: 94, 98]"""
        self.imports.append(node.module)
        self.generic_visit(node)

    def visit_Name(self, node):
        """Instruction Manual for checking variables [cite: 121]"""
        # .id is the literal name (e.g., 'score') [cite: 107, 128]
        # .ctx (Context) tells if it is created or used [cite: 108, 131]
        
        if isinstance(node.ctx, ast.Store):
            # The code is storing a value (Defining) [cite: 132, 134]
            self.defined_vars.add(node.id)
        elif isinstance(node.ctx, ast.Load):
            # The code is reading a value (Using) [cite: 136, 138]
            self.used_vars.add(node.id)
        
        self.generic_visit(node)

def analyze_code_errors(tree):
    detector = ProjectErrorDetector()
    detector.visit(tree)
    
    # Logic: Any variable in List A NOT in List B is unused [cite: 142]
    unused = detector.defined_vars - detector.used_vars
    
    report = {
        "unused_variables": list(unused),
        "total_imports": detector.imports,
        "suggestions": []
    }
    
    if unused:
        for var in unused:
            report["suggestions"].append(f"Variable '{var}' is defined but never used.")
            
    return report

# Integration with your Code Parser
if __name__ == "__main__":
    from code_parser import validate_and_parse
    
    test_student_code = """
import os
score = 100
total = 50
print(score)
"""
    # 1. Parse the code [cite: 88, 115]
    parse_result = validate_and_parse(test_student_code)
    
    if parse_result["status"] == "success":
        # 2. Detect errors using the 'Detective' [cite: 93, 114]
        analysis = analyze_code_errors(parse_result["tree"])
        print("--- Error Detection Report ---")
        for suggestion in analysis["suggestions"]:
            print(f"[-] {suggestion}")
        print(f"Total Imports Found: {analysis['total_imports']}")