import ast

def validate_and_parse(source_code: str):
    
    try:
        
        tree = ast.parse(source_code)
        
        
        cleaned_code = ast.unparse(tree)
        
        return {
            "status": "success",
            "tree": tree,
            "cleaned_code": cleaned_code,
            "message": "Syntax is valid."
        }

    except SyntaxError as e:
        
        return {
            "status": "error",
            "message": f"Syntax Error: {e.msg}",
            "line": e.lineno,
            "offset": e.offset
        }


if __name__ == "__main__":
    test_code = "def hello(): print('world')"
    result = validate_and_parse(test_code)
    
    if result["status"] == "success":
        print("Success! Cleaned Code:\n", result["cleaned_code"])
    else:
        print(f"Failed:\n  {result['message']} at line {result['line']}")