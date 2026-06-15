import ast

class CodeParser:
    @staticmethod
    def extract_elements(code_string):
        """Extracts classes, functions, and their existing docstrings."""
        tree = ast.parse(code_string)
        elements = []
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                docstring = ast.get_docstring(node)
                # Reconstruct signature roughly
                elements.append({
                    "type": "class" if isinstance(node, ast.ClassDef) else "function",
                    "name": node.name,
                    "lineno": node.lineno,
                    "docstring": docstring,
                    "raw_code": ast.unparse(node) # Requires Python 3.9+
                })
        return elements