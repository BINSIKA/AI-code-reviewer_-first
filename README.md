**Milestone 1 – Syntax Validation & Parsing**

This project is a Python utility that validates Python source code using Python’s built-in AST (Abstract Syntax Tree) module. It checks whether the code is syntactically valid and, if so, returns a cleaned and standardized version of the code.

**Features**

  Validates Python syntax safely using ast.parse

  Identifies and reports syntax errors with line and offset information

  Automatically reformats valid code using ast.unparse

  Does not rely on any external libraries (pure Python standard library)

**How It Work**

  Takes Python source code as a string input

  Parses the source code into an Abstract Syntax Tree

  If parsing is successful:

   Returns a cleaned version of the source code

If parsing fails:

 Returns a clear syntax error message with location information
